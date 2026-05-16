import os
import subprocess
import tempfile

import pytest

from src.bot.services.audio import extract_audio, get_audio_duration

# Check if ffmpeg is available
FFMPEG_AVAILABLE = True
try:
    subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
except (FileNotFoundError, subprocess.CalledProcessError):
    FFMPEG_AVAILABLE = False


@pytest.fixture
def sample_audio() -> str:
    """Generate a short sine wave audio file for testing."""
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            path,
        ],
        capture_output=True,
        check=True,
    )
    yield path  # type: ignore[misc]
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def sample_video() -> str:
    """Generate a short video with audio for testing."""
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:d=1",
            "-shortest",
            path,
        ],
        capture_output=True,
        check=True,
    )
    yield path  # type: ignore[misc]
    if os.path.exists(path):
        os.unlink(path)


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed")
async def test_extract_audio_from_video(sample_video: str) -> None:
    audio_path = await extract_audio(sample_video)
    assert os.path.exists(audio_path)
    assert audio_path.endswith(".ogg")
    os.unlink(audio_path)


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed")
async def test_get_audio_duration(sample_audio: str) -> None:
    duration = await get_audio_duration(sample_audio)
    assert duration is not None
    assert 0.5 < duration < 2.0


@pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg not installed")
async def test_get_duration_nonexistent_file() -> None:
    duration = await get_audio_duration("/nonexistent/file.ogg")
    assert duration is None
