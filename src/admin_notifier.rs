use std::sync::Arc;
use teloxide::{prelude::*, types::ChatId};
use tracing::{error, info};

use crate::config::Config;

pub struct AdminNotifier {
    bot: Bot,
    config: Arc<Config>,
}

impl AdminNotifier {
    pub fn new(bot: Bot, config: Arc<Config>) -> Self {
        Self { bot, config }
    }

    /// Notify admins about an oversized file attempt
    pub async fn notify_oversized_file(
        &self,
        user_id: i64,
        username: &str,
        message_id: i32,
        file_size: u64,
        max_size: u64,
    ) {
        let admin_text = format!(
            "🚨 **Oversized File Alert**\n\n\
            User: @{} (ID: {})\n\
            Message ID: {}\n\
            File size: {} bytes ({:.2} MB)\n\
            Max allowed: {} bytes ({:.2} MB)\n\
            Timestamp: {}",
            username,
            user_id,
            message_id,
            file_size,
            file_size as f64 / 1_000_000.0,
            max_size,
            max_size as f64 / 1_000_000.0,
            chrono::Utc::now().to_rfc3339()
        );

        self.send_to_admins(&admin_text).await;
    }

    /// Notify admins about a transcription timeout
    pub async fn notify_transcription_timeout(
        &self,
        user_id: i64,
        username: &str,
        message_id: i32,
        duration_seconds: u32,
    ) {
        let admin_text = format!(
            "⏱️ **Transcription Timeout Alert**\n\n\
            User: @{} (ID: {})\n\
            Message ID: {}\n\
            Audio duration: {} seconds\n\
            Error: Transcription timed out after all retries\n\
            Timestamp: {}",
            username,
            user_id,
            message_id,
            duration_seconds,
            chrono::Utc::now().to_rfc3339()
        );

        self.send_to_admins(&admin_text).await;
    }

    /// Notify admins about a transcription error
    pub async fn notify_transcription_error(
        &self,
        user_id: i64,
        username: &str,
        message_id: i32,
        error_type: &str,
        error_message: &str,
    ) {
        let admin_text = format!(
            "❌ **Transcription Error Alert**\n\n\
            User: @{} (ID: {})\n\
            Message ID: {}\n\
            Error Type: {}\n\
            Error: {}\n\
            Timestamp: {}",
            username,
            user_id,
            message_id,
            error_type,
            error_message,
            chrono::Utc::now().to_rfc3339()
        );

        self.send_to_admins(&admin_text).await;
    }

    /// Notify admins about a Telegram API error
    pub async fn notify_telegram_error(
        &self,
        user_id: i64,
        username: &str,
        message_id: i32,
        error_type: &str,
        error_message: &str,
    ) {
        let admin_text = format!(
            "📡 **Telegram API Error Alert**\n\n\
            User: @{} (ID: {})\n\
            Message ID: {}\n\
            Error Type: {}\n\
            Error: {}\n\
            Timestamp: {}",
            username,
            user_id,
            message_id,
            error_type,
            error_message,
            chrono::Utc::now().to_rfc3339()
        );

        self.send_to_admins(&admin_text).await;
    }

    /// Notify admins about duration limit exceeded
    pub async fn notify_duration_exceeded(
        &self,
        user_id: i64,
        username: &str,
        message_id: i32,
        duration_seconds: u32,
        max_duration: u32,
    ) {
        let admin_text = format!(
            "⚠️ **Audio Duration Limit Exceeded**\n\n\
            User: @{} (ID: {})\n\
            Message ID: {}\n\
            Audio duration: {} seconds\n\
            Max allowed: {} seconds\n\
            Timestamp: {}",
            username,
            user_id,
            message_id,
            duration_seconds,
            max_duration,
            chrono::Utc::now().to_rfc3339()
        );

        self.send_to_admins(&admin_text).await;
    }

    /// Send a message to all configured admins
    async fn send_to_admins(&self, message: &str) {
        for admin_id in &self.config.admin_ids {
            match self.bot.send_message(ChatId(*admin_id), message).await {
                Ok(_) => {
                    info!("Admin notification sent to {}", admin_id);
                }
                Err(e) => {
                    error!("Failed to notify admin {}: {}", admin_id, e);
                }
            }
        }
    }
}
