"""Localised user-facing strings.

RULES — read before adding or changing messages:
1. During development, adding a key with ENGLISH ONLY is fine.
   Before merging, all keys must be translated into every supported
   language listed below. The test suite catches partial translations.
2. Translations must be CONTEXTUALLY accurate for a transcription bot.
   Do not use literal/dictionary translations. Consider how a native
   speaker would phrase the message in the context of voice-to-text.
3. Use gender-neutral phrasing where applicable (e.g. Hindi).
4. Keep the same tone across languages: friendly, concise, helpful.

Supported languages:
en, ru, hi, id, fa

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
        "hi": (
            "नमस्ते {user}! मैं वॉइस मैसेज को टेक्स्ट में बदलता हूँ।\n"
            "\n"
            "बस वॉइस मैसेज, ऑडियो या वीडियो भेजें या फॉरवर्ड करें — मैं तुरंत ट्रांसक्राइब कर दूँगा।"
        ),
        "id": (
            "Hai {user}! Saya mengubah pesan suara menjadi teks.\n"
            "\n"
            "Cukup kirim atau teruskan pesan suara, audio, atau video — saya akan langsung mentranskripsikannya."
        ),
        "fa": (
            "سلام {user}! من پیام‌های صوتی را به متن تبدیل می‌کنم.\n"
            "\n"
            "فقط پیام صوتی، صوت یا ویدیو بفرستید یا فوروارد کنید — فوراً رونویسی می‌کنم."
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
        "hi": (
            "🎙 मुझे वॉइस मैसेज, ऑडियो, वीडियो नोट या वीडियो भेजें — मैं ट्रांसक्राइब कर दूँगा।\n"
            "\n"
            "ट्रांसक्रिप्शन के बाद सारांश बना सकते हैं या .txt / .srt में सेव कर सकते हैं। कई वक्ता अपने आप पहचाने जाते हैं।\n"
            "\n"
            "/secretary — चैट में वॉइस मैसेज ट्रांसक्राइब करें\n"
            "/stats — उपयोग सांख्यिकी"
        ),
        "id": (
            "🎙 Kirimkan pesan suara, audio, catatan video, atau video — saya akan mentranskripsikannya.\n"
            "\n"
            "Setelah transkripsi Anda bisa meringkas atau menyimpan sebagai .txt / .srt. Beberapa pembicara terdeteksi secara otomatis.\n"
            "\n"
            "/secretary — transkripsi pesan suara di chat Anda\n"
            "/stats — statistik penggunaan"
        ),
        "fa": (
            "🎙 پیام صوتی، صوت، یادداشت ویدیویی یا ویدیو بفرستید — رونویسی می‌کنم.\n"
            "\n"
            "بعد از رونویسی می‌توانید خلاصه بگیرید یا به‌صورت .txt / .srt ذخیره کنید. چندین گوینده به‌صورت خودکار شناسایی می‌شوند.\n"
            "\n"
            "/secretary — رونویسی پیام‌های صوتی در چت‌ها\n"
            "/stats — آمار استفاده"
        ),
    },
    "transcribing": {
        "en": "Transcribing...",
        "ru": "Расшифровываю...",
        "hi": "ट्रांसक्राइब हो रहा है...",
        "id": "Sedang mentranskripsikan...",
        "fa": "در حال رونویسی...",
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
        "hi": (
            "यह फाइल डाउनलोड करने के लिए बहुत बड़ी है। Telegram बॉट फाइल डाउनलोड को 20 MB तक सीमित करता है।\n"
            "वॉइस मैसेज और वीडियो नोट Telegram द्वारा संपीड़ित होते हैं और आमतौर पर ठीक काम करते हैं।\n"
            "भेजने से पहले फाइल को संपीड़ित या ट्रिम करने का प्रयास करें।"
        ),
        "id": (
            "File ini terlalu besar untuk diunduh. Telegram membatasi unduhan file bot hingga 20 MB.\n"
            "Pesan suara dan catatan video dikompresi oleh Telegram dan biasanya berfungsi dengan baik.\n"
            "Coba kompres atau potong file sebelum mengirim."
        ),
        "fa": (
            "این فایل برای دانلود خیلی بزرگ است. تلگرام دانلود فایل توسط ربات را به ۲۰ مگابایت محدود می‌کند.\n"
            "پیام‌های صوتی و یادداشت‌های ویدیویی توسط تلگرام فشرده می‌شوند و معمولاً به خوبی کار می‌کنند.\n"
            "قبل از ارسال، فایل را فشرده یا برش دهید."
        ),
    },
    "audio_too_long": {
        "en": "This audio is too long ({duration}). Max supported duration is {max_min} minutes.",
        "ru": "Это аудио слишком длинное ({duration}). Максимальная поддерживаемая длительность — {max_min} минут.",
        "hi": "यह ऑडियो बहुत लंबा है ({duration})। अधिकतम समर्थित अवधि {max_min} मिनट है।",
        "id": "Audio ini terlalu panjang ({duration}). Durasi maksimal yang didukung adalah {max_min} menit.",
        "fa": "این صوت خیلی طولانی است ({duration}). حداکثر مدت پشتیبانی شده {max_min} دقیقه است.",
    },
    "no_speech": {
        "en": "No speech was detected in this audio. The recording may be silent or too short.",
        "ru": "В этом аудио не обнаружена речь. Запись может быть беззвучной или слишком короткой.",
        "hi": "इस ऑडियो में कोई भाषण नहीं मिला। रिकॉर्डिंग शायद साइलेंट या बहुत छोटी है।",
        "id": "Tidak ada ucapan yang terdeteksi dalam audio ini. Rekaman mungkin kosong atau terlalu pendek.",
        "fa": "هیچ گفتاری در این صوت شناسایی نشد. ضبط ممکن است ساکت یا خیلی کوتاه باشد.",
    },
    "something_went_wrong": {
        "en": "Something went wrong on our end. Please try again later.",
        "ru": "Что-то пошло не так с нашей стороны. Пожалуйста, попробуйте позже.",
        "hi": "हमारी तरफ कुछ गलत हो गया। कृपया बाद में पुनः प्रयास करें।",
        "id": "Terjadi kesalahan di pihak kami. Silakan coba lagi nanti.",
        "fa": "مشکلی از سمت ما پیش آمد. لطفاً بعداً دوباره امتحان کنید.",
    },
    "extraction_failed": {
        "en": "Could not extract audio from this video.",
        "ru": "Не удалось извлечь аудио из этого видео.",
        "hi": "इस वीडियो से ऑडियो नहीं निकाला जा सका।",
        "id": "Tidak dapat mengekstrak audio dari video ini.",
        "fa": "استخراج صدا از این ویدیو ممکن نشد.",
    },
    "transcription_expired": {
        "en": "This transcription has expired.",
        "ru": "Эта расшифровка истекла.",
        "hi": "यह ट्रांसक्रिप्शन समाप्त हो गया है।",
        "id": "Transkripsi ini telah kedaluwarsa.",
        "fa": "این رونویسی منقضی شده است.",
    },
    "no_usage": {
        "en": "No usage recorded yet.",
        "ru": "Статистика использования пока отсутствует.",
        "hi": "अभी तक कोई उपयोग दर्ज नहीं हुआ।",
        "id": "Belum ada penggunaan yang tercatat.",
        "fa": "هنوز استفاده‌ای ثبت نشده است.",
    },
    "srt_no_words": {
        "en": "Word-level data is not available for SRT export. Try saving as .txt instead.",
        "ru": "Данные на уровне слов недоступны для экспорта SRT. Попробуйте сохранить как .txt.",
        "hi": "SRT निर्यात के लिए शब्द-स्तरीय डेटा उपलब्ध नहीं है। .txt में सेव करें।",
        "id": "Data tingkat kata tidak tersedia untuk ekspor SRT. Coba simpan sebagai .txt.",
        "fa": "داده‌های سطح کلمه برای صادرات SRT در دسترس نیست. به‌جای آن به‌صورت .txt ذخیره کنید.",
    },
    "srt_no_timed": {
        "en": "Could not generate subtitles — no timed words found. Try saving as .txt instead.",
        "ru": "Не удалось создать субтитры — не найдены слова с временными метками. Попробуйте .txt.",
        "hi": "सबटाइटल नहीं बनाए जा सके — समयबद्ध शब्द नहीं मिले। .txt में सेव करें।",
        "id": "Tidak dapat membuat subtitle — tidak ditemukan kata bertanda waktu. Coba .txt.",
        "fa": "ساخت زیرنویس ممکن نشد — کلمات زمان‌بندی شده یافت نشد. .txt را امتحان کنید.",
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
        "hi": (
            "आपकी सांख्यिकी:\n"
            "ट्रांसक्रिप्शन: {transcriptions}\n"
            "कुल ऑडियो: {duration}\n"
            "पहली बार: {first_used}\n"
            "आखिरी बार: {last_used}"
        ),
        "id": (
            "Statistik Anda:\n"
            "Transkripsi: {transcriptions}\n"
            "Total audio: {duration}\n"
            "Pertama digunakan: {first_used}\n"
            "Terakhir digunakan: {last_used}"
        ),
        "fa": (
            "آمار شما:\n"
            "رونویسی‌ها: {transcriptions}\n"
            "کل صوت: {duration}\n"
            "اولین استفاده: {first_used}\n"
            "آخرین استفاده: {last_used}"
        ),
    },
    "transcription_timeout": {
        "en": "Transcription is taking too long. This can happen with very long recordings. Please try again — if the problem persists, try a shorter clip.",
        "ru": "Расшифровка занимает слишком много времени. Это может произойти с очень длинными записями. Попробуйте ещё раз — если проблема сохранится, попробуйте более короткий фрагмент.",
        "hi": "ट्रांसक्रिप्शन में बहुत समय लग रहा है। यह बहुत लंबी रिकॉर्डिंग के साथ हो सकता है। कृपया दोबारा कोशिश करें — अगर समस्या बनी रहे, तो छोटी क्लिप भेजें।",
        "id": "Transkripsi memakan waktu terlalu lama. Ini bisa terjadi dengan rekaman yang sangat panjang. Silakan coba lagi — jika masalah berlanjut, coba klip yang lebih pendek.",
        "fa": "رونویسی بیش از حد طول می‌کشد. این ممکن است با ضبط‌های خیلی طولانی اتفاق بیفتد. لطفاً دوباره امتحان کنید — اگر مشکل ادامه داشت، یک کلیپ کوتاه‌تر بفرستید.",
    },
    "download_timeout": {
        "en": "Could not download the file from Telegram. Please try sending it again.",
        "ru": "Не удалось загрузить файл из Telegram. Попробуйте отправить его ещё раз.",
        "hi": "Telegram से फाइल डाउनलोड नहीं हो सकी। कृपया इसे दोबारा भेजें।",
        "id": "Tidak dapat mengunduh file dari Telegram. Silakan coba kirim ulang.",
        "fa": "دانلود فایل از تلگرام ممکن نشد. لطفاً دوباره ارسال کنید.",
    },
    "secretary_manual_prompt": {
        "en": "🎙 Voice message ({duration})",
        "ru": "🎙 Голосовое сообщение ({duration})",
        "hi": "🎙 वॉइस मैसेज ({duration})",
        "id": "🎙 Pesan suara ({duration})",
        "fa": "🎙 پیام صوتی ({duration})",
    },
    "stats_direct": {
        "en": "Direct: {transcriptions} transcriptions, {duration}",
        "ru": "Прямые: {transcriptions} расшифровок, {duration}",
        "hi": "प्रत्यक्ष: {transcriptions} ट्रांसक्रिप्शन, {duration}",
        "id": "Langsung: {transcriptions} transkripsi, {duration}",
        "fa": "مستقیم: {transcriptions} رونویسی, {duration}",
    },
    "stats_secretary": {
        "en": "Secretary: {transcriptions} transcriptions, {duration}",
        "ru": "Секретарь: {transcriptions} расшифровок, {duration}",
        "hi": "सेक्रेटरी: {transcriptions} ट्रांसक्रिप्शन, {duration}",
        "id": "Sekretaris: {transcriptions} transkripsi, {duration}",
        "fa": "منشی: {transcriptions} رونویسی, {duration}",
    },
    "stats_total": {
        "en": "Total: {transcriptions} transcriptions, {duration}",
        "ru": "Всего: {transcriptions} расшифровок, {duration}",
        "hi": "कुल: {transcriptions} ट्रांसक्रिप्शन, {duration}",
        "id": "Total: {transcriptions} transkripsi, {duration}",
        "fa": "مجموع: {transcriptions} رونویسی, {duration}",
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
        "hi": (
            "पहली बार: {first_used}\n"
            "आखिरी बार: {last_used}"
        ),
        "id": (
            "Pertama digunakan: {first_used}\n"
            "Terakhir: {last_used}"
        ),
        "fa": (
            "اولین استفاده: {first_used}\n"
            "آخرین: {last_used}"
        ),
    },
    "btn_summarize": {
        "en": "Summarize",
        "ru": "Краткое содержание",
        "hi": "सारांश",
        "id": "Ringkasan",
        "fa": "خلاصه",
    },
    "btn_save_file": {
        "en": "Save as file",
        "ru": "Сохранить как файл",
        "hi": "फाइल में सेव",
        "id": "Simpan sebagai file",
        "fa": "ذخیره به‌عنوان فایل",
    },
    "btn_transcribe": {
        "en": "📝 Transcribe",
        "ru": "📝 Расшифровать",
        "hi": "📝 ट्रांसक्राइब",
        "id": "📝 Transkripsikan",
        "fa": "📝 رونویسی",
    },
    "secretary_setup": {
        "en": (
            "✨ <b>Transcribe voice messages right in your DMs</b>\n"
            "\n"
            "Go to your <b>Account → Chat Automation</b> in Telegram settings and add this bot. Once connected, I'll add a “Transcribe” button under voice messages and video notes in your private chats."
        ),
        "ru": (
            "✨ <b>Расшифровывайте голосовые прямо в личных чатах</b>\n"
            "\n"
            "Откройте <b>Аккаунт → Чат-автоматизация</b> в настройках Telegram и добавьте этого бота. После подключения я буду добавлять кнопку «Расшифровать» под голосовыми сообщениями и видеосообщениями в ваших личных чатах."
        ),
        "hi": (
            "✨ <b>अपनी DM में ही वॉइस मैसेज ट्रांसक्राइब करें</b>\n"
            "\n"
            "Telegram सेटिंग्स में <b>Account → Chat Automation</b> पर जाएँ और इस बॉट को जोड़ें। कनेक्ट होने के बाद, मैं आपकी निजी चैट में वॉइस मैसेज और वीडियो नोट के नीचे एक “ट्रांसक्राइब” बटन जोड़ूँगा।"
        ),
        "id": (
            "✨ <b>Transkripsikan pesan suara langsung di DM Anda</b>\n"
            "\n"
            "Buka <b>Account → Chat Automation</b> di pengaturan Telegram dan tambahkan bot ini. Setelah terhubung, saya akan menambahkan tombol “Transkripsi” di bawah pesan suara dan video note di chat pribadi Anda."
        ),
        "fa": (
            "✨ <b>پیام‌های صوتی را همان‌جا در دایرکت رونویسی کنید</b>\n"
            "\n"
            "در تنظیمات تلگرام به <b>Account → Chat Automation</b> بروید و این بات را اضافه کنید. پس از اتصال، زیر پیام‌های صوتی و ویدیو نوت‌ها در گفت‌وگوهای خصوصی‌تان یک دکمهٔ «رونویسی» اضافه می‌کنم."
        ),
    },
    "secretary_connected": {
        "en": (
            "✅ Transcription is already set up in your DMs.\n"
            "\n"
            "I add a “Transcribe” button under voice messages and video notes in your private chats. To turn it off, remove this bot from Account → Chat Automation in Telegram settings."
        ),
        "ru": (
            "✅ Транскрипция уже настроена в ваших личных чатах.\n"
            "\n"
            "Я добавляю кнопку «Расшифровать» под голосовыми сообщениями и видеосообщениями. Чтобы отключить, удалите бота в разделе Аккаунт → Чат-автоматизация в настройках Telegram."
        ),
        "hi": (
            "✅ आपकी DM में ट्रांसक्रिप्शन पहले से सेट है।\n"
            "\n"
            "मैं आपकी निजी चैट में वॉइस मैसेज और वीडियो नोट के नीचे एक “ट्रांसक्राइब” बटन जोड़ता हूँ। बंद करने के लिए, Telegram सेटिंग्स में Account → Chat Automation से इस बॉट को हटाएँ।"
        ),
        "id": (
            "✅ Transkripsi sudah aktif di DM Anda.\n"
            "\n"
            "Saya menambahkan tombol “Transkripsi” di bawah pesan suara dan video note di chat pribadi Anda. Untuk menonaktifkan, hapus bot ini dari Account → Chat Automation di pengaturan Telegram."
        ),
        "fa": (
            "✅ رونویسی از قبل در دایرکت شما فعال است.\n"
            "\n"
            "زیر پیام‌های صوتی و ویدیو نوت‌ها در گفت‌وگوهای خصوصی یک دکمهٔ «رونویسی» اضافه می‌کنم. برای خاموش‌کردن، این بات را از Account → Chat Automation در تنظیمات تلگرام حذف کنید."
        ),
    },
    "btn_secretary_setup": {
        "en": "✨ Set up transcription in DMs",
        "ru": "✨ Настроить расшифровку в чатах",
        "hi": "✨ DM में ट्रांसक्रिप्शन सेट करें",
        "id": "✨ Atur transkripsi di DM",
        "fa": "✨ تنظیم رونویسی در چت‌ها",
    },
    "btn_secretary_settings": {
        "en": "✅ Transcription is set up",
        "ru": "✅ Транскрипция настроена",
        "hi": "✅ ट्रांसक्रिप्शन सेट है",
        "id": "✅ Transkripsi sudah aktif",
        "fa": "✅ رونویسی فعال است",
    },
    "text_nudge": {
        "en": "I work with voice messages, audio, and video. Send or forward one and I'll transcribe it!",
        "ru": "Я работаю с голосовыми, аудио и видео. Отправьте или перешлите — и я расшифрую!",
        "hi": "मैं वॉइस मैसेज, ऑडियो और वीडियो के साथ काम करता हूँ। भेजें या फॉरवर्ड करें और मैं ट्रांसक्राइब कर दूँगा!",
        "id": "Saya bekerja dengan pesan suara, audio, dan video. Kirim atau teruskan dan saya akan mentranskripsikannya!",
        "fa": "من با پیام‌های صوتی، صوت و ویدیو کار می‌کنم. بفرستید یا فوروارد کنید و رونویسی می‌کنم!",
    },
    "secretary_welcome": {
        "en": (
            "✅ <b>Transcription is set up!</b>\n"
            "\n"
            "When someone sends a voice message or video note in your private chats, I'll add a “Transcribe” button. You or the other person can tap it to see the text.\n"
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
        "hi": (
            "✅ <b>ट्रांसक्रिप्शन सेट हो गया!</b>\n"
            "\n"
            "जब आपकी निजी चैट में कोई वॉइस मैसेज या वीडियो नोट भेजेगा, तो मैं एक “ट्रांसक्राइब” बटन जोड़ूँगा। टेक्स्ट देखने के लिए आप या सामने वाला उसे टैप कर सकते हैं।\n"
            "\n"
            "बिना ट्रांसक्राइब किए प्रॉम्प्ट एक दिन बाद अपने आप हट जाते हैं।"
        ),
        "id": (
            "✅ <b>Transkripsi sudah aktif!</b>\n"
            "\n"
            "Ketika seseorang mengirim pesan suara atau video note di chat pribadi Anda, saya akan menambahkan tombol “Transkripsi”. Anda atau lawan bicara bisa menekannya untuk melihat teksnya.\n"
            "\n"
            "Prompt yang belum ditranskripsi akan dihapus otomatis setelah satu hari."
        ),
        "fa": (
            "✅ <b>رونویسی فعال شد!</b>\n"
            "\n"
            "وقتی کسی در گفت‌وگوهای خصوصی شما پیام صوتی یا ویدیو نوت بفرستد، یک دکمهٔ «رونویسی» اضافه می‌کنم. شما یا طرف مقابل می‌توانید برای دیدن متن روی آن بزنید.\n"
            "\n"
            "پیام‌های رونویسی‌نشده پس از یک روز به‌طور خودکار حذف می‌شوند."
        ),
    },
    "broadcast_secretary": {
        "en": (
            "🎙 <b>New: transcribe voice messages right in your chats</b>\n"
            "\n"
            "You can now add me to your private chats so a “Transcribe” button "
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
    },
    "secretary_promo": {
        "en": "Or add me as your secretary and transcribe the messages right in your chats!",
    },
    "video_timeout": {
        "en": "Could not process this video. Please try again or send just the audio.",
        "ru": "Не удалось обработать это видео. Попробуйте ещё раз или отправьте только аудио.",
        "hi": "इस वीडियो को प्रोसेस नहीं किया जा सका। कृपया दोबारा कोशिश करें या सिर्फ ऑडियो भेजें।",
        "id": "Tidak dapat memproses video ini. Silakan coba lagi atau kirim audionya saja.",
        "fa": "پردازش این ویدیو ممکن نشد. لطفاً دوباره امتحان کنید یا فقط صوت را بفرستید.",
    },
}


DEFAULT_LANG = "en"


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
