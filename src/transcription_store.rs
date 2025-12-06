use std::collections::HashMap;
use std::sync::Arc;
use std::time::{SystemTime, UNIX_EPOCH};
use tokio::sync::RwLock;

/// Entry in the transcription store with timestamp
pub struct TranscriptionEntry {
    text: String,
    timestamp: u64,
}

/// Stores transcriptions in memory for later summarization
/// Key: message_id, Value: transcription entry with timestamp
pub type TranscriptionStore = Arc<RwLock<HashMap<i32, TranscriptionEntry>>>;

pub fn create_transcription_store() -> TranscriptionStore {
    Arc::new(RwLock::new(HashMap::new()))
}

pub async fn save_transcription(store: &TranscriptionStore, message_id: i32, text: String) {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs();
    
    let entry = TranscriptionEntry { text, timestamp };
    
    let mut map = store.write().await;
    map.insert(message_id, entry);
    
    // Clean up entries older than 1 hour
    let cutoff = timestamp.saturating_sub(3600);
    map.retain(|_, entry| entry.timestamp > cutoff);
}

pub async fn get_transcription(store: &TranscriptionStore, message_id: i32) -> Option<String> {
    let map = store.read().await;
    map.get(&message_id).map(|entry| entry.text.clone())
}

pub async fn remove_transcription(store: &TranscriptionStore, message_id: i32) -> Option<String> {
    let mut map = store.write().await;
    map.remove(&message_id).map(|entry| entry.text)
}
