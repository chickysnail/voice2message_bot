use crate::errors::TranscribeError;
use async_trait::async_trait;
use std::path::Path;

#[async_trait]
pub trait Transcriber: Send + Sync {
    async fn transcribe(&self, file_path: &Path) -> Result<String, TranscribeError>;
}
