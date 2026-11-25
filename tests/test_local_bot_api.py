import os
import time
from pathlib import Path

from src.bot.config import Settings
from src.bot.services.local_bot_api import LARGE_FILE_BYTES, LocalBotApiServer

MINUTE = 60
LARGE = LARGE_FILE_BYTES + 1


def _touch(path: Path, age_seconds: float, size: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.truncate(size)  # sparse, so "large" files take no real disk space
    mtime = time.time() - age_seconds
    os.utime(path, (mtime, mtime))


def test_delete_old_downloads_by_size_and_age(tmp_path: Path) -> None:
    bot_dir = tmp_path / "123456-ABC"  # named after the bot token (":" breaks on Windows)
    large_old = bot_dir / "videos" / "file_0.mp4"
    large_fresh = bot_dir / "documents" / "file_1.wav"
    small_15_min = bot_dir / "voice" / "file_2.oga"
    small_old_nested = bot_dir / "documents" / "sub" / "file_3.mp3"
    session = bot_dir / "td.binlog"
    _touch(large_old, 15 * MINUTE, LARGE)
    _touch(large_fresh, 5 * MINUTE, LARGE)
    _touch(small_15_min, 15 * MINUTE)
    _touch(small_old_nested, 2 * 60 * MINUTE)
    _touch(session, 2 * 60 * MINUTE)

    server = LocalBotApiServer("1", "hash", str(tmp_path))
    removed = server.delete_old_downloads()

    assert removed == 2
    assert not large_old.exists()
    assert not small_old_nested.exists()
    assert large_fresh.exists()
    assert small_15_min.exists()
    assert session.exists()


def test_delete_old_downloads_without_work_dir(tmp_path: Path) -> None:
    server = LocalBotApiServer("1", "hash", str(tmp_path / "missing"))
    assert server.delete_old_downloads() == 0


def test_local_bot_api_is_off_by_default() -> None:
    settings = Settings(
        telegram_bot_token="tok",
        elevenlabs_api_key="elk",
        openai_api_key="oai",
    )
    assert settings.telegram_api_id == ""
    assert settings.telegram_api_hash == ""
    assert settings.telegram_bot_api_dir == "/data/telegram-bot-api"
