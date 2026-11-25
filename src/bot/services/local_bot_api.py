"""Self-hosted Telegram Bot API server running next to the bot.

The cloud Bot API (api.telegram.org) refuses to let bots download files over
20 MB. telegram-bot-api started with --local downloads files up to 2000 MB and
answers getFile with an absolute path on its own disk. It runs in the bot's
container, so python-telegram-bot copies that file instead of fetching it over
HTTP.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

HOST = "127.0.0.1"
PORT = 8081
# The first start logs the bot in to Telegram, which can take a while.
STARTUP_TIMEOUT = 60

# The server never deletes what it downloads. Handlers copy each file out right
# after getFile, so what stays behind only fills the volume. Files over the
# cloud API's 20 MB limit go after 10 minutes, smaller ones after an hour.
LARGE_FILE_BYTES = 20 * 1024 * 1024
LARGE_FILE_MAX_AGE = 600
SMALL_FILE_MAX_AGE = 3600
CLEANUP_INTERVAL = 300


class LocalBotApiServer:
    def __init__(self, api_id: str, api_hash: str, work_dir: str) -> None:
        self._api_id = api_id
        self._api_hash = api_hash
        self._work_dir = work_dir
        self._process: subprocess.Popen[bytes] | None = None
        self._stopping = False

    @property
    def url(self) -> str:
        return f"http://{HOST}:{PORT}"

    def start(self, bot_token: str) -> None:
        """Start the server and block until it serves the bot."""
        temp_dir = os.path.join(tempfile.gettempdir(), "telegram-bot-api")
        os.makedirs(self._work_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        # Credentials go through the environment, which the server reads, so
        # they don't show up in the process list.
        env = {
            **os.environ,
            "TELEGRAM_API_ID": self._api_id,
            "TELEGRAM_API_HASH": self._api_hash,
        }
        self._process = subprocess.Popen(
            [
                "telegram-bot-api",
                "--local",
                f"--dir={self._work_dir}",
                f"--temp-dir={temp_dir}",
                f"--http-ip-address={HOST}",
                f"--http-port={PORT}",
            ],
            env=env,
        )
        self._wait_until_ready(bot_token)
        threading.Thread(target=self._exit_if_server_dies, daemon=True).start()
        logger.info("Local Telegram Bot API server is up (data in %s)", self._work_dir)

    def _wait_until_ready(self, bot_token: str) -> None:
        assert self._process is not None
        deadline = time.monotonic() + STARTUP_TIMEOUT
        while True:
            if self._process.poll() is not None:
                raise RuntimeError(
                    f"telegram-bot-api exited with code {self._process.returncode}"
                )
            try:
                urllib.request.urlopen(f"{self.url}/bot{bot_token}/getMe", timeout=30).close()
                return
            except urllib.error.HTTPError:
                # It answers; python-telegram-bot reports what is wrong (e.g. a bad token).
                return
            except OSError:  # not listening yet
                if time.monotonic() > deadline:
                    self.stop()
                    raise RuntimeError(
                        f"telegram-bot-api did not start within {STARTUP_TIMEOUT}s"
                    ) from None
                time.sleep(0.5)

    def _exit_if_server_dies(self) -> None:
        assert self._process is not None
        code = self._process.wait()
        if self._stopping:
            return
        # Without the server the bot can't reach Telegram at all. A non-zero
        # exit makes Railway restart both.
        logger.critical("telegram-bot-api exited with code %s; exiting", code)
        os._exit(1)

    def stop(self) -> None:
        if self._process is None or self._process.poll() is not None:
            return
        self._stopping = True
        self._process.terminate()
        try:
            self._process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._process.kill()

    async def delete_old_downloads_forever(self) -> None:
        while True:
            try:
                removed = await asyncio.to_thread(self.delete_old_downloads)
                if removed:
                    logger.info("Deleted %d old Bot API downloads", removed)
            except Exception:
                logger.exception("Bot API download cleanup failed")
            await asyncio.sleep(CLEANUP_INTERVAL)

    def delete_old_downloads(self) -> int:
        """Delete downloads past LARGE_FILE_MAX_AGE / SMALL_FILE_MAX_AGE.

        The server keeps one folder per bot: session files at its top level
        (left alone) and downloads in subfolders such as ``voice/``.
        """
        now = time.time()
        removed = 0
        root = Path(self._work_dir)
        if not root.is_dir():
            return 0
        for bot_dir in root.iterdir():
            if not bot_dir.is_dir():
                continue
            for media_dir in bot_dir.iterdir():
                if not media_dir.is_dir():
                    continue
                for path in media_dir.rglob("*"):
                    try:
                        if not path.is_file():
                            continue
                        stat = path.stat()
                        max_age = (
                            LARGE_FILE_MAX_AGE
                            if stat.st_size > LARGE_FILE_BYTES
                            else SMALL_FILE_MAX_AGE
                        )
                        if now - stat.st_mtime > max_age:
                            path.unlink()
                            removed += 1
                    except OSError:
                        logger.warning("Could not delete old download %s", path)
        return removed
