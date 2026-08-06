"""Localised user-facing strings.

RULES — read before adding or changing messages:
1. Every key must have English, Russian and Portuguese translations.
   The test suite enforces completeness.
2. Translations must be CONTEXTUALLY accurate for a transcription bot.
   Do not use literal/dictionary translations. Consider how a native
   speaker would phrase the message in the context of voice-to-text.
3. Keep the same tone across languages: friendly, concise, helpful.

Supported languages:
en, ru, pt (European Portuguese)

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
        "pt": (
            "Olá {user}! Eu transformo mensagens de voz em texto.\n"
            "\n"
            "É só enviar ou reencaminhar uma mensagem de voz, áudio ou vídeo — transcrevo num instante."
        ),
    },
    "help": {
        "en": (
            "🎙 Send me a voice message, audio, video note, or video — I'll transcribe it.\n"
            "\n"
            "You can also send an Instagram reel or YouTube link — I'll take the audio from it.\n"
            "\n"
            "After transcription you can summarize it or save as .txt / .srt file. Multiple speakers are detected automatically.\n"
            "\n"
            "/secretary — transcribe voice messages in your chats\n"
            "/stats — your usage statistics"
        ),
        "ru": (
            "🎙 Отправьте мне голосовое, аудио, видеозаметку или видео — я сделаю расшифровку.\n"
            "\n"
            "Также можно прислать ссылку на рилс в Instagram или видео на YouTube — я возьму из него звук.\n"
            "\n"
            "После расшифровки можно получить краткое содержание или сохранить в .txt / .srt. Несколько говорящих распознаются автоматически.\n"
            "\n"
            "/secretary — расшифровка голосовых в ваших чатах\n"
            "/stats — статистика использования"
        ),
        "pt": (
            "🎙 Envie-me uma mensagem de voz, áudio, videomensagem ou vídeo — eu faço a transcrição.\n"
            "\n"
            "Também pode enviar um link de um reel do Instagram ou do YouTube — retiro o som de lá.\n"
            "\n"
            "Depois da transcrição pode pedir um resumo ou guardar em ficheiro .txt / .srt. Vários oradores são detetados automaticamente.\n"
            "\n"
            "/secretary — transcrever mensagens de voz nas suas conversas\n"
            "/stats — as suas estatísticas de utilização"
        ),
    },
    "transcribing": {
        "en": "Transcribing...",
        "ru": "Расшифровываю...",
        "pt": "A transcrever...",
    },
    "transcribing_donate": {
        "en": (
            "Transcribing...\n"
            "\n"
            "If you enjoy the bot, you can support it with "
            "Telegram Stars — it would mean the world to me ^^"
        ),
        "ru": (
            "Расшифровываю...\n"
            "\n"
            "Если бот вам полезен, вы можете поддержать "
            "его звёздами Telegram — это значило бы для меня очень много ^^"
        ),
        "pt": (
            "A transcrever...\n"
            "\n"
            "Se gosta do bot, pode apoiá-lo com "
            "Telegram Stars — significaria imenso para mim ^^"
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
        "pt": (
            "Este ficheiro é demasiado grande para descarregar. O Telegram limita a 20 MB os ficheiros que os bots podem transferir.\n"
            "As mensagens de voz e as videomensagens são comprimidas pelo Telegram e costumam funcionar bem — este limite afeta sobretudo ficheiros de áudio/vídeo grandes enviados como anexo.\n"
            "Experimente comprimir ou cortar o ficheiro antes de o enviar."
        ),
    },
    "audio_too_long": {
        "en": "This audio is too long ({duration}). Max supported duration is {max_min} minutes.",
        "ru": "Это аудио слишком длинное ({duration}). Максимальная поддерживаемая длительность — {max_min} минут.",
        "pt": "Este áudio é demasiado longo ({duration}). A duração máxima suportada é de {max_min} minutos.",
    },
    "no_speech": {
        "en": "No speech was detected in this audio. The recording may be silent or too short.",
        "ru": "В этом аудио не обнаружена речь. Запись может быть беззвучной или слишком короткой.",
        "pt": "Não detetei fala neste áudio. A gravação pode estar silenciosa ou ser demasiado curta.",
    },
    "something_went_wrong": {
        "en": "Something went wrong on our end. Please try again later.",
        "ru": "Что-то пошло не так с нашей стороны. Пожалуйста, попробуйте позже.",
        "pt": "Algo correu mal do nosso lado. Tente novamente mais tarde.",
    },
    "extraction_failed": {
        "en": "Could not extract audio from this video.",
        "ru": "Не удалось извлечь аудио из этого видео.",
        "pt": "Não consegui extrair o áudio deste vídeo.",
    },
    "link_choice": {
        "en": (
            "Got the audio ({duration}). Transcribing this long a recording takes a "
            "while — transcribe it, or just get the audio file?"
        ),
        "ru": (
            "Звук готов ({duration}). Расшифровка такой длинной записи занимает время — "
            "расшифровать или прислать только аудиофайл?"
        ),
        "pt": (
            "Já tenho o áudio ({duration}). Transcrever uma gravação tão longa demora algum "
            "tempo — quer a transcrição ou prefere só o ficheiro de áudio?"
        ),
    },
    "link_audio_expired": {
        "en": "This audio is no longer available — send the link again.",
        "ru": "Этого аудио больше нет — пришлите ссылку ещё раз.",
        "pt": "Este áudio já não está disponível — envie o link outra vez.",
    },
    "link_audio_too_big": {
        "en": "The audio file is too large for Telegram (over 50 MB).",
        "ru": "Аудиофайл слишком большой для Telegram (больше 50 МБ).",
        "pt": "O ficheiro de áudio é demasiado grande para o Telegram (mais de 50 MB).",
    },
    "transcript_as_file": {
        "en": "The transcript is too long for a message — open the file to read it.",
        "ru": "Расшифровка слишком длинная для сообщения — откройте файл, чтобы прочитать.",
        "pt": "A transcrição é demasiado longa para uma mensagem — abra o ficheiro para a ler.",
    },
    "transcription_expired": {
        "en": "This transcription has expired.",
        "ru": "Эта расшифровка истекла.",
        "pt": "Esta transcrição já expirou.",
    },
    "no_usage": {
        "en": "No usage recorded yet.",
        "ru": "Статистика использования пока отсутствует.",
        "pt": "Ainda não há utilização registada.",
    },
    "srt_no_words": {
        "en": "Word-level data is not available for SRT export. Try saving as .txt instead.",
        "ru": "Данные на уровне слов недоступны для экспорта SRT. Попробуйте сохранить как .txt.",
        "pt": "Não há dados ao nível da palavra para exportar em SRT. Experimente guardar em .txt.",
    },
    "srt_no_timed": {
        "en": "Could not generate subtitles — no timed words found. Try saving as .txt instead.",
        "ru": "Не удалось создать субтитры — не найдены слова с временными метками. Попробуйте .txt.",
        "pt": "Não consegui criar as legendas — não encontrei palavras com marcação temporal. Experimente .txt.",
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
        "pt": (
            "As suas estatísticas:\n"
            "Transcrições: {transcriptions}\n"
            "Áudio total: {duration}\n"
            "Primeira utilização: {first_used}\n"
            "Última utilização: {last_used}"
        ),
    },
    "transcription_timeout": {
        "en": "Transcription is taking too long. This can happen with very long recordings. Please try again — if the problem persists, try a shorter clip.",
        "ru": "Расшифровка занимает слишком много времени. Это может произойти с очень длинными записями. Попробуйте ещё раз — если проблема сохранится, попробуйте более короткий фрагмент.",
        "pt": "A transcrição está a demorar demasiado. Isto pode acontecer com gravações muito longas. Tente novamente — se o problema persistir, experimente um excerto mais curto.",
    },
    "download_timeout": {
        "en": "Could not download the file from Telegram. Please try sending it again.",
        "ru": "Не удалось загрузить файл из Telegram. Попробуйте отправить его ещё раз.",
        "pt": "Não consegui transferir o ficheiro do Telegram. Tente enviá-lo novamente.",
    },
    "secretary_manual_prompt": {
        "en": "🎙 Voice message ({duration})",
        "ru": "🎙 Голосовое сообщение ({duration})",
        "pt": "🎙 Mensagem de voz ({duration})",
    },
    "stats_direct": {
        "en": "Direct: {transcriptions} transcriptions, {duration}",
        "ru": "Прямые: {transcriptions} расшифровок, {duration}",
        "pt": "Diretas: {transcriptions} transcrições, {duration}",
    },
    "stats_secretary": {
        "en": "Secretary: {transcriptions} transcriptions, {duration}",
        "ru": "Секретарь: {transcriptions} расшифровок, {duration}",
        "pt": "Secretário: {transcriptions} transcrições, {duration}",
    },
    "stats_total": {
        "en": "Total: {transcriptions} transcriptions, {duration}",
        "ru": "Всего: {transcriptions} расшифровок, {duration}",
        "pt": "Total: {transcriptions} transcrições, {duration}",
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
        "pt": (
            "Primeira utilização: {first_used}\n"
            "Última: {last_used}"
        ),
    },
    "btn_summarize": {
        "en": "Summarize",
        "ru": "Краткое содержание",
        "pt": "Resumir",
    },
    "btn_save_file": {
        "en": "Save as file",
        "ru": "Сохранить как файл",
        "pt": "Guardar como ficheiro",
    },
    "btn_transcribe": {
        "en": "📝 Transcribe",
        "ru": "📝 Расшифровать",
        "pt": "📝 Transcrever",
    },
    "btn_download_audio": {
        "en": "🎵 Download audio",
        "ru": "🎵 Скачать аудио",
        "pt": "🎵 Descarregar áudio",
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
        "pt": (
            "✨ <b>Transcreva mensagens de voz nas suas conversas privadas</b>\n"
            "\n"
            "Vá a <b>Conta → Automatização de Conversas</b> nas definições do Telegram e adicione este bot. Depois de ligado, passo a colocar um botão “Transcrever” por baixo das mensagens de voz e videomensagens nas suas conversas privadas."
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
        "pt": (
            "✅ A transcrição já está ativa nas suas conversas privadas.\n"
            "\n"
            "Coloco um botão “Transcrever” por baixo das mensagens de voz e videomensagens. Para desativar, remova este bot em Conta → Automatização de Conversas nas definições do Telegram."
        ),
    },
    "btn_secretary_setup": {
        "en": "✨ Set up transcription in DMs",
        "ru": "✨ Настроить расшифровку в чатах",
        "pt": "✨ Ativar transcrição nas conversas",
    },
    "btn_secretary_settings": {
        "en": "✅ Transcription is set up",
        "ru": "✅ Транскрипция настроена",
        "pt": "✅ Transcrição ativa",
    },
    "text_nudge": {
        "en": "I work with voice messages, audio, and video. Send or forward one and I'll transcribe it!",
        "ru": "Я работаю с голосовыми, аудио и видео. Отправьте или перешлите — и я расшифрую!",
        "pt": "Eu trabalho com mensagens de voz, áudio e vídeo. Envie ou reencaminhe uma e eu transcrevo!",
    },
    "link_downloading": {
        "en": "Getting the audio from that link...",
        "ru": "Забираю звук из ссылки...",
        "pt": "A obter o áudio desse link...",
    },
    "link_failed": {
        "en": "Couldn't get the audio from that link. It may be private or unavailable.",
        "ru": "Не удалось получить звук по ссылке. Возможно, публикация приватная или недоступна.",
        "pt": "Não consegui obter o áudio desse link. A publicação pode ser privada ou estar indisponível.",
    },
    "link_unsupported": {
        "en": "Links aren't supported right now — send the video or voice message itself and I'll transcribe it.",
        "ru": "Ссылки сейчас не поддерживаются — пришлите само видео или голосовое, и я расшифрую.",
        "pt": "De momento não suporto links — envie o próprio vídeo ou a mensagem de voz e eu transcrevo.",
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
        "pt": (
            "✅ <b>Transcrição ativada!</b>\n"
            "\n"
            "Sempre que alguém enviar uma mensagem de voz ou uma videomensagem nas suas conversas privadas, coloco um botão “Transcrever”. Você ou a outra pessoa podem tocar nele para ver o texto.\n"
            "\n"
            "Os botões não usados são removidos automaticamente ao fim de um dia."
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
        "pt": (
            "🎙 <b>Novidade: transcreva mensagens de voz nas suas conversas</b>\n"
            "\n"
            "Já pode adicionar-me às suas conversas privadas para que apareça um botão "
            "“Transcrever” por baixo das mensagens de voz e videomensagens — sem "
            "precisar de me reencaminhar nada.\n"
            "\n"
            "Configure em 3 toques (veja as imagens abaixo):\n"
            "1. Telegram <b>Definições → Conta → Automatização de Conversas</b>\n"
            "2. Adicione <b>@cant_listen_right_now_bot</b>\n"
            "3. Ative as permissões de <b>Gerir Mensagens</b>\n"
            "\n"
            "Pronto — passo a colocar o botão Transcrever automaticamente."
        ),
    },
    "secretary_promo": {
        "en": "Or add me as your secretary and transcribe the messages right in your chats!",
        "ru": "Или добавьте меня как секретаря и расшифровывайте сообщения прямо в ваших чатах!",
        "pt": "Ou adicione-me como secretário e transcreva as mensagens diretamente nas suas conversas!",
    },
    "video_timeout": {
        "en": "Could not process this video. Please try again or send just the audio.",
        "ru": "Не удалось обработать это видео. Попробуйте ещё раз или отправьте только аудио.",
        "pt": "Não consegui processar este vídeo. Tente novamente ou envie apenas o áudio.",
    },
    "donation_thanks": {
        "en": "Thank you for your support! 🌟",
        "ru": "Спасибо за вашу поддержку! 🌟",
        "pt": "Obrigado pelo seu apoio! 🌟",
    },
    "btn_donate": {
        "en": "⭐{amount}",
        "ru": "⭐{amount}",
        "pt": "⭐{amount}",
    },
}


DEFAULT_LANG = "en"

SUPPORTED_LANGS = {"en", "ru", "pt"}


def normalize_lang(lang: str | None) -> str:
    """Map a Telegram language code (e.g. "pt-BR") to a supported language."""
    if not lang:
        return DEFAULT_LANG
    code = lang.lower().replace("_", "-").split("-")[0]
    return code if code in SUPPORTED_LANGS else DEFAULT_LANG


def t(key: str, lang: str | None = None, **kwargs: object) -> str:
    """Get a translated string.

    Falls back to English if the key or language is not found.
    Supports {placeholder} formatting via kwargs.
    """
    messages = _STRINGS.get(key)
    if messages is None:
        return key

    text = messages.get(normalize_lang(lang), messages[DEFAULT_LANG])
    if kwargs:
        text = text.format(**kwargs)
    return text
