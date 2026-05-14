import time
from unittest.mock import patch

from src.bot.storage.transcription_store import TranscriptionStore


def test_save_and_get(store: TranscriptionStore) -> None:
    store.save(user_id=1, message_id=100, text="Hello world")
    assert store.get(user_id=1, message_id=100) == "Hello world"


def test_get_missing_returns_none(store: TranscriptionStore) -> None:
    assert store.get(user_id=1, message_id=999) is None


def test_user_isolation(store: TranscriptionStore) -> None:
    store.save(user_id=1, message_id=100, text="User 1 text")
    store.save(user_id=2, message_id=100, text="User 2 text")
    assert store.get(user_id=1, message_id=100) == "User 1 text"
    assert store.get(user_id=2, message_id=100) == "User 2 text"
    assert store.get(user_id=3, message_id=100) is None


def test_expiry() -> None:
    s = TranscriptionStore(ttl_seconds=1)
    s.save(user_id=1, message_id=100, text="will expire")

    assert s.get(user_id=1, message_id=100) == "will expire"

    with patch("src.bot.storage.transcription_store.time") as mock_time:
        mock_time.monotonic.return_value = time.monotonic() + 2
        assert s.get(user_id=1, message_id=100) is None


def test_overwrite(store: TranscriptionStore) -> None:
    store.save(user_id=1, message_id=100, text="first")
    store.save(user_id=1, message_id=100, text="second")
    assert store.get(user_id=1, message_id=100) == "second"
