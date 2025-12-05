use anyhow::{Context, Result};
use serde::Deserialize;
use std::path::PathBuf;

#[derive(Debug, Clone, Deserialize)]
pub struct Config {
    pub telegram_token: String,
    pub openai_key: String,
    pub admin_ids: Vec<i64>,
    pub audio_max_seconds: u32,
    pub temp_dir: PathBuf,
    pub log_level: String,
    pub concurrency_limit: usize,
    pub http_bind: String,
    pub http_port: u16,
    pub openai_timeout_seconds: u64,
    pub save_log_file: bool,
}

impl Config {
    pub fn from_env() -> Result<Self> {
        // Try to load .env file if it exists (for development)
        let _ = dotenvy::dotenv();

        let telegram_token = std::env::var("TELEGRAM_BOT_TOKEN")
            .context("TELEGRAM_BOT_TOKEN environment variable not set")?;

        let openai_key = std::env::var("OPENAI_API_KEY")
            .context("OPENAI_API_KEY environment variable not set")?;

        let admin_ids_str =
            std::env::var("ADMIN_IDS").context("ADMIN_IDS environment variable not set")?;
        let admin_ids: Vec<i64> = admin_ids_str
            .split(',')
            .filter(|s| !s.is_empty())
            .map(|s| s.trim().parse::<i64>())
            .collect::<Result<Vec<_>, _>>()
            .context("Failed to parse ADMIN_IDS")?;

        let audio_max_seconds = std::env::var("AUDIO_MAX_SECONDS")
            .unwrap_or_else(|_| "3600".to_string())
            .parse::<u32>()
            .context("Failed to parse AUDIO_MAX_SECONDS")?;

        let temp_dir = std::env::var("TEMP_DIR")
            .unwrap_or_else(|_| "/tmp/voicebot".to_string())
            .into();

        let log_level = std::env::var("LOG_LEVEL").unwrap_or_else(|_| "info".to_string());

        let concurrency_limit = std::env::var("CONCURRENCY_LIMIT")
            .unwrap_or_else(|_| "4".to_string())
            .parse::<usize>()
            .context("Failed to parse CONCURRENCY_LIMIT")?;

        let http_bind = std::env::var("HTTP_BIND").unwrap_or_else(|_| "0.0.0.0".to_string());

        let http_port = std::env::var("HTTP_PORT")
            .unwrap_or_else(|_| "8080".to_string())
            .parse::<u16>()
            .context("Failed to parse HTTP_PORT")?;

        let openai_timeout_seconds = std::env::var("OPENAI_TIMEOUT_SECONDS")
            .unwrap_or_else(|_| "120".to_string())
            .parse::<u64>()
            .context("Failed to parse OPENAI_TIMEOUT_SECONDS")?;

        let save_log_file = std::env::var("SAVE_LOG_FILE")
            .unwrap_or_else(|_| "true".to_string())
            .parse::<bool>()
            .unwrap_or(true);

        Ok(Config {
            telegram_token,
            openai_key,
            admin_ids,
            audio_max_seconds,
            temp_dir,
            log_level,
            concurrency_limit,
            http_bind,
            http_port,
            openai_timeout_seconds,
            save_log_file,
        })
    }
}
