from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.bot.services.transcription import WordData


class TranscriptionStore:
    """In-memory store for transcriptions with TTL-based expiry.

    Keyed by (user_id, message_id) to ensure user isolation.
    Stores both the formatted text and the raw word-level data.
    """

    def __init__(self, ttl_seconds: int = 600) -> None:
        self._ttl = ttl_seconds
        self._store: dict[
            tuple[int, int], tuple[str, list[WordData], float]
        ] = {}

    def save(
        self,
        user_id: int,
        message_id: int,
        text: str,
        words: list[WordData] | None = None,
    ) -> None:
        self._cleanup()
        self._store[(user_id, message_id)] = (
            text,
            words or [],
            time.monotonic(),
        )

    def get(self, user_id: int, message_id: int) -> str | None:
        """Retrieve the transcription text. Returns None if expired or not found."""
        self._cleanup()
        entry = self._store.get((user_id, message_id))
        if entry is None:
            return None
        text, _, _ = entry
        return text

    def get_words(self, user_id: int, message_id: int) -> list[WordData] | None:
        """Retrieve word-level data. Returns None if expired or not found."""
        self._cleanup()
        entry = self._store.get((user_id, message_id))
        if entry is None:
            return None
        _, words, _ = entry
        return words

    def _cleanup(self) -> None:
        now = time.monotonic()
        expired = [
            k for k, (_, _, ts) in self._store.items() if now - ts > self._ttl
        ]
        for k in expired:
            del self._store[k]
