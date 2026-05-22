"""Tests for secretary (business message) handler."""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.secretary import SecretaryHandler
from src.bot.services.notifier import AdminNotifier
from src.bot.services.summarization import SummarizationClient
from src.bot.services.transcription import (
    EmptyTranscriptionError,
    TranscriptionClient,
    TranscriptionResult,
)
from src.bot.storage.statistics import StatisticsDB
from src.bot.storage.transcription_store import TranscriptionStore


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
def store() -> TranscriptionStore:
    return TranscriptionStore(ttl_seconds=600)


@pytest.fixture
def mock_summarizer() -> MagicMock:
    s = MagicMock(spec=SummarizationClient)
    s.summarize.return_value = "This is a summary."
    return s


@pytest.fixture
def handler(
    mock_transcriber: MagicMock,
    mock_summarizer: MagicMock,
    mock_notifier: AsyncMock,
    store: TranscriptionStore,
    db: StatisticsDB,
) -> SecretaryHandler:
    return SecretaryHandler(
        transcriber=mock_transcriber,
        summarizer=mock_summarizer,
        notifier=mock_notifier,
        store=store,
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
    handler: SecretaryHandler, mock_notifier: AsyncMock
) -> None:
    conn = _make_business_connection(is_enabled=True)
    update = _make_update_with_connection(conn)
    ctx = _make_context()

    await handler.handle_business_connection(update, ctx)

    assert "biz_123" in handler._connections
    mock_notifier.notify_secretary_event.assert_called_once_with(
        "connected", "testuser", 42
    )


async def test_handle_connection_disabled(
    handler: SecretaryHandler, mock_notifier: AsyncMock
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


async def test_handle_connection_none(handler: SecretaryHandler) -> None:
    update = MagicMock()
    update.business_connection = None
    ctx = _make_context()
    await handler.handle_business_connection(update, ctx)
    assert len(handler._connections) == 0


# --- Auto Mode Tests ---


async def test_auto_mode_transcribes_voice(
    handler: SecretaryHandler,
    mock_transcriber: MagicMock,
    db: StatisticsDB,
) -> None:
    # Set up connection
    conn = _make_business_connection()
    handler._connections["biz_123"] = conn

    message = _make_voice_message()
    update = _make_update_with_business_message(message)

    bot = AsyncMock()
    tg_file = AsyncMock()
    tg_file.file_path = "audio.ogg"
    tg_file.download_to_drive = AsyncMock()
    bot.get_file = AsyncMock(return_value=tg_file)

    sent_msg = MagicMock()
    sent_msg.message_id = 99
    sent_msg.chat.id = 100
    bot.send_message = AsyncMock(return_value=sent_msg)
    bot.edit_message_text = AsyncMock()

    ctx = _make_context(bot)

    with patch("src.bot.secretary.os.path.exists", return_value=True), \
         patch("src.bot.secretary.os.remove"):
        await handler.handle_business_message(update, ctx)

    # Should have called transcriber
    mock_transcriber.transcribe.assert_called_once()

    # Should have recorded secretary usage
    stats = await db.get_secretary_stats(42)
    assert stats is not None
    assert stats[0] == 1  # 1 transcription


async def test_auto_mode_skips_non_audio(handler: SecretaryHandler) -> None:
    conn = _make_business_connection()
    handler._connections["biz_123"] = conn

    message = MagicMock()
    message.business_connection_id = "biz_123"
    message.voice = None
    message.video_note = None

    update = _make_update_with_business_message(message)
    ctx = _make_context()

    await handler.handle_business_message(update, ctx)
    # No transcription should happen — bot methods should not be called
    ctx.bot.send_message.assert_not_called()


# --- Manual Mode Tests ---


async def test_manual_mode_sends_prompt(
    handler: SecretaryHandler, db: StatisticsDB
) -> None:
    conn = _make_business_connection()
    handler._connections["biz_123"] = conn
    await db.set_secretary_mode(42, "manual")

    message = _make_voice_message()
    update = _make_update_with_business_message(message)

    bot = AsyncMock()
    ctx = _make_context(bot)

    await handler.handle_business_message(update, ctx)

    # Should send a prompt with keyboard, not transcribe
    bot.send_message.assert_called_once()
    call_kwargs = bot.send_message.call_args
    assert "reply_markup" in call_kwargs.kwargs
    assert "sec_transcribe" in str(call_kwargs.kwargs["reply_markup"])


async def test_transcribe_callback_flow(
    handler: SecretaryHandler,
    mock_transcriber: MagicMock,
    db: StatisticsDB,
) -> None:
    conn = _make_business_connection()
    handler._connections["biz_123"] = conn

    # Simulate the callback query
    update = MagicMock()
    query = MagicMock()
    query.data = "sec_transcribe:1:biz_123"
    query.answer = AsyncMock()

    # The prompt message that will be edited
    prompt_msg = MagicMock()
    prompt_msg.chat.id = 100
    prompt_msg.message_id = 99

    # The original voice message (reply_to_message of the prompt)
    original_msg = _make_voice_message()
    prompt_msg.reply_to_message = original_msg

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

    # Should have edited the prompt to "Transcribing..."
    # and then to the transcription text
    assert bot.edit_message_text.call_count >= 2
    mock_transcriber.transcribe.assert_called_once()


async def test_transcribe_callback_invalid_data(handler: SecretaryHandler) -> None:
    update = MagicMock()
    query = MagicMock()
    query.data = "something_else:1"
    query.answer = AsyncMock()
    update.callback_query = query

    ctx = _make_context()
    await handler.handle_transcribe_callback(update, ctx)
    # Should return early without doing anything
    query.answer.assert_not_called()


# --- Secretary Mode Settings Tests ---


async def test_secretary_mode_default_auto(db: StatisticsDB) -> None:
    mode = await db.get_secretary_mode(42)
    assert mode == "auto"


async def test_secretary_mode_set_manual(db: StatisticsDB) -> None:
    await db.set_secretary_mode(42, "manual")
    mode = await db.get_secretary_mode(42)
    assert mode == "manual"


async def test_secretary_mode_set_auto(db: StatisticsDB) -> None:
    await db.set_secretary_mode(42, "manual")
    await db.set_secretary_mode(42, "auto")
    mode = await db.get_secretary_mode(42)
    assert mode == "auto"


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


# --- Error Handling Tests ---


async def test_auto_mode_handles_empty_transcription(
    handler: SecretaryHandler,
    mock_transcriber: MagicMock,
) -> None:
    conn = _make_business_connection()
    handler._connections["biz_123"] = conn

    mock_transcriber.transcribe.side_effect = EmptyTranscriptionError("no speech")

    message = _make_voice_message()
    update = _make_update_with_business_message(message)

    bot = AsyncMock()
    tg_file = AsyncMock()
    tg_file.file_path = "audio.ogg"
    tg_file.download_to_drive = AsyncMock()
    bot.get_file = AsyncMock(return_value=tg_file)

    sent_msg = MagicMock()
    sent_msg.message_id = 99
    sent_msg.chat.id = 100
    bot.send_message = AsyncMock(return_value=sent_msg)
    bot.edit_message_text = AsyncMock()

    ctx = _make_context(bot)

    with patch("src.bot.secretary.os.path.exists", return_value=True), \
         patch("src.bot.secretary.os.remove"):
        await handler.handle_business_message(update, ctx)

    # Should edit message with "no speech" text
    bot.edit_message_text.assert_called()
    last_call = bot.edit_message_text.call_args
    assert "no_speech" in str(last_call) or "speech" in str(last_call).lower()


async def test_auto_mode_audio_too_long(
    handler: SecretaryHandler,
) -> None:
    h = SecretaryHandler(
        transcriber=MagicMock(),
        summarizer=MagicMock(),
        notifier=AsyncMock(),
        store=TranscriptionStore(),
        stats_db=MagicMock(),
        max_audio_duration=60,  # 1 minute max
    )

    conn = _make_business_connection()
    h._connections["biz_123"] = conn

    message = _make_voice_message(duration=120)  # 2 minutes — too long
    update = _make_update_with_business_message(message)

    bot = AsyncMock()
    sent_msg = MagicMock()
    sent_msg.message_id = 99
    sent_msg.chat.id = 100
    bot.send_message = AsyncMock(return_value=sent_msg)
    bot.edit_message_text = AsyncMock()

    # Need to mock get_secretary_mode
    h._stats_db = AsyncMock()
    h._stats_db.get_secretary_mode = AsyncMock(return_value="auto")

    ctx = _make_context(bot)

    await h.handle_business_message(update, ctx)

    # Should edit with "too long" message
    bot.edit_message_text.assert_called_once()
    call_text = str(bot.edit_message_text.call_args)
    assert "audio_too_long" in call_text or "too long" in call_text.lower()


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


# --- Post-Transcription Callback Tests ---


def _make_callback_update(
    callback_data: str,
    user_id: int = 99,
    username: str = "otheruser",
    lang: str = "en",
) -> MagicMock:
    """Create an update with a callback query, simulating a button press."""
    update = MagicMock()
    query = MagicMock()
    query.data = callback_data
    query.answer = AsyncMock()
    query.message = MagicMock()
    query.message.reply_text = AsyncMock()
    query.message.reply_document = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    update.callback_query = query

    user = MagicMock()
    user.id = user_id
    user.username = username
    user.language_code = lang
    update.effective_user = user
    return update


async def test_sec_summarize_by_other_user(
    handler: SecretaryHandler,
    mock_summarizer: MagicMock,
    store: TranscriptionStore,
) -> None:
    """Other person clicks Summarize — should find transcription via owner_user_id."""
    owner_id = 42
    msg_id = 1
    store.save(owner_id, msg_id, "Hello world transcript")

    # Other user (id=99) clicks the sec_summarize button
    update = _make_callback_update(f"sec_summarize:{msg_id}:{owner_id}")
    ctx = _make_context()

    await handler.handle_post_transcription_callback(update, ctx)

    mock_summarizer.summarize.assert_called_once_with("Hello world transcript")
    update.callback_query.message.reply_text.assert_called()


async def test_sec_summarize_expired(
    handler: SecretaryHandler,
    store: TranscriptionStore,
) -> None:
    """Summarize with no stored transcription — should show expired message."""
    update = _make_callback_update("sec_summarize:1:42")
    ctx = _make_context()

    await handler.handle_post_transcription_callback(update, ctx)

    update.callback_query.message.reply_text.assert_called_once()
    call_text = str(update.callback_query.message.reply_text.call_args)
    assert "expired" in call_text.lower() or "transcription_expired" in call_text


async def test_sec_savefile_shows_format_keyboard(
    handler: SecretaryHandler,
    store: TranscriptionStore,
) -> None:
    """Save as file button should show format selection keyboard."""
    owner_id = 42
    msg_id = 1
    store.save(owner_id, msg_id, "Hello world transcript")

    update = _make_callback_update(f"sec_savefile:{msg_id}:{owner_id}")
    ctx = _make_context()

    await handler.handle_post_transcription_callback(update, ctx)

    update.callback_query.edit_message_reply_markup.assert_called()
    markup = str(update.callback_query.edit_message_reply_markup.call_args)
    assert "sec_export_txt" in markup
    assert "sec_export_srt" in markup


async def test_sec_export_txt(
    handler: SecretaryHandler,
    store: TranscriptionStore,
) -> None:
    """Export as .txt should send a document."""
    owner_id = 42
    msg_id = 1
    store.save(owner_id, msg_id, "Hello world transcript")

    update = _make_callback_update(f"sec_export_txt:{msg_id}:{owner_id}")
    ctx = _make_context()

    await handler.handle_post_transcription_callback(update, ctx)

    update.callback_query.message.reply_document.assert_called_once()
    call_kwargs = update.callback_query.message.reply_document.call_args.kwargs
    assert call_kwargs["filename"] == "transcription.txt"


async def test_sec_summarize_by_owner(
    handler: SecretaryHandler,
    mock_summarizer: MagicMock,
    store: TranscriptionStore,
) -> None:
    """Owner clicks Summarize — should also work with embedded owner_id."""
    owner_id = 42
    msg_id = 1
    store.save(owner_id, msg_id, "Hello world transcript")

    # Owner themselves clicks (user_id matches owner_id)
    update = _make_callback_update(
        f"sec_summarize:{msg_id}:{owner_id}", user_id=owner_id
    )
    ctx = _make_context()

    await handler.handle_post_transcription_callback(update, ctx)

    mock_summarizer.summarize.assert_called_once_with("Hello world transcript")
