use std::sync::Arc;
use teloxide::prelude::*;
use tokio::sync::Semaphore;
use tracing::info;

mod admin_notifier;
mod bot;
mod config;
mod errors;
mod http;
mod logger;
mod storage;
mod telegram_api;
mod transcriber;
mod utils;
mod whisper_api;

use config::Config;
use storage::FileStore;
use transcriber::Transcriber;
use whisper_api::WhisperTranscriber;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Load configuration
    let config = Config::from_env()?;
    let config = Arc::new(config);

    // Initialize logger
    logger::init_logger(&config.log_level, config.save_log_file)?;
    info!("Voice Transcriber Bot starting...");
    info!("Configuration loaded successfully");

    // Initialize file storage
    let file_store = Arc::new(FileStore::new(config.temp_dir.clone()));
    file_store.init().await?;

    // Initialize transcriber
    let transcriber = Arc::new(WhisperTranscriber::new(
        config.openai_key.clone(),
        config.openai_timeout_seconds,
    )?) as Arc<dyn Transcriber>;
    info!("Whisper transcriber initialized");

    // Initialize semaphore for concurrency control
    let semaphore = Arc::new(Semaphore::new(config.concurrency_limit));
    info!("Concurrency limit set to {}", config.concurrency_limit);

    // Start health check server
    let health_bind = config.http_bind.clone();
    let health_port = config.http_port;
    tokio::spawn(async move {
        if let Err(e) = http::start_health_server(health_bind, health_port).await {
            tracing::error!("Health check server error: {}", e);
        }
    });

    // Initialize Telegram bot
    let bot = Bot::new(config.telegram_token.clone());
    info!("Telegram bot initialized");

    // Run bot
    bot::run_bot(bot, config, transcriber, file_store, semaphore).await;

    Ok(())
}
