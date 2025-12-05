use anyhow::{Context, Result};
use reqwest::Client;
use serde::Deserialize;
use std::time::Duration;
use tracing::{debug, info, warn};

use crate::errors::TelegramError;

const TELEGRAM_API_BASE: &str = "https://api.telegram.org";
const MAX_FILE_SIZE_BYTES: u64 = 50_000_000; // 50 MB - Telegram's bot API limit

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
pub struct TelegramFile {
    pub file_id: String,
    pub file_unique_id: String,
    pub file_size: Option<u64>,
    pub file_path: Option<String>,
}

#[derive(Debug, Deserialize)]
struct GetFileResponse {
    ok: bool,
    result: Option<TelegramFile>,
    description: Option<String>,
}

pub struct TelegramFileDownloader {
    client: Client,
    bot_token: String,
}

impl TelegramFileDownloader {
    pub fn new(bot_token: String) -> Result<Self> {
        let client = Client::builder()
            .timeout(Duration::from_secs(300)) // 5 minutes for large file downloads
            .connect_timeout(Duration::from_secs(30))
            .build()
            .context("Failed to create HTTP client for Telegram API")?;

        Ok(Self { client, bot_token })
    }

    /// Get file information from Telegram, including size
    pub async fn get_file_info(&self, file_id: &str) -> Result<TelegramFile, TelegramError> {
        let url = format!("{}/bot{}/getFile", TELEGRAM_API_BASE, self.bot_token);

        debug!("Getting file info for file_id: {}", file_id);

        let response = self
            .client
            .post(&url)
            .json(&serde_json::json!({ "file_id": file_id }))
            .send()
            .await
            .map_err(|e| {
                if e.is_timeout() {
                    TelegramError::Timeout(format!("Timeout getting file info: {}", e))
                } else if e.is_connect() {
                    TelegramError::NetworkError(format!("Connection failed: {}", e))
                } else {
                    TelegramError::ApiError(format!("HTTP error: {}", e))
                }
            })?;

        let file_response: GetFileResponse = response
            .json()
            .await
            .map_err(|e| TelegramError::ApiError(format!("Failed to parse response: {}", e)))?;

        if !file_response.ok {
            let desc = file_response
                .description
                .unwrap_or_else(|| "Unknown error".to_string());
            return Err(TelegramError::ApiError(desc));
        }

        let file = file_response
            .result
            .ok_or_else(|| TelegramError::ApiError("No file in response".to_string()))?;

        info!(
            "File info retrieved - file_id: {}, size: {:?} bytes",
            file_id, file.file_size
        );

        Ok(file)
    }

    /// Check if file size exceeds Telegram's limit
    pub fn is_file_too_large(&self, file_size: Option<u64>) -> bool {
        match file_size {
            Some(size) => size > MAX_FILE_SIZE_BYTES,
            None => {
                warn!("File size not available from Telegram API");
                false // If size is unknown, try to download
            }
        }
    }

    /// Download file content from Telegram
    pub async fn download_file(&self, file_path: &str) -> Result<Vec<u8>, TelegramError> {
        let download_url = format!(
            "{}/file/bot{}/{}",
            TELEGRAM_API_BASE, self.bot_token, file_path
        );

        debug!("Downloading file from: {}", file_path);

        let response = self.client.get(&download_url).send().await.map_err(|e| {
            if e.is_timeout() {
                TelegramError::Timeout(format!("Timeout downloading file: {}", e))
            } else if e.is_connect() {
                TelegramError::NetworkError(format!("Connection failed: {}", e))
            } else {
                TelegramError::ApiError(format!("HTTP error: {}", e))
            }
        })?;

        if !response.status().is_success() {
            return Err(TelegramError::ApiError(format!(
                "Download failed with status: {}",
                response.status()
            )));
        }

        let file_bytes = response
            .bytes()
            .await
            .map_err(|e| TelegramError::ApiError(format!("Failed to read file bytes: {}", e)))?;

        info!(
            "File downloaded successfully, size: {} bytes",
            file_bytes.len()
        );

        Ok(file_bytes.to_vec())
    }

    /// Get the maximum file size limit
    pub fn max_file_size() -> u64 {
        MAX_FILE_SIZE_BYTES
    }
}
