"""A main ElevenLabs API key with an optional backup key from another account.

When ElevenLabs refuses the main key (out of credits, plan expired, missing
permission, rate limited), the request is retried with the backup key. For
the next hour requests go straight to the backup, then the main key is
tried again. Admins are told when the bot switches keys and when it
switches back.
"""

import logging
import threading
import time
from collections.abc import Callable
from typing import TypeVar

from elevenlabs.client import ElevenLabs
from elevenlabs.core.api_error import ApiError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Answers about the key or its account rather than about the request.
KEY_REFUSED_STATUSES = frozenset({401, 402, 403, 429})
RETRY_MAIN_AFTER_SECONDS = 3600


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


def key_refused(error: Exception) -> bool:
    return isinstance(error, ApiError) and error.status_code in KEY_REFUSED_STATUSES


class KeyFailover:
    """Runs ElevenLabs requests on the main client, or the backup one when
    the main key is refused. Thread-safe: requests run in worker threads."""

    def __init__(
        self,
        main: ElevenLabs,
        backup: ElevenLabs | None = None,
        *,
        service: str,
        retry_main_after: float = RETRY_MAIN_AFTER_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._main = main
        self._backup = backup
        self._service = service
        self._retry_main_after = retry_main_after
        self._clock = clock
        self._lock = threading.Lock()
        # When the main key was last refused; None while it works.
        self._main_refused_at: float | None = None
        # Gets a message for admins whenever the key in use changes. Set once
        # the event loop runs; called from worker threads.
        self.notify: Callable[[str], None] | None = None

    def call(self, request: Callable[[ElevenLabs], T]) -> T:
        """Run ``request`` with a client, switching keys as described above.

        ``request`` may run twice, so it must reopen anything it reads.
        """
        if self._backup is not None and self._resting_main():
            return request(self._backup)
        try:
            result = request(self._main)
        except Exception as e:
            if self._backup is None or not key_refused(e):
                raise
            self._switch_to_backup(e)
            return request(self._backup)
        self._back_on_main()
        return result

    def _resting_main(self) -> bool:
        with self._lock:
            refused_at = self._main_refused_at
        return refused_at is not None and self._clock() - refused_at < self._retry_main_after

    def _switch_to_backup(self, error: Exception) -> None:
        with self._lock:
            already_switched = self._main_refused_at is not None
            self._main_refused_at = self._clock()
        if not already_switched:
            self._tell(
                f"⚠️ ElevenLabs refused the main API key for {self._service}: "
                f"{describe_error(error)}\n"
                f"Using the backup key; the main key is tried again every hour."
            )

    def _back_on_main(self) -> None:
        with self._lock:
            was_switched = self._main_refused_at is not None
            self._main_refused_at = None
        if was_switched:
            self._tell(f"✅ ElevenLabs {self._service}: back on the main API key.")

    def _tell(self, text: str) -> None:
        logger.warning(text)
        if self.notify is not None:
            try:
                self.notify(text)
            except Exception:
                logger.exception("Couldn't tell admins about an ElevenLabs key switch")
