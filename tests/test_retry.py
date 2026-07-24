"""Tests for the transient-network-error retry helper."""

import pytest
from telegram.error import NetworkError, TimedOut

from src.bot.utils.retry import with_network_retry


async def test_returns_result_without_retry() -> None:
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    result = await with_network_retry(
        factory, timeout=1, base_delay=0
    )
    assert result == "ok"
    assert calls == 1


async def test_retries_network_error_then_succeeds() -> None:
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise NetworkError("httpx.ReadError: ")
        return "ok"

    result = await with_network_retry(
        factory, timeout=1, attempts=3, base_delay=0
    )
    assert result == "ok"
    assert calls == 3


async def test_reraises_after_exhausting_attempts() -> None:
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        raise NetworkError("httpx.ReadError: ")

    with pytest.raises(NetworkError):
        await with_network_retry(
            factory, timeout=1, attempts=3, base_delay=0
        )
    assert calls == 3


async def test_does_not_retry_timed_out() -> None:
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        raise TimedOut()

    with pytest.raises(TimedOut):
        await with_network_retry(
            factory, timeout=1, attempts=3, base_delay=0
        )
    assert calls == 1


async def test_does_not_retry_timeout_error() -> None:
    calls = 0

    async def factory() -> str:
        nonlocal calls
        calls += 1
        raise TimeoutError()

    with pytest.raises(TimeoutError):
        await with_network_retry(
            factory, timeout=1, attempts=3, base_delay=0
        )
    assert calls == 1
