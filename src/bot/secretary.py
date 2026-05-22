"""Secretary mode — transcribe voice messages in users' DM chats."""

import asyncio
import html
import io
import logging
import os
import tempfile
import uuid

from telegram import Bot, BusinessConnection, Message, Update, User
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.bot.keyboards import (
    CALLBACK_SEC_EXPORT_SRT,
    CALLBACK_SEC_EXPORT_TXT,
    CALLBACK_SEC_SAVEFILE,
    CALLBACK_SEC_SUMMARIZE,
    CALLBACK_SEC_TRANSCRIBE,
    secretary_file_format_keyboard,
    secretary_post_transcription_keyboard,
    secretary_transcribe_keyboard,
)
from src.bot.locales import t
from src.bot.services.audio import extract_audio, get_audio_duration
from src.bot.services.export import generate_srt, generate_txt
from src.bot.services.notifier import AdminNotifier
from src.bot.services.summarization import SummarizationClient
from src.bot.services.transcription import EmptyTranscriptionError, TranscriptionClient
from src.bot.storage.statistics import StatisticsDB
from src.bot.storage.transcription_store import TranscriptionStore
from src.bot.utils.text import format_duration, split_message

logger = logging.getLogger(__name__)


class SecretaryHandler:
    """Handles business (secretary) messages."""

    def __init__(
        self,
        transcriber: TranscriptionClient,
        summarizer: SummarizationClient,
        notifier: AdminNotifier,
        store: TranscriptionStore,
        stats_db: StatisticsDB,
        max_audio_duration: int,
        transcription_timeout: int = 900,
        ffmpeg_timeout: int = 120,
        file_download_timeout: int = 60,
    ) -> None:
        self._transcriber = transcriber
        self._summarizer = summarizer
        self._notifier = notifier
        self._store = store
        self._stats_db = stats_db
        self._max_audio_duration = max_audio_duration
        self._transcription_timeout = transcription_timeout
        self._ffmpeg_timeout = ffmpeg_timeout
        self._file_download_timeout = file_download_timeout
        # business_connection_id -> BusinessConnection
        self._connections: dict[str, BusinessConnection] = {}

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def handle_business_connection(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle a user connecting/disconnecting the bot as secretary."""
        conn = update.business_connection
        if conn is None:
            return

        user = conn.user
        if conn.is_enabled:
            self._connections[conn.id] = conn
            logger.info(
                "Secretary connected: user %s (%d), connection %s",
                user.username, user.id, conn.id,
            )
            await self._notifier.notify_secretary_event(
                "connected", user.username, user.id
            )
        else:
            self._connections.pop(conn.id, None)
            logger.info(
                "Secretary disconnected: user %s (%d), connection %s",
                user.username, user.id, conn.id,
            )
            await self._notifier.notify_secretary_event(
                "disconnected", user.username, user.id
            )

    # ------------------------------------------------------------------
    # Business message handling
    # ------------------------------------------------------------------

    async def handle_business_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle an incoming business message — auto or manual mode."""
        message = update.business_message
        if message is None or message.business_connection_id is None:
            return

        biz_conn_id = message.business_connection_id

        # Only handle voice messages and video notes
        if not message.voice and not message.video_note:
            return

        # Determine the bot-owner user from the connection
        conn = self._connections.get(biz_conn_id)
        if conn is None:
            # Try to fetch connection info via API
            try:
                conn = await context.bot.get_business_connection(biz_conn_id)
                self._connections[biz_conn_id] = conn
            except Exception:
                logger.warning("Could not fetch business connection %s", biz_conn_id)
                return

        owner_user = conn.user
        mode = await self._stats_db.get_secretary_mode(owner_user.id)
        lang = owner_user.language_code or "en"

        if mode == "manual":
            await self._send_manual_prompt(
                context.bot, message, biz_conn_id, lang
            )
        else:
            await self._auto_transcribe(
                context.bot, message, biz_conn_id, owner_user, lang
            )

    # ------------------------------------------------------------------
    # Auto mode
    # ------------------------------------------------------------------

    async def _auto_transcribe(
        self,
        bot: Bot,
        message: Message,
        biz_conn_id: str,
        owner_user: User,
        lang: str,
    ) -> None:
        """Transcribe and reply automatically."""

        chat_id = message.chat.id
        prefix = t("secretary_prefix", lang)

        processing_msg = await bot.send_message(
            chat_id=chat_id,
            text=t("transcribing", lang),
            reply_to_message_id=message.message_id,
            business_connection_id=biz_conn_id,
        )

        await self._do_transcription(
            bot, message, processing_msg, biz_conn_id,
            owner_user, lang, prefix,
        )

    # ------------------------------------------------------------------
    # Manual mode
    # ------------------------------------------------------------------

    async def _send_manual_prompt(
        self,
        bot: Bot,
        message: Message,
        biz_conn_id: str,
        lang: str,
    ) -> None:
        """Send a prompt with a Transcribe button."""
        chat_id = message.chat.id
        duration = message.voice.duration if message.voice else (
            message.video_note.duration if message.video_note else 0
        )
        dur_str = format_duration(duration) if duration else "?"

        await bot.send_message(
            chat_id=chat_id,
            text=t("secretary_manual_prompt", lang, duration=dur_str),
            reply_to_message_id=message.message_id,
            reply_markup=secretary_transcribe_keyboard(
                message.message_id, biz_conn_id
            ),
            business_connection_id=biz_conn_id,
        )

    async def handle_transcribe_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle the Transcribe button press in manual mode."""
        query = update.callback_query
        if not query or not query.data:
            return

        parts = query.data.split(":")
        if len(parts) != 3 or parts[0] != CALLBACK_SEC_TRANSCRIBE:
            return

        await query.answer()

        try:
            int(parts[1])  # validate message ID is numeric
        except ValueError:
            return
        biz_conn_id = parts[2]

        conn = self._connections.get(biz_conn_id)
        if conn is None:
            try:
                conn = await context.bot.get_business_connection(biz_conn_id)
                self._connections[biz_conn_id] = conn
            except Exception:
                logger.warning("Could not fetch business connection %s", biz_conn_id)
                return

        owner_user = conn.user
        lang = owner_user.language_code or "en"
        prefix = t("secretary_prefix", lang)

        # The callback query message is the prompt we sent
        prompt_msg = query.message
        if prompt_msg is None:
            return

        # Edit prompt to "Transcribing..."
        await context.bot.edit_message_text(
            chat_id=prompt_msg.chat.id,
            message_id=prompt_msg.message_id,
            text=t("transcribing", lang),
            business_connection_id=biz_conn_id,
        )

        # Get the original voice message (the one the prompt replied to)
        original_message = prompt_msg.reply_to_message
        if original_message is None:
            await context.bot.edit_message_text(
                chat_id=prompt_msg.chat.id,
                message_id=prompt_msg.message_id,
                text=t("something_went_wrong", lang),
                business_connection_id=biz_conn_id,
            )
            return

        await self._do_transcription(
            context.bot, original_message, prompt_msg, biz_conn_id,
            owner_user, lang, prefix,
        )

    # ------------------------------------------------------------------
    # Post-transcription callbacks (summarize, save file, export)
    # ------------------------------------------------------------------

    async def handle_post_transcription_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle Summarize / Save as file / Export buttons for secretary transcriptions."""
        query = update.callback_query
        if not query or not query.data:
            return

        parts = query.data.split(":")
        if len(parts) != 3:
            return

        action = parts[0]
        try:
            original_message_id = int(parts[1])
            owner_user_id = int(parts[2])
        except ValueError:
            return

        await query.answer()

        user = update.effective_user
        lang = user.language_code or "en" if user else "en"

        if action == CALLBACK_SEC_SUMMARIZE:
            await self._handle_secretary_summarize(
                query, owner_user_id, original_message_id, lang
            )
        elif action == CALLBACK_SEC_SAVEFILE:
            await self._handle_secretary_save_file(
                query, owner_user_id, original_message_id, lang
            )
        elif action in (CALLBACK_SEC_EXPORT_TXT, CALLBACK_SEC_EXPORT_SRT):
            await self._handle_secretary_export(
                query, owner_user_id, original_message_id, action, lang
            )

    async def _handle_secretary_summarize(
        self,
        query: object,
        owner_user_id: int,
        original_message_id: int,
        lang: str,
    ) -> None:
        transcript = self._store.get(owner_user_id, original_message_id)
        if transcript is None:
            await query.edit_message_reply_markup(reply_markup=None)
            if query.message:
                await query.message.reply_text(t("transcription_expired", lang))
            return

        await query.edit_message_reply_markup(reply_markup=None)

        try:
            summary = self._summarizer.summarize(transcript)
        except RuntimeError as e:
            if query.message:
                await query.message.reply_text(t("something_went_wrong", lang))
            await self._notifier.notify_error(
                "Secretary: summarization failed",
                username=f"owner:{owner_user_id}",
                error_detail=str(e),
            )
            return

        if query.message:
            for chunk in split_message(summary):
                await query.message.reply_text(chunk)

        logger.info(
            "Secretary: summarized transcription for owner %d", owner_user_id
        )

    async def _handle_secretary_save_file(
        self,
        query: object,
        owner_user_id: int,
        original_message_id: int,
        lang: str,
    ) -> None:
        transcript = self._store.get(owner_user_id, original_message_id)
        if transcript is None:
            await query.edit_message_reply_markup(reply_markup=None)
            if query.message:
                await query.message.reply_text(t("transcription_expired", lang))
            return

        await query.edit_message_reply_markup(
            reply_markup=secretary_file_format_keyboard(
                original_message_id, owner_user_id
            ),
        )

    async def _handle_secretary_export(
        self,
        query: object,
        owner_user_id: int,
        original_message_id: int,
        action: str,
        lang: str,
    ) -> None:
        transcript = self._store.get(owner_user_id, original_message_id)
        if transcript is None:
            await query.edit_message_reply_markup(reply_markup=None)
            if query.message:
                await query.message.reply_text(t("transcription_expired", lang))
            return

        await query.edit_message_reply_markup(reply_markup=None)

        if action == CALLBACK_SEC_EXPORT_TXT:
            content = generate_txt(transcript)
            filename = "transcription.txt"
        else:
            words = self._store.get_words(owner_user_id, original_message_id)
            if not words:
                if query.message:
                    await query.message.reply_text(t("srt_no_words", lang))
                return
            content = generate_srt(words)
            if not content:
                if query.message:
                    await query.message.reply_text(t("srt_no_timed", lang))
                return
            filename = "transcription.srt"

        file_bytes = b"\xef\xbb\xbf" + content.encode("utf-8")
        if query.message:
            await query.message.reply_document(
                document=io.BytesIO(file_bytes),
                filename=filename,
            )

        logger.info(
            "Secretary: exported %s for owner %d", filename, owner_user_id
        )

    # ------------------------------------------------------------------
    # Shared transcription logic
    # ------------------------------------------------------------------

    async def _do_transcription(
        self,
        bot: Bot,
        message: Message,
        status_msg: Message,
        biz_conn_id: str,
        owner_user: User,
        lang: str,
        prefix: str,
    ) -> None:
        """Download, transcribe, and send the result."""

        chat_id = message.chat.id
        file_id: str | None = None
        duration: int | None = None
        is_video = False
        file_type = "unknown"

        if message.voice:
            file_id = message.voice.file_id
            duration = message.voice.duration
            file_type = "voice message"
        elif message.video_note:
            file_id = message.video_note.file_id
            duration = message.video_note.duration
            is_video = True
            file_type = "video note"

        if not file_id:
            return

        if duration and duration > self._max_audio_duration:
            max_min = self._max_audio_duration // 60
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=(
                    f"{prefix}\n"
                    + t('audio_too_long', lang,
                        duration=format_duration(duration),
                        max_min=max_min)
                ),
                business_connection_id=biz_conn_id,
            )
            return

        file_path: str | None = None
        audio_path: str | None = None
        try:
            # Download file
            try:
                tg_file = await asyncio.wait_for(
                    bot.get_file(file_id),
                    timeout=self._file_download_timeout,
                )
            except TimeoutError:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=f"{prefix}\n{t('download_timeout', lang)}",
                    business_connection_id=biz_conn_id,
                )
                await self._notifier.notify_error(
                    "Secretary: file download timeout",
                    username=owner_user.username,
                    error_detail=f"{file_type}, timed out after {self._file_download_timeout}s",
                )
                return

            ext = (tg_file.file_path or "").rsplit(".", 1)[-1] if tg_file.file_path else "ogg"
            file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.{ext}")
            try:
                await asyncio.wait_for(
                    tg_file.download_to_drive(custom_path=file_path),
                    timeout=self._file_download_timeout,
                )
            except TimeoutError:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=f"{prefix}\n{t('download_timeout', lang)}",
                    business_connection_id=biz_conn_id,
                )
                return

            # Extract audio from video if needed
            if is_video:
                try:
                    audio_path = await extract_audio(
                        file_path, timeout=self._ffmpeg_timeout
                    )
                except RuntimeError as e:
                    msg_key = (
                        "video_timeout"
                        if "timed out" in str(e).lower()
                        else "extraction_failed"
                    )
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_msg.message_id,
                        text=f"{prefix}\n{t(msg_key, lang)}",
                        business_connection_id=biz_conn_id,
                    )
                    await self._notifier.notify_error(
                        "Secretary: audio extraction failed",
                        username=owner_user.username,
                        error_detail=str(e),
                    )
                    return
            else:
                audio_path = file_path

            # Get actual duration if not provided
            if duration is None:
                measured = await get_audio_duration(audio_path)
                if measured is not None:
                    duration = int(measured)
                    if duration > self._max_audio_duration:
                        max_min = self._max_audio_duration // 60
                        await bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=status_msg.message_id,
                            text=(
                                f"{prefix}\n"
                                + t('audio_too_long', lang,
                                    duration=format_duration(duration),
                                    max_min=max_min)
                            ),
                            business_connection_id=biz_conn_id,
                        )
                        return

            # Transcribe (with one retry on timeout)
            transcript = None
            for attempt in range(2):
                try:
                    transcript = await asyncio.wait_for(
                        asyncio.to_thread(
                            self._transcriber.transcribe, audio_path
                        ),
                        timeout=self._transcription_timeout,
                    )
                    break
                except TimeoutError:
                    if attempt == 0:
                        logger.warning(
                            "Secretary transcription timed out for user %s, retrying",
                            owner_user.username,
                        )
                        continue
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_msg.message_id,
                        text=f"{prefix}\n{t('transcription_timeout', lang)}",
                        business_connection_id=biz_conn_id,
                    )
                    await self._notifier.notify_error(
                        "Secretary: transcription timeout",
                        username=owner_user.username,
                        error_detail=f"Timed out after {self._transcription_timeout}s",
                        audio_duration=duration,
                    )
                    return
                except EmptyTranscriptionError:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_msg.message_id,
                        text=f"{prefix}\n{t('no_speech', lang)}",
                        business_connection_id=biz_conn_id,
                    )
                    return
                except RuntimeError as e:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_msg.message_id,
                        text=f"{prefix}\n{t('something_went_wrong', lang)}",
                        business_connection_id=biz_conn_id,
                    )
                    await self._notifier.notify_error(
                        "Secretary: transcription failed",
                        username=owner_user.username,
                        error_detail=str(e),
                        audio_duration=duration,
                    )
                    return

            if transcript is None:
                return

            # Store transcription for summarize/export actions
            self._store.save(
                owner_user.id, message.message_id,
                transcript.text, transcript.words,
            )

            # Record secretary usage
            await self._stats_db.record_secretary_usage(
                owner_user.id, owner_user.username, duration or 0
            )

            # Send transcription in an expandable blockquote so it
            # takes less visual space in the chat.
            keyboard = secretary_post_transcription_keyboard(
                message.message_id, owner_user.id
            )
            escaped_prefix = html.escape(prefix)
            escaped_text = html.escape(transcript.text)

            # Split the escaped text first, then wrap each chunk in
            # blockquote tags so HTML is never broken by the splitter.
            bq_overhead = len("<blockquote expandable></blockquote>")
            first_overhead = len(escaped_prefix) + 1 + bq_overhead
            raw_chunks = split_message(
                escaped_text, max_length=4096 - first_overhead
            )
            for i, chunk in enumerate(raw_chunks):
                is_last = i == len(raw_chunks) - 1
                text = (
                    f"{escaped_prefix}\n"
                    f"<blockquote expandable>{chunk}</blockquote>"
                    if i == 0
                    else f"<blockquote expandable>{chunk}</blockquote>"
                )
                if i == 0:
                    await bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_msg.message_id,
                        text=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard if is_last else None,
                        business_connection_id=biz_conn_id,
                    )
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=keyboard if is_last else None,
                        business_connection_id=biz_conn_id,
                    )

            logger.info(
                "Secretary transcribed %s for user %s (%d), duration=%s",
                file_type, owner_user.username, owner_user.id,
                format_duration(duration) if duration else "unknown",
            )

        except Exception as e:
            logger.exception(
                "Secretary: unexpected error for user %d", owner_user.id
            )
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=f"{prefix}\n{t('something_went_wrong', lang)}",
                    business_connection_id=biz_conn_id,
                )
            except Exception:
                pass
            await self._notifier.notify_error(
                "Secretary: unexpected error",
                username=owner_user.username,
                error_detail=str(e),
                audio_duration=duration,
            )
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            if audio_path and audio_path != file_path and os.path.exists(audio_path):
                os.remove(audio_path)
