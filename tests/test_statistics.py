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


async def test_get_all_user_ids_unions_sources(db: StatisticsDB) -> None:
    await db.record_usage(user_id=1, username="direct", audio_duration=10)
    await db.record_secretary_usage(user_id=2, username="sec", audio_duration=10)
    await db.save_secretary_connection(3, "conn_3", "connected")
    # Overlap: user 1 is also connected — should be deduplicated.
    await db.save_secretary_connection(1, "conn_1", "direct")

    ids = await db.get_all_user_ids()
    assert set(ids) == {1, 2, 3}


async def test_get_all_user_ids_empty(db: StatisticsDB) -> None:
    assert await db.get_all_user_ids() == []


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


async def test_record_event_and_summary_cost(db: StatisticsDB) -> None:
    from src.bot.storage.statistics import KIND_SUMMARIZATION, KIND_TRANSCRIPTION, UsageEvent

    await db.record_event(UsageEvent(1, "a", KIND_TRANSCRIPTION, "voice", 60, cost_usd=0.5))
    await db.record_event(UsageEvent(1, "a", KIND_SUMMARIZATION, "summary", cost_usd=0.01))
    await db.record_event(UsageEvent(2, "b", KIND_SUMMARIZATION, "summary", cost_usd=0.02))
    rows = await db.fetchall("SELECT COUNT(*) FROM usage_events")
    assert rows[0][0] == 3
    assert await db.get_summarization_cost(1) == 0.01
    assert await db.get_summarization_cost(3) == 0


async def test_total_audio_seconds_includes_secretary(db: StatisticsDB) -> None:
    await db.record_usage(1, "a", 100)
    await db.record_secretary_usage(1, "a", 50)
    assert await db.get_total_audio_seconds(1) == 150
    assert await db.get_total_audio_seconds(2) == 0


async def test_donations_are_deduplicated_by_charge(db: StatisticsDB) -> None:
    await db.record_donation(1, "a", 50, "charge_1")
    await db.record_donation(1, "a", 50, "charge_1")
    await db.record_donation(1, "a", 100, "charge_2")
    assert await db.get_donated_stars(1) == 150
    assert await db.get_donated_stars(2) == 0


async def test_nudge_state(db: StatisticsDB) -> None:
    assert await db.get_nudge_state(1) == (None, 0.0)
    await db.save_nudge(1, 1.25)
    since, cost = await db.get_nudge_state(1)
    assert since is not None and 0 <= since < 60
    assert cost == 1.25
