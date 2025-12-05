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

    #[error("Whisper error: {0}")]
    WhisperError(WhisperError),
}

#[derive(Error, Debug)]
pub enum WhisperError {
    #[error("HTTP request failed: {0}")]
    HttpError(String),

    #[error("I/O error: {0}")]
    IoError(String),

    #[error("API error: {0}")]
    ApiError(String),

    #[error("Rate limited, retry after {0} seconds")]
    RateLimited(u64),

    #[error("Timeout waiting for transcription")]
    Timeout,

    #[error("Connection error: {0}")]
    ConnectionError(String),

    #[error("Server error (5xx): {0}")]
    ServerError(String),

    #[error("Invalid response format: {0}")]
    InvalidResponse(String),

    #[error("Invalid API key")]
    InvalidApiKey,

    #[error("Unsupported audio format")]
    UnsupportedFormat,
}

#[derive(Error, Debug)]
pub enum TelegramError {
    #[error("Telegram API error: {0}")]
    ApiError(String),

    #[error("Timeout: {0}")]
    Timeout(String),

    #[error("Network error: {0}")]
    NetworkError(String),

    #[error("File too large: {0} bytes (max: {1} bytes)")]
    FileTooLarge(u64, u64),

    #[error("File size unknown")]
    FileSizeUnknown,
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

// Implement conversion from WhisperError to TranscribeError
impl From<WhisperError> for TranscribeError {
    fn from(error: WhisperError) -> Self {
        TranscribeError::WhisperError(error)
    }
}
