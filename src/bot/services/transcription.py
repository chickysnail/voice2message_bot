import logging
from typing import Protocol

from elevenlabs.client import ElevenLabs

logger = logging.getLogger(__name__)


class TranscriptionClient(Protocol):
    """Protocol for transcription clients (enables mocking)."""

    def transcribe(self, file_path: str) -> str: ...


class ElevenLabsTranscriber:
    """Transcription service using ElevenLabs Scribe v2."""

    def __init__(self, api_key: str) -> None:
        self._client = ElevenLabs(api_key=api_key)

    def transcribe(self, file_path: str) -> str:
        """Transcribe an audio file and return the text.

        Raises RuntimeError on API failure.
        """
        try:
            with open(file_path, "rb") as f:
                result = self._client.speech_to_text.convert(
                    file=f,
                    model_id="scribe_v2",
                    tag_audio_events=False,
                )
            text: str = result.text
            if not text.strip():
                raise RuntimeError("Transcription returned empty text")
            logger.info("Transcribed %s (%d chars)", file_path, len(text))
            return text
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"ElevenLabs transcription failed: {e}") from e
