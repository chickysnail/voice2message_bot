from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CALLBACK_SUMMARIZE = "summarize"
CALLBACK_SAVE_FILE = "savefile"
CALLBACK_EXPORT_TXT = "export_txt"
CALLBACK_EXPORT_SRT = "export_srt"


def post_transcription_keyboard(message_id: int) -> InlineKeyboardMarkup:
    """Keyboard shown after transcription, with action buttons."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "Summarize",
                callback_data=f"{CALLBACK_SUMMARIZE}:{message_id}",
            ),
            InlineKeyboardButton(
                "Save as file",
                callback_data=f"{CALLBACK_SAVE_FILE}:{message_id}",
            ),
        ]
    ])


def file_format_keyboard(message_id: int) -> InlineKeyboardMarkup:
    """Keyboard for choosing file export format."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                ".txt",
                callback_data=f"{CALLBACK_EXPORT_TXT}:{message_id}",
            ),
            InlineKeyboardButton(
                ".srt",
                callback_data=f"{CALLBACK_EXPORT_SRT}:{message_id}",
            ),
        ]
    ])
