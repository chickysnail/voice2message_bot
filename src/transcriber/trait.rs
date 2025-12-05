use async_trait::async_trait;
use std::path::Path;
use crate::errors::TranscribeError;

#[async_trait]
pub trait Transcriber: Send + Sync {
    async fn transcribe(&self, file_path: &Path) -> Result<String, TranscribeError>;
}
