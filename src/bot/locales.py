"""Localised user-facing strings.

RULES — read before adding or changing messages:
1. Every key must have both English and Russian translations.
   The test suite enforces completeness.
2. Translations must be CONTEXTUALLY accurate for a transcription bot.
   Do not use literal/dictionary translations. Consider how a native
   speaker would phrase the message in the context of voice-to-text.
3. Keep the same tone across languages: friendly, concise, helpful.

Supported languages:
en, ru

Usage:
    from src.bot.locales import t
    text = t("greeting", lang, user=mention_html)
"""

from __future__ import annotations

# --- all translatable message keys ---

_STRINGS: dict[str, dict[str, str]] = {
    "greeting": {
        "en": (
            "Hi {user}! I turn voice messages into text.\n"
            "\n"
            "Just send or forward a voice message, audio, or video — I'll transcribe it instantly."
        ),
        "ru": (
            "Привет {user}! Я превращаю голосовые сообщения в текст.\n"
            "\n"
            "Просто отправьте или перешлите голосовое, аудио или видео — я мгновенно сделаю расшифровку."
        ),
    },
    "help": {
        "en": (
            "🎙 Send me a voice message, audio, video note, or video — I'll transcribe it.\n"
            "\n"
            "After transcription you can summarize it or save as .txt / .srt file. Multiple speakers are detected automatically.\n"
            "\n"
            "/secretary — transcribe voice messages in your chats\n"
            "/stats — your usage statistics"
        ),
        "ru": (
            "🎙 Отправьте мне голосовое, аудио, видеозаметку или видео — я сделаю расшифровку.\n"
            "\n"
            "После расшифровки можно получить краткое содержание или сохранить в .txt / .srt. Несколько говорящих распознаются автоматически.\n"
            "\n"
            "/secretary — расшифровка голосовых в ваших чатах\n"
            "/stats — статистика использования"
        ),
    },
    "transcribing": {
        "en": "Transcribing...",
        "ru": "Расшифровываю...",
    },
    "transcribing_donate": {
        "en": (
            "Transcribing... If you enjoy the bot, you can support it with "
            "Telegram Stars — it would mean the world to me ^^"
        ),
        "ru": (
            "Расшифровываю... Если бот вам полезен, вы можете поддержать "
            "его звёздами Telegram — это значило бы для меня очень много ^^"
        ),
    },
    "file_too_large": {
        "en": (
            "This file is too large to download. Telegram limits bot file downloads to 20 MB.\n"
            "Voice messages and video notes are compressed by Telegram and usually work fine — this limit mainly affects large audio/video files sent as attachments.\n"
            "You can try compressing or trimming the file before sending."
        ),
        "ru": (
            "Этот файл слишком большой для загрузки. Telegram ограничивает загрузку файлов ботами до 20 МБ.\n"
            "Голосовые сообщения и видеозаметки сжимаются Telegram и обычно работают нормально — это ограничение в основном касается больших аудио/видео файлов, отправленных как вложения.\n"
            "Попробуйте сжать или обрезать файл перед отправкой."
        ),
    },
    "audio_too_long": {
        "en": "This audio is too long ({duration}). Max supported duration is {max_min} minutes.",
        "ru": "Это аудио слишком длинное ({duration}). Максимальная поддерживаемая длительность — {max_min} минут.",
    },
    "no_speech": {
        "en": "No speech was detected in this audio. The recording may be silent or too short.",
        "ru": "В этом аудио не обнаружена речь. Запись может быть беззвучной или слишком короткой.",
    },
    "something_went_wrong": {
        "en": "Something went wrong on our end. Please try again later.",
        "ru": "Что-то пошло не так с нашей стороны. Пожалуйста, попробуйте позже.",
    },
    "extraction_failed": {
        "en": "Could not extract audio from this video.",
        "ru": "Не удалось извлечь аудио из этого видео.",
    },
    "transcription_expired": {
        "en": "This transcription has expired.",
        "ru": "Эта расшифровка истекла.",
    },
    "no_usage": {
        "en": "No usage recorded yet.",
        "ru": "Статистика использования пока отсутствует.",
    },
    "srt_no_words": {
        "en": "Word-level data is not available for SRT export. Try saving as .txt instead.",
        "ru": "Данные на уровне слов недоступны для экспорта SRT. Попробуйте сохранить как .txt.",
    },
    "srt_no_timed": {
        "en": "Could not generate subtitles — no timed words found. Try saving as .txt instead.",
        "ru": "Не удалось создать субтитры — не найдены слова с временными метками. Попробуйте .txt.",
    },
    "your_stats": {
        "en": (
            "Your stats:\n"
            "Transcriptions: {transcriptions}\n"
            "Total audio: {duration}\n"
            "First used: {first_used}\n"
            "Last used: {last_used}"
        ),
        "ru": (
            "Ваша статистика:\n"
            "Расшифровок: {transcriptions}\n"
            "Всего аудио: {duration}\n"
            "Первое использование: {first_used}\n"
            "Последнее использование: {last_used}"
        ),
    },
    "transcription_timeout": {
        "en": "Transcription is taking too long. This can happen with very long recordings. Please try again — if the problem persists, try a shorter clip.",
        "ru": "Расшифровка занимает слишком много времени. Это может произойти с очень длинными записями. Попробуйте ещё раз — если проблема сохранится, попробуйте более короткий фрагмент.",
    },
    "download_timeout": {
        "en": "Could not download the file from Telegram. Please try sending it again.",
        "ru": "Не удалось загрузить файл из Telegram. Попробуйте отправить его ещё раз.",
    },
    "secretary_manual_prompt": {
        "en": "🎙 Voice message ({duration})",
        "ru": "🎙 Голосовое сообщение ({duration})",
    },
    "stats_direct": {
        "en": "Direct: {transcriptions} transcriptions, {duration}",
        "ru": "Прямые: {transcriptions} расшифровок, {duration}",
    },
    "stats_secretary": {
        "en": "Secretary: {transcriptions} transcriptions, {duration}",
        "ru": "Секретарь: {transcriptions} расшифровок, {duration}",
    },
    "stats_total": {
        "en": "Total: {transcriptions} transcriptions, {duration}",
        "ru": "Всего: {transcriptions} расшифровок, {duration}",
    },
    "stats_dates": {
        "en": (
            "First used: {first_used}\n"
            "Last used: {last_used}"
        ),
        "ru": (
            "Первое использование: {first_used}\n"
            "Последнее: {last_used}"
        ),
    },
    "btn_summarize": {
        "en": "Summarize",
        "ru": "Краткое содержание",
    },
    "btn_save_file": {
        "en": "Save as file",
        "ru": "Сохранить как файл",
    },
    "btn_transcribe": {
        "en": "📝 Transcribe",
        "ru": "📝 Расшифровать",
    },
    "secretary_setup": {
        "en": (
            "✨ <b>Transcribe voice messages right in your DMs</b>\n"
            "\n"
            "Go to your <b>Account → Chat Automation</b> in Telegram settings and add this bot. Once connected, I'll add a \u201cTranscribe\u201d button under voice messages and video notes in your private chats."
        ),
        "ru": (
            "✨ <b>Расшифровывайте голосовые прямо в личных чатах</b>\n"
            "\n"
            "Откройте <b>Аккаунт → Чат-автоматизация</b> в настройках Telegram и добавьте этого бота. После подключения я буду добавлять кнопку «Расшифровать» под голосовыми сообщениями и видеосообщениями в ваших личных чатах."
        ),
    },
    "secretary_connected": {
        "en": (
            "✅ Transcription is already set up in your DMs.\n"
            "\n"
            "I add a \u201cTranscribe\u201d button under voice messages and video notes in your private chats. To turn it off, remove this bot from Account → Chat Automation in Telegram settings."
        ),
        "ru": (
            "✅ Транскрипция уже настроена в ваших личных чатах.\n"
            "\n"
            "Я добавляю кнопку «Расшифровать» под голосовыми сообщениями и видеосообщениями. Чтобы отключить, удалите бота в разделе Аккаунт → Чат-автоматизация в настройках Telegram."
        ),
    },
    "btn_secretary_setup": {
        "en": "✨ Set up transcription in DMs",
        "ru": "✨ Настроить расшифровку в чатах",
    },
    "btn_secretary_settings": {
        "en": "✅ Transcription is set up",
        "ru": "✅ Транскрипция настроена",
    },
    "text_nudge": {
        "en": "I work with voice messages, audio, and video. Send or forward one and I'll transcribe it!",
        "ru": "Я работаю с голосовыми, аудио и видео. Отправьте или перешлите — и я расшифрую!",
    },
    "secretary_welcome": {
        "en": (
            "✅ <b>Transcription is set up!</b>\n"
            "\n"
            "When someone sends a voice message or video note in your private chats, I'll add a \u201cTranscribe\u201d button. You or the other person can tap it to see the text.\n"
            "\n"
            "Untranscribed prompts are removed automatically after a day."
        ),
        "ru": (
            "✅ <b>Транскрипция настроена!</b>\n"
            "\n"
            "Когда в ваших личных чатах кто-то пришлёт голосовое сообщение или видеосообщение, я добавлю кнопку «Расшифровать». Вы или собеседник можете нажать её, чтобы увидеть текст.\n"
            "\n"
            "Нерасшифрованные сообщения автоматически удаляются через сутки."
        ),
    },
    "broadcast_secretary": {
        "en": (
            "🎙 <b>New: transcribe voice messages right in your chats</b>\n"
            "\n"
            "You can now add me to your private chats so a \u201cTranscribe\u201d button "
            "appears under voice messages and video notes — no need to forward "
            "anything to me.\n"
            "\n"
            "Set it up in 3 taps (see the screenshots below):\n"
            "1. Telegram <b>Settings → Account → Chat Automation</b>\n"
            "2. Add <b>@cant_listen_right_now_bot</b>\n"
            "3. Enable the <b>Manage Messages</b> permissions\n"
            "\n"
            "That's it — I'll start adding the Transcribe button automatically."
        ),
        "ru": (
            "🎙 <b>Новое: расшифровка голосовых прямо в ваших чатах</b>\n"
            "\n"
            "Теперь вы можете добавить меня в свои личные чаты — кнопка «Расшифровать» "
            "будет появляться под голосовыми и видеосообщениями. Ничего пересылать не нужно.\n"
            "\n"
            "Настройка в 3 шага (скриншоты ниже):\n"
            "1. Telegram <b>Настройки → Аккаунт → Чат-автоматизация</b>\n"
            "2. Добавьте <b>@cant_listen_right_now_bot</b>\n"
            "3. Включите разрешение <b>Управление сообщениями</b>\n"
            "\n"
            "Готово — кнопка «Расшифровать» будет добавляться автоматически."
        ),
    },
    "secretary_promo": {
        "en": "Or add me as your secretary and transcribe the messages right in your chats!",
        "ru": "Или добавьте меня как секретаря и расшифровывайте сообщения прямо в ваших чатах!",
    },
    "video_timeout": {
        "en": "Could not process this video. Please try again or send just the audio.",
        "ru": "Не удалось обработать это видео. Попробуйте ещё раз или отправьте только аудио.",
    },
    "donation_thanks": {
        "en": "Thank you for your support! 🌟",
        "ru": "Спасибо за вашу поддержку! 🌟",
    },
    "btn_donate": {
        "en": "Support ⭐{amount}",
        "ru": "Поддержать ⭐{amount}",
    },
}


DEFAULT_LANG = "en"

SUPPORTED_LANGS = {"en", "ru"}


def t(key: str, lang: str | None = None, **kwargs: object) -> str:
    """Get a translated string.

    Falls back to English if the key or language is not found.
    Supports {placeholder} formatting via kwargs.
    """
    messages = _STRINGS.get(key)
    if messages is None:
        return key

    lang = lang or DEFAULT_LANG
    text = messages.get(lang, messages[DEFAULT_LANG])
    if kwargs:
        text = text.format(**kwargs)
    return text
