import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.bot.services.transcription import (
    ElevenLabsTranscriber,
    EmptyTranscriptionError,
    format_diarized_transcript,
)


@pytest.fixture
def dummy_audio() -> str:
    fd, path = tempfile.mkstemp(suffix=".ogg")
    os.write(fd, b"fake audio data")
    os.close(fd)
    yield path  # type: ignore[misc]
    if os.path.exists(path):
        os.unlink(path)


def _make_word(
    text: str,
    speaker_id: str | None = None,
    word_type: str = "word",
) -> MagicMock:
    w = MagicMock()
    w.text = text
    w.speaker_id = speaker_id
    w.type = word_type
    return w


def _make_result(
    text: str, words: list[MagicMock] | None = None
) -> MagicMock:
    result = MagicMock()
    result.text = text
    result.words = words or []
    return result


def test_transcribe_success_single_speaker(dummy_audio: str) -> None:
    with patch("src.bot.services.transcription.ElevenLabs") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        words = [
            _make_word("Hello,", "speaker_0"),
            _make_word(" ", "speaker_0", "spacing"),
            _make_word("world.", "speaker_0"),
        ]
        mock_client.speech_to_text.convert.return_value = _make_result(
            "Hello, world.", words
        )

        transcriber = ElevenLabsTranscriber(api_key="fake-key")
        result = transcriber.transcribe(dummy_audio)

        assert result == "Hello, world."
        call_kwargs = mock_client.speech_to_text.convert.call_args
        assert call_kwargs[1]["diarize"] is True


def test_transcribe_success_multi_speaker(dummy_audio: str) -> None:
    with patch("src.bot.services.transcription.ElevenLabs") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        words = [
            _make_word("Hey", "speaker_0"),
            _make_word(" ", None, "spacing"),
            _make_word("there", "speaker_0"),
            _make_word("Hi", "speaker_1"),
            _make_word(" ", None, "spacing"),
            _make_word("back", "speaker_1"),
        ]
        mock_client.speech_to_text.convert.return_value = _make_result(
            "Hey there Hi back", words
        )

        transcriber = ElevenLabsTranscriber(api_key="fake-key")
        result = transcriber.transcribe(dummy_audio)

        assert "Speaker 1:" in result
        assert "Speaker 2:" in result
        assert "Hey" in result
        assert "Hi" in result


def test_transcribe_empty_text(dummy_audio: str) -> None:
    with patch("src.bot.services.transcription.ElevenLabs") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_client.speech_to_text.convert.return_value = _make_result(
            "   ", []
        )

        transcriber = ElevenLabsTranscriber(api_key="fake-key")

        with pytest.raises(EmptyTranscriptionError, match="empty text"):
            transcriber.transcribe(dummy_audio)


def test_transcribe_api_error(dummy_audio: str) -> None:
    with patch("src.bot.services.transcription.ElevenLabs") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_client.speech_to_text.convert.side_effect = Exception("API rate limit")

        transcriber = ElevenLabsTranscriber(api_key="fake-key")

        with pytest.raises(RuntimeError, match="ElevenLabs transcription failed"):
            transcriber.transcribe(dummy_audio)


# --- format_diarized_transcript unit tests ---


def test_format_single_speaker_returns_plain_text() -> None:
    result = _make_result(
        "Hello world",
        [_make_word("Hello", "speaker_0"), _make_word("world", "speaker_0")],
    )
    assert format_diarized_transcript(result) == "Hello world"


def test_format_no_words_returns_plain_text() -> None:
    result = _make_result("Hello world", [])
    assert format_diarized_transcript(result) == "Hello world"


def test_format_multi_speaker_labels() -> None:
    words = [
        _make_word("Hi", "speaker_0"),
        _make_word(" ", None, "spacing"),
        _make_word("there", "speaker_0"),
        _make_word("Hello", "speaker_1"),
        _make_word("back", "speaker_0"),
    ]
    result = _make_result("Hi there Hello back", words)
    formatted = format_diarized_transcript(result)
    lines = formatted.split("\n")
    assert len(lines) == 3
    assert lines[0] == "Speaker 1: Hi there"
    assert lines[1] == "Speaker 2: Hello"
    assert lines[2] == "Speaker 1: back"


def test_format_three_speakers() -> None:
    words = [
        _make_word("A", "s0"),
        _make_word("B", "s1"),
        _make_word("C", "s2"),
    ]
    result = _make_result("A B C", words)
    formatted = format_diarized_transcript(result)
    lines = formatted.split("\n")
    assert len(lines) == 3
    assert lines[0].startswith("Speaker 1:")
    assert lines[1].startswith("Speaker 2:")
    assert lines[2].startswith("Speaker 3:")
