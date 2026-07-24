import asyncio
import logging
from collections.abc import Awaitable, Callable

from telegram.error import NetworkError, TimedOut

logger = logging.getLogger(__name__)

# Transient Telegram network failures (e.g. httpx.ReadError, wrapped by
# python-telegram-bot into NetworkError) happen occasionally while
# downloading files from Telegram's servers. Retrying the request a few
# times with a short backoff recovers from them without the user having to
# resend the message.
NETWORK_RETRY_ATTEMPTS = 3
NETWORK_RETRY_BASE_DELAY = 0.5


async def with_network_retry[T](
    factory: Callable[[], Awaitable[T]],
    *,
    timeout: float,
    description: str = "telegram request",
    attempts: int = NETWORK_RETRY_ATTEMPTS,
    base_delay: float = NETWORK_RETRY_BASE_DELAY,
) -> T:
    """Await ``factory()`` under ``timeout``, retrying transient network errors.

    ``factory`` is called afresh on every attempt so a new request is issued
    each time. Retries only cover :class:`telegram.error.NetworkError`
    (such as ``httpx.ReadError``). Genuine timeouts —
    :class:`asyncio.TimeoutError` from :func:`asyncio.wait_for` and
    :class:`telegram.error.TimedOut` — are re-raised immediately so callers
    keep their existing timeout handling instead of waiting through several
    slow retries.
    """
    last_exc: NetworkError | None = None
    for attempt in range(attempts):
        try:
            return await asyncio.wait_for(factory(), timeout=timeout)
        except (TimeoutError, TimedOut):
            raise
        except NetworkError as exc:
            last_exc = exc
            if attempt == attempts - 1:
                break
            delay = base_delay * (2**attempt)
            logger.warning(
                "Transient network error on %s (attempt %d/%d): %r; "
                "retrying in %.1fs",
                description,
                attempt + 1,
                attempts,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc
