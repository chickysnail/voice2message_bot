use async_trait::async_trait;
use reqwest::{multipart, Client};
use serde::Deserialize;
use std::path::Path;
use std::time::Duration;
use tokio::fs::File;
use tokio::io::AsyncReadExt;
use tracing::{debug, info, warn};

use crate::errors::WhisperError;
use crate::transcriber::Transcriber;
use crate::utils::exponential_backoff_with_jitter;

const OPENAI_TRANSCRIPTION_URL: &str = "https://api.openai.com/v1/audio/transcriptions";
const MAX_RETRIES: u32 = 3;

#[derive(Deserialize)]
struct TranscriptionResponse {
    text: String,
}

pub struct WhisperTranscriber {
    client: Client,
    api_key: String,
    timeout: Duration,
}

impl WhisperTranscriber {
    pub fn new(api_key: String, timeout_seconds: u64) -> Result<Self, WhisperError> {
        let timeout = Duration::from_secs(timeout_seconds);
        // Use a long timeout for Whisper API - long audio can take 5-10 minutes to process
        let client = Client::builder()
            .timeout(timeout)
            .connect_timeout(Duration::from_secs(30))
            .build()
            .map_err(|e| WhisperError::HttpError(format!("Failed to create HTTP client: {}", e)))?;

        info!(
            "WhisperTranscriber initialized with timeout: {} seconds ({} minutes)",
            timeout_seconds,
            timeout_seconds / 60
        );

        Ok(Self {
            client,
            api_key,
            timeout,
        })
    }

    async fn transcribe_with_retry(
        &self,
        file_path: &Path,
        attempt: u32,
    ) -> Result<String, WhisperError> {
        // Read file contents
        let mut file = File::open(file_path)
            .await
            .map_err(|e| WhisperError::IoError(format!("Failed to open file: {}", e)))?;

        let mut buffer = Vec::new();
        file.read_to_end(&mut buffer)
            .await
            .map_err(|e| WhisperError::IoError(format!("Failed to read file: {}", e)))?;

        let file_name = file_path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("audio.ogg");

        // Determine MIME type from extension
        let mime_type = if file_name.ends_with(".mp3") {
            "audio/mpeg"
        } else if file_name.ends_with(".m4a") {
            "audio/mp4"
        } else if file_name.ends_with(".ogg") {
            "audio/ogg"
        } else {
            "audio/ogg" // default
        };

        // Create multipart form
        let part = multipart::Part::bytes(buffer)
            .file_name(file_name.to_string())
            .mime_str(mime_type)
            .map_err(|e| WhisperError::ApiError(format!("Failed to create multipart: {}", e)))?;

        let form = multipart::Form::new()
            .part("file", part)
            .text("model", "whisper-1");

        info!(
            "Sending transcription request to OpenAI Whisper (attempt {})",
            attempt + 1
        );

        // Send request
        let response = self
            .client
            .post(OPENAI_TRANSCRIPTION_URL)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .multipart(form)
            .send()
            .await
            .map_err(|e| {
                if e.is_timeout() {
                    warn!("OpenAI Whisper request timed out on attempt {}", attempt + 1);
                    WhisperError::Timeout
                } else if e.is_connect() {
                    warn!("Connection to OpenAI failed on attempt {}", attempt + 1);
                    WhisperError::ConnectionError(format!("Connection failed: {}", e))
                } else {
                    WhisperError::HttpError(format!("HTTP error: {}", e))
                }
            })?;

        let status = response.status();
        debug!("OpenAI Whisper response status: {}", status);

        if status.is_success() {
            let transcription: TranscriptionResponse = response.json().await.map_err(|e| {
                WhisperError::InvalidResponse(format!("Failed to parse JSON: {}", e))
            })?;

            info!("Transcription successful on attempt {}", attempt + 1);
            return Ok(transcription.text);
        }

        // Handle error responses
        if status == 429 {
            // Rate limited
            let retry_after = response
                .headers()
                .get("retry-after")
                .and_then(|v| v.to_str().ok())
                .and_then(|s| s.parse::<u64>().ok())
                .unwrap_or(5);

            warn!(
                "Rate limited by OpenAI on attempt {}, retry after {} seconds",
                attempt + 1,
                retry_after
            );
            return Err(WhisperError::RateLimited(retry_after));
        }

        if status.is_server_error() {
            // 5xx error - can retry
            let error_text = response
                .text()
                .await
                .unwrap_or_else(|_| "Unknown error".to_string());
            warn!(
                "OpenAI server error (5xx) on attempt {}: {}",
                attempt + 1,
                error_text
            );
            return Err(WhisperError::ServerError(error_text));
        }

        // Client error (4xx) - don't retry
        let error_text = response
            .text()
            .await
            .unwrap_or_else(|_| "Unknown error".to_string());
        
        // Check for invalid API key
        if status == 401 {
            return Err(WhisperError::InvalidApiKey);
        }

        Err(WhisperError::ApiError(format!(
            "API error ({}): {}",
            status, error_text
        )))
    }

    /// Check if an error should be retried
    fn should_retry(error: &WhisperError) -> bool {
        matches!(
            error,
            WhisperError::Timeout
                | WhisperError::RateLimited(_)
                | WhisperError::ServerError(_)
                | WhisperError::ConnectionError(_)
        )
    }
}

#[async_trait]
impl Transcriber for WhisperTranscriber {
    async fn transcribe(&self, file_path: &Path) -> Result<String, crate::errors::TranscribeError> {
        let mut last_error = None;

        for attempt in 0..MAX_RETRIES {
            if attempt > 0 {
                let backoff = exponential_backoff_with_jitter(attempt - 1);
                info!(
                    "Waiting {:?} before retry attempt {}",
                    backoff,
                    attempt + 1
                );
                tokio::time::sleep(backoff).await;
            }

            match self.transcribe_with_retry(file_path, attempt).await {
                Ok(text) => return Ok(text),
                Err(WhisperError::RateLimited(retry_after)) => {
                    if attempt < MAX_RETRIES - 1 {
                        let wait_duration = Duration::from_secs(retry_after);
                        info!("Rate limited, waiting {:?} before retry", wait_duration);
                        tokio::time::sleep(wait_duration).await;
                        last_error = Some(WhisperError::RateLimited(retry_after));
                        continue;
                    }
                    last_error = Some(WhisperError::RateLimited(retry_after));
                }
                Err(e) if Self::should_retry(&e) => {
                    warn!(
                        "Retryable error on attempt {}: {}",
                        attempt + 1,
                        e
                    );
                    last_error = Some(e);
                    continue;
                }
                Err(e) => {
                    // For non-retryable errors, fail immediately
                    warn!("Non-retryable error: {}", e);
                    return Err(e.into());
                }
            }
        }

        // Convert WhisperError to TranscribeError for the final error
        Err(last_error
            .unwrap_or_else(|| WhisperError::ApiError("Max retries exceeded".to_string()))
            .into())
    }
}
