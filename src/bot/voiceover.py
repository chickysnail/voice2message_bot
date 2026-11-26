"""Voiceover: text read out in the bot author's ElevenLabs voice.

Anyone who sends the bot plain text or a .txt file gets a "Voice it" button
under the usual reply. Everyone but admins has a quota of minutes of speech
per period; admins have no quota but confirm a voiceover first when it would
cost more than a set amount. Admins get a DM whenever someone else uses the
voice, and see what each of their own voiceovers cost.

The text to voice is the message the offer replies to, so nothing is kept
in memory between the offer and the tap.
"""

import asyncio
import contextlib
import logging
import math
import os
from collections.abc import AsyncIterator

from telegram import Bot, CallbackQuery, Document, InlineKeyboardMarkup, Message, Update, User
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from src.bot.keyboards import (
    CALLBACK_VOICEOVER_CANCEL,
    CALLBACK_VOICEOVER_CONFIRM,
    voiceover_confirm_keyboard,
    voiceover_keyboard,
)
from src.bot.locales import t
from src.bot.services.notifier import AdminNotifier
from src.bot.services.pricing import Pricing
from src.bot.services.tts import SpeechClient, SpeechResult, estimate_seconds, synthesize_voice
from src.bot.storage.statistics import KIND_SPEECH, StatisticsDB, UsageEvent
from src.bot.utils.retry import with_network_retry

logger = logging.getLogger(__name__)

# Bigger text files aren't voiced (1 MB is roughly 18 hours of speech).
TEXT_FILE_MAX_BYTES = 1024 * 1024
TEXT_FILE_EXTENSIONS = (".txt", ".md")

# usage_events.source for voiceovers.
SOURCE_TEXT = "text"
SOURCE_TEXT_FILE = "text_file"

# Uploading a long voice message can take a while.
UPLOAD_TIMEOUT_SECONDS = 300


def clock(seconds: float) -> str:
    """1:05, or 1:02:05 past an hour."""
    total = round(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def _count(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def _usd(amount: float) -> str:
    return f"${amount:.3f}" if amount < 0.1 else f"${amount:.2f}"


def is_text_file(document: Document) -> bool:
    name = (document.file_name or "").lower()
    return document.mime_type == "text/plain" or name.endswith(TEXT_FILE_EXTENSIONS)


def _decode(data: bytes) -> str | None:
    if b"\x00" in data:
        return None
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


@contextlib.asynccontextmanager
async def _recording(bot: Bot, chat_id: int) -> AsyncIterator[None]:
    """Show "recording voice..." in the chat until the block ends."""

    async def keep_showing() -> None:
        while True:
            with contextlib.suppress(Exception):
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)
            await asyncio.sleep(4)

    task = asyncio.create_task(keep_showing())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


async def _edit(
    query: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None = None
) -> None:
    try:
        await query.edit_message_text(text, reply_markup=markup)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            raise


class VoiceoverHandler:
    """Offers and makes voiceovers in one fixed voice."""

    def __init__(
        self,
        speech: SpeechClient,
        notifier: AdminNotifier,
        stats_db: StatisticsDB,
        admin_ids: list[int],
        pricing: Pricing,
        *,
        quota_minutes: float = 10,
        quota_days: int = 30,
        confirm_usd: float = 1.0,
        notify_admins: bool = True,
        ffmpeg_timeout: int = 120,
        file_download_timeout: int = 60,
    ) -> None:
        self._speech = speech
        self._notifier = notifier
        self._stats_db = stats_db
        self._admin_ids = set(admin_ids)
        self._pricing = pricing
        self._quota_minutes = quota_minutes
        self._quota_days = quota_days
        self._confirm_usd = confirm_usd
        self._notify_admins = notify_admins
        self._ffmpeg_timeout = ffmpeg_timeout
        self._file_download_timeout = file_download_timeout
        # Offer messages being voiced right now, so a second tap does nothing.
        self._busy: set[tuple[int, int]] = set()

    async def offer_for_file(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Answer a .txt file with the "Voice it" button."""
        message = update.message
        if not message or not message.document or not update.effective_user:
            return
        if not is_text_file(message.document):
            return
        lang = update.effective_user.language_code or "en"
        await message.reply_text(
            t("text_file_voiceover", lang),
            reply_markup=voiceover_keyboard(lang),
            do_quote=True,
        )

    async def handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Voice it / Yes, voice it / Cancel."""
        query = update.callback_query
        user = update.effective_user
        if not query or not user:
            return
        offer = query.message
        if not isinstance(offer, Message):
            await query.answer()
            return
        key = (offer.chat_id, offer.message_id)
        if key in self._busy:
            await query.answer()
            return
        self._busy.add(key)
        try:
            await query.answer()
            lang = user.language_code or "en"
            if query.data == CALLBACK_VOICEOVER_CANCEL:
                await _edit(query, t("voiceover_cancelled", lang))
                return
            await self._voice(
                query, offer, user, lang, context.bot,
                confirmed=query.data == CALLBACK_VOICEOVER_CONFIRM,
            )
        finally:
            self._busy.discard(key)

    async def _voice(
        self,
        query: CallbackQuery,
        offer: Message,
        user: User,
        lang: str,
        bot: Bot,
        *,
        confirmed: bool,
    ) -> None:
        source = offer.reply_to_message
        found = await self._source_text(query, source, lang)
        if found is None or source is None:
            return
        text, source_kind = found
        estimate = estimate_seconds(len(text))
        is_admin = user.id in self._admin_ids

        used = 0.0
        if is_admin:
            cost = self._pricing.speech_cost(len(text))
            if not confirmed and cost > self._confirm_usd:
                await _edit(
                    query,
                    t("voiceover_confirm", lang, duration=clock(estimate),
                      chars=_count(len(text)), cost=_usd(cost)),
                    voiceover_confirm_keyboard(lang),
                )
                return
        else:
            used = await self._stats_db.get_speech_seconds(user.id, self._quota_days)
            left = self._quota_minutes * 60 - used
            if estimate > left:
                await _edit(query, t(
                    "voiceover_limit", lang,
                    quota=f"{self._quota_minutes:g}", days=self._quota_days,
                    left=int(max(left, 0) // 60), need=math.ceil(estimate / 60),
                ))
                return

        await _edit(query, t("voiceover_working", lang))
        try:
            async with _recording(bot, offer.chat_id):
                result = await synthesize_voice(
                    self._speech, text, ffmpeg_timeout=self._ffmpeg_timeout
                )
                try:
                    await self._send(source, result)
                finally:
                    os.remove(result.path)
        except Exception as e:
            logger.exception("Voiceover failed for user %d", user.id)
            await _edit(query, t("voiceover_failed", lang))
            await self._notifier.notify_error(
                "Voiceover failed", username=user.username, error_detail=str(e)[:300]
            )
            return

        cost = self._pricing.speech_cost(result.chars)
        await self._stats_db.record_event(UsageEvent(
            user_id=user.id,
            username=user.username,
            kind=KIND_SPEECH,
            source=source_kind,
            audio_seconds=result.seconds,
            upload_bytes=len(text.encode("utf-8")),
            output_chars=result.chars,
            cost_usd=cost,
        ))

        if is_admin:
            await _edit(query, t(
                "voiceover_done_admin", lang,
                duration=clock(result.seconds), chars=_count(result.chars),
                credits=_count(result.credits) if result.credits is not None else "—",
                cost=_usd(cost),
            ))
            return
        used += result.seconds
        await _edit(query, t(
            "voiceover_done", lang,
            left=int(max(self._quota_minutes * 60 - used, 0) // 60),
            quota=f"{self._quota_minutes:g}", days=self._quota_days,
        ))
        if self._notify_admins:
            await self._report(user, result, cost, used)

    async def _source_text(
        self, query: CallbackQuery, source: Message | None, lang: str
    ) -> tuple[str, str] | None:
        """The text to voice and where it came from; None after telling the user why not."""
        if source is not None and source.text and source.text.strip():
            return source.text.strip(), SOURCE_TEXT
        document = source.document if source is not None else None
        if document is None or not is_text_file(document):
            await _edit(query, t("voiceover_no_text", lang))
            return None
        if (document.file_size or 0) > TEXT_FILE_MAX_BYTES:
            await _edit(query, t(
                "voiceover_file_too_large", lang, max_mb=TEXT_FILE_MAX_BYTES // (1024 * 1024)
            ))
            return None
        try:
            tg_file = await with_network_retry(
                lambda: document.get_file(read_timeout=self._file_download_timeout),
                timeout=self._file_download_timeout,
                description="get_file",
            )
            data = bytes(await with_network_retry(
                lambda: tg_file.download_as_bytearray(),
                timeout=self._file_download_timeout,
                description="download_as_bytearray",
            ))
        except Exception:
            logger.exception("Couldn't download a text file to voice")
            await _edit(query, t("voiceover_failed", lang))
            return None
        text = _decode(data)
        if text is None or not text.strip():
            await _edit(query, t("voiceover_file_unreadable", lang))
            return None
        return text.strip(), SOURCE_TEXT_FILE

    async def _send(self, source: Message, result: SpeechResult) -> None:
        """Reply to the voiced message with the speech, as a voice message.

        Users who only accept voice messages from contacts get an audio file.
        """
        with open(result.path, "rb") as f:
            try:
                await source.reply_voice(
                    voice=f,
                    duration=round(result.seconds),
                    do_quote=True,
                    write_timeout=UPLOAD_TIMEOUT_SECONDS,
                )
            except BadRequest as e:
                if "voice_messages_forbidden" not in str(e).lower():
                    raise
                f.seek(0)
                await source.reply_audio(
                    audio=f,
                    duration=round(result.seconds),
                    filename="voiceover.ogg",
                    do_quote=True,
                    write_timeout=UPLOAD_TIMEOUT_SECONDS,
                )

    async def _report(
        self, user: User, result: SpeechResult, cost: float, used_seconds: float
    ) -> None:
        """Tell admins someone used the voice. Never includes the text."""
        handle = f"@{user.username}, " if user.username else ""
        credits = f" · {_count(result.credits)} credits" if result.credits is not None else ""
        await self._notifier.notify_admins(
            f"🗣 Your voice was used by {user.full_name} ({handle}ID {user.id})\n"
            f"{clock(result.seconds)} of audio · {_count(result.chars)} chars"
            f"{credits} · ≈ {_usd(cost)}\n"
            f"Last {self._quota_days} days: {clock(used_seconds)} of "
            f"{clock(self._quota_minutes * 60)}"
        )
