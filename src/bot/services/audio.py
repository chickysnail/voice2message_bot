import asyncio
import logging
import os
import tempfile

logger = logging.getLogger(__name__)


async def extract_audio(
    video_path: str, *, timeout: int = 120
) -> str:
    """Extract audio from a video file using ffmpeg.

    Returns the path to the extracted audio file (.ogg).
    Raises RuntimeError if ffmpeg fails or video has no audio.
    """
    fd, audio_path = tempfile.mkstemp(suffix=".ogg")
    os.close(fd)

    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-i",
        video_path,
        "-vn",
        "-acodec",
        "libopus",
        "-y",
        audio_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
    except TimeoutError:
        process.kill()
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise RuntimeError(
            f"ffmpeg timed out after {timeout}s"
        )

    if process.returncode != 0:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        error_msg = stderr.decode(errors="replace")
        if "does not contain any stream" in error_msg or "Output file is empty" in error_msg:
            raise RuntimeError("Video has no audio track")
        raise RuntimeError(f"ffmpeg failed: {error_msg[:200]}")

    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        raise RuntimeError("Video has no audio track")

    logger.info("Extracted audio from %s to %s", video_path, audio_path)
    return audio_path


async def encode_voice(parts: list[str], *, timeout: int = 120) -> str:
    """Join audio files, in order, into one OGG/Opus voice message.

    Returns the path to the new .ogg file; the caller deletes it.
    Raises RuntimeError if ffmpeg fails.
    """
    fd, list_path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for path in parts:
            # ffmpeg accepts forward slashes on every OS; quotes keep spaces.
            f.write(f"file '{path.replace(os.sep, '/')}'\n")
    fd, voice_path = tempfile.mkstemp(suffix=".ogg")
    os.close(fd)

    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", list_path,
        "-vn",
        "-c:a", "libopus",
        "-b:a", "64k",
        "-y",
        voice_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except TimeoutError:
        process.kill()
        failure = f"ffmpeg timed out after {timeout}s"
    else:
        failure = (
            f"ffmpeg failed: {stderr.decode(errors='replace')[-200:]}"
            if process.returncode != 0 else ""
        )
    finally:
        os.remove(list_path)

    if failure or os.path.getsize(voice_path) == 0:
        os.remove(voice_path)
        raise RuntimeError(failure or "ffmpeg produced no audio")
    return voice_path


async def get_audio_duration(
    file_path: str, *, timeout: int = 30
) -> float | None:
    """Get duration of an audio/video file in seconds using ffprobe.

    Returns None if duration cannot be determined.
    """
    process = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, _ = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
    except TimeoutError:
        process.kill()
        return None

    if process.returncode != 0:
        return None

    try:
        return float(stdout.decode().strip())
    except (ValueError, AttributeError):
        return None
