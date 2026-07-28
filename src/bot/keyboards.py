from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.bot.locales import t

CALLBACK_SUMMARIZE = "summarize"
CALLBACK_SAVE_FILE = "savefile"
CALLBACK_EXPORT_TXT = "export_txt"
CALLBACK_EXPORT_SRT = "export_srt"
CALLBACK_SEC_TRANSCRIBE = "sec_transcribe"
CALLBACK_SECRETARY_SETUP = "secretary_setup"
CALLBACK_LINK_TRANSCRIBE = "link_transcribe"
CALLBACK_LINK_AUDIO = "link_audio"


def post_transcription_keyboard(
    message_id: int, lang: str = "en", with_audio: bool = False
) -> InlineKeyboardMarkup:
    """Keyboard shown after transcription, with action buttons."""
    rows = [
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
    ]
    if with_audio:
        rows.append([_download_audio_button(message_id, lang)])
    return InlineKeyboardMarkup(rows)


def _download_audio_button(message_id: int, lang: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        t("btn_download_audio", lang),
        callback_data=f"{CALLBACK_LINK_AUDIO}:{message_id}",
    )


def link_audio_keyboard(message_id: int, lang: str = "en") -> InlineKeyboardMarkup:
    """Single 'Download audio' button, shown while a link is transcribing."""
    return InlineKeyboardMarkup([[_download_audio_button(message_id, lang)]])


def link_choice_keyboard(message_id: int, lang: str = "en") -> InlineKeyboardMarkup:
    """Transcribe / download choice, shown for long linked videos."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t("btn_transcribe", lang),
                callback_data=f"{CALLBACK_LINK_TRANSCRIBE}:{message_id}",
            ),
            _download_audio_button(message_id, lang),
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


DONATION_STAR_AMOUNTS = [50, 100, 250]


def donation_keyboard(lang: str = "en") -> InlineKeyboardMarkup:
    """Inline keyboard with Telegram Stars donation tiers."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                t("btn_donate", lang, amount=amount),
                callback_data=f"donate:{amount}",
            )
            for amount in DONATION_STAR_AMOUNTS
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
