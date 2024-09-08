import logging
from logging.handlers import RotatingFileHandler
import configparser
import os
import uuid
from telegram import error
from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode 
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from voice2message import VoiceToMessage

# Enable logging
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
log_handler = RotatingFileHandler("voice2message_bot.log", maxBytes=10*1024*1024, backupCount=5)
logging.basicConfig(
    format=log_format, 
    level=logging.INFO,
    handlers=[
        log_handler,
        logging.StreamHandler()
    ]
)

# Set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

greeting_messages = {
    'en': "Welcome {user}! I can help you if you were sent an audio message but you can't listen right now. I will listen and summarize it for you!\n<b>Just send me the audio message</b>",
    'ru': "Добро пожаловать {user}! Я могу помочь вам, если вам было отправлено аудиосообщение, но вы не можете его прослушать прямо сейчас. Я послушаю и сделаю для вас краткое содержание!\n<b>Просто отправьте мне аудиосообщение</b>",
    'es': "¡Bienvenido {user}! Puedo ayudarte si te enviaron un mensaje de audio pero no puedes escucharlo en este momento. ¡Lo escucharé y lo resumiré para ti!\n<b>Solo envíame el mensaje de audio</b>",
    'de': "Willkommen {user}! Ich kann Ihnen helfen, wenn Ihnen eine Sprachnachricht gesendet wurde, Sie sie aber gerade nicht anhören können. Ich werde zuhören und sie für Sie zusammenfassen!\n<b>Schicken Sie mir einfach die Sprachnachricht</b>",
    # Add more languages as needed
}

# Define a few command handlers. These usually take the two arguments update and context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    # Get the user's language code
    user_language = update.effective_user.language_code

    # Get the appropriate greeting message or default to English
    greeting_message = greeting_messages.get(user_language, greeting_messages['en'])

    # Format the greeting message with the user's mention
    user = update.effective_user
    formatted_greeting_message = greeting_message.format(user=user.mention_html())

    # Log the start command usage
    logger.info(f"User {user.username} ({user.id}) user /start. Language: {user_language}")

    await update.message.reply_text(
        formatted_greeting_message,
        reply_markup=ForceReply(selective=True),
        parse_mode=ParseMode.HTML,
    )

help_messages = {
    'en': "*Just send me the audio message*",
    'ru': "*Просто отправьте мне аудиосообщение*",
    'es': "*Solo envíame el mensaje de audio*",
    'de': "*Schicken Sie mir einfach die Sprachnachricht*",
    # Add more languages as needed
}

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    # Get the user's language code
    user_language = update.effective_user.language_code
    help_message = help_messages.get(user_language, help_messages['en'])

    # Log the help command usage
    logger.info(f"User {update.effective_user.username} ({update.effective_user.id}) user /help.")

    await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN_V2)

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

    # Save the file ID in user data instead of downloading the file
    file_id = update.message.voice.file_id
    context.user_data['file_id'] = file_id

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

    try:
        # Disable the buttons to prevent further presses
        await query.edit_message_reply_markup(reply_markup=None)

        # Update the message to indicate that processing has started
        await query.edit_message_text(text="Processing the audio...")

    except error.BadRequest as e:
        logger.warning(str(e))
        return

    # Load API key from config file
    config = configparser.ConfigParser()
    config.read("config.ini")
    api_key = config["credentials"]["api_key"]

    voice_to_message = VoiceToMessage(api_key)

    # Retrieve the file ID from user data
    file_id = context.user_data.get('file_id')

    # Download the voice file
    new_file = await context.bot.get_file(file_id)
    audio_path = os.path.join('audios', f"{file_id}.ogg")
    os.makedirs(os.path.dirname(audio_path), exist_ok=True) # ensure the directory exists
    await new_file.download_to_drive(custom_path=audio_path)

    # Log the choice made by the user
    logger.info(f"Processing audio for {update.effective_user.username}. Choice: {choice}")

    try:
        # Process the audio file
        rewritten_transcript = voice_to_message.process_audio(audio_path, is_summary=is_summary)
        logger.debug(f"Transcription result: {rewritten_transcript}")

        if rewritten_transcript:
            await query.edit_message_text(text=rewritten_transcript)
            logger.info(f"Successfully processed audio for {update.effective_user.username}.")
        else:
            logger.error(f"No transcript returned for {update.effective_user.username}.")
            await query.edit_message_text(text="Failed to process audio and rewrite transcript.")
    except Exception as e:
        logger.exception(f"An error occurred during audio processing for {update.effective_user.username}: {e}")
        await query.edit_message_text(text="Failed to process audio and rewrite transcript.")
    finally:
        # Delete the audio file after processing
        if os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info(f"Deleted audio file {audio_path} after processing.")

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the log file to the admin."""
    if update.effective_user.username != "chickysnail":
        return

    log_file_path = 'voice2message_bot.log'
    if os.path.exists(log_file_path):
        await context.bot.send_document(chat_id=update.effective_chat.id, document=open(log_file_path, 'rb'))
    else:
        await update.message.reply_text("Log file not found.")

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
    application.add_handler(CommandHandler("logs", logs_command))  
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(CallbackQueryHandler(button))

    # On non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
