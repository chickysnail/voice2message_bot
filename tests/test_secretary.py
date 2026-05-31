"""Tests for secretary (business message) handler."""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.secretary import PROMPT_TTL_SECONDS, SecretaryHandler
from src.bot.services.notifier import AdminNotifier
from src.bot.services.transcription import (
    EmptyTranscriptionError,
    TranscriptionClient,
    TranscriptionResult,
)
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
def mock_transcriber() -> MagicMock:
    t = MagicMock(spec=TranscriptionClient)
    t.transcribe.return_value = TranscriptionResult(
        text="Speaker 1: Hello world", words=[]
    )
    return t


@pytest.fixture
def mock_notifier() -> AsyncMock:
    n = AsyncMock(spec=AdminNotifier)
    n._admin_user_ids = [111]
    return n


@pytest.fixture
def handler(
    mock_transcriber: MagicMock,
    mock_notifier: AsyncMock,
    db: StatisticsDB,
) -> SecretaryHandler:
    return SecretaryHandler(
        transcriber=mock_transcriber,
        notifier=mock_notifier,
        stats_db=db,
        max_audio_duration=3600,
        transcription_timeout=30,
        ffmpeg_timeout=10,
        file_download_timeout=10,
    )


def _make_user(user_id: int = 42, username: str = "testuser", lang: str = "en") -> MagicMock:
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.language_code = lang
    return user


def _make_business_connection(
    conn_id: str = "biz_123",
    user: MagicMock | None = None,
    is_enabled: bool = True,
) -> MagicMock:
    conn = MagicMock()
    conn.id = conn_id
    conn.user = user or _make_user()
    conn.is_enabled = is_enabled
    return conn


def _make_voice_message(
    chat_id: int = 100,
    message_id: int = 1,
    biz_conn_id: str = "biz_123",
    duration: int = 10,
) -> MagicMock:
    msg = MagicMock()
    msg.chat.id = chat_id
    msg.message_id = message_id
    msg.business_connection_id = biz_conn_id

    voice = MagicMock()
    voice.file_id = "file_abc"
    voice.duration = duration
    msg.voice = voice
    msg.video_note = None
    msg.from_user = None
    return msg


def _make_update_with_connection(
    conn: MagicMock | None = None,
) -> MagicMock:
    update = MagicMock()
    update.business_connection = conn or _make_business_connection()
    return update


def _make_update_with_business_message(
    message: MagicMock | None = None,
) -> MagicMock:
    update = MagicMock()
    update.business_message = message or _make_voice_message()
    return update


def _make_context(bot: AsyncMock | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.bot = bot or AsyncMock()
    return ctx


# --- Business Connection Tests ---


async def test_handle_connection_enabled(
    handler: SecretaryHandler, mock_notifier: AsyncMock, db: StatisticsDB
) -> None:
    conn = _make_business_connection(is_enabled=True)
    update = _make_update_with_connection(conn)
    bot = AsyncMock()
    ctx = _make_context(bot)

    await handler.handle_business_connection(update, ctx)

    assert "biz_123" in handler._connections
    mock_notifier.notify_secretary_event.assert_called_once_with(
        "connected", "testuser", 42
    )
    # Connection should be persisted in DB
    assert await db.is_user_secretary_connected(42)
    # Welcome DM should be sent
    bot.send_message.assert_called_once()
    call_kwargs = bot.send_message.call_args.kwargs
    assert call_kwargs["chat_id"] == 42


async def test_handle_connection_disabled(
    handler: SecretaryHandler, mock_notifier: AsyncMock, db: StatisticsDB
) -> None:
    # First connect
    conn = _make_business_connection(is_enabled=True)
    update = _make_update_with_connection(conn)
    ctx = _make_context()
    await handler.handle_business_connection(update, ctx)

    # Then disconnect
    conn2 = _make_business_connection(is_enabled=False)
    update2 = _make_update_with_connection(conn2)
    await handler.handle_business_connection(update2, ctx)

    assert "biz_123" not in handler._connections
    # Connection should be removed from DB
    assert not await db.is_user_secretary_connected(42)


async def test_handle_connection_none(handler: SecretaryHandler) -> None:
    update = MagicMock()
    update.business_connection = None
    ctx = _make_context()
    await handler.handle_business_connection(update, ctx)
    assert len(handler._connections) == 0


# --- Manual prompt tests (manual is the only mode) ---


async def test_business_message_sends_prompt(
    handler: SecretaryHandler, mock_transcriber: MagicMock, db: StatisticsDB
) -> None:
    conn = _make_business_connection()
    handler._connections["biz_123"] = conn

    message = _make_voice_message()
    update = _make_update_with_business_message(message)

    bot = AsyncMock()
    sent_msg = MagicMock()
    sent_msg.message_id = 99
    sent_msg.chat.id = 100
    bot.send_message = AsyncMock(return_value=sent_msg)
    ctx = _make_context(bot)

    await handler.handle_business_message(update, ctx)

    # Should send a prompt with a Transcribe button, NOT transcribe
    bot.send_message.assert_called_once()
    call_kwargs = bot.send_message.call_args.kwargs
    assert "sec_transcribe" in str(call_kwargs["reply_markup"])
    mock_transcriber.transcribe.assert_not_called()

    # Prompt should be tracked for auto-deletion
    expired = await db.get_expired_pending_prompts(0)
    assert ("biz_123", 100, 99) in expired


async def test_business_message_skips_non_audio(handler: SecretaryHandler) -> None:
    conn = _make_business_connection()
    handler._connections["biz_123"] = conn

    message = MagicMock()
    message.business_connection_id = "biz_123"
    message.voice = None
    message.video_note = None

    update = _make_update_with_business_message(message)
    ctx = _make_context()

    await handler.handle_business_message(update, ctx)
    ctx.bot.send_message.assert_not_called()


async def test_transcribe_callback_flow(
    handler: SecretaryHandler,
    mock_transcriber: MagicMock,
    db: StatisticsDB,
) -> None:
    conn = _make_business_connection()
    handler._connections["biz_123"] = conn

    # Track a pending prompt that the callback should remove
    await db.add_pending_prompt("biz_123", 100, 99)

    update = MagicMock()
    query = MagicMock()
    query.data = "sec_transcribe:1:biz_123"
    query.answer = AsyncMock()

    prompt_msg = MagicMock()
    prompt_msg.chat.id = 100
    prompt_msg.message_id = 99
    prompt_msg.reply_to_message = _make_voice_message()
    query.message = prompt_msg
    update.callback_query = query

    bot = AsyncMock()
    tg_file = AsyncMock()
    tg_file.file_path = "audio.ogg"
    tg_file.download_to_drive = AsyncMock()
    bot.get_file = AsyncMock(return_value=tg_file)
    bot.edit_message_text = AsyncMock()
    bot.send_message = AsyncMock()

    ctx = _make_context(bot)

    with patch("src.bot.secretary.os.path.exists", return_value=True), \
         patch("src.bot.secretary.os.remove"):
        await handler.handle_transcribe_callback(update, ctx)

    mock_transcriber.transcribe.assert_called_once()

    # The final message is a bare expandable blockquote — no prefix, no buttons
    final_call = bot.edit_message_text.call_args
    text = final_call.kwargs["text"]
    assert text.startswith("<blockquote expandable>")
    assert text.endswith("</blockquote>")
    assert "reply_markup" not in final_call.kwargs or final_call.kwargs.get(
        "reply_markup"
    ) is None

    # Pending prompt should be removed once transcription starts
    expired = await db.get_expired_pending_prompts(0)
    assert ("biz_123", 100, 99) not in expired

    # Usage recorded
    stats = await db.get_secretary_stats(42)
    assert stats is not None
    assert stats[0] == 1


async def test_transcribe_callback_invalid_data(handler: SecretaryHandler) -> None:
    update = MagicMock()
    query = MagicMock()
    query.data = "something_else:1"
    query.answer = AsyncMock()
    update.callback_query = query

    ctx = _make_context()
    await handler.handle_transcribe_callback(update, ctx)
    query.answer.assert_not_called()


async def test_transcribe_callback_handles_empty_transcription(
    handler: SecretaryHandler,
    mock_transcriber: MagicMock,
) -> None:
    conn = _make_business_connection()
    handler._connections["biz_123"] = conn
    mock_transcriber.transcribe.side_effect = EmptyTranscriptionError("no speech")

    update = MagicMock()
    query = MagicMock()
    query.data = "sec_transcribe:1:biz_123"
    query.answer = AsyncMock()
    prompt_msg = MagicMock()
    prompt_msg.chat.id = 100
    prompt_msg.message_id = 99
    prompt_msg.reply_to_message = _make_voice_message()
    query.message = prompt_msg
    update.callback_query = query

    bot = AsyncMock()
    tg_file = AsyncMock()
    tg_file.file_path = "audio.ogg"
    tg_file.download_to_drive = AsyncMock()
    bot.get_file = AsyncMock(return_value=tg_file)
    bot.edit_message_text = AsyncMock()
    ctx = _make_context(bot)

    with patch("src.bot.secretary.os.path.exists", return_value=True), \
         patch("src.bot.secretary.os.remove"):
        await handler.handle_transcribe_callback(update, ctx)

    last_call = str(bot.edit_message_text.call_args)
    assert "speech" in last_call.lower() or "no_speech" in last_call


async def test_transcribe_callback_audio_too_long(
    handler: SecretaryHandler,
    db: StatisticsDB,
) -> None:
    handler._max_audio_duration = 60  # 1 minute max
    conn = _make_business_connection()
    handler._connections["biz_123"] = conn

    update = MagicMock()
    query = MagicMock()
    query.data = "sec_transcribe:1:biz_123"
    query.answer = AsyncMock()
    prompt_msg = MagicMock()
    prompt_msg.chat.id = 100
    prompt_msg.message_id = 99
    prompt_msg.reply_to_message = _make_voice_message(duration=120)  # too long
    query.message = prompt_msg
    update.callback_query = query

    bot = AsyncMock()
    bot.edit_message_text = AsyncMock()
    ctx = _make_context(bot)

    await handler.handle_transcribe_callback(update, ctx)

    call_text = str(bot.edit_message_text.call_args)
    assert "too long" in call_text.lower() or "audio_too_long" in call_text


# --- Prompt auto-deletion tests ---


async def test_delete_expired_prompts_removes_old(
    handler: SecretaryHandler, db: StatisticsDB
) -> None:
    await db.add_pending_prompt("biz_123", 100, 5)
    await db.add_pending_prompt("biz_123", 100, 6)

    bot = AsyncMock()
    bot.delete_business_messages = AsyncMock()

    # Use a 0s threshold so the just-added prompts count as expired
    deleted = await handler.delete_expired_prompts(bot, older_than_seconds=0)

    assert deleted == 2
    assert bot.delete_business_messages.await_count == 2
    # DB should be cleared
    assert await db.get_expired_pending_prompts(0) == []


async def test_delete_expired_prompts_keeps_fresh(
    handler: SecretaryHandler, db: StatisticsDB
) -> None:
    await db.add_pending_prompt("biz_123", 100, 5)

    bot = AsyncMock()
    bot.delete_business_messages = AsyncMock()

    # Fresh prompt should not be deleted with the real TTL
    deleted = await handler.delete_expired_prompts(
        bot, older_than_seconds=PROMPT_TTL_SECONDS
    )

    assert deleted == 0
    bot.delete_business_messages.assert_not_called()


async def test_delete_expired_prompts_cleans_db_even_on_api_error(
    handler: SecretaryHandler, db: StatisticsDB
) -> None:
    await db.add_pending_prompt("biz_123", 100, 5)

    bot = AsyncMock()
    bot.delete_business_messages = AsyncMock(side_effect=Exception("boom"))

    deleted = await handler.delete_expired_prompts(bot, older_than_seconds=0)

    # Even if the Telegram API call fails, we stop tracking the prompt
    assert deleted == 1
    assert await db.get_expired_pending_prompts(0) == []


# --- Secretary Stats Tests ---


async def test_secretary_stats_record_and_get(db: StatisticsDB) -> None:
    await db.record_secretary_usage(42, "alice", 60)
    stats = await db.get_secretary_stats(42)
    assert stats is not None
    assert stats[0] == 1
    assert stats[1] == 60


async def test_secretary_stats_multiple(db: StatisticsDB) -> None:
    await db.record_secretary_usage(42, "alice", 60)
    await db.record_secretary_usage(42, "alice", 120)
    stats = await db.get_secretary_stats(42)
    assert stats is not None
    assert stats[0] == 2
    assert stats[1] == 180


async def test_secretary_stats_nonexistent(db: StatisticsDB) -> None:
    stats = await db.get_secretary_stats(999)
    assert stats is None


async def test_secretary_stats_get_all(db: StatisticsDB) -> None:
    await db.record_secretary_usage(1, "user1", 30)
    await db.record_secretary_usage(2, "user2", 60)
    all_stats = await db.get_all_secretary_stats()
    assert len(all_stats) == 2


# --- Notifier Tests ---


async def test_notify_secretary_event() -> None:
    bot = AsyncMock()
    notifier = AdminNotifier(bot, [111, 222])

    await notifier.notify_secretary_event("connected", "alice", 42)

    assert bot.send_message.call_count == 2
    call_text = bot.send_message.call_args_list[0].kwargs.get(
        "text", bot.send_message.call_args_list[0][1].get("text", "")
    )
    assert "connected" in call_text
    assert "alice" in call_text


async def test_notify_secretary_event_no_admins() -> None:
    bot = AsyncMock()
    notifier = AdminNotifier(bot, [])

    await notifier.notify_secretary_event("connected", "alice", 42)
    bot.send_message.assert_not_called()


# --- Dedup Tests ---


async def test_dedup_skips_second_business_message(
    handler: SecretaryHandler, db: StatisticsDB
) -> None:
    """Same file_id arriving via two connections — only one prompt is sent."""
    conn_a = _make_business_connection(conn_id="biz_a", user=_make_user(user_id=42))
    conn_b = _make_business_connection(
        conn_id="biz_b", user=_make_user(user_id=99, username="otheruser")
    )
    handler._connections["biz_a"] = conn_a
    handler._connections["biz_b"] = conn_b

    msg1 = _make_voice_message(biz_conn_id="biz_a")
    msg2 = _make_voice_message(biz_conn_id="biz_b")
    msg1.voice.file_id = "same_file_abc"
    msg2.voice.file_id = "same_file_abc"

    bot = AsyncMock()
    sent_msg = MagicMock()
    sent_msg.message_id = 99
    sent_msg.chat.id = 100
    bot.send_message = AsyncMock(return_value=sent_msg)
    ctx = _make_context(bot)

    await handler.handle_business_message(_make_update_with_business_message(msg1), ctx)
    await handler.handle_business_message(_make_update_with_business_message(msg2), ctx)

    assert bot.send_message.call_count == 1


async def test_dedup_allows_different_file_ids(
    handler: SecretaryHandler, db: StatisticsDB
) -> None:
    conn = _make_business_connection()
    handler._connections["biz_123"] = conn

    msg1 = _make_voice_message(message_id=1)
    msg1.voice.file_id = "file_1"
    msg2 = _make_voice_message(message_id=2)
    msg2.voice.file_id = "file_2"

    bot = AsyncMock()
    sent_msg = MagicMock()
    sent_msg.message_id = 99
    sent_msg.chat.id = 100
    bot.send_message = AsyncMock(return_value=sent_msg)
    ctx = _make_context(bot)

    await handler.handle_business_message(_make_update_with_business_message(msg1), ctx)
    await handler.handle_business_message(_make_update_with_business_message(msg2), ctx)

    assert bot.send_message.call_count == 2


async def test_smart_dedup_skips_outgoing_when_recipient_connected(
    handler: SecretaryHandler, db: StatisticsDB
) -> None:
    """Owner sends voice → skip if recipient also has the bot connected."""
    owner = _make_user(user_id=42)
    recipient_id = 99

    conn = _make_business_connection(conn_id="biz_a", user=owner)
    handler._connections["biz_a"] = conn
    await db.save_secretary_connection(recipient_id, "biz_b", "otheruser")

    msg = _make_voice_message(biz_conn_id="biz_a", chat_id=recipient_id)
    msg.from_user = owner  # Owner sent this (outgoing)
    msg.voice.file_id = "outgoing_file"

    bot = AsyncMock()
    bot.send_message = AsyncMock()
    ctx = _make_context(bot)

    await handler.handle_business_message(_make_update_with_business_message(msg), ctx)

    bot.send_message.assert_not_called()


async def test_smart_dedup_allows_outgoing_when_recipient_not_connected(
    handler: SecretaryHandler, db: StatisticsDB
) -> None:
    owner = _make_user(user_id=42)
    recipient_id = 99

    conn = _make_business_connection(conn_id="biz_a", user=owner)
    handler._connections["biz_a"] = conn

    msg = _make_voice_message(biz_conn_id="biz_a", chat_id=recipient_id)
    msg.from_user = owner
    msg.voice.file_id = "outgoing_file_2"

    bot = AsyncMock()
    sent_msg = MagicMock()
    sent_msg.message_id = 99
    sent_msg.chat.id = recipient_id
    bot.send_message = AsyncMock(return_value=sent_msg)
    ctx = _make_context(bot)

    await handler.handle_business_message(_make_update_with_business_message(msg), ctx)

    bot.send_message.assert_called_once()


async def test_smart_dedup_always_transcribes_incoming(
    handler: SecretaryHandler, db: StatisticsDB
) -> None:
    owner = _make_user(user_id=42)
    sender = _make_user(user_id=99, username="otheruser")

    conn = _make_business_connection(conn_id="biz_a", user=owner)
    handler._connections["biz_a"] = conn
    await db.save_secretary_connection(99, "biz_b", "otheruser")

    msg = _make_voice_message(biz_conn_id="biz_a", chat_id=99)
    msg.from_user = sender  # Other person sent this (incoming to owner)
    msg.voice.file_id = "incoming_file"

    bot = AsyncMock()
    sent_msg = MagicMock()
    sent_msg.message_id = 99
    sent_msg.chat.id = 99
    bot.send_message = AsyncMock(return_value=sent_msg)
    ctx = _make_context(bot)

    await handler.handle_business_message(_make_update_with_business_message(msg), ctx)

    bot.send_message.assert_called_once()
