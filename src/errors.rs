use thiserror::Error;

#[derive(Error, Debug)]
pub enum TranscribeError {
    #[error("HTTP request failed: {0}")]
    HttpError(#[from] reqwest::Error),

    #[error("I/O error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("API error: {0}")]
    ApiError(String),

    #[error("Rate limited, retry after {0} seconds")]
    RateLimited(u64),

    #[error("Timeout waiting for transcription")]
    Timeout,

    #[error("Invalid response format: {0}")]
    InvalidResponse(String),
}

#[derive(Error, Debug)]
#[allow(dead_code)]
pub enum BotError {
    #[error("Telegram API error: {0}")]
    TelegramError(String),

    #[error("Transcription error: {0}")]
    TranscribeError(#[from] TranscribeError),

    #[error("File storage error: {0}")]
    StorageError(#[from] std::io::Error),

    #[error("Configuration error: {0}")]
    ConfigError(String),
}
