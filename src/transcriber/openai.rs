use async_trait::async_trait;
use reqwest::{multipart, Client};
use serde::Deserialize;
use std::path::Path;
use std::time::Duration;
use tokio::fs::File;
use tokio::io::AsyncReadExt;
use tracing::{debug, info, warn};

use crate::errors::TranscribeError;
use crate::transcriber::Transcriber;
use crate::utils::exponential_backoff;

const OPENAI_TRANSCRIPTION_URL: &str = "https://api.openai.com/v1/audio/transcriptions";
const MAX_RETRIES: u32 = 3;

#[derive(Deserialize)]
struct TranscriptionResponse {
    text: String,
}

pub struct OpenAITranscriber {
    client: Client,
    api_key: String,
    #[allow(dead_code)]
    timeout: Duration,
}

impl OpenAITranscriber {
    pub fn new(api_key: String, timeout_seconds: u64) -> Result<Self, TranscribeError> {
        let timeout = Duration::from_secs(timeout_seconds);
        let client = Client::builder()
            .timeout(timeout)
            .build()
            .map_err(|e| TranscribeError::HttpError(e))?;

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
    ) -> Result<String, TranscribeError> {
        // Read file contents
        let mut file = File::open(file_path)
            .await
            .map_err(|e| TranscribeError::IoError(e))?;

        let mut buffer = Vec::new();
        file.read_to_end(&mut buffer)
            .await
            .map_err(|e| TranscribeError::IoError(e))?;

        let file_name = file_path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("audio.ogg");

        // Create multipart form
        let part = multipart::Part::bytes(buffer)
            .file_name(file_name.to_string())
            .mime_str("audio/ogg")
            .map_err(|e| TranscribeError::ApiError(format!("Failed to create multipart: {}", e)))?;

        let form = multipart::Form::new()
            .part("file", part)
            .text("model", "whisper-1");

        debug!("Sending transcription request to OpenAI (attempt {})", attempt + 1);

        // Send request
        let response = self
            .client
            .post(OPENAI_TRANSCRIPTION_URL)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .multipart(form)
            .send()
            .await
            .map_err(|e| TranscribeError::HttpError(e))?;

        let status = response.status();
        debug!("OpenAI response status: {}", status);

        if status.is_success() {
            let transcription: TranscriptionResponse = response
                .json()
                .await
                .map_err(|e| TranscribeError::InvalidResponse(format!("Failed to parse JSON: {}", e)))?;

            info!("Transcription successful");
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

            warn!("Rate limited by OpenAI, retry after {} seconds", retry_after);
            return Err(TranscribeError::RateLimited(retry_after));
        }

        if status.is_server_error() {
            // 5xx error - can retry
            let error_text = response.text().await.unwrap_or_else(|_| "Unknown error".to_string());
            warn!("OpenAI server error (5xx): {}", error_text);
            return Err(TranscribeError::ApiError(format!("Server error: {}", error_text)));
        }

        // Client error (4xx) - don't retry
        let error_text = response.text().await.unwrap_or_else(|_| "Unknown error".to_string());
        Err(TranscribeError::ApiError(format!(
            "API error ({}): {}",
            status, error_text
        )))
    }
}

#[async_trait]
impl Transcriber for OpenAITranscriber {
    async fn transcribe(&self, file_path: &Path) -> Result<String, TranscribeError> {
        let mut last_error = None;

        for attempt in 0..MAX_RETRIES {
            if attempt > 0 {
                let backoff = exponential_backoff(attempt - 1);
                debug!("Waiting {:?} before retry", backoff);
                tokio::time::sleep(backoff).await;
            }

            match self.transcribe_with_retry(file_path, attempt).await {
                Ok(text) => return Ok(text),
                Err(TranscribeError::RateLimited(retry_after)) => {
                    if attempt < MAX_RETRIES - 1 {
                        let wait_duration = Duration::from_secs(retry_after);
                        debug!("Rate limited, waiting {:?}", wait_duration);
                        tokio::time::sleep(wait_duration).await;
                        last_error = Some(TranscribeError::RateLimited(retry_after));
                        continue;
                    }
                    last_error = Some(TranscribeError::RateLimited(retry_after));
                }
                Err(TranscribeError::ApiError(msg)) if msg.contains("Server error") => {
                    // Retry server errors
                    warn!("Server error on attempt {}, will retry", attempt + 1);
                    last_error = Some(TranscribeError::ApiError(msg));
                    continue;
                }
                Err(e) => {
                    // For other errors, don't retry
                    return Err(e);
                }
            }
        }

        Err(last_error.unwrap_or_else(|| {
            TranscribeError::ApiError("Max retries exceeded".to_string())
        }))
    }
}
