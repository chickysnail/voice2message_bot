import asyncio
import logging
import os
import tempfile
import uuid

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from src.bot.keyboards import CALLBACK_SUMMARIZE, post_transcription_keyboard
from src.bot.services.audio import extract_audio, get_audio_duration
from src.bot.services.notifier import AdminNotifier
from src.bot.services.summarization import SummarizationClient
from src.bot.services.transcription import EmptyTranscriptionError, TranscriptionClient
from src.bot.storage.statistics import StatisticsDB
from src.bot.storage.transcription_store import TranscriptionStore
from src.bot.utils.text import format_duration, split_message

logger = logging.getLogger(__name__)

GREETING_MESSAGES = {
    "en": (
        "Welcome {user}! Send me a voice message, audio file, or video note "
        "and I'll transcribe it for you."
    ),
    "ru": (
        "Добро пожаловать {user}! Отправьте мне голосовое сообщение, аудиофайл "
        "или видеозаметку, и я сделаю расшифровку."
    ),
    "es": (
        "¡Bienvenido {user}! Envíame un mensaje de voz, archivo de audio o "
        "nota de video y lo transcribiré para ti."
    ),
    "de": (
        "Willkommen {user}! Senden Sie mir eine Sprachnachricht, Audiodatei "
        "oder Videonachricht und ich werde sie transkribieren."
    ),
}

HELP_MESSAGES = {
    "en": (
        "Send me a voice message, audio file, or video note.\n"
        "I'll transcribe it immediately, then you can choose to summarize it."
    ),
    "ru": (
        "Отправьте мне голосовое сообщение, аудиофайл или видеозаметку.\n"
        "Я сразу сделаю расшифровку, после чего вы сможете получить краткое содержание."
    ),
}


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
    ) -> None:
        self._transcriber = transcriber
        self._summarizer = summarizer
        self._notifier = notifier
        self._store = store
        self._stats_db = stats_db
        self._max_audio_duration = max_audio_duration

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.message or not update.effective_user:
            return
        lang = update.effective_user.language_code or "en"
        greeting = GREETING_MESSAGES.get(lang, GREETING_MESSAGES["en"])
        await update.message.reply_text(
            greeting.format(user=update.effective_user.mention_html()),
            parse_mode=ParseMode.HTML,
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
        msg = HELP_MESSAGES.get(lang, HELP_MESSAGES["en"])
        await update.message.reply_text(msg)

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

        if message.voice:
            file_id = message.voice.file_id
            duration = message.voice.duration
        elif message.video_note:
            file_id = message.video_note.file_id
            duration = message.video_note.duration
            is_video = True
        elif message.audio:
            file_id = message.audio.file_id
            duration = message.audio.duration
        elif message.video:
            file_id = message.video.file_id
            duration = message.video.duration
            is_video = True
        elif message.document:
            file_id = message.document.file_id
            duration = None

        if not file_id:
            return

        # Check duration limit
        if duration and duration > self._max_audio_duration:
            max_min = self._max_audio_duration // 60
            await message.reply_text(
                f"This audio is too long ({format_duration(duration)}). "
                f"Max supported duration is {max_min} minutes."
            )
            return

        # Send a "processing" message
        processing_msg = await message.reply_text("Transcribing...")

        file_path: str | None = None
        audio_path: str | None = None
        try:
            # Download the file
            try:
                tg_file = await context.bot.get_file(file_id)
            except BadRequest as e:
                if "file is too big" in str(e).lower():
                    await processing_msg.edit_text(
                        "This file is too large to download. "
                        "Telegram limits bot file downloads to 20 MB.\n"
                        "Voice messages and video notes are compressed "
                        "by Telegram and usually work fine \u2014 this limit "
                        "mainly affects large audio/video files sent "
                        "as attachments.\n"
                        "You can try compressing or trimming the file "
                        "before sending."
                    )
                    return
                raise
            ext = (tg_file.file_path or "").rsplit(".", 1)[-1] if tg_file.file_path else "ogg"
            file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.{ext}")
            await tg_file.download_to_drive(custom_path=file_path)

            # Extract audio from video if needed
            if is_video:
                try:
                    audio_path = await extract_audio(file_path)
                except RuntimeError as e:
                    await processing_msg.edit_text("Could not extract audio from this video.")
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
                            f"This audio is too long ({format_duration(duration)}). "
                            f"Max supported duration is {max_min} minutes."
                        )
                        return

            # Transcribe (run in thread to avoid blocking the event loop)
            try:
                transcript = await asyncio.to_thread(
                    self._transcriber.transcribe, audio_path
                )
            except EmptyTranscriptionError as e:
                await processing_msg.edit_text(
                    "No speech was detected in this audio. "
                    "The recording may be silent or too short."
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
                    "Something went wrong on our end. "
                    "Please try again later."
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

            # Store the transcription for later actions (summarize)
            original_message_id = message.message_id
            self._store.save(user.id, original_message_id, transcript)

            # Record usage statistics
            await self._stats_db.record_usage(
                user.id, user.username, duration or 0
            )

            # Send the transcription
            await processing_msg.delete()
            chunks = split_message(transcript)
            for i, chunk in enumerate(chunks):
                is_last = i == len(chunks) - 1
                if is_last:
                    await message.reply_text(
                        chunk,
                        reply_markup=post_transcription_keyboard(original_message_id),
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
                    "Something went wrong. Please try again later."
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

        if not query.data.startswith(CALLBACK_SUMMARIZE):
            return

        parts = query.data.split(":")
        if len(parts) != 2:
            return

        try:
            original_message_id = int(parts[1])
        except ValueError:
            return

        user = update.effective_user

        # Look up the stored transcription
        transcript = self._store.get(user.id, original_message_id)
        if transcript is None:
            await query.edit_message_reply_markup(reply_markup=None)
            if query.message:
                await query.message.reply_text("This transcription has expired.")
            return

        # Remove buttons while processing
        await query.edit_message_reply_markup(reply_markup=None)

        try:
            summary = self._summarizer.summarize(transcript)
        except RuntimeError as e:
            if query.message:
                await query.message.reply_text(
                    "Something went wrong on our end. "
                    "Please try again later."
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

        stats = await self._stats_db.get_user_stats(user.id)
        if stats is None:
            await update.message.reply_text("No usage recorded yet.")
            return

        transcriptions, total_duration, first_used, last_used = stats
        await update.message.reply_text(
            f"Your stats:\n"
            f"Transcriptions: {transcriptions}\n"
            f"Total audio: {format_duration(total_duration)}\n"
            f"First used: {first_used}\n"
            f"Last used: {last_used}"
        )

        # Admin: show all users + error stats
        if user.id in self._admin_ids:
            all_stats = await self._stats_db.get_all_stats()
            if all_stats:
                lines = ["All users:"]
                for uid, uname, count, dur, _, last in all_stats:
                    lines.append(
                        f"@{uname or uid} | {count} msgs | {format_duration(dur)} | last: {last}"
                    )
                await update.message.reply_text("\n".join(lines))
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

    @property
    def _admin_ids(self) -> list[int]:
        return self._notifier._admin_user_ids
