from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CALLBACK_SUMMARIZE = "summarize"


def post_transcription_keyboard(message_id: int) -> InlineKeyboardMarkup:
    """Keyboard shown after transcription, with action buttons."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "Summarize",
                callback_data=f"{CALLBACK_SUMMARIZE}:{message_id}",
            )
        ]
    ])
