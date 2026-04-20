use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::Duration;
use tracing::{debug, info, warn};

use crate::errors::TranscribeError;

const OPENAI_CHAT_URL: &str = "https://api.openai.com/v1/chat/completions";

/// System prompt for summarization that instructs the model to:
/// - Rewrite as a text message format
/// - Make text more readable
/// - Keep the main point
/// - Preserve the original language
const SUMMARIZATION_PROMPT: &str = "Rewrite the following transcript as if it were a text message. Make the text more readable. Keep the main point of the message. The message will be read by the user. The user only speaks the language they recorded the audio in. Preserve user's language";

#[derive(Serialize)]
struct ChatCompletionRequest {
    model: String,
    messages: Vec<ChatMessage>,
}

#[derive(Serialize, Deserialize, Clone)]
struct ChatMessage {
    role: String,
    content: String,
}

#[derive(Deserialize)]
struct ChatCompletionResponse {
    choices: Vec<ChatChoice>,
}

#[derive(Deserialize)]
struct ChatChoice {
    message: ChatMessage,
}

pub struct ChatCompletionClient {
    client: Client,
    api_key: String,
}

impl ChatCompletionClient {
    pub fn new(api_key: String, timeout_seconds: u64) -> Result<Self, TranscribeError> {
        let timeout = Duration::from_secs(timeout_seconds);
        let client = Client::builder()
            .timeout(timeout)
            .connect_timeout(Duration::from_secs(30))
            .build()
            .map_err(|e| {
                TranscribeError::ApiError(format!("Failed to create HTTP client: {}", e))
            })?;

        info!("ChatCompletionClient initialized with timeout: {} seconds", timeout_seconds);

        Ok(Self { client, api_key })
    }

    pub async fn summarize(&self, transcript: &str) -> Result<String, TranscribeError> {
        let messages = vec![
            ChatMessage {
                role: "system".to_string(),
                content: SUMMARIZATION_PROMPT.to_string(),
            },
            ChatMessage {
                role: "user".to_string(),
                content: transcript.to_string(),
            },
        ];

        let request = ChatCompletionRequest {
            model: "gpt-4o-mini".to_string(),
            messages,
        };

        info!("Sending summarization request to OpenAI Chat Completions API");

        let response = self
            .client
            .post(OPENAI_CHAT_URL)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .json(&request)
            .send()
            .await
            .map_err(|e| {
                if e.is_timeout() {
                    warn!("OpenAI Chat API request timed out");
                    TranscribeError::Timeout
                } else if e.is_connect() {
                    warn!("Connection to OpenAI failed");
                    TranscribeError::ApiError(format!("Connection failed: {}", e))
                } else {
                    TranscribeError::ApiError(format!("HTTP error: {}", e))
                }
            })?;

        let status = response.status();
        debug!("OpenAI Chat API response status: {}", status);

        if status.is_success() {
            let completion: ChatCompletionResponse = response.json().await.map_err(|e| {
                TranscribeError::ApiError(format!("Failed to parse JSON: {}", e))
            })?;

            if let Some(choice) = completion.choices.first() {
                info!("Summarization successful");
                return Ok(choice.message.content.clone());
            } else {
                return Err(TranscribeError::ApiError(
                    "No choices in response".to_string(),
                ));
            }
        }

        // Handle error responses
        if status == 429 {
            let retry_after = response
                .headers()
                .get("retry-after")
                .and_then(|v| v.to_str().ok())
                .and_then(|s| s.parse::<u64>().ok())
                .unwrap_or(5);

            warn!("Rate limited by OpenAI, retry after {} seconds", retry_after);
            return Err(TranscribeError::RateLimited(retry_after));
        }

        if status == 401 {
            return Err(TranscribeError::ApiError("Invalid API key".to_string()));
        }

        let error_text = response
            .text()
            .await
            .unwrap_or_else(|_| "Unknown error".to_string());

        Err(TranscribeError::ApiError(format!(
            "API error ({}): {}",
            status, error_text
        )))
    }
}
