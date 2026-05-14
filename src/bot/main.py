import logging
from logging.handlers import RotatingFileHandler

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.bot.config import Settings
from src.bot.handlers import BotHandlers
from src.bot.services.notifier import AdminNotifier
from src.bot.services.summarization import OpenAISummarizer
from src.bot.services.transcription import ElevenLabsTranscriber
from src.bot.storage.statistics import StatisticsDB
from src.bot.storage.transcription_store import TranscriptionStore

logger = logging.getLogger(__name__)


def setup_logging(level: str) -> None:
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_handler = RotatingFileHandler(
        "voice2message_bot.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    logging.basicConfig(
        format=log_format,
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=[log_handler, logging.StreamHandler()],
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


def main() -> None:
    settings = Settings()  # type: ignore[call-arg]
    setup_logging(settings.log_level)

    # Build services
    transcriber = ElevenLabsTranscriber(settings.elevenlabs_api_key)
    summarizer = OpenAISummarizer(settings.openai_api_key)
    store = TranscriptionStore(ttl_seconds=settings.transcription_ttl)
    stats_db = StatisticsDB(settings.database_path)

    # Build application
    application = Application.builder().token(settings.telegram_bot_token).build()

    notifier = AdminNotifier(application.bot, settings.admin_user_ids)

    handlers = BotHandlers(
        transcriber=transcriber,
        summarizer=summarizer,
        notifier=notifier,
        store=store,
        stats_db=stats_db,
        max_audio_duration=settings.max_audio_duration,
    )

    # Register handlers
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("stats", handlers.stats_command))
    application.add_handler(CommandHandler("logs", handlers.logs_command))

    audio_filter = (
        filters.VOICE
        | filters.VIDEO_NOTE
        | filters.AUDIO
        | filters.VIDEO
        | filters.Document.AUDIO
    )
    application.add_handler(MessageHandler(audio_filter, handlers.handle_audio))
    application.add_handler(CallbackQueryHandler(handlers.handle_callback))

    # Initialize DB on startup
    async def post_init(app: Application) -> None:  # type: ignore[type-arg]
        await stats_db.initialize()
        logger.info("Bot started. Admin IDs: %s", settings.admin_user_ids)

    async def post_shutdown(app: Application) -> None:  # type: ignore[type-arg]
        await stats_db.close()

    application.post_init = post_init
    application.post_shutdown = post_shutdown

    logger.info("Starting bot...")
    application.run_polling()


if __name__ == "__main__":
    main()
