use std::sync::Arc;
use teloxide::{
    prelude::*,
    types::{ChatAction, InlineKeyboardButton, InlineKeyboardMarkup},
};
use tokio::sync::Semaphore;
use tracing::{error, info, warn};

use crate::{
    admin_notifier::AdminNotifier, config::Config, errors::TranscribeError,
    storage::FileStore, telegram_api::TelegramFileDownloader, transcriber::Transcriber,
    utils::format_duration,
};

pub async fn handle_start(bot: Bot, msg: Message) -> ResponseResult<()> {
    let text = "Welcome to Voice Transcriber Bot! 🎤\n\n\
                Send me a voice message or audio file, and I'll transcribe it for you using OpenAI Whisper.\n\n\
                Commands:\n\
                /start - Show this message\n\
                /help - Show help information\n\
                /settings - Show current settings";

    bot.send_message(msg.chat.id, text).await?;
    Ok(())
}

pub async fn handle_help(bot: Bot, msg: Message) -> ResponseResult<()> {
    let text = "Voice Transcriber Bot Help 📖\n\n\
                This bot transcribes voice messages and audio files using OpenAI Whisper API.\n\n\
                How to use:\n\
                1. Send a voice message or audio file\n\
                2. Wait for the transcription (I'll show 'typing...' while processing)\n\
                3. Receive the transcribed text\n\n\
                Limitations:\n\
                - Maximum audio duration: 1 hour (3600 seconds)\n\
                - Maximum file size: 50 MB (Telegram's bot API limit)\n\
                - Long audio files may take several minutes to process\n\n\
                Features:\n\
                - Automatic transcription of voice messages\n\
                - Support for various audio formats\n\
                - Automatic retry logic for reliability\n\
                - Inline 'Summarize' button (coming soon)\n\n\
                If you encounter any issues, please contact the bot administrator.";

    bot.send_message(msg.chat.id, text).await?;
    Ok(())
}

pub async fn handle_settings(bot: Bot, msg: Message, config: Arc<Config>) -> ResponseResult<()> {
    let text = format!(
        "Current Settings ⚙️\n\n\
         Maximum audio duration: {} seconds ({})\n\
         Maximum file size: 50 MB\n\
         Concurrent transcriptions: {}\n\
         OpenAI timeout: {} seconds ({} minutes)",
        config.audio_max_seconds,
        format_duration(config.audio_max_seconds),
        config.concurrency_limit,
        config.openai_timeout_seconds,
        config.openai_timeout_seconds / 60
    );

    bot.send_message(msg.chat.id, text).await?;
    Ok(())
}

pub async fn handle_voice_message(
    bot: Bot,
    msg: Message,
    config: Arc<Config>,
    transcriber: Arc<dyn Transcriber>,
    file_store: Arc<FileStore>,
    semaphore: Arc<Semaphore>,
) -> ResponseResult<()> {
    let chat_id = msg.chat.id;
    let message_id = msg.id;

    // Extract voice or audio information
    let (file_id, duration, file_ext) = if let Some(voice) = msg.voice() {
        (voice.file.id.clone(), voice.duration, "ogg".to_string())
    } else if let Some(audio) = msg.audio() {
        let ext = audio
            .file_name
            .as_ref()
            .and_then(|name| {
                let name_str = name.as_str();
                name_str.rsplit('.').next().map(|s| s.to_string())
            })
            .unwrap_or_else(|| "mp3".to_string());
        (audio.file.id.clone(), audio.duration, ext)
    } else {
        return Ok(());
    };

    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);
    let username = msg
        .from()
        .and_then(|u| u.username.as_ref())
        .map(|s| s.to_string())
        .unwrap_or_else(|| "unknown".to_string());

    info!(
        "Received audio from user {} (id: {}), duration: {}s, message_id: {}",
        username, user_id, duration, message_id
    );

    // Check duration limit
    if duration > config.audio_max_seconds {
        let text = format!(
            "⚠️ Audio is too long (max {} seconds / {}).\n\
             Your audio: {} seconds / {}",
            config.audio_max_seconds,
            format_duration(config.audio_max_seconds),
            duration,
            format_duration(duration)
        );

        bot.send_message(chat_id, text).await?;

        // Notify admins
        let notifier = AdminNotifier::new(bot.clone(), config.clone());
        notifier
            .notify_duration_exceeded(user_id, &username, message_id.0, duration, config.audio_max_seconds)
            .await;

        return Ok(());
    }

    // Acquire semaphore permit
    let permit = semaphore.clone().acquire_owned().await;
    if permit.is_err() {
        bot.send_message(
            chat_id,
            "Sorry, the system is currently busy. Please try again later.",
        )
        .await?;
        return Ok(());
    }
    let permit = permit.unwrap();

    // Clone for async task
    let bot_clone = bot.clone();
    let config_clone = config.clone();
    let transcriber_clone = transcriber.clone();
    let file_store_clone = file_store.clone();

    tokio::spawn(async move {
        // Send typing action
        if let Err(e) = bot_clone
            .send_chat_action(chat_id, ChatAction::Typing)
            .await
        {
            error!("Failed to send typing action: {}", e);
        }

        // Initialize file downloader
        let downloader = match TelegramFileDownloader::new(config_clone.telegram_token.clone()) {
            Ok(d) => d,
            Err(e) => {
                error!("Failed to create file downloader: {}", e);
                let _ = bot_clone
                    .send_message(chat_id, "Sorry, failed to initialize file downloader.")
                    .await;
                drop(permit);
                return;
            }
        };

        // Get file info to check size
        let file_info = match downloader.get_file_info(&file_id).await {
            Ok(info) => info,
            Err(e) => {
                error!("Failed to get file info: {}", e);
                let notifier = AdminNotifier::new(bot_clone.clone(), config_clone.clone());
                notifier
                    .notify_telegram_error(
                        user_id,
                        &username,
                        message_id.0,
                        "FileInfoError",
                        &e.to_string(),
                    )
                    .await;

                let _ = bot_clone
                    .send_message(
                        chat_id,
                        "Sorry, failed to get file information from Telegram.",
                    )
                    .await;
                drop(permit);
                return;
            }
        };

        // Check file size
        if downloader.is_file_too_large(file_info.file_size) {
            let file_size = file_info.file_size.unwrap_or(0);
            let max_size = TelegramFileDownloader::max_file_size();

            warn!(
                "File too large for user {}: {} bytes (max: {} bytes)",
                user_id, file_size, max_size
            );

            let text = format!(
                "⚠️ This audio file is too large for Telegram to deliver to bots.\n\
                 File size: {:.2} MB\n\
                 Maximum: {:.2} MB\n\n\
                 Please send a shorter voice message.",
                file_size as f64 / 1_000_000.0,
                max_size as f64 / 1_000_000.0
            );

            let _ = bot_clone.send_message(chat_id, text).await;

            // Notify admins
            let notifier = AdminNotifier::new(bot_clone.clone(), config_clone.clone());
            notifier
                .notify_oversized_file(user_id, &username, message_id.0, file_size, max_size)
                .await;

            drop(permit);
            return;
        }

        // Download file
        let file_path_str = match file_info.file_path {
            Some(path) => path,
            None => {
                error!("No file path in Telegram response for file_id: {}", file_id);
                let _ = bot_clone
                    .send_message(chat_id, "Sorry, failed to get file path from Telegram.")
                    .await;
                drop(permit);
                return;
            }
        };

        let file_bytes = match downloader.download_file(&file_path_str).await {
            Ok(bytes) => bytes,
            Err(e) => {
                error!("Failed to download file: {}", e);
                let notifier = AdminNotifier::new(bot_clone.clone(), config_clone.clone());
                notifier
                    .notify_telegram_error(
                        user_id,
                        &username,
                        message_id.0,
                        "FileDownloadError",
                        &e.to_string(),
                    )
                    .await;

                let _ = bot_clone
                    .send_message(chat_id, "Sorry, failed to download the audio file.")
                    .await;
                drop(permit);
                return;
            }
        };

        // Save file
        let saved_path = match file_store_clone
            .save_file(chat_id.0, message_id.0, &file_ext, &file_bytes)
            .await
        {
            Ok(path) => path,
            Err(e) => {
                error!("Failed to save file: {}", e);
                let _ = bot_clone
                    .send_message(chat_id, "Sorry, failed to save the audio file.")
                    .await;
                drop(permit);
                return;
            }
        };

        info!("File saved to: {:?}", saved_path);

        // Transcribe
        info!("Starting transcription for message {}", message_id);
        let transcription_result = transcriber_clone.transcribe(&saved_path).await;

        // Delete file
        if let Err(e) = file_store_clone.delete_file(&saved_path).await {
            warn!("Failed to delete file {:?}: {}", saved_path, e);
        }

        match transcription_result {
            Ok(text) => {
                info!("Transcription successful for message {}", message_id);

                // Create inline keyboard with Summarize button
                let keyboard =
                    InlineKeyboardMarkup::new(vec![vec![InlineKeyboardButton::callback(
                        "📝 Summarize",
                        format!("summarize:{}", message_id),
                    )]]);

                if let Err(e) = bot_clone
                    .send_message(chat_id, text)
                    .reply_markup(keyboard)
                    .await
                {
                    error!("Failed to send transcription: {}", e);
                }
            }
            Err(e) => {
                error!("Transcription failed for message {}: {}", message_id, e);

                // Determine error type and user message
                let (user_message, error_type) = match &e {
                    TranscribeError::Timeout => (
                        "⏱️ Transcription took too long. Please try again later or send a shorter audio file.",
                        "Timeout",
                    ),
                    TranscribeError::RateLimited(_) => (
                        "⚠️ The transcription service is currently rate limited. Please try again in a few minutes.",
                        "RateLimited",
                    ),
                    TranscribeError::ApiError(msg) if msg.contains("Invalid API key") => {
                        (
                            "❌ The transcription service failed due to a configuration issue. Please contact the administrator.",
                            "InvalidApiKey",
                        )
                    }
                    TranscribeError::ApiError(_) | TranscribeError::WhisperError(_) => (
                        "❌ The transcription service failed. Please try again later.",
                        "ApiError",
                    ),
                    _ => (
                        "❌ Something went wrong while transcribing your audio. Please try again later.",
                        "UnknownError",
                    ),
                };

                let _ = bot_clone.send_message(chat_id, user_message).await;

                // Notify admins for timeout or unexpected errors
                let notifier = AdminNotifier::new(bot_clone.clone(), config_clone.clone());
                if matches!(e, TranscribeError::Timeout) {
                    notifier
                        .notify_transcription_timeout(user_id, &username, message_id.0, duration)
                        .await;
                } else {
                    notifier
                        .notify_transcription_error(
                            user_id,
                            &username,
                            message_id.0,
                            error_type,
                            &e.to_string(),
                        )
                        .await;
                }
            }
        }

        drop(permit);
    });

    Ok(())
}

pub async fn handle_callback_query(bot: Bot, q: CallbackQuery) -> ResponseResult<()> {
    if let Some(data) = q.data {
        if data.starts_with("summarize:") {
            // Stub for future summarization feature
            bot.answer_callback_query(&q.id)
                .text("Summarization feature coming soon! 🚀")
                .await?;

            if let Some(msg) = q.message {
                bot.send_message(
                    msg.chat.id,
                    "The summarization feature is not yet implemented. Stay tuned!",
                )
                .await?;
            }
        }
    }

    Ok(())
}
