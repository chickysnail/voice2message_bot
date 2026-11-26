"""Tests for voiceovers: the offer, quota, admin confirmation and reports."""

import os
import tempfile
from collections.abc import Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Document, Message
from telegram.error import BadRequest

from src.bot import voiceover as voiceover_module
from src.bot.handlers import BotHandlers
from src.bot.keyboards import (
    CALLBACK_VOICEOVER,
    CALLBACK_VOICEOVER_CANCEL,
    CALLBACK_VOICEOVER_CONFIRM,
)
from src.bot.locales import t
from src.bot.services.notifier import AdminNotifier
from src.bot.services.pricing import Pricing
from src.bot.services.tts import SpeechResult
from src.bot.storage.statistics import KIND_SPEECH, StatisticsDB, UsageEvent
from src.bot.voiceover import VoiceoverHandler, clock

ADMIN_ID = 111
USER_ID = 42


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
    return AsyncMock(spec=AdminNotifier)


@pytest.fixture
def synth(monkeypatch: pytest.MonkeyPatch) -> Iterator[AsyncMock]:
    """Stands in for ElevenLabs: 1 s of "speech" per 15 characters."""
    made: list[str] = []

    async def fake(client: object, text: str, **kwargs: object) -> SpeechResult:
        fd, path = tempfile.mkstemp(suffix=".ogg")
        os.write(fd, b"OggS")
        os.close(fd)
        made.append(path)
        return SpeechResult(path=path, seconds=len(text) / 15, chars=len(text), credits=len(text))

    mock = AsyncMock(side_effect=fake)
    monkeypatch.setattr(voiceover_module, "synthesize_voice", mock)
    yield mock
    for path in made:
        assert not os.path.exists(path), "voice file left on disk"


def _handler(notifier: AsyncMock, db: StatisticsDB, **kwargs: Any) -> VoiceoverHandler:
    return VoiceoverHandler(
        speech=MagicMock(),
        notifier=notifier,
        stats_db=db,
        admin_ids=[ADMIN_ID],
        pricing=Pricing(),
        **kwargs,
    )


def _source(text: str | None = "Привет! Это тест.") -> MagicMock:
    source = MagicMock(spec=Message)
    source.text = text
    source.document = None
    source.reply_voice = AsyncMock()
    source.reply_audio = AsyncMock()
    return source


def _tap(data: str, source: MagicMock | None, user_id: int = USER_ID) -> MagicMock:
    offer = MagicMock(spec=Message)
    offer.chat_id = user_id
    offer.message_id = 7
    offer.reply_to_message = source
    update = MagicMock()
    update.callback_query.data = data
    update.callback_query.message = offer
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.effective_user.id = user_id
    update.effective_user.username = "someone"
    update.effective_user.full_name = "Some One"
    update.effective_user.language_code = "en"
    return update


def _context() -> MagicMock:
    ctx = MagicMock()
    ctx.bot.send_chat_action = AsyncMock()
    return ctx


def _last_edit(update: MagicMock) -> str:
    return str(update.callback_query.edit_message_text.call_args.args[0])


async def _speech_events(db: StatisticsDB) -> list[tuple[Any, ...]]:
    return await db.fetchall(
        "SELECT user_id, source, audio_seconds, output_chars, cost_usd "
        "FROM usage_events WHERE kind = ?",
        (KIND_SPEECH,),
    )


async def test_admin_text_is_voiced_with_cost(
    notifier: AsyncMock, db: StatisticsDB, synth: AsyncMock
) -> None:
    source = _source("Привет! Это тест.")
    update = _tap(CALLBACK_VOICEOVER, source, user_id=ADMIN_ID)
    await _handler(notifier, db).handle_callback(update, _context())

    synth.assert_awaited_once()
    assert synth.call_args.args[1] == "Привет! Это тест."
    source.reply_voice.assert_awaited_once()
    status = _last_edit(update)
    assert "Characters: 17" in status
    assert "credits: 17" in status
    assert "$" in status
    events = await _speech_events(db)
    assert len(events) == 1
    assert events[0][0] == ADMIN_ID
    assert events[0][1] == "text"
    assert events[0][4] == pytest.approx(17 / 1000 * 0.08)
    notifier.notify_admins.assert_not_awaited()


async def test_admin_is_asked_before_an_expensive_voiceover(
    notifier: AsyncMock, db: StatisticsDB, synth: AsyncMock
) -> None:
    handler = _handler(notifier, db, confirm_usd=1.0)
    source = _source("Слово. " * 2500)  # 17,500 chars ≈ $1.40
    update = _tap(CALLBACK_VOICEOVER, source, user_id=ADMIN_ID)
    await handler.handle_callback(update, _context())

    synth.assert_not_awaited()
    kwargs = update.callback_query.edit_message_text.call_args.kwargs
    buttons = [b.callback_data for b in kwargs["reply_markup"].inline_keyboard[0]]
    assert buttons == [CALLBACK_VOICEOVER_CONFIRM, CALLBACK_VOICEOVER_CANCEL]
    assert "$1.40" in _last_edit(update)

    confirm = _tap(CALLBACK_VOICEOVER_CONFIRM, source, user_id=ADMIN_ID)
    await handler.handle_callback(confirm, _context())
    synth.assert_awaited_once()
    source.reply_voice.assert_awaited_once()


async def test_admin_has_no_quota(
    notifier: AsyncMock, db: StatisticsDB, synth: AsyncMock
) -> None:
    await db.record_event(UsageEvent(
        user_id=ADMIN_ID, username="me", kind=KIND_SPEECH, source="text", audio_seconds=3600,
    ))
    update = _tap(CALLBACK_VOICEOVER, _source(), user_id=ADMIN_ID)
    await _handler(notifier, db).handle_callback(update, _context())
    synth.assert_awaited_once()


async def test_cancel_does_not_voice(
    notifier: AsyncMock, db: StatisticsDB, synth: AsyncMock
) -> None:
    update = _tap(CALLBACK_VOICEOVER_CANCEL, _source(), user_id=ADMIN_ID)
    await _handler(notifier, db).handle_callback(update, _context())
    synth.assert_not_awaited()
    assert _last_edit(update) == t("voiceover_cancelled", "en")


async def test_user_voiceover_reports_to_admins(
    notifier: AsyncMock, db: StatisticsDB, synth: AsyncMock
) -> None:
    source = _source("a" * 150)  # 10 s
    update = _tap(CALLBACK_VOICEOVER, source)
    await _handler(notifier, db).handle_callback(update, _context())

    source.reply_voice.assert_awaited_once()
    assert _last_edit(update) == t("voiceover_done", "en", left=9, quota="10", days=30)
    notifier.notify_admins.assert_awaited_once()
    report = notifier.notify_admins.call_args.args[0]
    assert "Some One" in report and "@someone" in report and str(USER_ID) in report
    assert "0:10 of audio" in report
    assert "150 chars" in report
    assert "Last 30 days: 0:10 of 10:00" in report
    assert "a" * 150 not in report  # never the text itself


async def test_user_reports_can_be_turned_off(
    notifier: AsyncMock, db: StatisticsDB, synth: AsyncMock
) -> None:
    update = _tap(CALLBACK_VOICEOVER, _source())
    await _handler(notifier, db, notify_admins=False).handle_callback(update, _context())
    synth.assert_awaited_once()
    notifier.notify_admins.assert_not_awaited()


async def test_user_over_quota_is_refused(
    notifier: AsyncMock, db: StatisticsDB, synth: AsyncMock
) -> None:
    await db.record_event(UsageEvent(
        user_id=USER_ID, username="someone", kind=KIND_SPEECH, source="text",
        audio_seconds=9.5 * 60,
    ))
    update = _tap(CALLBACK_VOICEOVER, _source("a" * 900))  # 1 min
    await _handler(notifier, db).handle_callback(update, _context())

    synth.assert_not_awaited()
    assert _last_edit(update) == t(
        "voiceover_limit", "en", quota="10", days=30, left=0, need=1
    )


async def test_quota_only_counts_recent_speech(db: StatisticsDB) -> None:
    for seconds in (60, 120):
        await db.record_event(UsageEvent(
            user_id=USER_ID, username=None, kind=KIND_SPEECH, source="text",
            audio_seconds=seconds,
        ))
    await db.record_event(UsageEvent(
        user_id=USER_ID, username=None, kind="transcription", source="voice",
        audio_seconds=500,
    ))
    assert db._db is not None
    await db._db.execute(
        "UPDATE usage_events SET created_at = datetime('now', '-40 days') "
        "WHERE audio_seconds = 120"
    )
    assert await db.get_speech_seconds(USER_ID, 30) == 60
    assert await db.get_speech_seconds(USER_ID, 60) == 180


async def test_second_tap_while_voicing_is_ignored(
    notifier: AsyncMock, db: StatisticsDB, synth: AsyncMock
) -> None:
    handler = _handler(notifier, db)
    update = _tap(CALLBACK_VOICEOVER, _source())
    handler._busy.add((USER_ID, 7))
    await handler.handle_callback(update, _context())
    synth.assert_not_awaited()
    update.callback_query.answer.assert_awaited_once()


async def test_missing_source_text(
    notifier: AsyncMock, db: StatisticsDB, synth: AsyncMock
) -> None:
    update = _tap(CALLBACK_VOICEOVER, None)
    await _handler(notifier, db).handle_callback(update, _context())
    synth.assert_not_awaited()
    assert _last_edit(update) == t("voiceover_no_text", "en")


async def test_voice_messages_forbidden_falls_back_to_audio(
    notifier: AsyncMock, db: StatisticsDB, synth: AsyncMock
) -> None:
    source = _source()
    source.reply_voice.side_effect = BadRequest("Voice_messages_forbidden")
    update = _tap(CALLBACK_VOICEOVER, source)
    await _handler(notifier, db).handle_callback(update, _context())
    source.reply_audio.assert_awaited_once()
    assert len(await _speech_events(db)) == 1


async def test_failure_tells_user_and_admins(
    notifier: AsyncMock, db: StatisticsDB, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        voiceover_module, "synthesize_voice",
        AsyncMock(side_effect=RuntimeError("ElevenLabs speech failed: quota_exceeded")),
    )
    update = _tap(CALLBACK_VOICEOVER, _source())
    await _handler(notifier, db).handle_callback(update, _context())
    assert _last_edit(update) == t("voiceover_failed", "en")
    notifier.notify_error.assert_awaited_once()
    assert "quota_exceeded" in notifier.notify_error.call_args.kwargs["error_detail"]
    assert await _speech_events(db) == []


def _text_file_source(data: bytes, name: str = "notes.txt", size: int | None = None) -> MagicMock:
    source = _source(None)
    document = MagicMock(spec=Document)
    document.file_name = name
    document.mime_type = "text/plain"
    document.file_size = len(data) if size is None else size
    tg_file = MagicMock()
    tg_file.download_as_bytearray = AsyncMock(return_value=bytearray(data))
    document.get_file = AsyncMock(return_value=tg_file)
    source.document = document
    return source


async def test_text_file_is_voiced(
    notifier: AsyncMock, db: StatisticsDB, synth: AsyncMock
) -> None:
    source = _text_file_source("Текст из файла.".encode("cp1251"))
    update = _tap(CALLBACK_VOICEOVER, source)
    await _handler(notifier, db).handle_callback(update, _context())
    assert synth.call_args.args[1] == "Текст из файла."
    events = await _speech_events(db)
    assert events[0][1] == "text_file"


async def test_too_big_text_file_is_refused(
    notifier: AsyncMock, db: StatisticsDB, synth: AsyncMock
) -> None:
    source = _text_file_source(b"x", size=5 * 1024 * 1024)
    update = _tap(CALLBACK_VOICEOVER, source, user_id=ADMIN_ID)
    await _handler(notifier, db).handle_callback(update, _context())
    synth.assert_not_awaited()
    assert _last_edit(update) == t("voiceover_file_too_large", "en", max_mb=1)


async def test_binary_file_is_unreadable(
    notifier: AsyncMock, db: StatisticsDB, synth: AsyncMock
) -> None:
    source = _text_file_source(b"\x00\x01\x02")
    update = _tap(CALLBACK_VOICEOVER, source)
    await _handler(notifier, db).handle_callback(update, _context())
    synth.assert_not_awaited()
    assert _last_edit(update) == t("voiceover_file_unreadable", "en")


async def test_offer_for_text_file(notifier: AsyncMock, db: StatisticsDB) -> None:
    update = MagicMock()
    update.message.document = _text_file_source(b"hi").document
    update.message.reply_text = AsyncMock()
    update.effective_user.language_code = "ru"
    await _handler(notifier, db).offer_for_file(update, _context())
    kwargs = update.message.reply_text.call_args.kwargs
    assert kwargs["do_quote"] is True
    assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data == CALLBACK_VOICEOVER


def _bot_handlers(db: StatisticsDB, voiceover: bool) -> BotHandlers:
    return BotHandlers(
        transcriber=MagicMock(),
        summarizer=MagicMock(),
        notifier=AsyncMock(spec=AdminNotifier),
        store=MagicMock(),
        stats_db=db,
        max_audio_duration=3600,
        voiceover=voiceover,
    )


def _text_update(text: str) -> MagicMock:
    update = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.effective_user.language_code = "ru"
    return update


async def test_plain_text_gets_the_voice_button(db: StatisticsDB) -> None:
    update = _text_update("просто текст")
    await _bot_handlers(db, voiceover=True).handle_text(update, MagicMock())
    args, kwargs = update.message.reply_text.call_args
    assert args[0] == t("text_nudge_voiceover", "ru")
    assert kwargs["do_quote"] is True
    assert kwargs["reply_markup"].inline_keyboard[0][0].callback_data == CALLBACK_VOICEOVER


async def test_plain_text_without_voiceover_keeps_old_nudge(db: StatisticsDB) -> None:
    update = _text_update("просто текст")
    await _bot_handlers(db, voiceover=False).handle_text(update, MagicMock())
    update.message.reply_text.assert_awaited_once_with(t("text_nudge", "ru"))


async def test_help_mentions_voiceover_before_privacy(db: StatisticsDB) -> None:
    update = _text_update("/help")
    await _bot_handlers(db, voiceover=True).help_command(update, MagicMock())
    text = update.message.reply_text.call_args.args[0]
    assert t("help_voiceover", "ru") in text
    assert text.rstrip().endswith(t("help", "ru").rpartition("\n\n")[2])


def test_clock() -> None:
    assert clock(5) == "0:05"
    assert clock(83.4) == "1:23"
    assert clock(3725) == "1:02:05"
