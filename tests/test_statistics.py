import os
import tempfile

import pytest

from src.bot.storage.statistics import StatisticsDB


@pytest.fixture
async def db() -> StatisticsDB:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    stats_db = StatisticsDB(path)
    await stats_db.initialize()
    yield stats_db  # type: ignore[misc]
    await stats_db.close()
    os.unlink(path)


async def test_record_and_get(db: StatisticsDB) -> None:
    await db.record_usage(user_id=123, username="alice", audio_duration=60)
    stats = await db.get_user_stats(123)
    assert stats is not None
    transcriptions, duration, first_used, last_used = stats
    assert transcriptions == 1
    assert duration == 60


async def test_multiple_records(db: StatisticsDB) -> None:
    await db.record_usage(user_id=123, username="alice", audio_duration=60)
    await db.record_usage(user_id=123, username="alice", audio_duration=120)
    stats = await db.get_user_stats(123)
    assert stats is not None
    assert stats[0] == 2
    assert stats[1] == 180


async def test_username_update(db: StatisticsDB) -> None:
    await db.record_usage(user_id=123, username="alice", audio_duration=10)
    await db.record_usage(user_id=123, username="alice_new", audio_duration=10)
    all_stats = await db.get_all_stats()
    assert len(all_stats) == 1
    assert all_stats[0][1] == "alice_new"


async def test_get_nonexistent_user(db: StatisticsDB) -> None:
    stats = await db.get_user_stats(999)
    assert stats is None


async def test_get_all_stats(db: StatisticsDB) -> None:
    await db.record_usage(user_id=1, username="user1", audio_duration=30)
    await db.record_usage(user_id=2, username="user2", audio_duration=60)
    all_stats = await db.get_all_stats()
    assert len(all_stats) == 2


async def test_record_error(db: StatisticsDB) -> None:
    await db.record_error("Transcription", "alice", "API timeout")
    total, by_type, last_error = await db.get_error_stats()
    assert total == 1
    assert by_type == {"Transcription": 1}
    assert last_error is not None


async def test_multiple_errors(db: StatisticsDB) -> None:
    await db.record_error("Transcription", "alice", "API timeout")
    await db.record_error("Transcription", "bob", "rate limit")
    await db.record_error("Summarization", "alice", "model error")
    total, by_type, last_error = await db.get_error_stats()
    assert total == 3
    assert by_type == {"Transcription": 2, "Summarization": 1}
    assert last_error is not None


async def test_error_stats_empty(db: StatisticsDB) -> None:
    total, by_type, last_error = await db.get_error_stats()
    assert total == 0
    assert by_type == {}
    assert last_error is None
