"""File export for transcriptions (TXT, SRT and HTML formats)."""

from __future__ import annotations

import html
import re
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


_PARAGRAPH_CHARS = 600
_SENTENCE_END_RE = re.compile(r"(?<=[.!?…])\s+")


def _paragraphs(text: str) -> list[str]:
    """Split a transcript into readable paragraphs.

    Speaker segments already come one per line; a single-speaker transcript is
    one long line, so it is regrouped at sentence boundaries.
    """
    result: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) <= _PARAGRAPH_CHARS:
            result.append(line)
            continue
        current = ""
        for sentence in _SENTENCE_END_RE.split(line):
            if current and len(current) + len(sentence) > _PARAGRAPH_CHARS:
                result.append(current)
                current = ""
            current = f"{current} {sentence}".strip()
        if current:
            result.append(current)
    return result


def generate_html(text: str, title: str = "Transcript") -> str:
    """Generate a minimal HTML page for reading a transcript in a browser.

    Kept deliberately plain — bare paragraphs, no classes, colors or custom
    fonts — so copying the page out keeps clean, unstyled text.
    """
    paragraphs = "\n".join(
        f"<p>{html.escape(paragraph)}</p>" for paragraph in _paragraphs(text)
    )
    return (
        "<!DOCTYPE html>\n"
        '<html><head><meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        "<style>body{max-width:40em;margin:1em auto;padding:0 1em;"
        "font-family:system-ui,sans-serif;line-height:1.5}</style>\n"
        f"</head><body>\n{paragraphs}\n</body></html>\n"
    )


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
