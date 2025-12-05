use std::sync::Arc;
use teloxide::{
    prelude::*,
    types::{ChatAction, InlineKeyboardButton, InlineKeyboardMarkup},
};
use tokio::sync::Semaphore;
use tracing::{error, info, warn};

use crate::{
    config::Config,
    storage::FileStore,
    transcriber::Transcriber,
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
                - Audio files longer than this will be rejected\n\n\
                Features:\n\
                - Automatic transcription of voice messages\n\
                - Support for various audio formats\n\
                - Retry logic for reliability\n\
                - Inline 'Summarize' button (coming soon)\n\n\
                If you encounter any issues, please contact the bot administrator.";

    bot.send_message(msg.chat.id, text).await?;
    Ok(())
}

pub async fn handle_settings(bot: Bot, msg: Message, config: Arc<Config>) -> ResponseResult<()> {
    let text = format!(
        "Current Settings ⚙️\n\n\
         Maximum audio duration: {} seconds ({})\n\
         Concurrent transcriptions: {}\n\
         OpenAI timeout: {} seconds",
        config.audio_max_seconds,
        format_duration(config.audio_max_seconds),
        config.concurrency_limit,
        config.openai_timeout_seconds
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
        (voice.file.id.clone(), voice.duration, "ogg")
    } else if let Some(audio) = msg.audio() {
        (audio.file.id.clone(), audio.duration, "mp3")
    } else {
        return Ok(());
    };

    let user_id = msg.from().map(|u| u.id.0 as i64).unwrap_or(0);
    let username = msg
        .from()
        .and_then(|u| u.username.as_ref())
        .map(|s| s.as_str())
        .unwrap_or("unknown");

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
        let admin_text = format!(
            "⚠️ User {} (id: {}) tried sending audio of {} seconds.\n\
             Username: @{}\n\
             Message ID: {}\n\
             Max allowed: {} seconds",
            user_id, user_id, duration, username, message_id, config.audio_max_seconds
        );

        for admin_id in &config.admin_ids {
            if let Err(e) = bot.send_message(ChatId(*admin_id), &admin_text).await {
                error!("Failed to notify admin {}: {}", admin_id, e);
            }
        }

        return Ok(());
    }

    // Acquire semaphore permit
    let permit = semaphore.clone().acquire_owned().await;
    if permit.is_err() {
        bot.send_message(chat_id, "Sorry, the system is currently busy. Please try again later.")
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
        if let Err(e) = bot_clone.send_chat_action(chat_id, ChatAction::Typing).await {
            error!("Failed to send typing action: {}", e);
        }

        // Download file
        let file_result = bot_clone.get_file(&file_id).await;
        if let Err(e) = file_result {
            error!("Failed to get file info: {}", e);
            let _ = bot_clone
                .send_message(chat_id, "Sorry, failed to download the audio file.")
                .await;
            drop(permit);
            return;
        }

        let file = file_result.unwrap();
        let file_path = file.path;

        // Download file content
        let download_url = format!(
            "https://api.telegram.org/file/bot{}/{}",
            config_clone.telegram_token, file_path
        );

        let client = reqwest::Client::new();
        let response = client.get(&download_url).send().await;

        if let Err(e) = response {
            error!("Failed to download file: {}", e);
            let _ = bot_clone
                .send_message(chat_id, "Sorry, failed to download the audio file.")
                .await;
            drop(permit);
            return;
        }

        let response = response.unwrap();
        let file_bytes = response.bytes().await;

        if let Err(e) = file_bytes {
            error!("Failed to read file bytes: {}", e);
            let _ = bot_clone
                .send_message(chat_id, "Sorry, failed to download the audio file.")
                .await;
            drop(permit);
            return;
        }

        let file_bytes = file_bytes.unwrap();

        // Save file
        let saved_path = file_store_clone
            .save_file(chat_id.0, message_id.0, file_ext, &file_bytes)
            .await;

        if let Err(e) = saved_path {
            error!("Failed to save file: {}", e);
            let _ = bot_clone
                .send_message(chat_id, "Sorry, failed to save the audio file.")
                .await;
            drop(permit);
            return;
        }

        let saved_path = saved_path.unwrap();
        info!("File saved to: {:?}", saved_path);

        // Transcribe
        let transcription_result = transcriber_clone.transcribe(&saved_path).await;

        // Delete file
        if let Err(e) = file_store_clone.delete_file(&saved_path).await {
            warn!("Failed to delete file {:?}: {}", saved_path, e);
        }

        match transcription_result {
            Ok(text) => {
                info!("Transcription successful for message {}", message_id);

                // Create inline keyboard with Summarize button
                let keyboard = InlineKeyboardMarkup::new(vec![vec![
                    InlineKeyboardButton::callback(
                        "📝 Summarize",
                        format!("summarize:{}", message_id)
                    ),
                ]]);

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
                let _ = bot_clone
                    .send_message(
                        chat_id,
                        "Sorry, something went wrong while transcribing your audio. Please try again later.",
                    )
                    .await;
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
