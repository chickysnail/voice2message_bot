"""Text to speech with ElevenLabs, in the bot author's cloned voice."""

import asyncio
import logging
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from elevenlabs.client import ElevenLabs
from elevenlabs.core.api_error import ApiError

from src.bot.services.audio import encode_voice, get_audio_duration

logger = logging.getLogger(__name__)

# Longer texts go to ElevenLabs in pieces of at most this many characters,
# well under every model's per-request limit (5,000 for v3, 10,000 for v4).
CHUNK_CHARS = 4000

# Speech runs at roughly 900 characters a minute in Russian and English.
# Used to estimate length and price before anything is generated.
CHARS_PER_SECOND = 15.0

# ElevenLabs reports what a request cost in this response header.
_CREDITS_HEADER = "character-cost"

_SENTENCE_END = re.compile(r"[.!?…](?=\s)")


class SpeechClient(Protocol):
    """Protocol for text-to-speech clients (enables mocking)."""

    def synthesize(self, text: str, mp3_path: str) -> int | None:
        """Write the speech for ``text`` to ``mp3_path``.

        Returns the credits ElevenLabs charged, or None if it didn't say.
        """
        ...


@dataclass(frozen=True)
class SpeechResult:
    """A finished voiceover."""

    # OGG/Opus file, ready to send as a Telegram voice message.
    path: str
    seconds: float
    chars: int
    # Credits ElevenLabs reported charging; None if it didn't report them.
    credits: int | None


def estimate_seconds(chars: int) -> float:
    """How long speech for this many characters roughly runs."""
    return chars / CHARS_PER_SECOND


def split_text(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    """Split text into pieces of at most ``limit`` characters.

    Cuts at a paragraph break if there is one, else a line break, else the
    end of a sentence, else a space, so that no piece starts mid-word.
    """
    text = text.strip()
    chunks: list[str] = []
    while len(text) > limit:
        window = text[:limit]
        cut = window.rfind("\n\n")
        if cut < limit // 2:
            cut = window.rfind("\n")
        if cut < limit // 2:
            ends = [m.end() for m in _SENTENCE_END.finditer(window)]
            cut = ends[-1] if ends else -1
        if cut < limit // 2:
            cut = window.rfind(" ")
        if cut <= 0:
            cut = limit
        chunks.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        chunks.append(text)
    return chunks


def describe_error(error: Exception) -> str:
    """Status and reason of a failed ElevenLabs call, e.g.
    "HTTP 401 missing_permissions: The API key ... text_to_speech ...".

    The SDK's own message starts with every response header, which pushes
    the reason out of any message that gets shortened.
    """
    if not isinstance(error, ApiError):
        return str(error)
    detail = error.body
    if isinstance(detail, dict):
        detail = detail.get("detail", detail)
    if isinstance(detail, dict) and "message" in detail:
        code = detail.get("status") or detail.get("code") or detail.get("type")
        detail = f"{code}: {detail['message']}" if code else detail["message"]
    return f"HTTP {error.status_code} {detail}"


def _credits(headers: Mapping[str, str]) -> int | None:
    value = headers.get(_CREDITS_HEADER)
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


class ElevenLabsSpeech:
    """Speech synthesis with one fixed ElevenLabs voice."""

    def __init__(
        self, api_key: str, voice_id: str, model_id: str, *, timeout: int = 300
    ) -> None:
        self._client = ElevenLabs(api_key=api_key, timeout=timeout)
        self._voice_id = voice_id
        self._model_id = model_id

    def synthesize(self, text: str, mp3_path: str) -> int | None:
        try:
            with self._client.text_to_speech.with_raw_response.convert(
                self._voice_id,
                text=text,
                model_id=self._model_id,
                output_format="mp3_44100_128",
            ) as response:
                with open(mp3_path, "wb") as f:
                    for chunk in response.data:
                        f.write(chunk)
                credits = _credits(response.headers)
        except Exception as e:
            raise RuntimeError(f"ElevenLabs speech failed: {describe_error(e)}") from e
        logger.info(
            "Synthesized %d chars with %s (%s credits)",
            len(text), self._model_id, credits,
        )
        return credits


async def synthesize_voice(
    client: SpeechClient, text: str, *, ffmpeg_timeout: int = 120
) -> SpeechResult:
    """Voice ``text`` and return it as one OGG/Opus file.

    Long texts are generated piece by piece and joined. The caller deletes
    the returned file. Raises RuntimeError if generation or encoding fails.
    """
    chunks = split_text(text)
    if not chunks:
        raise RuntimeError("Nothing to voice")
    parts: list[str] = []
    credits: int | None = 0
    try:
        for chunk in chunks:
            fd, path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            parts.append(path)
            charged = await asyncio.to_thread(client.synthesize, chunk, path)
            credits = None if charged is None or credits is None else credits + charged
        voice_path = await encode_voice(parts, timeout=ffmpeg_timeout)
    finally:
        for path in parts:
            if os.path.exists(path):
                os.remove(path)

    chars = sum(len(c) for c in chunks)
    seconds = await get_audio_duration(voice_path)
    return SpeechResult(
        path=voice_path,
        seconds=seconds if seconds is not None else estimate_seconds(chars),
        chars=chars,
        credits=credits,
    )
