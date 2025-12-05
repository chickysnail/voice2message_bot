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

pub fn exponential_backoff(attempt: u32) -> Duration {
    let base_ms = 500;
    let delay_ms = base_ms * 2u64.pow(attempt);
    Duration::from_millis(delay_ms)
}
