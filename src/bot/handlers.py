import asyncio
import io
import logging
import os
import tempfile
import uuid
from pathlib import Path

from telegram import InputMediaPhoto, LabeledPrice, Update
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from src.bot.keyboards import (
    CALLBACK_EXPORT_SRT,
    CALLBACK_EXPORT_TXT,
    CALLBACK_SAVE_FILE,
    CALLBACK_SECRETARY_SETUP,
    CALLBACK_SUMMARIZE,
    donation_keyboard,
    file_format_keyboard,
    post_transcription_keyboard,
    secretary_settings_keyboard,
    secretary_setup_keyboard,
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

_ASSETS_DIR = Path(__file__).parent / "assets"
SECRETARY_SETUP_IMAGES = [
    _ASSETS_DIR / f"secretary_setup_{i}.jpg" for i in (1, 2, 3)
]
SECRETARY_EXPLAINER_VIDEO = _ASSETS_DIR / "secretary_explainer.mp4"

# Show a soft donation prompt on the processing message when the
# audio is longer than this threshold (seconds).
DONATION_DURATION_THRESHOLD = 60


def _secretary_setup_media() -> list[InputMediaPhoto]:
    """Build the 3-image album that illustrates secretary setup."""
    return [
        InputMediaPhoto(media=path.read_bytes())
        for path in SECRETARY_SETUP_IMAGES
    ]


class BotHandlers:
    """Telegram bot command and message handlers."""

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

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return
        user = update.effective_user
        lang = user.language_code or "en"
        connected = await self._stats_db.is_user_secretary_connected(user.id)
        keyboard = (
            secretary_settings_keyboard(lang) if connected
            else secretary_setup_keyboard(lang)
        )
        await update.message.reply_text(
            t("greeting", lang, user=user.mention_html()),
            parse_mode=ParseMode.HTML,
        )
        await update.message.reply_text(
            t("secretary_promo", lang),
            reply_markup=keyboard,
        )
        await update.message.reply_video(
            video=SECRETARY_EXPLAINER_VIDEO.read_bytes(),
        )

    async def help_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not update.message:
            return
        lang = (
            update.effective_user.language_code
            if update.effective_user
            else "en"
        ) or "en"
        await update.message.reply_text(t("help", lang))

    async def handle_text(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Nudge users who send plain text instead of audio."""
        if not update.message or not update.effective_user:
            return
        lang = update.effective_user.language_code or "en"
        await update.message.reply_text(t("text_nudge", lang))

    async def handle_audio(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle voice messages, video notes, audio files, and documents."""
        if not update.message or not update.effective_user:
            return

        user = update.effective_user
        message = update.message

        # Determine file_id and duration from the incoming message
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
        elif message.audio:
            file_id = message.audio.file_id
            duration = message.audio.duration
            file_type = "audio file"
        elif message.video:
            file_id = message.video.file_id
            duration = message.video.duration
            is_video = True
            file_type = "video"
        elif message.document:
            file_id = message.document.file_id
            duration = None
            file_type = "document"

        if not file_id:
            return

        # Check duration limit
        lang = user.language_code or "en"

        if duration and duration > self._max_audio_duration:
            max_min = self._max_audio_duration // 60
            await message.reply_text(
                t("audio_too_long", lang,
                  duration=format_duration(duration), max_min=max_min)
            )
            await self._notifier.notify_error(
                "Audio too long",
                username=user.username,
                error_detail=(
                    f"{file_type}, {format_duration(duration)}"
                ),
                audio_duration=duration,
            )
            return

        # Send a "processing" message and show typing indicator
        await context.bot.send_chat_action(
            chat_id=message.chat_id, action=ChatAction.TYPING
        )
        show_donation = bool(duration and duration >= DONATION_DURATION_THRESHOLD)
        processing_text = (
            t("transcribing_donate", lang)
            if show_donation
            else t("transcribing", lang)
        )
        processing_msg = await message.reply_text(
            processing_text,
            reply_markup=donation_keyboard(lang) if show_donation else None,
        )

        file_path: str | None = None
        audio_path: str | None = None
        try:
            # Download the file
            try:
                tg_file = await asyncio.wait_for(
                    context.bot.get_file(file_id),
                    timeout=self._file_download_timeout,
                )
            except TimeoutError:
                await processing_msg.edit_text(
                    t("download_timeout", lang)
                )
                await self._notifier.notify_error(
                    "File download timeout",
                    username=user.username,
                    error_detail=(
                        f"{file_type}, timed out after "
                        f"{self._file_download_timeout}s"
                    ),
                )
                await self._stats_db.record_error(
                    "File download timeout", user.username,
                    f"Timed out after {self._file_download_timeout}s",
                )
                return
            except BadRequest as e:
                if "file is too big" in str(e).lower():
                    await processing_msg.edit_text(
                        t("file_too_large", lang)
                    )
                    await self._notifier.notify_error(
                        "File too large",
                        username=user.username,
                        error_detail=f"{file_type}, exceeded 20 MB",
                    )
                    return
                raise
            ext = (tg_file.file_path or "").rsplit(".", 1)[-1] if tg_file.file_path else "ogg"
            file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.{ext}")
            try:
                await asyncio.wait_for(
                    tg_file.download_to_drive(custom_path=file_path),
                    timeout=self._file_download_timeout,
                )
            except TimeoutError:
                await processing_msg.edit_text(
                    t("download_timeout", lang)
                )
                await self._notifier.notify_error(
                    "File download timeout",
                    username=user.username,
                    error_detail=(
                        f"{file_type}, download timed out after "
                        f"{self._file_download_timeout}s"
                    ),
                )
                await self._stats_db.record_error(
                    "File download timeout", user.username,
                    f"Timed out after {self._file_download_timeout}s",
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
                    await processing_msg.edit_text(t(msg_key, lang))
                    await self._notifier.notify_error(
                        "Audio extraction failed",
                        username=user.username,
                        error_detail=str(e),
                    )
                    await self._stats_db.record_error(
                        "Audio extraction", user.username, str(e)
                    )
                    return
            else:
                audio_path = file_path

            # Get actual duration if not provided by Telegram
            if duration is None:
                measured = await get_audio_duration(audio_path)
                if measured is not None:
                    duration = int(measured)
                    if duration > self._max_audio_duration:
                        max_min = self._max_audio_duration // 60
                        await processing_msg.edit_text(
                            t("audio_too_long", lang,
                              duration=format_duration(duration),
                              max_min=max_min)
                        )
                        await self._notifier.notify_error(
                            "Audio too long",
                            username=user.username,
                            error_detail=(
                                f"{file_type}, {format_duration(duration)}"
                            ),
                            audio_duration=duration,
                        )
                        return

            # Transcribe (with one automatic retry on timeout)
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
                            "Transcription timed out for user %s, retrying",
                            user.username,
                        )
                        continue
                    await processing_msg.edit_text(
                        t("transcription_timeout", lang)
                    )
                    await self._notifier.notify_error(
                        "Transcription timeout",
                        username=user.username,
                        error_detail=(
                            "Timed out after "
                            f"{self._transcription_timeout}s "
                            "(2 attempts)"
                        ),
                        audio_duration=duration,
                    )
                    await self._stats_db.record_error(
                        "Transcription timeout", user.username,
                        f"Timed out after {self._transcription_timeout}s"
                        " (2 attempts)",
                    )
                    return
                except EmptyTranscriptionError as e:
                    await processing_msg.edit_text(
                        t("no_speech", lang)
                    )
                    await self._notifier.notify_error(
                        "Transcription failed",
                        username=user.username,
                        error_detail=str(e),
                        audio_duration=duration,
                    )
                    await self._stats_db.record_error(
                        "Transcription (empty)", user.username, str(e)
                    )
                    return
                except RuntimeError as e:
                    await processing_msg.edit_text(
                        t("something_went_wrong", lang)
                    )
                    await self._notifier.notify_error(
                        "Transcription failed",
                        username=user.username,
                        error_detail=str(e),
                        audio_duration=duration,
                    )
                    await self._stats_db.record_error(
                        "Transcription", user.username, str(e)
                    )
                    return
            if transcript is None:
                return

            # Store the transcription for later actions (summarize, export)
            original_message_id = message.message_id
            self._store.save(
                user.id, original_message_id,
                transcript.text, transcript.words,
            )

            # Record usage statistics
            await self._stats_db.record_usage(
                user.id, user.username, duration or 0
            )

            # Send the transcription
            await processing_msg.delete()
            chunks = split_message(transcript.text)
            for i, chunk in enumerate(chunks):
                is_last = i == len(chunks) - 1
                if is_last:
                    await message.reply_text(
                        chunk,
                        reply_markup=post_transcription_keyboard(original_message_id, lang),
                    )
                else:
                    await message.reply_text(chunk)

            logger.info(
                "Transcribed audio for user %s (%d), duration=%s",
                user.username,
                user.id,
                format_duration(duration) if duration else "unknown",
            )

        except Exception as e:
            logger.exception("Unexpected error processing audio for user %d", user.id)
            try:
                await processing_msg.edit_text(
                    t("something_went_wrong", lang)
                )
            except Exception:
                pass
            await self._notifier.notify_error(
                "Unexpected error",
                username=user.username,
                error_detail=str(e),
                audio_duration=duration,
            )
            await self._stats_db.record_error(
                "Unexpected error", user.username, str(e)
            )
        finally:
            # Clean up temp files
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            if audio_path and audio_path != file_path and os.path.exists(audio_path):
                os.remove(audio_path)

    async def handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline keyboard button presses."""
        query = update.callback_query
        if not query or not query.data or not update.effective_user:
            return

        await query.answer()

        data = query.data
        user = update.effective_user
        lang = user.language_code or "en"

        # Handle secretary setup button (no colon, single token)
        if data == CALLBACK_SECRETARY_SETUP:
            connected = await self._stats_db.is_user_secretary_connected(
                user.id
            )
            key = "secretary_connected" if connected else "secretary_setup"
            await query.edit_message_text(
                t(key, lang),
                parse_mode=ParseMode.HTML,
            )
            if not connected:
                await query.message.reply_media_group(
                    _secretary_setup_media()
                )
            return

        parts = data.split(":")
        if len(parts) != 2:
            return

        action = parts[0]
        try:
            original_message_id = int(parts[1])
        except ValueError:
            return

        if action == CALLBACK_SUMMARIZE:
            await self._handle_summarize(query, user, original_message_id)
        elif action == CALLBACK_SAVE_FILE:
            await self._handle_save_file(query, user, original_message_id)
        elif action in (CALLBACK_EXPORT_TXT, CALLBACK_EXPORT_SRT):
            await self._handle_export(query, user, original_message_id, action)

    async def _handle_summarize(
        self,
        query: object,
        user: object,
        original_message_id: int,
    ) -> None:
        """Handle the Summarize button press."""
        from telegram import CallbackQuery, User

        assert isinstance(query, CallbackQuery)
        assert isinstance(user, User)

        lang = user.language_code or "en"

        transcript = self._store.get(user.id, original_message_id)
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
                await query.message.reply_text(
                    t("something_went_wrong", lang)
                )
            await self._notifier.notify_error(
                "Summarization failed",
                username=user.username,
                error_detail=str(e),
            )
            await self._stats_db.record_error(
                "Summarization", user.username, str(e)
            )
            return

        if query.message:
            for chunk in split_message(summary):
                await query.message.reply_text(chunk)

        logger.info("Summarized transcription for user %s (%d)", user.username, user.id)

    async def _handle_save_file(
        self,
        query: object,
        user: object,
        original_message_id: int,
    ) -> None:
        """Handle the Save as file button — show format options."""
        from telegram import CallbackQuery, User

        assert isinstance(query, CallbackQuery)
        assert isinstance(user, User)

        lang = user.language_code or "en"

        transcript = self._store.get(user.id, original_message_id)
        if transcript is None:
            await query.edit_message_reply_markup(reply_markup=None)
            if query.message:
                await query.message.reply_text(t("transcription_expired", lang))
            return

        await query.edit_message_reply_markup(
            reply_markup=file_format_keyboard(original_message_id),
        )

    async def _handle_export(
        self,
        query: object,
        user: object,
        original_message_id: int,
        action: str,
    ) -> None:
        """Handle a file format selection (TXT or SRT)."""
        from telegram import CallbackQuery, User

        assert isinstance(query, CallbackQuery)
        assert isinstance(user, User)

        lang = user.language_code or "en"

        transcript = self._store.get(user.id, original_message_id)
        if transcript is None:
            await query.edit_message_reply_markup(reply_markup=None)
            if query.message:
                await query.message.reply_text(t("transcription_expired", lang))
            return

        await query.edit_message_reply_markup(reply_markup=None)

        if action == CALLBACK_EXPORT_TXT:
            content = generate_txt(transcript)
            filename = "transcription.txt"
        else:
            words = self._store.get_words(user.id, original_message_id)
            if not words:
                if query.message:
                    await query.message.reply_text(
                        t("srt_no_words", lang)
                    )
                return
            content = generate_srt(words)
            if not content:
                if query.message:
                    await query.message.reply_text(
                        t("srt_no_timed", lang)
                    )
                return
            filename = "transcription.srt"

        file_bytes = b"\xef\xbb\xbf" + content.encode("utf-8")
        if query.message:
            await query.message.reply_document(
                document=io.BytesIO(file_bytes),
                filename=filename,
            )

        logger.info(
            "Exported %s for user %s (%d)", filename, user.username, user.id
        )

    async def secretary_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /secretary command — show setup or connected status."""
        if not update.message or not update.effective_user:
            return

        user = update.effective_user
        lang = user.language_code or "en"

        connected = await self._stats_db.is_user_secretary_connected(user.id)
        key = "secretary_connected" if connected else "secretary_setup"
        await update.message.reply_text(
            t(key, lang),
            parse_mode=ParseMode.HTML,
        )
        # Show the visual setup guide below the text for users who
        # haven't connected the bot yet.
        if not connected:
            await update.message.reply_media_group(_secretary_setup_media())

    async def broadcast_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Admin-only: announce secretary mode to all known users.

        `/broadcast` shows a preview and the recipient count.
        `/broadcast confirm` sends it.
        """
        if not update.message or not update.effective_user:
            return
        if update.effective_user.id not in self._admin_ids:
            return

        user_ids = await self._stats_db.get_all_user_ids()
        args = context.args or []
        confirm = bool(args) and args[0] == "confirm"

        if not confirm:
            await update.message.reply_text(
                f"📢 Preview below — will be sent to {len(user_ids)} users.\n"
                "Send /broadcast confirm to send it."
            )
            await update.message.reply_text(
                t("broadcast_secretary", "en"),
                parse_mode=ParseMode.HTML,
            )
            await update.message.reply_media_group(_secretary_setup_media())
            return

        sent = 0
        failed = 0
        for uid in user_ids:
            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=t("broadcast_secretary", "en"),
                    parse_mode=ParseMode.HTML,
                )
                await context.bot.send_media_group(
                    chat_id=uid,
                    media=_secretary_setup_media(),
                )
                sent += 1
            except Exception as e:
                failed += 1
                logger.warning("Broadcast to %d failed: %s", uid, e)
            # Stay well under Telegram's per-second message limits.
            await asyncio.sleep(0.05)

        await update.message.reply_text(
            f"📢 Broadcast complete. Sent: {sent}, failed: {failed}."
        )

    async def stats_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not update.message or not update.effective_user:
            return

        user = update.effective_user
        logger.info(
            "Stats requested by user %s (id=%d). Admin IDs: %s. Is admin: %s",
            user.username, user.id, self._admin_ids, user.id in self._admin_ids,
        )

        lang = user.language_code or "en"

        direct = await self._stats_db.get_user_stats(user.id)
        sec = await self._stats_db.get_secretary_stats(user.id)

        if direct is None and sec is None:
            await update.message.reply_text(t("no_usage", lang))
            return

        lines: list[str] = []
        total_t = 0
        total_d = 0
        first_used = None
        last_used = None

        if direct:
            dt, dd, df, dl = direct
            total_t += dt
            total_d += dd
            first_used = df
            last_used = dl
            lines.append(
                t("stats_direct", lang,
                  transcriptions=dt, duration=format_duration(dd))
            )

        if sec:
            st, sd, sf, sl = sec
            total_t += st
            total_d += sd
            if first_used is None or (sf and sf < first_used):
                first_used = sf
            if last_used is None or (sl and sl > last_used):
                last_used = sl
            lines.append(
                t("stats_secretary", lang,
                  transcriptions=st, duration=format_duration(sd))
            )

        lines.append(
            t("stats_total", lang,
              transcriptions=total_t, duration=format_duration(total_d))
        )
        lines.append(
            t("stats_dates", lang,
              first_used=first_used or "—", last_used=last_used or "—")
        )

        await update.message.reply_text("\n".join(lines))

        # Admin: show all users + error stats
        if user.id in self._admin_ids:
            all_direct = await self._stats_db.get_all_stats()
            all_sec = await self._stats_db.get_all_secretary_stats()

            # Build combined per-user stats
            user_data: dict[int, dict[str, object]] = {}
            for uid, uname, count, dur, _, last in all_direct:
                user_data[uid] = {
                    "name": uname, "d_count": count, "d_dur": dur,
                    "s_count": 0, "s_dur": 0, "last": last,
                }
            for uid, uname, count, dur, _, last in all_sec:
                if uid in user_data:
                    entry = user_data[uid]
                    entry["s_count"] = count
                    entry["s_dur"] = dur
                    if last and (not entry["last"] or last > entry["last"]):  # type: ignore[operator]
                        entry["last"] = last
                else:
                    user_data[uid] = {
                        "name": uname, "d_count": 0, "d_dur": 0,
                        "s_count": count, "s_dur": dur, "last": last,
                    }

            if user_data:
                admin_lines = ["All users:"]
                for uid, d in sorted(
                    user_data.items(),
                    key=lambda x: x[1]["last"] or "",  # type: ignore[arg-type]
                    reverse=True,
                ):
                    name = d["name"] or uid
                    d_count = d["d_count"]
                    s_count = d["s_count"]
                    total = int(d_count) + int(s_count)  # type: ignore[arg-type]
                    total_dur = int(d["d_dur"]) + int(d["s_dur"])  # type: ignore[arg-type]
                    parts = [f"@{name} | {total} msgs | {format_duration(total_dur)}"]
                    if int(d_count) > 0 and int(s_count) > 0:  # type: ignore[arg-type]
                        parts.append(f"(D:{d_count} S:{s_count})")
                    elif int(s_count) > 0:  # type: ignore[arg-type]
                        parts.append("(S)")
                    parts.append(f"| last: {d['last']}")
                    admin_lines.append(" ".join(parts))
                await update.message.reply_text("\n".join(admin_lines))
            else:
                await update.message.reply_text("No user stats found in database.")

            total_errors, by_type, last_error = (
                await self._stats_db.get_error_stats()
            )
            if total_errors > 0:
                err_lines = [f"Errors: {total_errors} total"]
                for etype, ecount in sorted(by_type.items()):
                    err_lines.append(f"  {etype}: {ecount}")
                err_lines.append(f"Last error: {last_error}")
                await update.message.reply_text("\n".join(err_lines))

    async def logs_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not update.message or not update.effective_user:
            return
        if update.effective_user.id not in self._admin_ids:
            return

        log_path = "voice2message_bot.log"
        if os.path.exists(log_path):
            with open(log_path, "rb") as f:
                await update.message.reply_document(f, filename="bot.log")
        else:
            await update.message.reply_text("Log file not found.")

    async def handle_donate_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Send a Telegram Stars invoice when a donation button is tapped."""
        query = update.callback_query
        if not query or not query.data or not update.effective_user:
            return

        await query.answer()

        parts = query.data.split(":")
        if len(parts) != 2:
            return
        try:
            amount = int(parts[1])
        except ValueError:
            return

        lang = update.effective_user.language_code or "en"
        await query.edit_message_reply_markup(reply_markup=None)

        await context.bot.send_invoice(
            chat_id=update.effective_user.id,
            title=t("btn_donate", lang, amount=amount),
            description=t("donation_prompt", lang, count=""),
            payload=f"donate_{amount}",
            currency="XTR",
            prices=[LabeledPrice(label="Stars", amount=amount)],
        )

    async def handle_pre_checkout(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Approve all pre-checkout queries for donations."""
        if update.pre_checkout_query:
            await update.pre_checkout_query.answer(ok=True)

    async def handle_successful_payment(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Thank the user after a successful Stars payment."""
        if not update.message or not update.effective_user:
            return
        lang = update.effective_user.language_code or "en"
        await update.message.reply_text(t("donation_thanks", lang))

    @property
    def _admin_ids(self) -> list[int]:
        return self._notifier._admin_user_ids
