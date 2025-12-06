use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Stores transcriptions in memory for later summarization
/// Key: message_id, Value: transcription text
pub type TranscriptionStore = Arc<RwLock<HashMap<i32, String>>>;

pub fn create_transcription_store() -> TranscriptionStore {
    Arc::new(RwLock::new(HashMap::new()))
}

pub async fn save_transcription(store: &TranscriptionStore, message_id: i32, text: String) {
    let mut map = store.write().await;
    map.insert(message_id, text);
}

pub async fn get_transcription(store: &TranscriptionStore, message_id: i32) -> Option<String> {
    let map = store.read().await;
    map.get(&message_id).cloned()
}

pub async fn remove_transcription(store: &TranscriptionStore, message_id: i32) -> Option<String> {
    let mut map = store.write().await;
    map.remove(&message_id)
}
