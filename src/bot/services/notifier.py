import logging

from telegram import Bot

logger = logging.getLogger(__name__)


class AdminNotifier:
    """Sends error notifications to admin users via Telegram DM."""

    def __init__(self, bot: Bot, admin_user_ids: list[int]) -> None:
        self._bot = bot
        self._admin_user_ids = admin_user_ids

    async def notify_error(
        self,
        error_type: str,
        username: str | None = None,
        error_detail: str | None = None,
        audio_duration: int | None = None,
    ) -> None:
        """Send an error notification to all admins."""
        if not self._admin_user_ids:
            return

        lines = [f"\u26a0 {error_type}"]
        if username:
            lines.append(f"User: @{username}")
        if error_detail:
            lines.append(f"Error: {error_detail}")
        if audio_duration is not None:
            minutes, seconds = divmod(audio_duration, 60)
            lines.append(f"Audio duration: {minutes}m {seconds}s")

        message = "\n".join(lines)

        for admin_id in self._admin_user_ids:
            try:
                await self._bot.send_message(chat_id=admin_id, text=message)
            except Exception:
                logger.exception("Failed to notify admin %d", admin_id)
