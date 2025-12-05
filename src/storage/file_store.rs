use anyhow::{Context, Result};
use std::path::{Path, PathBuf};
use tokio::fs;
use tokio::io::AsyncWriteExt;
use tracing::{debug, info};

pub struct FileStore {
    temp_dir: PathBuf,
}

impl FileStore {
    pub fn new(temp_dir: PathBuf) -> Self {
        Self { temp_dir }
    }

    pub async fn init(&self) -> Result<()> {
        if !self.temp_dir.exists() {
            fs::create_dir_all(&self.temp_dir)
                .await
                .context("Failed to create temp directory")?;

            #[cfg(unix)]
            {
                use std::os::unix::fs::PermissionsExt;
                let metadata = fs::metadata(&self.temp_dir).await?;
                let mut permissions = metadata.permissions();
                permissions.set_mode(0o700);
                fs::set_permissions(&self.temp_dir, permissions).await?;
            }

            info!("Created temp directory: {:?}", self.temp_dir);
        }
        Ok(())
    }

    pub async fn save_file(
        &self,
        chat_id: i64,
        message_id: i32,
        extension: &str,
        data: &[u8],
    ) -> Result<PathBuf> {
        let timestamp = chrono::Utc::now().timestamp();
        let filename = format!("{}_{}_{}.{}", chat_id, message_id, timestamp, extension);
        let file_path = self.temp_dir.join(&filename);

        let mut file = fs::File::create(&file_path)
            .await
            .context("Failed to create file")?;

        file.write_all(data)
            .await
            .context("Failed to write file data")?;

        file.flush().await.context("Failed to flush file")?;

        debug!("Saved file: {:?}", file_path);
        Ok(file_path)
    }

    pub async fn delete_file(&self, file_path: &Path) -> Result<()> {
        if file_path.exists() {
            fs::remove_file(file_path)
                .await
                .context("Failed to delete file")?;
            debug!("Deleted file: {:?}", file_path);
        }
        Ok(())
    }
}
