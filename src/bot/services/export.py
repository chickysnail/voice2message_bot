"""File export for transcriptions (TXT and SRT formats)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.bot.services.transcription import WordData


def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_txt(text: str) -> str:
    """Generate plain text file content."""
    return text


def generate_srt(words: list[WordData], max_words_per_sub: int = 10) -> str:
    """Generate SRT subtitle content from word-level data.

    Groups words into subtitle blocks of up to max_words_per_sub words.
    Uses word-level timestamps from the API.
    """
    timed_words = [w for w in words if w.type == "word" and w.start is not None]
    if not timed_words:
        return ""

    blocks: list[str] = []
    block_num = 0
    i = 0

    while i < len(timed_words):
        chunk = timed_words[i : i + max_words_per_sub]
        start = chunk[0].start
        end = chunk[-1].end or chunk[-1].start

        if start is None or end is None:
            i += len(chunk)
            continue

        block_num += 1
        text = " ".join(w.text for w in chunk)

        speaker_ids = {w.speaker_id for w in chunk if w.speaker_id}
        if len(speaker_ids) == 1:
            sid = next(iter(speaker_ids))
            if sid:
                text = f"[{sid}] {text}"

        blocks.append(
            f"{block_num}\n"
            f"{_format_srt_time(start)} --> {_format_srt_time(end)}\n"
            f"{text}"
        )

        i += len(chunk)

    return "\n\n".join(blocks) + "\n" if blocks else ""
