import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.bot.services.transcription import ElevenLabsTranscriber


@pytest.fixture
def dummy_audio() -> str:
    fd, path = tempfile.mkstemp(suffix=".ogg")
    os.write(fd, b"fake audio data")
    os.close(fd)
    yield path  # type: ignore[misc]
    if os.path.exists(path):
        os.unlink(path)


def test_transcribe_success(dummy_audio: str) -> None:
    with patch("src.bot.services.transcription.ElevenLabs") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_result = MagicMock()
        mock_result.text = "Hello, this is a test transcription."
        mock_client.speech_to_text.convert.return_value = mock_result

        transcriber = ElevenLabsTranscriber(api_key="fake-key")
        result = transcriber.transcribe(dummy_audio)

        assert result == "Hello, this is a test transcription."
        mock_client.speech_to_text.convert.assert_called_once()


def test_transcribe_empty_text(dummy_audio: str) -> None:
    with patch("src.bot.services.transcription.ElevenLabs") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_result = MagicMock()
        mock_result.text = "   "
        mock_client.speech_to_text.convert.return_value = mock_result

        transcriber = ElevenLabsTranscriber(api_key="fake-key")

        with pytest.raises(RuntimeError, match="empty text"):
            transcriber.transcribe(dummy_audio)


def test_transcribe_api_error(dummy_audio: str) -> None:
    with patch("src.bot.services.transcription.ElevenLabs") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_client.speech_to_text.convert.side_effect = Exception("API rate limit")

        transcriber = ElevenLabsTranscriber(api_key="fake-key")

        with pytest.raises(RuntimeError, match="ElevenLabs transcription failed"):
            transcriber.transcribe(dummy_audio)
