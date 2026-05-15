import logging
from dataclasses import dataclass, field
from typing import Protocol

from elevenlabs.client import ElevenLabs
from elevenlabs.types.speech_to_text_chunk_response_model import (
    SpeechToTextChunkResponseModel,
)

logger = logging.getLogger(__name__)


class EmptyTranscriptionError(RuntimeError):
    """Raised when the API returns no speech content."""


@dataclass
class WordData:
    """Minimal word-level data needed for SRT generation."""

    text: str
    start: float | None = None
    end: float | None = None
    speaker_id: str | None = None
    type: str = "word"


@dataclass
class TranscriptionResult:
    """Result of a transcription, containing text and word-level data."""

    text: str
    words: list[WordData] = field(default_factory=list)


class TranscriptionClient(Protocol):
    """Protocol for transcription clients (enables mocking)."""

    def transcribe(self, file_path: str) -> TranscriptionResult: ...


def format_diarized_transcript(
    result: SpeechToTextChunkResponseModel,
) -> str:
    """Format a transcript with speaker labels from the words array.

    Groups consecutive words by speaker_id and labels each turn.
    If only one speaker is detected, returns plain text without labels.
    """
    words = result.words
    if not words:
        return result.text

    speaker_ids: set[str] = set()
    for w in words:
        if w.speaker_id is not None:
            speaker_ids.add(w.speaker_id)

    if len(speaker_ids) <= 1:
        return result.text

    speaker_label_map: dict[str, str] = {}
    label_counter = 0
    segments: list[str] = []
    current_speaker: str | None = None
    current_words: list[str] = []

    for w in words:
        if w.type != "word":
            if w.type == "spacing" and current_words:
                current_words.append(w.text)
            continue

        sid = w.speaker_id or "unknown"
        if sid != current_speaker:
            if current_words and current_speaker is not None:
                label = speaker_label_map[current_speaker]
                segments.append(f"{label}: {''.join(current_words).strip()}")
            current_speaker = sid
            current_words = []
            if sid not in speaker_label_map:
                label_counter += 1
                speaker_label_map[sid] = f"Speaker {label_counter}"

        current_words.append(w.text)

    if current_words and current_speaker is not None:
        label = speaker_label_map[current_speaker]
        segments.append(f"{label}: {''.join(current_words).strip()}")

    return "\n".join(segments)


class ElevenLabsTranscriber:
    """Transcription service using ElevenLabs Scribe v2."""

    def __init__(self, api_key: str) -> None:
        self._client = ElevenLabs(api_key=api_key)

    def transcribe(self, file_path: str) -> TranscriptionResult:
        """Transcribe an audio file and return text + word-level data.

        Uses speaker diarization. For multi-speaker audio, returns
        labeled transcript. For single-speaker audio, returns plain text.

        Raises RuntimeError on API failure.
        """
        try:
            with open(file_path, "rb") as f:
                result = self._client.speech_to_text.convert(
                    file=f,
                    model_id="scribe_v2",
                    tag_audio_events=False,
                    diarize=True,
                )
            text = format_diarized_transcript(result)  # type: ignore[arg-type]
            if not text.strip():
                raise EmptyTranscriptionError("Transcription returned empty text")

            words = [
                WordData(
                    text=w.text,
                    start=w.start,
                    end=w.end,
                    speaker_id=w.speaker_id,
                    type=w.type if isinstance(w.type, str) else "word",
                )
                for w in result.words  # type: ignore[union-attr]
            ]

            logger.info("Transcribed %s (%d chars)", file_path, len(text))
            return TranscriptionResult(text=text, words=words)
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"ElevenLabs transcription failed: {e}") from e
