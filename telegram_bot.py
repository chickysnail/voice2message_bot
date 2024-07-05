import logging
import configparser
import os
import uuid
from telegram import ForceReply, Update, Voice
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from voice2message import VoiceToMessage

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages."""
    # Load API key from config file
    config = configparser.ConfigParser()
    config.read("config.ini")
    api_key = config["credentials"]["api_key"]

    voice_to_message = VoiceToMessage(api_key)

    # Create audios folder if it does not exist
    if not os.path.exists('audios'):
        os.makedirs('audios')

    # Download the voice file
    new_file = await context.bot.get_file(update.message.voice.file_id)
    file_id = str(uuid.uuid4())  # Generate a unique file name
    audio_path = os.path.join('audios', f"{file_id}.ogg")
    await new_file.download_to_drive(custom_path=audio_path)

    # Process the audio file
    rewritten_transcript = voice_to_message.process_audio(audio_path)
    if rewritten_transcript:
        await update.message.reply_text(f"Processed Transcript:\n{rewritten_transcript}")
    else:
        await update.message.reply_text("Failed to process audio and rewrite transcript.")


def main() -> None:
    """Start the bot."""
    config = configparser.ConfigParser()
    config.read("config.ini")
    tg_token = config["telegram"]["bot_token"]
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(tg_token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
