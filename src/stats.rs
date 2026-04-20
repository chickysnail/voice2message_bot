use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;

/// Usage statistics for a single user
#[derive(Debug, Clone, Default)]
pub struct UserStats {
    pub username: String,
    pub message_count: u64,
    pub total_duration_seconds: u64,
}

/// In-memory store for per-user usage statistics.
/// Key: user_id (i64)
pub type StatsStore = Arc<RwLock<HashMap<i64, UserStats>>>;

pub fn create_stats_store() -> StatsStore {
    Arc::new(RwLock::new(HashMap::new()))
}

/// Record a processed message for the given user, incrementing their
/// message count and adding the audio duration.
pub async fn record_message(store: &StatsStore, user_id: i64, username: &str, duration_seconds: u32) {
    let mut map = store.write().await;
    let entry = map.entry(user_id).or_insert_with(|| UserStats {
        username: username.to_string(),
        ..Default::default()
    });
    // Update the stored username in case it changed
    entry.username = username.to_string();
    entry.message_count += 1;
    entry.total_duration_seconds += duration_seconds as u64;
}

/// Retrieve statistics for a single user.  Returns `None` if the user
/// has no recorded activity yet.
pub async fn get_user_stats(store: &StatsStore, user_id: i64) -> Option<UserStats> {
    let map = store.read().await;
    map.get(&user_id).cloned()
}

/// Retrieve statistics for all users, sorted by message count descending.
pub async fn get_all_stats(store: &StatsStore) -> Vec<UserStats> {
    let map = store.read().await;
    let mut stats: Vec<UserStats> = map.values().cloned().collect();
    stats.sort_by(|a, b| b.message_count.cmp(&a.message_count));
    stats
}
