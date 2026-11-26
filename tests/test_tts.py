"""Tests for text-to-speech: splitting, joining pieces, and the ElevenLabs call."""

import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from elevenlabs.core.api_error import ApiError

from src.bot.services.pricing import Pricing
from src.bot.services.tts import (
    CHARS_PER_SECOND,
    ElevenLabsSpeech,
    describe_error,
    estimate_seconds,
    split_text,
    synthesize_voice,
)

try:
    subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    FFMPEG_AVAILABLE = True
except (FileNotFoundError, subprocess.CalledProcessError):
    FFMPEG_AVAILABLE = False


def test_short_text_is_one_piece() -> None:
    assert split_text("  Привет, мир!  ") == ["Привет, мир!"]


def test_empty_text_has_no_pieces() -> None:
    assert split_text("   \n ") == []


def test_long_text_splits_at_paragraphs() -> None:
    first = "a" * 60
    second = "b" * 60
    assert split_text(f"{first}\n\n{second}", limit=100) == [first, second]


def test_long_text_splits_at_sentence_end() -> None:
    text = ("Это первое предложение. " * 6) + "Хвост"
    pieces = split_text(text, limit=100)
    assert all(len(p) <= 100 for p in pieces)
    assert all(p.endswith(".") for p in pieces[:-1])
    assert " ".join(pieces).split() == text.split()


def test_text_without_breaks_is_still_cut() -> None:
    pieces = split_text("x" * 250, limit=100)
    assert pieces == ["x" * 100, "x" * 100, "x" * 50]


def test_no_words_are_lost() -> None:
    words = [f"слово{i}" for i in range(3000)]
    text = " ".join(words)
    pieces = split_text(text, limit=1000)
    assert all(len(p) <= 1000 for p in pieces)
    assert " ".join(pieces).split() == words


def test_estimate_and_price() -> None:
    assert estimate_seconds(int(CHARS_PER_SECOND * 60)) == pytest.approx(60)
    assert Pricing().speech_cost(1000) == pytest.approx(0.08)
    assert Pricing(tts_usd_per_1k_chars=0.1).speech_cost(2500) == pytest.approx(0.25)


def _speech_with(client: MagicMock, backup: MagicMock | None = None) -> ElevenLabsSpeech:
    clients = [client] + ([backup] if backup is not None else [])
    with patch("src.bot.services.tts.ElevenLabs", side_effect=clients):
        return ElevenLabsSpeech(
            "key", "voice123", "eleven_v4", backup_api_key="backup" if backup else ""
        )


def test_elevenlabs_speech_writes_audio_and_reads_cost() -> None:
    response = MagicMock()
    response.headers = {"character-cost": "12"}
    response.data = iter([b"ID3", b"audio"])
    client = MagicMock()
    convert = client.text_to_speech.with_raw_response.convert
    convert.return_value.__enter__.return_value = response
    speech = _speech_with(client)

    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        assert speech.synthesize("Привет", path) == 12
        with open(path, "rb") as f:
            assert f.read() == b"ID3audio"
    finally:
        os.remove(path)
    args, kwargs = convert.call_args
    assert args == ("voice123",)
    assert kwargs["model_id"] == "eleven_v4"
    assert kwargs["text"] == "Привет"


def test_elevenlabs_speech_without_cost_header() -> None:
    response = MagicMock()
    response.headers = {}
    response.data = iter([b"x"])
    client = MagicMock()
    client.text_to_speech.with_raw_response.convert.return_value.__enter__.return_value = (
        response
    )
    speech = _speech_with(client)
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        assert speech.synthesize("Привет", path) is None
    finally:
        os.remove(path)


def test_elevenlabs_speech_failure_is_runtime_error() -> None:
    client = MagicMock()
    client.text_to_speech.with_raw_response.convert.side_effect = ValueError("401")
    speech = _speech_with(client)
    with pytest.raises(RuntimeError, match="ElevenLabs speech failed"):
        speech.synthesize("Привет", "unused.mp3")


def test_api_error_shows_status_and_reason_not_headers() -> None:
    client = MagicMock()
    client.text_to_speech.with_raw_response.convert.side_effect = ApiError(
        headers={"date": "Thu, 26 Nov 2026", "server": "uvicorn", "x-long": "x" * 400},
        status_code=401,
        body={"detail": {
            "status": "missing_permissions",
            "message": "The API key you used is missing the permission text_to_speech.",
        }},
    )
    speech = _speech_with(client)
    with pytest.raises(RuntimeError) as info:
        speech.synthesize("Привет", "unused.mp3")
    message = str(info.value)
    assert message == (
        "ElevenLabs speech failed: HTTP 401 missing_permissions: "
        "The API key you used is missing the permission text_to_speech."
    )


def test_voiceover_falls_back_to_backup_key() -> None:
    main, backup = MagicMock(), MagicMock()
    main.text_to_speech.with_raw_response.convert.side_effect = ApiError(
        status_code=401, body={"detail": {"status": "quota_exceeded", "message": "No credits"}},
    )
    response = MagicMock(headers={"character-cost": "6"}, data=iter([b"audio"]))
    backup.text_to_speech.with_raw_response.convert.return_value.__enter__.return_value = (
        response
    )
    speech = _speech_with(main, backup)
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    try:
        assert speech.synthesize("Привет", path) == 6
        with open(path, "rb") as f:
            assert f.read() == b"audio"
    finally:
        os.remove(path)


def test_describe_error_other_shapes() -> None:
    assert describe_error(ApiError(status_code=422, body={"detail": "bad model"})) == (
        "HTTP 422 bad model"
    )
    assert describe_error(ApiError(status_code=400, body={"detail": {
        "type": "invalid_request", "code": "model_not_found", "message": "No such model",
    }})) == "HTTP 400 model_not_found: No such model"
    assert describe_error(ValueError("timeout")) == "timeout"


@pytest.fixture
def one_second_mp3() -> Iterator[str]:
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    subprocess.run(
        ["ffmpeg", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
         "-c:a", "libmp3lame", "-y", path],
        capture_output=True, check=True,
    )
    yield path
    os.remove(path)


class FakeSpeech:
    """Writes one second of audio per piece and charges a credit per character."""

    def __init__(self, sample: str, report_cost: bool = True) -> None:
        self.sample = sample
        self.report_cost = report_cost
        self.texts: list[str] = []
        self.paths: list[str] = []

    def synthesize(self, text: str, mp3_path: str) -> int | None:
        self.texts.append(text)
        self.paths.append(mp3_path)
        shutil.copyfile(self.sample, mp3_path)
        return len(text) if self.report_cost else None


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed")
async def test_synthesize_joins_pieces_into_one_voice(one_second_mp3: str) -> None:
    fake = FakeSpeech(one_second_mp3)
    text = "Предложение номер один. " * 200  # 4,800 chars: two pieces
    result = await synthesize_voice(fake, text)
    try:
        assert len(fake.texts) == 2
        assert result.path.endswith(".ogg")
        assert result.seconds == pytest.approx(2.0, abs=0.2)
        assert result.chars == sum(len(t) for t in fake.texts)
        assert result.credits == result.chars
        # The mp3 pieces are cleaned up.
        assert not any(os.path.exists(p) for p in fake.paths)
    finally:
        os.remove(result.path)


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed")
async def test_credits_unknown_if_any_piece_did_not_report(one_second_mp3: str) -> None:
    result = await synthesize_voice(FakeSpeech(one_second_mp3, report_cost=False), "Привет")
    try:
        assert result.credits is None
    finally:
        os.remove(result.path)


async def test_synthesize_failure_cleans_up() -> None:
    class Failing:
        paths: list[str] = []

        def synthesize(self, text: str, mp3_path: str) -> int | None:
            self.paths.append(mp3_path)
            raise RuntimeError("ElevenLabs speech failed: quota")

    failing = Failing()
    with pytest.raises(RuntimeError, match="quota"):
        await synthesize_voice(failing, "Привет")
    assert not any(os.path.exists(p) for p in failing.paths)
