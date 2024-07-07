import logging
import configparser
import os
import uuid
from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from voice2message import VoiceToMessage

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Define a few command handlers. These usually take the two arguments update and context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    # Write a greeting message explaining how to use the bot
    user = update.effective_user
    greeting_message = f"Welcome {user.mention_html()}! I can help you if you were sent an audio message but you can't listen right now. I will listen and summarize it for you!"
    await update.message.reply_html(
        greeting_message,
        reply_markup=ForceReply(selective=True),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)

def check_audio_length(seconds):
    """Check if the audio length exceeds the threshold."""
    config = configparser.ConfigParser()
    config.read("config.ini")
    threshold = int(config["security"]["voice_threshold"])
    return seconds > threshold

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages."""
    # Check if the user has the nickname "chickysnail"
    if update.effective_user.username != "chickysnail":
        # Check if the audio file is longer than the threshold
        if check_audio_length(update.message.voice.duration):
            await update.message.reply_text("The audio file is too long. Please upgrade the plan to process longer audio files.")
            return

    # Create audios folder if it does not exist
    if not os.path.exists('audios'):
        os.makedirs('audios')

    # Download the voice file
    new_file = await context.bot.get_file(update.message.voice.file_id)
    file_id = str(uuid.uuid4())  # Generate a unique file name
    audio_path = os.path.join('audios', f"{file_id}.ogg")
    await new_file.download_to_drive(custom_path=audio_path)

    # Save the audio path in user data
    context.user_data['audio_path'] = audio_path

    # Ask the user if they want a summary or a transcript
    keyboard = [
        [
            InlineKeyboardButton("Summary", callback_data='summary'),
            InlineKeyboardButton("Transcript", callback_data='transcript')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('What would you like to receive?', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses and process the audio file accordingly."""
    query = update.callback_query
    await query.answer()
    choice = query.data
    is_summary = choice == 'summary'

    # Load API key from config file
    config = configparser.ConfigParser()
    config.read("config.ini")
    api_key = config["credentials"]["api_key"]

    voice_to_message = VoiceToMessage(api_key)

    # Retrieve the audio path from user data
    audio_path = context.user_data.get('audio_path')

    # Log the choice made by the user
    logger.info(f"Processing audio for {update.effective_user.username}. Choice: {choice}")

    # Process the audio file
    rewritten_transcript = voice_to_message.process_audio(audio_path, is_summary=is_summary)
    if rewritten_transcript:
        await query.edit_message_text(text=rewritten_transcript)
        logger.info(f"Successfully processed audio for {update.effective_user.username}.")
    else:
        await query.edit_message_text(text="Failed to process audio and rewrite transcript.")
        logger.error(f"Failed to process audio for {update.effective_user.username}.")

    # Delete the audio file after processing
    if os.path.exists(audio_path):
        os.remove(audio_path)
        logger.info(f"Deleted audio file {audio_path} after processing.")

def main() -> None:
    """Start the bot."""
    config = configparser.ConfigParser()
    config.read("config.ini")
    tg_token = config["telegram"]["bot_token"]
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(tg_token).build()

    # On different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(CallbackQueryHandler(button))

    # On non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
