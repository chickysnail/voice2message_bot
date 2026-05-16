from unittest.mock import AsyncMock, MagicMock

import pytest

from src.bot.services.notifier import AdminNotifier


@pytest.fixture
def mock_bot() -> MagicMock:
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


async def test_notify_error_sends_to_all_admins(mock_bot: MagicMock) -> None:
    notifier = AdminNotifier(bot=mock_bot, admin_user_ids=[111, 222])
    await notifier.notify_error(
        error_type="Transcription failed",
        username="testuser",
        error_detail="API rate limit",
        audio_duration=180,
    )
    assert mock_bot.send_message.call_count == 2

    first_call = mock_bot.send_message.call_args_list[0]
    assert first_call.kwargs["chat_id"] == 111
    assert "Transcription failed" in first_call.kwargs["text"]
    assert "@testuser" in first_call.kwargs["text"]
    assert "3m 0s" in first_call.kwargs["text"]


async def test_notify_error_no_admins(mock_bot: MagicMock) -> None:
    notifier = AdminNotifier(bot=mock_bot, admin_user_ids=[])
    await notifier.notify_error(error_type="Some error")
    mock_bot.send_message.assert_not_called()


async def test_notify_error_handles_send_failure(mock_bot: MagicMock) -> None:
    mock_bot.send_message.side_effect = Exception("Telegram error")
    notifier = AdminNotifier(bot=mock_bot, admin_user_ids=[111])
    # Should not raise
    await notifier.notify_error(error_type="Some error")
