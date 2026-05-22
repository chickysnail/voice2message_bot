from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.locales import t

CALLBACK_SUMMARIZE = "summarize"
CALLBACK_SAVE_FILE = "savefile"
CALLBACK_EXPORT_TXT = "export_txt"
CALLBACK_EXPORT_SRT = "export_srt"
CALLBACK_SEC_TRANSCRIBE = "sec_transcribe"
CALLBACK_SEC_SUMMARIZE = "sec_summarize"
CALLBACK_SEC_SAVEFILE = "sec_savefile"
CALLBACK_SEC_EXPORT_TXT = "sec_export_txt"
CALLBACK_SEC_EXPORT_SRT = "sec_export_srt"
CALLBACK_SEC_MODE_AUTO = "sec_mode_auto"
CALLBACK_SEC_MODE_MANUAL = "sec_mode_manual"
CALLBACK_SECRETARY_SETUP = "secretary_setup"


def post_transcription_keyboard(
    message_id: int, lang: str = "en"
) -> InlineKeyboardMarkup:
    """Keyboard shown after transcription, with action buttons."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t("btn_summarize", lang),
                callback_data=f"{CALLBACK_SUMMARIZE}:{message_id}",
            ),
            InlineKeyboardButton(
                t("btn_save_file", lang),
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
    message_id: int, owner_user_id: int, lang: str = "en"
) -> InlineKeyboardMarkup:
    """Post-transcription keyboard for secretary mode.

    Embeds owner_user_id so callbacks can look up the transcription
    regardless of who clicks the button.
    """
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t("btn_summarize", lang),
                callback_data=(
                    f"{CALLBACK_SEC_SUMMARIZE}:{message_id}"
                    f":{owner_user_id}"
                ),
            ),
            InlineKeyboardButton(
                t("btn_save_file", lang),
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
    message_id: int, business_connection_id: str, lang: str = "en"
) -> InlineKeyboardMarkup:
    """Keyboard for manual secretary mode — 'Transcribe' button."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t("btn_transcribe", lang),
                callback_data=(
                    f"{CALLBACK_SEC_TRANSCRIBE}:{message_id}"
                    f":{business_connection_id}"
                ),
            ),
        ]
    ])


def secretary_mode_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    """Inline buttons for switching secretary mode."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t("btn_mode_auto", lang),
                callback_data=CALLBACK_SEC_MODE_AUTO,
            ),
            InlineKeyboardButton(
                t("btn_mode_manual", lang),
                callback_data=CALLBACK_SEC_MODE_MANUAL,
            ),
        ]
    ])


def secretary_setup_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    """Button shown in /start for secretary setup discovery."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t("btn_secretary_setup", lang),
                callback_data=CALLBACK_SECRETARY_SETUP,
            ),
        ]
    ])


def secretary_settings_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    """Button shown in /start when secretary is already connected."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t("btn_secretary_settings", lang),
                callback_data=CALLBACK_SECRETARY_SETUP,
            ),
        ]
    ])
