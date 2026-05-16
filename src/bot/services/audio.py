import asyncio
import logging
import os
import tempfile

logger = logging.getLogger(__name__)


async def extract_audio(video_path: str) -> str:
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
    _, stderr = await process.communicate()

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


async def get_audio_duration(file_path: str) -> float | None:
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
    stdout, _ = await process.communicate()

    if process.returncode != 0:
        return None

    try:
        return float(stdout.decode().strip())
    except (ValueError, AttributeError):
        return None
