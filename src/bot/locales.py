"""Localised user-facing strings.

Supported languages (top Telegram markets):
en, ru, hi, id, pt, uk, ar, fa, de, tr, es, fr, uz, am, ko

Usage:
    from src.bot.locales import t
    text = t("greeting", lang, user=mention_html)
"""

from __future__ import annotations

# --- all translatable message keys ---

_STRINGS: dict[str, dict[str, str]] = {
    # /start greeting  ({user} placeholder)
    "greeting": {
        "en": (
            "Welcome {user}! Send me a voice message, audio file, or video note "
            "and I'll transcribe it for you."
        ),
        "ru": (
            "Добро пожаловать {user}! Отправьте мне голосовое сообщение, аудиофайл "
            "или видеозаметку, и я сделаю расшифровку."
        ),
        "hi": (
            "स्वागत है {user}! मुझे एक वॉइस मैसेज, ऑडियो फाइल या वीडियो नोट भेजें "
            "और मैं उसे ट्रांसक्राइब कर दूँगा।"
        ),
        "id": (
            "Selamat datang {user}! Kirimkan pesan suara, file audio, atau catatan video "
            "dan saya akan mentranskripsikannya untuk Anda."
        ),
        "pt": (
            "Bem-vindo {user}! Envie-me uma mensagem de voz, arquivo de áudio ou "
            "nota de vídeo e eu farei a transcrição."
        ),
        "uk": (
            "Ласкаво просимо {user}! Надішліть мені голосове повідомлення, аудіофайл "
            "або відеонотатку, і я зроблю транскрипцію."
        ),
        "ar": (
            "مرحبًا {user}! أرسل لي رسالة صوتية أو ملف صوتي أو ملاحظة فيديو "
            "وسأقوم بتحويلها إلى نص."
        ),
        "fa": (
            "خوش آمدید {user}! یک پیام صوتی، فایل صوتی یا یادداشت ویدیویی "
            "برایم بفرستید و من آن را رونویسی می‌کنم."
        ),
        "de": (
            "Willkommen {user}! Senden Sie mir eine Sprachnachricht, Audiodatei "
            "oder Videonachricht und ich werde sie transkribieren."
        ),
        "tr": (
            "Hoş geldiniz {user}! Bana bir sesli mesaj, ses dosyası veya video notu "
            "gönderin, sizin için yazıya dökeyim."
        ),
        "es": (
            "¡Bienvenido {user}! Envíame un mensaje de voz, archivo de audio o "
            "nota de video y lo transcribiré para ti."
        ),
        "fr": (
            "Bienvenue {user} ! Envoyez-moi un message vocal, un fichier audio ou "
            "une note vidéo et je le transcrirai pour vous."
        ),
        "uz": (
            "Xush kelibsiz {user}! Menga ovozli xabar, audio fayl yoki video eslatma "
            "yuboring va men uni matn shaklida yozib beraman."
        ),
        "am": (
            "እንኳን ደህና መጡ {user}! የድምፅ መልእክት፣ የኦዲዮ ፋይል ወይም የቪዲዮ ማስታወሻ "
            "ይላኩልኝ እና ወደ ጽሑፍ እለውጠዋለሁ።"
        ),
        "ko": (
            "환영합니다 {user}! 음성 메시지, 오디오 파일 또는 비디오 노트를 보내주시면 "
            "텍스트로 변환해 드리겠습니다."
        ),
    },
    # /help
    "help": {
        "en": (
            "🎙 Send me a voice message, audio file, video note, "
            "or video — I'll transcribe it right away.\n\n"
            "After transcription you can:\n"
            "• Summarize — get a short summary\n"
            "• Save as file — download as .txt or .srt (subtitles)\n\n"
            "Multiple speakers are detected automatically.\n\n"
            "Commands:\n"
            "/start — welcome message\n"
            "/help — this message\n"
            "/stats — your usage statistics"
        ),
        "ru": (
            "🎙 Отправьте мне голосовое сообщение, аудиофайл, "
            "видеозаметку или видео — я сразу сделаю расшифровку.\n\n"
            "После расшифровки вы можете:\n"
            "• Краткое содержание — получить сводку\n"
            "• Сохранить как файл — скачать в .txt или .srt (субтитры)\n\n"
            "Несколько говорящих распознаются автоматически.\n\n"
            "Команды:\n"
            "/start — приветствие\n"
            "/help — эта справка\n"
            "/stats — ваша статистика использования"
        ),
        "hi": (
            "🎙 मुझे वॉइस मैसेज, ऑडियो फाइल, वीडियो नोट "
            "या वीडियो भेजें — मैं तुरंत ट्रांसक्राइब कर दूँगा।\n\n"
            "ट्रांसक्रिप्शन के बाद आप कर सकते हैं:\n"
            "• सारांश — संक्षिप्त सारांश प्राप्त करें\n"
            "• फाइल में सेव — .txt या .srt (सबटाइटल) में डाउनलोड करें\n\n"
            "कई वक्ताओं की पहचान स्वचालित रूप से होती है।\n\n"
            "कमांड:\n"
            "/start — स्वागत संदेश\n"
            "/help — यह संदेश\n"
            "/stats — आपकी उपयोग सांख्यिकी"
        ),
        "id": (
            "🎙 Kirimkan pesan suara, file audio, catatan video, "
            "atau video — saya akan langsung mentranskripsikannya.\n\n"
            "Setelah transkripsi Anda dapat:\n"
            "• Ringkasan — dapatkan ringkasan singkat\n"
            "• Simpan sebagai file — unduh sebagai .txt atau .srt (subtitle)\n\n"
            "Beberapa pembicara terdeteksi secara otomatis.\n\n"
            "Perintah:\n"
            "/start — pesan selamat datang\n"
            "/help — pesan ini\n"
            "/stats — statistik penggunaan Anda"
        ),
        "pt": (
            "🎙 Envie-me uma mensagem de voz, arquivo de áudio, "
            "nota de vídeo ou vídeo — eu transcrevo na hora.\n\n"
            "Após a transcrição você pode:\n"
            "• Resumir — obter um resumo curto\n"
            "• Salvar como arquivo — baixar em .txt ou .srt (legendas)\n\n"
            "Múltiplos falantes são detectados automaticamente.\n\n"
            "Comandos:\n"
            "/start — mensagem de boas-vindas\n"
            "/help — esta mensagem\n"
            "/stats — suas estatísticas de uso"
        ),
        "uk": (
            "🎙 Надішліть мені голосове повідомлення, аудіофайл, "
            "відеонотатку або відео — я одразу зроблю транскрипцію.\n\n"
            "Після транскрипції ви можете:\n"
            "• Підсумок — отримати короткий зміст\n"
            "• Зберегти як файл — завантажити в .txt або .srt (субтитри)\n\n"
            "Кілька мовців розпізнаються автоматично.\n\n"
            "Команди:\n"
            "/start — привітання\n"
            "/help — ця довідка\n"
            "/stats — ваша статистика використання"
        ),
        "ar": (
            "🎙 أرسل لي رسالة صوتية أو ملف صوتي أو ملاحظة فيديو "
            "أو فيديو — سأقوم بتحويلها إلى نص فوراً.\n\n"
            "بعد التحويل يمكنك:\n"
            "• تلخيص — الحصول على ملخص قصير\n"
            "• حفظ كملف — تنزيل بصيغة .txt أو .srt (ترجمات)\n\n"
            "يتم الكشف عن المتحدثين المتعددين تلقائياً.\n\n"
            "الأوامر:\n"
            "/start — رسالة الترحيب\n"
            "/help — هذه الرسالة\n"
            "/stats — إحصائيات استخدامك"
        ),
        "fa": (
            "🎙 یک پیام صوتی، فایل صوتی، یادداشت ویدیویی "
            "یا ویدیو برایم بفرستید — فوراً رونویسی می‌کنم.\n\n"
            "بعد از رونویسی می‌توانید:\n"
            "• خلاصه — یک خلاصه کوتاه دریافت کنید\n"
            "• ذخیره به‌عنوان فایل — دانلود به‌صورت .txt یا .srt (زیرنویس)\n\n"
            "چندین گوینده به‌صورت خودکار شناسایی می‌شوند.\n\n"
            "دستورات:\n"
            "/start — پیام خوشامدگویی\n"
            "/help — این پیام\n"
            "/stats — آمار استفاده شما"
        ),
        "de": (
            "🎙 Senden Sie mir eine Sprachnachricht, Audiodatei, "
            "Videonachricht oder Video — ich transkribiere es sofort.\n\n"
            "Nach der Transkription können Sie:\n"
            "• Zusammenfassen — eine kurze Zusammenfassung erhalten\n"
            "• Als Datei speichern — als .txt oder .srt (Untertitel) herunterladen\n\n"
            "Mehrere Sprecher werden automatisch erkannt.\n\n"
            "Befehle:\n"
            "/start — Willkommensnachricht\n"
            "/help — diese Nachricht\n"
            "/stats — Ihre Nutzungsstatistiken"
        ),
        "tr": (
            "🎙 Bana sesli mesaj, ses dosyası, video notu "
            "veya video gönderin — hemen yazıya dökerim.\n\n"
            "Dönüştürmeden sonra şunları yapabilirsiniz:\n"
            "• Özetle — kısa bir özet alın\n"
            "• Dosya olarak kaydet — .txt veya .srt (altyazı) olarak indirin\n\n"
            "Birden fazla konuşmacı otomatik olarak algılanır.\n\n"
            "Komutlar:\n"
            "/start — hoş geldiniz mesajı\n"
            "/help — bu mesaj\n"
            "/stats — kullanım istatistikleriniz"
        ),
        "es": (
            "🎙 Envíame un mensaje de voz, archivo de audio, "
            "nota de video o video — lo transcribiré de inmediato.\n\n"
            "Después de la transcripción puedes:\n"
            "• Resumir — obtener un resumen breve\n"
            "• Guardar como archivo — descargar en .txt o .srt (subtítulos)\n\n"
            "Se detectan múltiples hablantes automáticamente.\n\n"
            "Comandos:\n"
            "/start — mensaje de bienvenida\n"
            "/help — este mensaje\n"
            "/stats — tus estadísticas de uso"
        ),
        "fr": (
            "🎙 Envoyez-moi un message vocal, un fichier audio, "
            "une note vidéo ou une vidéo — je le transcrirai immédiatement.\n\n"
            "Après la transcription vous pouvez :\n"
            "• Résumer — obtenir un résumé court\n"
            "• Enregistrer en fichier — télécharger en .txt ou .srt (sous-titres)\n\n"
            "Les locuteurs multiples sont détectés automatiquement.\n\n"
            "Commandes :\n"
            "/start — message de bienvenue\n"
            "/help — ce message\n"
            "/stats — vos statistiques d'utilisation"
        ),
        "uz": (
            "🎙 Menga ovozli xabar, audio fayl, video eslatma "
            "yoki video yuboring — darhol matn shaklida yozib beraman.\n\n"
            "Transkripsiyadan keyin siz:\n"
            "• Xulosa — qisqa xulosa oling\n"
            "• Fayl sifatida saqlash — .txt yoki .srt (subtitrlar) sifatida yuklab oling\n\n"
            "Bir nechta so'zlovchilar avtomatik aniqlanadi.\n\n"
            "Buyruqlar:\n"
            "/start — xush kelibsiz xabari\n"
            "/help — ushbu xabar\n"
            "/stats — foydalanish statistikasi"
        ),
        "am": (
            "🎙 የድምፅ መልእክት፣ የኦዲዮ ፋይል፣ የቪዲዮ ማስታወሻ "
            "ወይም ቪዲዮ ይላኩልኝ — ወዲያውኑ እጽፈዋለሁ።\n\n"
            "ከተቀየረ በኋላ ማድረግ የሚችሉት:\n"
            "• ማጠቃለያ — አጭር ማጠቃለያ ያግኙ\n"
            "• እንደ ፋይል ያስቀምጡ — በ .txt ወይም .srt (ንዑስ ጽሑፍ) ያውርዱ\n\n"
            "ብዙ ተናጋሪዎች በራስ-ሰር ይታወቃሉ።\n\n"
            "ትዕዛዞች:\n"
            "/start — የእንኳን ደህና መጡ መልእክት\n"
            "/help — ይህ መልእክት\n"
            "/stats — የእርስዎ የአጠቃቀም ስታቲስቲክስ"
        ),
        "ko": (
            "🎙 음성 메시지, 오디오 파일, 비디오 노트 "
            "또는 비디오를 보내주세요 — 바로 텍스트로 변환해 드립니다.\n\n"
            "변환 후 할 수 있는 것:\n"
            "• 요약 — 짧은 요약 받기\n"
            "• 파일로 저장 — .txt 또는 .srt(자막)로 다운로드\n\n"
            "여러 화자가 자동으로 감지됩니다.\n\n"
            "명령어:\n"
            "/start — 환영 메시지\n"
            "/help — 이 메시지\n"
            "/stats — 사용 통계"
        ),
    },
    # "Transcribing..." processing message
    "transcribing": {
        "en": "Transcribing...",
        "ru": "Расшифровываю...",
        "hi": "ट्रांसक्राइब हो रहा है...",
        "id": "Sedang mentranskripsikan...",
        "pt": "Transcrevendo...",
        "uk": "Транскрибую...",
        "ar": "جارٍ التحويل...",
        "fa": "در حال رونویسی...",
        "de": "Transkribiere...",
        "tr": "Yazıya dökülüyor...",
        "es": "Transcribiendo...",
        "fr": "Transcription en cours...",
        "uz": "Matn shaklida yozilmoqda...",
        "am": "ወደ ጽሑፍ በመቀየር ላይ...",
        "ko": "텍스트 변환 중...",
    },
    # File too large (20 MB limit)
    "file_too_large": {
        "en": (
            "This file is too large to download. "
            "Telegram limits bot file downloads to 20 MB.\n"
            "Voice messages and video notes are compressed "
            "by Telegram and usually work fine — this limit "
            "mainly affects large audio/video files sent "
            "as attachments.\n"
            "You can try compressing or trimming the file "
            "before sending."
        ),
        "ru": (
            "Этот файл слишком большой для загрузки. "
            "Telegram ограничивает загрузку файлов ботами до 20 МБ.\n"
            "Голосовые сообщения и видеозаметки сжимаются "
            "Telegram и обычно работают нормально — это ограничение "
            "в основном касается больших аудио/видео файлов, "
            "отправленных как вложения.\n"
            "Попробуйте сжать или обрезать файл перед отправкой."
        ),
        "hi": (
            "यह फाइल डाउनलोड करने के लिए बहुत बड़ी है। "
            "Telegram बॉट फाइल डाउनलोड को 20 MB तक सीमित करता है।\n"
            "वॉइस मैसेज और वीडियो नोट Telegram द्वारा संपीड़ित होते हैं "
            "और आमतौर पर ठीक काम करते हैं।\n"
            "भेजने से पहले फाइल को संपीड़ित या ट्रिम करने का प्रयास करें।"
        ),
        "id": (
            "File ini terlalu besar untuk diunduh. "
            "Telegram membatasi unduhan file bot hingga 20 MB.\n"
            "Pesan suara dan catatan video dikompresi oleh Telegram "
            "dan biasanya berfungsi dengan baik.\n"
            "Coba kompres atau potong file sebelum mengirim."
        ),
        "pt": (
            "Este arquivo é muito grande para baixar. "
            "O Telegram limita downloads de bots a 20 MB.\n"
            "Mensagens de voz e notas de vídeo são comprimidas "
            "pelo Telegram e geralmente funcionam bem.\n"
            "Tente comprimir ou cortar o arquivo antes de enviar."
        ),
        "uk": (
            "Цей файл занадто великий для завантаження. "
            "Telegram обмежує завантаження файлів ботами до 20 МБ.\n"
            "Голосові повідомлення та відеонотатки стискаються "
            "Telegram і зазвичай працюють нормально.\n"
            "Спробуйте стиснути або обрізати файл перед відправкою."
        ),
        "ar": (
            "هذا الملف كبير جداً للتنزيل. "
            "يحدد Telegram تنزيلات البوت بـ 20 ميغابايت.\n"
            "الرسائل الصوتية وملاحظات الفيديو مضغوطة بواسطة Telegram "
            "وعادةً تعمل بشكل جيد.\n"
            "حاول ضغط الملف أو قصه قبل الإرسال."
        ),
        "fa": (
            "این فایل برای دانلود خیلی بزرگ است. "
            "تلگرام دانلود فایل توسط ربات را به ۲۰ مگابایت محدود می‌کند.\n"
            "پیام‌های صوتی و یادداشت‌های ویدیویی توسط تلگرام فشرده می‌شوند "
            "و معمولاً به خوبی کار می‌کنند.\n"
            "قبل از ارسال، فایل را فشرده یا برش دهید."
        ),
        "de": (
            "Diese Datei ist zu groß zum Herunterladen. "
            "Telegram begrenzt Bot-Downloads auf 20 MB.\n"
            "Sprachnachrichten und Videonachrichten werden von Telegram "
            "komprimiert und funktionieren normalerweise problemlos.\n"
            "Versuchen Sie die Datei vor dem Senden zu komprimieren oder zu kürzen."
        ),
        "tr": (
            "Bu dosya indirmek için çok büyük. "
            "Telegram bot dosya indirmelerini 20 MB ile sınırlar.\n"
            "Sesli mesajlar ve video notları Telegram tarafından sıkıştırılır "
            "ve genellikle sorunsuz çalışır.\n"
            "Göndermeden önce dosyayı sıkıştırmayı veya kırpmayı deneyin."
        ),
        "es": (
            "Este archivo es demasiado grande para descargar. "
            "Telegram limita las descargas de bots a 20 MB.\n"
            "Los mensajes de voz y notas de video son comprimidos "
            "por Telegram y generalmente funcionan bien.\n"
            "Intenta comprimir o recortar el archivo antes de enviarlo."
        ),
        "fr": (
            "Ce fichier est trop volumineux pour être téléchargé. "
            "Telegram limite les téléchargements de bots à 20 Mo.\n"
            "Les messages vocaux et notes vidéo sont compressés "
            "par Telegram et fonctionnent généralement bien.\n"
            "Essayez de compresser ou raccourcir le fichier avant de l'envoyer."
        ),
        "uz": (
            "Bu fayl yuklab olish uchun juda katta. "
            "Telegram bot fayl yuklanishlarini 20 MB bilan cheklaydi.\n"
            "Ovozli xabarlar va video eslatmalar Telegram tomonidan "
            "siqiladi va odatda yaxshi ishlaydi.\n"
            "Yuborishdan oldin faylni siqish yoki qirqishga harakat qiling."
        ),
        "am": (
            "ይህ ፋይል ለማውረድ በጣም ትልቅ ነው። "
            "Telegram የቦት ፋይል ማውረዶችን ወደ 20 MB ይገድባል።\n"
            "የድምፅ መልእክቶች እና የቪዲዮ ማስታወሻዎች በ Telegram ተጨምቀው "
            "ብዙ ጊዜ ጥሩ ይሰራሉ።\n"
            "ከመላክዎ በፊት ፋይሉን ለመጭመቅ ወይም ለመቁረጥ ይሞክሩ።"
        ),
        "ko": (
            "이 파일은 다운로드하기에 너무 큽니다. "
            "Telegram은 봇 파일 다운로드를 20MB로 제한합니다.\n"
            "음성 메시지와 비디오 노트는 Telegram에서 압축되어 "
            "보통 잘 작동합니다.\n"
            "보내기 전에 파일을 압축하거나 자르세요."
        ),
    },
    # Audio too long
    "audio_too_long": {
        "en": "This audio is too long ({duration}). Max supported duration is {max_min} minutes.",
        "ru": "Это аудио слишком длинное ({duration}). Максимальная поддерживаемая длительность — {max_min} минут.",
        "hi": "यह ऑडियो बहुत लंबा है ({duration})। अधिकतम समर्थित अवधि {max_min} मिनट है।",
        "id": "Audio ini terlalu panjang ({duration}). Durasi maksimal yang didukung adalah {max_min} menit.",
        "pt": "Este áudio é muito longo ({duration}). A duração máxima suportada é {max_min} minutos.",
        "uk": "Це аудіо занадто довге ({duration}). Максимальна підтримувана тривалість — {max_min} хвилин.",
        "ar": "هذا الصوت طويل جداً ({duration}). الحد الأقصى المدعوم هو {max_min} دقيقة.",
        "fa": "این صوت خیلی طولانی است ({duration}). حداکثر مدت پشتیبانی شده {max_min} دقیقه است.",
        "de": "Dieses Audio ist zu lang ({duration}). Maximale unterstützte Dauer ist {max_min} Minuten.",
        "tr": "Bu ses çok uzun ({duration}). Desteklenen maksimum süre {max_min} dakikadır.",
        "es": "Este audio es demasiado largo ({duration}). La duración máxima soportada es {max_min} minutos.",
        "fr": "Cet audio est trop long ({duration}). La durée maximale supportée est de {max_min} minutes.",
        "uz": "Bu audio juda uzun ({duration}). Qo'llab-quvvatlanadigan maksimal davomiylik {max_min} daqiqa.",
        "am": "ይህ ኦዲዮ በጣም ረጅም ነው ({duration})። ከፍተኛ የሚደገፍ ርዝመት {max_min} ደቂቃ ነው።",
        "ko": "이 오디오가 너무 깁니다 ({duration}). 최대 지원 시간은 {max_min}분입니다.",
    },
    # No speech detected
    "no_speech": {
        "en": "No speech was detected in this audio. The recording may be silent or too short.",
        "ru": "В этом аудио не обнаружена речь. Запись может быть беззвучной или слишком короткой.",
        "hi": "इस ऑडियो में कोई भाषण नहीं मिला। रिकॉर्डिंग शायद साइलेंट या बहुत छोटी है।",
        "id": "Tidak ada ucapan yang terdeteksi dalam audio ini. Rekaman mungkin kosong atau terlalu pendek.",
        "pt": "Nenhuma fala foi detectada neste áudio. A gravação pode estar silenciosa ou muito curta.",
        "uk": "У цьому аудіо не виявлено мовлення. Запис може бути беззвучним або занадто коротким.",
        "ar": "لم يتم اكتشاف أي كلام في هذا الصوت. قد يكون التسجيل صامتاً أو قصيراً جداً.",
        "fa": "هیچ گفتاری در این صوت شناسایی نشد. ضبط ممکن است ساکت یا خیلی کوتاه باشد.",
        "de": "In diesem Audio wurde keine Sprache erkannt. Die Aufnahme ist möglicherweise stumm oder zu kurz.",
        "tr": "Bu ses kaydında konuşma algılanmadı. Kayıt sessiz veya çok kısa olabilir.",
        "es": "No se detectó habla en este audio. La grabación puede estar en silencio o ser muy corta.",
        "fr": "Aucune parole détectée dans cet audio. L'enregistrement est peut-être silencieux ou trop court.",
        "uz": "Ushbu audioda nutq aniqlanmadi. Yozuv sokin yoki juda qisqa bo'lishi mumkin.",
        "am": "በዚህ ኦዲዮ ውስጥ ንግግር አልተገኘም። ቀረጻው ጸጥ ያለ ወይም በጣም አጭር ሊሆን ይችላል።",
        "ko": "이 오디오에서 음성이 감지되지 않았습니다. 녹음이 무음이거나 너무 짧을 수 있습니다.",
    },
    # Something went wrong (bot/API error)
    "something_went_wrong": {
        "en": "Something went wrong on our end. Please try again later.",
        "ru": "Что-то пошло не так с нашей стороны. Пожалуйста, попробуйте позже.",
        "hi": "हमारी तरफ कुछ गलत हो गया। कृपया बाद में पुनः प्रयास करें।",
        "id": "Terjadi kesalahan di pihak kami. Silakan coba lagi nanti.",
        "pt": "Algo deu errado do nosso lado. Por favor, tente novamente mais tarde.",
        "uk": "Щось пішло не так з нашого боку. Будь ласка, спробуйте пізніше.",
        "ar": "حدث خطأ من جانبنا. يرجى المحاولة مرة أخرى لاحقاً.",
        "fa": "مشکلی از سمت ما پیش آمد. لطفاً بعداً دوباره امتحان کنید.",
        "de": "Bei uns ist ein Fehler aufgetreten. Bitte versuchen Sie es später erneut.",
        "tr": "Bizim tarafımızda bir sorun oluştu. Lütfen daha sonra tekrar deneyin.",
        "es": "Algo salió mal de nuestro lado. Por favor, inténtelo de nuevo más tarde.",
        "fr": "Un problème est survenu de notre côté. Veuillez réessayer plus tard.",
        "uz": "Bizning tomonda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
        "am": "ከኛ በኩል ችግር ተፈጠረ። እባክዎ ቆይተው እንደገና ይሞክሩ።",
        "ko": "저희 측에서 문제가 발생했습니다. 나중에 다시 시도해 주세요.",
    },
    # Could not extract audio from video
    "extraction_failed": {
        "en": "Could not extract audio from this video.",
        "ru": "Не удалось извлечь аудио из этого видео.",
        "hi": "इस वीडियो से ऑडियो नहीं निकाला जा सका।",
        "id": "Tidak dapat mengekstrak audio dari video ini.",
        "pt": "Não foi possível extrair o áudio deste vídeo.",
        "uk": "Не вдалося витягти аудіо з цього відео.",
        "ar": "تعذر استخراج الصوت من هذا الفيديو.",
        "fa": "استخراج صدا از این ویدیو ممکن نشد.",
        "de": "Audio konnte aus diesem Video nicht extrahiert werden.",
        "tr": "Bu videodan ses çıkarılamadı.",
        "es": "No se pudo extraer el audio de este video.",
        "fr": "Impossible d'extraire l'audio de cette vidéo.",
        "uz": "Ushbu videodan audio chiqarib bo'lmadi.",
        "am": "ከዚህ ቪዲዮ ኦዲዮ ማውጣት አልተቻለም።",
        "ko": "이 비디오에서 오디오를 추출할 수 없습니다.",
    },
    # Transcription expired
    "transcription_expired": {
        "en": "This transcription has expired.",
        "ru": "Эта расшифровка истекла.",
        "hi": "यह ट्रांसक्रिप्शन समाप्त हो गया है।",
        "id": "Transkripsi ini telah kedaluwarsa.",
        "pt": "Esta transcrição expirou.",
        "uk": "Ця розшифровка більше недоступна.",
        "ar": "انتهت صلاحية هذا التحويل النصي.",
        "fa": "این رونویسی منقضی شده است.",
        "de": "Diese Transkription ist abgelaufen.",
        "tr": "Bu transkripsiyon süresi doldu.",
        "es": "Esta transcripción ha expirado.",
        "fr": "Cette transcription a expiré.",
        "uz": "Ushbu transkripsiya muddati tugagan.",
        "am": "ይህ ጽሑፍ ጊዜው አልፎበታል።",
        "ko": "이 텍스트 변환이 만료되었습니다.",
    },
    # No usage recorded yet
    "no_usage": {
        "en": "No usage recorded yet.",
        "ru": "Статистика использования пока отсутствует.",
        "hi": "अभी तक कोई उपयोग दर्ज नहीं हुआ।",
        "id": "Belum ada penggunaan yang tercatat.",
        "pt": "Nenhum uso registrado ainda.",
        "uk": "Використання ще не зафіксовано.",
        "ar": "لم يتم تسجيل أي استخدام بعد.",
        "fa": "هنوز استفاده‌ای ثبت نشده است.",
        "de": "Noch keine Nutzung aufgezeichnet.",
        "tr": "Henüz kullanım kaydı yok.",
        "es": "Aún no se ha registrado uso.",
        "fr": "Aucune utilisation enregistrée pour le moment.",
        "uz": "Hali foydalanish qayd etilmagan.",
        "am": "እስካሁን ምንም አጠቃቀም አልተመዘገበም።",
        "ko": "아직 사용 기록이 없습니다.",
    },
    # SRT not available fallback
    "srt_no_words": {
        "en": "Word-level data is not available for SRT export. Try saving as .txt instead.",
        "ru": "Данные на уровне слов недоступны для экспорта SRT. Попробуйте сохранить как .txt.",
        "hi": "SRT निर्यात के लिए शब्द-स्तरीय डेटा उपलब्ध नहीं है। .txt में सेव करें।",
        "id": "Data tingkat kata tidak tersedia untuk ekspor SRT. Coba simpan sebagai .txt.",
        "pt": "Dados por palavra não disponíveis para exportação SRT. Tente salvar como .txt.",
        "uk": "Дані на рівні слів недоступні для експорту SRT. Спробуйте зберегти як .txt.",
        "ar": "بيانات التوقيت للكلمات غير متاحة لإنشاء ملف SRT. جرب الحفظ كـ .txt.",
        "fa": "داده‌های سطح کلمه برای صادرات SRT در دسترس نیست. به‌جای آن به‌صورت .txt ذخیره کنید.",
        "de": "Wort-Daten für SRT-Export nicht verfügbar. Versuchen Sie .txt.",
        "tr": "SRT dışa aktarımı için kelime düzeyi veri mevcut değil. .txt olarak kaydetmeyi deneyin.",
        "es": "Los datos a nivel de palabra no están disponibles para exportar SRT. Intente guardar como .txt.",
        "fr": "Les données mot par mot ne sont pas disponibles pour l'export SRT. Essayez .txt.",
        "uz": "SRT eksport uchun so'z darajasidagi ma'lumotlar mavjud emas. .txt sifatida saqlang.",
        "am": "ለ SRT ወደ ውጭ ለመላክ የቃል ደረጃ ውሂብ የለም። እንደ .txt ያስቀምጡ።",
        "ko": "SRT 내보내기에 필요한 단어 수준 데이터가 없습니다. .txt로 저장해 보세요.",
    },
    # SRT no timed words
    "srt_no_timed": {
        "en": "Could not generate subtitles — no timed words found. Try saving as .txt instead.",
        "ru": "Не удалось создать субтитры — не найдены слова с временными метками. Попробуйте .txt.",
        "hi": "सबटाइटल नहीं बनाए जा सके — समयबद्ध शब्द नहीं मिले। .txt में सेव करें।",
        "id": "Tidak dapat membuat subtitle — tidak ditemukan kata bertanda waktu. Coba .txt.",
        "pt": "Não foi possível gerar legendas — palavras com marcação temporal não encontradas. Tente .txt.",
        "uk": "Не вдалося створити субтитри — не знайдено слів з часовими мітками. Спробуйте .txt.",
        "ar": "تعذر إنشاء ملف الترجمة — لم يتم العثور على كلمات ذات توقيت. جرب .txt.",
        "fa": "ساخت زیرنویس ممکن نشد — کلمات زمان‌بندی شده یافت نشد. .txt را امتحان کنید.",
        "de": "Untertitel konnten nicht erstellt werden — keine Zeitstempel gefunden. Versuchen Sie .txt.",
        "tr": "Altyazı oluşturulamadı — zamanlı kelime bulunamadı. .txt olarak deneyin.",
        "es": "No se pudieron generar subtítulos — no se encontraron palabras con marca temporal. Intente .txt.",
        "fr": "Impossible de générer les sous-titres — aucun mot horodaté trouvé. Essayez .txt.",
        "uz": "Subtitrlarni yaratib bo'lmadi — vaqt belgilangan so'zlar topilmadi. .txt ni sinab ko'ring.",
        "am": "ንዑስ ጽሑፎችን ማመንጨት አልተቻለም — ጊዜ የተሰጣቸው ቃላት አልተገኙም። .txt ይሞክሩ።",
        "ko": "자막을 생성할 수 없습니다 — 시간 정보가 있는 단어를 찾을 수 없습니다. .txt로 저장해 보세요.",
    },
    # Stats header
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
        "pt": (
            "Suas estatísticas:\n"
            "Transcrições: {transcriptions}\n"
            "Total de áudio: {duration}\n"
            "Primeiro uso: {first_used}\n"
            "Último uso: {last_used}"
        ),
        "uk": (
            "Ваша статистика:\n"
            "Транскрипцій: {transcriptions}\n"
            "Всього аудіо: {duration}\n"
            "Перше використання: {first_used}\n"
            "Останнє використання: {last_used}"
        ),
        "ar": (
            "إحصائياتك:\n"
            "التحويلات: {transcriptions}\n"
            "إجمالي مدة الصوت: {duration}\n"
            "أول استخدام: {first_used}\n"
            "آخر استخدام: {last_used}"
        ),
        "fa": (
            "آمار شما:\n"
            "رونویسی‌ها: {transcriptions}\n"
            "کل صوت: {duration}\n"
            "اولین استفاده: {first_used}\n"
            "آخرین استفاده: {last_used}"
        ),
        "de": (
            "Ihre Statistiken:\n"
            "Transkriptionen: {transcriptions}\n"
            "Audio gesamt: {duration}\n"
            "Erste Nutzung: {first_used}\n"
            "Letzte Nutzung: {last_used}"
        ),
        "tr": (
            "İstatistikleriniz:\n"
            "Transkripsiyonlar: {transcriptions}\n"
            "Toplam ses: {duration}\n"
            "İlk kullanım: {first_used}\n"
            "Son kullanım: {last_used}"
        ),
        "es": (
            "Tus estadísticas:\n"
            "Transcripciones: {transcriptions}\n"
            "Audio total: {duration}\n"
            "Primer uso: {first_used}\n"
            "Último uso: {last_used}"
        ),
        "fr": (
            "Vos statistiques :\n"
            "Transcriptions : {transcriptions}\n"
            "Audio total : {duration}\n"
            "Première utilisation : {first_used}\n"
            "Dernière utilisation : {last_used}"
        ),
        "uz": (
            "Statistikangiz:\n"
            "Transkripsiyalar: {transcriptions}\n"
            "Jami audio: {duration}\n"
            "Birinchi foydalanish: {first_used}\n"
            "Oxirgi foydalanish: {last_used}"
        ),
        "am": (
            "የእርስዎ ስታቲስቲክስ:\n"
            "ጽሑፎች: {transcriptions}\n"
            "ጠቅላላ ኦዲዮ: {duration}\n"
            "የመጀመሪያ አጠቃቀም: {first_used}\n"
            "የመጨረሻ አጠቃቀም: {last_used}"
        ),
        "ko": (
            "사용 통계:\n"
            "변환 횟수: {transcriptions}\n"
            "총 오디오: {duration}\n"
            "처음 사용: {first_used}\n"
            "마지막 사용: {last_used}"
        ),
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
