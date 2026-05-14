import time


class TranscriptionStore:
    """In-memory store for transcriptions with TTL-based expiry.

    Keyed by (user_id, message_id) to ensure user isolation.
    """

    def __init__(self, ttl_seconds: int = 600) -> None:
        self._ttl = ttl_seconds
        self._store: dict[tuple[int, int], tuple[str, float]] = {}

    def save(self, user_id: int, message_id: int, text: str) -> None:
        self._cleanup()
        self._store[(user_id, message_id)] = (text, time.monotonic())

    def get(self, user_id: int, message_id: int) -> str | None:
        """Retrieve a transcription. Returns None if expired or not found."""
        self._cleanup()
        entry = self._store.get((user_id, message_id))
        if entry is None:
            return None
        text, _ = entry
        return text

    def _cleanup(self) -> None:
        now = time.monotonic()
        expired = [k for k, (_, ts) in self._store.items() if now - ts > self._ttl]
        for k in expired:
            del self._store[k]
