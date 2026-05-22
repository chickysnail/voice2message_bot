from telegram import InlineKeyboardButton, InlineKeyboardMarkup

CALLBACK_SUMMARIZE = "summarize"
CALLBACK_SAVE_FILE = "savefile"
CALLBACK_EXPORT_TXT = "export_txt"
CALLBACK_EXPORT_SRT = "export_srt"
CALLBACK_SEC_TRANSCRIBE = "sec_transcribe"
CALLBACK_SEC_SUMMARIZE = "sec_summarize"
CALLBACK_SEC_SAVEFILE = "sec_savefile"
CALLBACK_SEC_EXPORT_TXT = "sec_export_txt"
CALLBACK_SEC_EXPORT_SRT = "sec_export_srt"


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


def secretary_post_transcription_keyboard(
    message_id: int, owner_user_id: int
) -> InlineKeyboardMarkup:
    """Post-transcription keyboard for secretary mode.

    Embeds owner_user_id so callbacks can look up the transcription
    regardless of who clicks the button.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "Summarize",
                callback_data=(
                    f"{CALLBACK_SEC_SUMMARIZE}:{message_id}"
                    f":{owner_user_id}"
                ),
            ),
            InlineKeyboardButton(
                "Save as file",
                callback_data=(
                    f"{CALLBACK_SEC_SAVEFILE}:{message_id}"
                    f":{owner_user_id}"
                ),
            ),
        ]
    ])


def secretary_file_format_keyboard(
    message_id: int, owner_user_id: int
) -> InlineKeyboardMarkup:
    """File format keyboard for secretary mode."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                ".txt",
                callback_data=(
                    f"{CALLBACK_SEC_EXPORT_TXT}:{message_id}"
                    f":{owner_user_id}"
                ),
            ),
            InlineKeyboardButton(
                ".srt",
                callback_data=(
                    f"{CALLBACK_SEC_EXPORT_SRT}:{message_id}"
                    f":{owner_user_id}"
                ),
            ),
        ]
    ])


def secretary_transcribe_keyboard(
    message_id: int, business_connection_id: str
) -> InlineKeyboardMarkup:
    """Keyboard for manual secretary mode — 'Transcribe' button."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📝 Transcribe",
                callback_data=(
                    f"{CALLBACK_SEC_TRANSCRIBE}:{message_id}"
                    f":{business_connection_id}"
                ),
            ),
        ]
    ])
