use std::time::Duration;

pub fn format_duration(seconds: u32) -> String {
    let hours = seconds / 3600;
    let minutes = (seconds % 3600) / 60;
    let secs = seconds % 60;

    if hours > 0 {
        format!("{}h {}m {}s", hours, minutes, secs)
    } else if minutes > 0 {
        format!("{}m {}s", minutes, secs)
    } else {
        format!("{}s", secs)
    }
}

#[allow(dead_code)]
pub fn exponential_backoff(attempt: u32) -> Duration {
    let base_ms = 500;
    let delay_ms = base_ms * 2u64.pow(attempt);
    Duration::from_millis(delay_ms)
}

/// Exponential backoff with jitter to prevent thundering herd
pub fn exponential_backoff_with_jitter(attempt: u32) -> Duration {
    let base_ms = 500;
    let delay_ms = base_ms * 2u64.pow(attempt);

    // Add up to 50% jitter
    let jitter_range = delay_ms / 2;
    let jitter = (rand::random::<u64>() % jitter_range).max(1);

    Duration::from_millis(delay_ms + jitter)
}

#[allow(dead_code)]
fn rand_random<T>() -> T
where
    T: From<u8>,
{
    // Simple pseudo-random using system time for jitter
    use std::time::SystemTime;
    let nanos = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .unwrap()
        .subsec_nanos();
    T::from((nanos % 256) as u8)
}

// Use a simple random function to avoid adding a dependency
mod rand {
    use std::time::SystemTime;

    pub fn random<T>() -> T
    where
        T: From<u64>,
    {
        let nanos = SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        T::from((nanos % u64::MAX as u128) as u64)
    }
}
