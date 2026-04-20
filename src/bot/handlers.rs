use std::sync::Arc;
use teloxide::{
    prelude::*,
    types::{InlineKeyboardButton, InlineKeyboardMarkup},
};
use tokio::sync::Semaphore;
use tracing::{error, info, warn};

use crate::{
    admin_notifier::AdminNotifier, 
    chat_completion::ChatCompletionClient,
    config::Config, 
    errors::TranscribeError, 
    stats::{self, StatsStore},
    storage::FileStore,
    telegram_api::TelegramFileDownloader, 
    transcriber::Transcriber, 
    transcription_store::{self, TranscriptionStore},
    utils::format_duration,
};

const TELEGRAM_MESSAGE_LIMIT: usize = 4096;

/// Split a long text into chunks by sentence (splitting on ".")
/// Each chunk will be under the Telegram message limit
fn chunk_text_by_sentence(text: &str) -> Vec<String> {
    if text.len() <= TELEGRAM_MESSAGE_LIMIT {
        return vec![text.to_string()];
    }

    let mut chunks = Vec::new();
    let mut current_chunk = String::new();

    // Split by sentences (on ".")
    for sentence in text.split('.') {
        if sentence.trim().is_empty() {
            continue;
        }
        
        // Always add the period back (split removes it)
        let sentence_with_period = format!("{}.", sentence);

        // Check if adding this sentence would exceed the limit
        if current_chunk.len() + sentence_with_period.len() > TELEGRAM_MESSAGE_LIMIT {
            // Save current chunk if it's not empty
            if !current_chunk.is_empty() {
                chunks.push(current_chunk.trim().to_string());
                current_chunk = String::new();
            }

            // If a single sentence is longer than the limit, split it by words
            if sentence_with_period.len() > TELEGRAM_MESSAGE_LIMIT {
                let mut word_chunk = String::new();
                for word in sentence_with_period.split_whitespace() {
                    if word_chunk.len() + word.len() + 1 > TELEGRAM_MESSAGE_LIMIT
                        && !word_chunk.is_empty()
                    {
                        chunks.push(word_chunk.trim().to_string());
                        word_chunk = String::new();
                    }
                    if !word_chunk.is_empty() {
                        word_chunk.push(' ');
                    }
                    word_chunk.push_str(word);
                }
                if !word_chunk.is_empty() {
                    current_chunk = word_chunk;
                }
            } else {
                current_chunk = sentence_with_period;
            }
        } else {
            current_chunk.push_str(&sentence_with_period);
        }
    }

    // Add the last chunk if it exists
    if !current_chunk.is_empty() {
        chunks.push(current_chunk.trim().to_string());
    }

    // If no chunks were created, return the original text as a single chunk
    if chunks.is_empty() {
        chunks.push(text.to_string());
    }

    chunks
}

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
    transcription_store: TranscriptionStore,
    stats_store: StatsStore,
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
            .notify_duration_exceeded(
                user_id,
                &username,
                message_id.0,
                duration,
                config.audio_max_seconds,
            )
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
    let transcription_store_clone = transcription_store.clone();
    let stats_store_clone = stats_store.clone();

    tokio::spawn(async move {
        // Send initial progress message
        let progress_msg = bot_clone
            .send_message(chat_id, "📥 Receiving your audio file...")
            .await;

        let progress_msg_id = match progress_msg {
            Ok(msg) => Some(msg.id),
            Err(e) => {
                error!("Failed to send progress message: {}", e);
                None
            }
        };

        // Helper macro to update progress
        macro_rules! update_progress {
            ($text:expr) => {
                if let Some(id) = progress_msg_id {
                    let _ = bot_clone.edit_message_text(chat_id, id, $text).await;
                }
            };
        }

        // Initialize file downloader
        let downloader = match TelegramFileDownloader::new(config_clone.telegram_token.clone()) {
            Ok(d) => d,
            Err(e) => {
                error!("Failed to create file downloader: {}", e);
                update_progress!("❌ Failed to initialize downloader.");
                let _ = bot_clone
                    .send_message(chat_id, "Sorry, failed to initialize file downloader.")
                    .await;
                drop(permit);
                return;
            }
        };

        // Update progress: Getting file info
        update_progress!("🔍 Checking file information...");

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

                update_progress!("❌ Failed to get file information.");
                let _ = bot_clone
                    .send_message(
                        chat_id,
                        "Sorry, failed to get file information from Telegram.",
                    )
                    .await;

                // Delete progress message after a delay
                if let Some(id) = progress_msg_id {
                    tokio::time::sleep(tokio::time::Duration::from_secs(3)).await;
                    let _ = bot_clone.delete_message(chat_id, id).await;
                }

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

            update_progress!("❌ File too large.");
            let _ = bot_clone.send_message(chat_id, text).await;

            // Notify admins
            let notifier = AdminNotifier::new(bot_clone.clone(), config_clone.clone());
            notifier
                .notify_oversized_file(user_id, &username, message_id.0, file_size, max_size)
                .await;

            // Delete progress message after a delay
            if let Some(id) = progress_msg_id {
                tokio::time::sleep(tokio::time::Duration::from_secs(3)).await;
                let _ = bot_clone.delete_message(chat_id, id).await;
            }

            drop(permit);
            return;
        }

        // Update progress: Downloading
        update_progress!("⬇️ Downloading audio file...");

        // Download file
        let file_path_str = match file_info.file_path {
            Some(path) => path,
            None => {
                error!("No file path in Telegram response for file_id: {}", file_id);
                update_progress!("❌ Failed to get file path.");
                let _ = bot_clone
                    .send_message(chat_id, "Sorry, failed to get file path from Telegram.")
                    .await;

                // Delete progress message after a delay
                if let Some(id) = progress_msg_id {
                    tokio::time::sleep(tokio::time::Duration::from_secs(3)).await;
                    let _ = bot_clone.delete_message(chat_id, id).await;
                }

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

                update_progress!("❌ Download failed.");
                let _ = bot_clone
                    .send_message(chat_id, "Sorry, failed to download the audio file.")
                    .await;

                // Delete progress message after a delay
                if let Some(id) = progress_msg_id {
                    tokio::time::sleep(tokio::time::Duration::from_secs(3)).await;
                    let _ = bot_clone.delete_message(chat_id, id).await;
                }

                drop(permit);
                return;
            }
        };

        // Update progress: Saving
        update_progress!("💾 Saving audio file...");

        // Save file
        let saved_path = match file_store_clone
            .save_file(chat_id.0, message_id.0, &file_ext, &file_bytes)
            .await
        {
            Ok(path) => path,
            Err(e) => {
                error!("Failed to save file: {}", e);
                update_progress!("❌ Failed to save file.");
                let _ = bot_clone
                    .send_message(chat_id, "Sorry, failed to save the audio file.")
                    .await;

                // Delete progress message after a delay
                if let Some(id) = progress_msg_id {
                    tokio::time::sleep(tokio::time::Duration::from_secs(3)).await;
                    let _ = bot_clone.delete_message(chat_id, id).await;
                }

                drop(permit);
                return;
            }
        };

        info!("File saved to: {:?}", saved_path);

        // Update progress: Transcribing
        update_progress!(
            "🎤 Transcribing audio... This may take several minutes for long recordings."
        );

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

                // Record usage statistics for the user
                stats::record_message(&stats_store_clone, user_id, &username, duration).await;

                // Store the transcription for potential summarization
                transcription_store::save_transcription(&transcription_store_clone, message_id.0, text.clone()).await;
                info!("Transcription stored for message {}", message_id);

                // Update progress: Sending results
                update_progress!("✅ Transcription complete! Sending results...");

                // Chunk the transcription text if it's too long
                let text_chunks = chunk_text_by_sentence(&text);

                info!(
                    "Transcription length: {} chars, split into {} chunk(s)",
                    text.len(),
                    text_chunks.len()
                );

                // Send each chunk as a separate message
                for (i, chunk) in text_chunks.iter().enumerate() {
                    // Add "Summarize" button only to the last chunk
                    let result = if i == text_chunks.len() - 1 {
                        let keyboard =
                            InlineKeyboardMarkup::new(vec![vec![InlineKeyboardButton::callback(
                                "📝 Summarize",
                                format!("summarize:{}", message_id),
                            )]]);

                        bot_clone
                            .send_message(chat_id, chunk)
                            .reply_markup(keyboard)
                            .await
                    } else {
                        // For chunks other than the last, prepend a counter
                        let chunk_header = if text_chunks.len() > 1 {
                            format!("📄 Part {}/{}:\n\n{}", i + 1, text_chunks.len(), chunk)
                        } else {
                            chunk.to_string()
                        };

                        bot_clone.send_message(chat_id, chunk_header).await
                    };

                    if let Err(e) = result {
                        error!("Failed to send transcription chunk {}: {}", i + 1, e);
                    }
                }

                // Delete progress message
                if let Some(id) = progress_msg_id {
                    if let Err(e) = bot_clone.delete_message(chat_id, id).await {
                        warn!("Failed to delete progress message: {}", e);
                    }
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

                // Update progress message with error, then delete after sending full error
                update_progress!("❌ Transcription failed.");
                let _ = bot_clone.send_message(chat_id, user_message).await;

                // Delete progress message after a delay
                if let Some(id) = progress_msg_id {
                    tokio::time::sleep(tokio::time::Duration::from_secs(3)).await;
                    let _ = bot_clone.delete_message(chat_id, id).await;
                }

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

pub async fn handle_callback_query(
    bot: Bot,
    q: CallbackQuery,
    chat_client: Arc<ChatCompletionClient>,
    transcription_store: TranscriptionStore,
) -> ResponseResult<()> {
    if let Some(data) = q.data {
        if data.starts_with("summarize:") {
            // Extract message_id from callback data
            let message_id_str = data.strip_prefix("summarize:").unwrap_or("");
            let message_id: i32 = match message_id_str.parse() {
                Ok(id) => id,
                Err(_) => {
                    bot.answer_callback_query(&q.id)
                        .text("Invalid message ID")
                        .await?;
                    return Ok(());
                }
            };

            // Acknowledge the callback query
            bot.answer_callback_query(&q.id).await?;

            if let Some(msg) = q.message {
                let chat_id = msg.chat.id;

                // Send initial processing message
                let processing_msg = bot
                    .send_message(chat_id, "🔄 Generating summary...")
                    .await?;

                // Retrieve the transcription from storage
                let transcription = match transcription_store::get_transcription(&transcription_store, message_id).await {
                    Some(text) => text,
                    None => {
                        bot.edit_message_text(
                            chat_id,
                            processing_msg.id,
                            "❌ Transcription not found. Please request a new transcription.",
                        )
                        .await?;
                        return Ok(());
                    }
                };

                info!("Summarizing transcription for message {}", message_id);

                // Call the chat completion API to summarize
                match chat_client.summarize(&transcription).await {
                    Ok(summary) => {
                        info!("Summarization successful for message {}", message_id);

                        // Delete the processing message
                        bot.delete_message(chat_id, processing_msg.id).await?;

                        // Send the summary
                        bot.send_message(chat_id, format!("📝 Summary:\n\n{}", summary))
                            .await?;

                        // Remove the transcription from storage after successful summarization
                        transcription_store::remove_transcription(&transcription_store, message_id).await;
                        info!("Transcription removed from storage for message {}", message_id);
                    }
                    Err(e) => {
                        error!("Summarization failed for message {}: {}", message_id, e);

                        let error_message = match e {
                            crate::errors::TranscribeError::Timeout => {
                                "⏱️ Summarization took too long. Please try again later."
                            }
                            crate::errors::TranscribeError::RateLimited(_) => {
                                "⚠️ The service is currently rate limited. Please try again in a few minutes."
                            }
                            _ => "❌ Failed to generate summary. Please try again later.",
                        };

                        bot.edit_message_text(chat_id, processing_msg.id, error_message)
                            .await?;
                    }
                }
            }
        }
    }

    Ok(())
}

pub async fn handle_stats(
    bot: Bot,
    msg: Message,
    stats_store: StatsStore,
    config: Arc<Config>,
) -> ResponseResult<()> {
    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);

    let user_stats = stats::get_user_stats(&stats_store, user_id).await;

    let user_text = match user_stats {
        Some(s) => format!(
            "📊 Your usage statistics:\n\
             • Messages transcribed: {}\n\
             • Total audio duration: {}",
            s.message_count,
            format_duration(s.total_duration_seconds as u32),
        ),
        None => "📊 You haven't transcribed any messages yet.".to_string(),
    };

    bot.send_message(msg.chat.id, &user_text).await?;

    // Admins also receive a global summary
    if config.admin_ids.contains(&user_id) {
        let all_stats = stats::get_all_stats(&stats_store).await;

        if all_stats.is_empty() {
            bot.send_message(msg.chat.id, "📊 No global statistics recorded yet.")
                .await?;
        } else {
            let mut lines = vec!["📊 Global statistics (all users):".to_string()];
            for s in &all_stats {
                let display_name = if s.username.is_empty() {
                    "Unknown User".to_string()
                } else {
                    format!("@{}", s.username)
                };
                lines.push(format!(
                    "• {} — {} messages, {}",
                    display_name,
                    s.message_count,
                    format_duration(s.total_duration_seconds as u32),
                ));
            }
            bot.send_message(msg.chat.id, lines.join("\n")).await?;
        }
    }

    Ok(())
}
