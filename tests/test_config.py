
from src.bot.config import Settings


def test_parse_admin_ids_from_string() -> None:
    settings = Settings(
        telegram_bot_token="tok",
        elevenlabs_api_key="elk",
        openai_api_key="oai",
        admin_user_ids="123, 456, 789",  # type: ignore[arg-type]
    )
    assert settings.admin_user_ids == [123, 456, 789]


def test_parse_empty_admin_ids() -> None:
    settings = Settings(
        telegram_bot_token="tok",
        elevenlabs_api_key="elk",
        openai_api_key="oai",
        admin_user_ids="",  # type: ignore[arg-type]
    )
    assert settings.admin_user_ids == []


def test_defaults() -> None:
    settings = Settings(
        telegram_bot_token="tok",
        elevenlabs_api_key="elk",
        openai_api_key="oai",
    )
    assert settings.database_path == "./stats.db"
    assert settings.max_audio_duration == 3600
    assert settings.transcription_ttl == 600
    assert settings.log_level == "INFO"
