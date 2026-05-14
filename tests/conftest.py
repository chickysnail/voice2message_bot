import pytest

from src.bot.storage.transcription_store import TranscriptionStore


@pytest.fixture
def store() -> TranscriptionStore:
    return TranscriptionStore(ttl_seconds=600)


@pytest.fixture
def short_ttl_store() -> TranscriptionStore:
    return TranscriptionStore(ttl_seconds=0)
