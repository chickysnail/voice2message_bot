"""Tests for command handlers — secretary setup album and broadcast."""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Message

from src.bot.handlers import SECRETARY_SETUP_IMAGES, BotHandlers
from src.bot.keyboards import link_audio_keyboard
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


@pytest.fixture
def link_handlers(notifier: AsyncMock, db: StatisticsDB) -> BotHandlers:
    resolver = AsyncMock()
    resolver.resolve.return_value = "https://cdn.example.com/a.mp3"
    resolver.referer = "https://provider.example.com/"
    return BotHandlers(
        transcriber=MagicMock(),
        summarizer=MagicMock(),
        notifier=notifier,
        store=MagicMock(),
        stats_db=db,
        max_audio_duration=3600,
        media_resolvers={"youtube": resolver},
    )


def _link_update(text: str) -> MagicMock:
    update = _make_update()
    update.message.text = text
    update.message.message_id = 7
    update.message.reply_text = AsyncMock(return_value=AsyncMock())
    return update


def _patch_download(monkeypatch: pytest.MonkeyPatch, duration: float, tmp: str) -> None:
    async def fake_download(url: str, **kwargs: object) -> str:
        path = os.path.join(tmp, "media.mp3")
        with open(path, "wb") as fh:
            fh.write(b"id3")
        return path

    async def fake_extract(path: str, **kwargs: object) -> str:
        out = os.path.join(tmp, "audio.ogg")
        with open(out, "wb") as fh:
            fh.write(b"ogg")
        return out

    async def fake_duration(path: str) -> float:
        return duration

    monkeypatch.setattr("src.bot.handlers.download_media", fake_download)
    monkeypatch.setattr("src.bot.handlers.extract_audio", fake_extract)
    monkeypatch.setattr("src.bot.handlers.get_audio_duration", fake_duration)


async def test_short_link_transcribes_and_offers_audio(
    link_handlers: BotHandlers,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: object,
) -> None:
    _patch_download(monkeypatch, 60.0, str(tmp_path))
    transcribe = AsyncMock()
    monkeypatch.setattr(link_handlers, "_transcribe_link_audio", transcribe)
    update = _link_update("https://youtu.be/jNQXAC9IVRw")

    await link_handlers.handle_text(update, MagicMock())

    processing = update.message.reply_text.return_value
    markup = processing.edit_text.call_args.kwargs["reply_markup"]
    assert [b.callback_data for row in markup.inline_keyboard for b in row] == [
        "link_audio:7"
    ]
    transcribe.assert_awaited_once()
    # The mp3 the provider returned is kept for the button, not the .ogg copy.
    assert transcribe.await_args.args[2].endswith("media.mp3")


async def test_long_link_offers_transcribe_or_audio(
    link_handlers: BotHandlers,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: object,
) -> None:
    _patch_download(monkeypatch, 25 * 60.0, str(tmp_path))
    transcribe = AsyncMock()
    monkeypatch.setattr(link_handlers, "_transcribe_link_audio", transcribe)
    update = _link_update("https://youtu.be/jNQXAC9IVRw")

    await link_handlers.handle_text(update, MagicMock())

    processing = update.message.reply_text.return_value
    markup = processing.edit_text.call_args.kwargs["reply_markup"]
    assert [b.callback_data for row in markup.inline_keyboard for b in row] == [
        "link_transcribe:7",
        "link_audio:7",
    ]
    transcribe.assert_not_awaited()


async def test_download_audio_button_removed_after_sending(
    link_handlers: BotHandlers, tmp_path: object
) -> None:
    from src.bot.keyboards import link_choice_keyboard, post_transcription_keyboard

    path = os.path.join(str(tmp_path), "audio.mp3")
    with open(path, "wb") as fh:
        fh.write(b"id3")
    link_handlers._media_audio.save(42, 7, path, 30)

    for markup, expected in (
        (post_transcription_keyboard(7, "en", with_audio=True),
         ["summarize:7", "savefile:7"]),
        (link_choice_keyboard(7, "en"), ["link_transcribe:7"]),
        (link_audio_keyboard(7, "en"), None),
    ):
        query = AsyncMock()
        query.message = MagicMock(spec=Message)
        query.message.reply_markup = markup
        query.message.reply_audio = AsyncMock()
        user = MagicMock()
        user.id = 42
        user.language_code = "en"

        await link_handlers._handle_link_audio(query, user, 7)

        query.message.reply_audio.assert_awaited_once()
        new_markup = query.edit_message_reply_markup.await_args.kwargs["reply_markup"]
        if expected is None:
            assert new_markup is None
        else:
            assert [
                b.callback_data for row in new_markup.inline_keyboard for b in row
            ] == expected


async def test_long_transcript_is_sent_as_html_file() -> None:
    from src.bot.handlers import _send_transcript
    from src.bot.keyboards import post_transcription_keyboard

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    message.reply_document = AsyncMock()
    keyboard = post_transcription_keyboard(1, "en")

    await _send_transcript(message, "word " * 1200, "en", keyboard)

    message.reply_text.assert_not_awaited()
    kwargs = message.reply_document.await_args.kwargs
    assert kwargs["filename"] == "transcript.html"
    assert kwargs["reply_markup"] is keyboard
    assert b"<p>word" in kwargs["document"].getvalue()


async def test_short_transcript_is_sent_as_message() -> None:
    from src.bot.handlers import _send_transcript
    from src.bot.keyboards import post_transcription_keyboard

    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    message.reply_document = AsyncMock()

    await _send_transcript(message, "short one", "en", post_transcription_keyboard(1))

    message.reply_document.assert_not_awaited()
    assert message.reply_text.await_args.args[0] == "short one"
