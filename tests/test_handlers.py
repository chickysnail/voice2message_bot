"""Tests for command handlers — secretary setup album and broadcast."""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bot.handlers import SECRETARY_SETUP_IMAGES, BotHandlers
from src.bot.services.notifier import AdminNotifier
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


@pytest.fixture
def notifier() -> AsyncMock:
    n = AsyncMock(spec=AdminNotifier)
    n._admin_user_ids = [111]
    return n


@pytest.fixture
def handlers(notifier: AsyncMock, db: StatisticsDB) -> BotHandlers:
    return BotHandlers(
        transcriber=MagicMock(),
        summarizer=MagicMock(),
        notifier=notifier,
        store=MagicMock(),
        stats_db=db,
        max_audio_duration=3600,
    )


def _make_update(user_id: int = 42) -> MagicMock:
    update = MagicMock()
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    update.message.reply_media_group = AsyncMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.language_code = "en"
    return update


def test_setup_images_exist() -> None:
    assert len(SECRETARY_SETUP_IMAGES) == 3
    for path in SECRETARY_SETUP_IMAGES:
        assert path.exists(), f"missing asset: {path}"


async def test_secretary_command_sends_album_when_not_connected(
    handlers: BotHandlers,
) -> None:
    update = _make_update()
    ctx = MagicMock()
    await handlers.secretary_command(update, ctx)
    update.message.reply_text.assert_awaited_once()
    update.message.reply_media_group.assert_awaited_once()
    media = update.message.reply_media_group.call_args.args[0]
    assert len(media) == 3


async def test_secretary_command_no_album_when_connected(
    handlers: BotHandlers, db: StatisticsDB
) -> None:
    await db.save_secretary_connection(42, "conn_42", "user")
    update = _make_update(42)
    ctx = MagicMock()
    await handlers.secretary_command(update, ctx)
    update.message.reply_text.assert_awaited_once()
    update.message.reply_media_group.assert_not_awaited()


async def test_broadcast_ignored_for_non_admin(handlers: BotHandlers) -> None:
    update = _make_update(user_id=999)  # not an admin
    ctx = MagicMock()
    ctx.args = ["confirm"]
    ctx.bot = AsyncMock()
    await handlers.broadcast_command(update, ctx)
    update.message.reply_text.assert_not_awaited()
    ctx.bot.send_message.assert_not_awaited()


async def test_broadcast_preview_without_confirm(
    handlers: BotHandlers, db: StatisticsDB
) -> None:
    await db.record_usage(1, "a", 10)
    await db.record_usage(2, "b", 10)
    update = _make_update(user_id=111)  # admin
    ctx = MagicMock()
    ctx.args = []
    ctx.bot = AsyncMock()
    await handlers.broadcast_command(update, ctx)
    # Preview goes to the admin only, not to all users.
    ctx.bot.send_message.assert_not_awaited()
    update.message.reply_media_group.assert_awaited_once()
    assert "2 users" in update.message.reply_text.call_args_list[0].args[0]


async def test_broadcast_confirm_sends_to_all(
    handlers: BotHandlers, db: StatisticsDB
) -> None:
    await db.record_usage(1, "a", 10)
    await db.record_usage(2, "b", 10)
    await db.save_secretary_connection(3, "conn_3", "c")
    update = _make_update(user_id=111)  # admin
    ctx = MagicMock()
    ctx.args = ["confirm"]
    ctx.bot = AsyncMock()
    await handlers.broadcast_command(update, ctx)
    assert ctx.bot.send_message.await_count == 3
    assert ctx.bot.send_media_group.await_count == 3
    assert "Sent: 3, failed: 0" in update.message.reply_text.call_args.args[0]


async def test_broadcast_counts_failures(
    handlers: BotHandlers, db: StatisticsDB
) -> None:
    await db.record_usage(1, "a", 10)
    await db.record_usage(2, "b", 10)
    update = _make_update(user_id=111)  # admin
    ctx = MagicMock()
    ctx.args = ["confirm"]
    ctx.bot = AsyncMock()
    ctx.bot.send_message.side_effect = [None, Exception("blocked")]
    await handlers.broadcast_command(update, ctx)
    assert "Sent: 1, failed: 1" in update.message.reply_text.call_args.args[0]
