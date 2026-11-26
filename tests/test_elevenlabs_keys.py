"""Tests for switching to the backup ElevenLabs key when the main one is refused."""

import os
import tempfile
from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from elevenlabs.core.api_error import ApiError

from src.bot.services.elevenlabs_keys import KeyFailover, key_refused
from src.bot.services.transcription import ElevenLabsTranscriber


def _refused(status: int = 401, code: str = "quota_exceeded") -> ApiError:
    return ApiError(
        headers={"server": "uvicorn"},
        status_code=status,
        body={"detail": {"status": code, "message": "This request exceeds your quota."}},
    )


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> Clock:
    return Clock()


def _failover(clock: Clock, backup: bool = True) -> tuple[KeyFailover, list[str]]:
    keys = KeyFailover(
        MagicMock(name="main"),
        MagicMock(name="backup") if backup else None,
        service="transcription",
        retry_main_after=3600,
        clock=clock,
    )
    told: list[str] = []
    keys.notify = told.append
    return keys, told


def _request(refuse: dict[str, Exception]) -> tuple[Any, list[str]]:
    """A request that records which client ran it and fails for some of them."""
    used: list[str] = []

    def request(client: MagicMock) -> str:
        name = client._mock_name
        used.append(name)
        if name in refuse:
            raise refuse[name]
        return f"done by {name}"

    return request, used


def test_main_key_is_used_while_it_works(clock: Clock) -> None:
    keys, told = _failover(clock)
    request, used = _request({})
    assert keys.call(request) == "done by main"
    assert used == ["main"]
    assert told == []


def test_refused_main_key_switches_to_backup(clock: Clock) -> None:
    keys, told = _failover(clock)
    request, used = _request({"main": _refused()})
    assert keys.call(request) == "done by backup"
    assert used == ["main", "backup"]
    assert len(told) == 1
    assert "HTTP 401 quota_exceeded" in told[0]
    assert "backup key" in told[0]


def test_backup_is_used_directly_for_an_hour(clock: Clock) -> None:
    keys, told = _failover(clock)
    keys.call(_request({"main": _refused()})[0])

    clock.now += 3599
    request, used = _request({})
    assert keys.call(request) == "done by backup"
    assert used == ["backup"]
    assert len(told) == 1


def test_main_key_is_retried_after_an_hour(clock: Clock) -> None:
    keys, told = _failover(clock)
    keys.call(_request({"main": _refused()})[0])

    clock.now += 3600
    request, used = _request({})
    assert keys.call(request) == "done by main"
    assert used == ["main"]
    assert told[-1] == "✅ ElevenLabs transcription: back on the main API key."

    # Back on main: the next request goes there too.
    request, used = _request({})
    keys.call(request)
    assert used == ["main"]
    assert len(told) == 2


def test_still_refused_after_an_hour_does_not_repeat_the_alert(clock: Clock) -> None:
    keys, told = _failover(clock)
    keys.call(_request({"main": _refused()})[0])
    clock.now += 3600
    request, used = _request({"main": _refused()})
    assert keys.call(request) == "done by backup"
    assert used == ["main", "backup"]
    assert len(told) == 1

    # The hour starts over.
    clock.now += 1800
    request, used = _request({})
    keys.call(request)
    assert used == ["backup"]


@pytest.mark.parametrize("status", [401, 402, 403, 429])
def test_key_refusals(status: int) -> None:
    assert key_refused(_refused(status))


@pytest.mark.parametrize(
    "error", [ApiError(status_code=400, body={}), ApiError(status_code=500, body={}),
              ValueError("timeout")],
)
def test_other_errors_are_not_retried(clock: Clock, error: Exception) -> None:
    keys, told = _failover(clock)
    request, used = _request({"main": error})
    with pytest.raises(type(error)):
        keys.call(request)
    assert used == ["main"]
    assert told == []


def test_without_backup_the_refusal_is_raised(clock: Clock) -> None:
    keys, told = _failover(clock, backup=False)
    request, used = _request({"main": _refused()})
    with pytest.raises(ApiError):
        keys.call(request)
    assert used == ["main"]
    assert told == []


def test_backup_refused_too_raises_its_error(clock: Clock) -> None:
    keys, _ = _failover(clock)
    backup_error = _refused(401, "missing_permissions")
    request, used = _request({"main": _refused(), "backup": backup_error})
    with pytest.raises(ApiError) as info:
        keys.call(request)
    assert info.value is backup_error
    assert used == ["main", "backup"]


def test_broken_notify_does_not_break_the_request(clock: Clock) -> None:
    keys, _ = _failover(clock)

    def explode(text: str) -> None:
        raise RuntimeError("telegram down")

    keys.notify = explode
    assert keys.call(_request({"main": _refused()})[0]) == "done by backup"


@pytest.fixture
def audio_file() -> Iterator[str]:
    fd, path = tempfile.mkstemp(suffix=".ogg")
    os.write(fd, b"OggS fake audio")
    os.close(fd)
    yield path
    os.remove(path)


def test_transcription_falls_back_to_backup_key(audio_file: str) -> None:
    main, backup = MagicMock(), MagicMock()
    main.speech_to_text.convert.side_effect = _refused()
    result = MagicMock(text="Привет", words=[], audio_duration_secs=3.0)
    backup.speech_to_text.convert.return_value = result
    with patch("src.bot.services.transcription.ElevenLabs", side_effect=[main, backup]):
        transcriber = ElevenLabsTranscriber("main-key", backup_api_key="backup-key")
    told: list[str] = []
    transcriber.keys.notify = told.append

    assert transcriber.transcribe(audio_file).text == "Привет"
    # The file was reopened for the retry, not read past its end.
    first = main.speech_to_text.convert.call_args.kwargs["file"]
    second = backup.speech_to_text.convert.call_args.kwargs["file"]
    assert first is not second
    assert len(told) == 1


def test_transcription_error_shows_reason_not_headers(audio_file: str) -> None:
    main = MagicMock()
    main.speech_to_text.convert.side_effect = _refused()
    with patch("src.bot.services.transcription.ElevenLabs", return_value=main):
        transcriber = ElevenLabsTranscriber("main-key")
    with pytest.raises(RuntimeError) as info:
        transcriber.transcribe(audio_file)
    assert str(info.value) == (
        "ElevenLabs transcription failed: HTTP 401 quota_exceeded: "
        "This request exceeds your quota."
    )
