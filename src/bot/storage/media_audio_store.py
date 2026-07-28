from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class StoredAudio:
    """An audio file downloaded from a link, kept for button-driven actions."""

    path: str
    duration: int | None


class MediaAudioStore:
    """Keeps audio downloaded from links on disk with TTL-based expiry.

    Keyed by (user_id, message_id) like `TranscriptionStore`, so a callback can
    transcribe or send the file after the link message was handled. Expired
    entries have their files removed.
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._ttl = ttl_seconds
        self._store: dict[tuple[int, int], tuple[StoredAudio, float]] = {}

    def save(
        self, user_id: int, message_id: int, path: str, duration: int | None
    ) -> None:
        self.cleanup()
        self._store[(user_id, message_id)] = (
            StoredAudio(path, duration),
            time.monotonic(),
        )

    def get(self, user_id: int, message_id: int) -> StoredAudio | None:
        """Return the stored audio, or None if expired or not found."""
        self.cleanup()
        entry = self._store.get((user_id, message_id))
        if entry is None:
            return None
        audio, _ = entry
        if not os.path.exists(audio.path):
            del self._store[(user_id, message_id)]
            return None
        return audio

    def discard(self, user_id: int, message_id: int) -> None:
        """Drop an entry and delete its file."""
        entry = self._store.pop((user_id, message_id), None)
        if entry is not None:
            _remove(entry[0].path)

    def cleanup(self) -> None:
        now = time.monotonic()
        expired = [
            key for key, (_, ts) in self._store.items() if now - ts > self._ttl
        ]
        for key in expired:
            audio, _ = self._store.pop(key)
            _remove(audio.path)


def _remove(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)
