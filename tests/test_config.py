
from src.bot.config import Settings


def test_parse_admin_ids_from_string() -> None:
    settings = Settings(
        telegram_bot_token="tok",
        elevenlabs_api_key="elk",
        openai_api_key="oai",
        admin_user_ids="123, 456, 789",  # type: ignore[arg-type]
    )
    assert settings.admin_user_ids == [123, 456, 789]


def test_parse_admin_ids_from_int() -> None:
    settings = Settings(
        telegram_bot_token="tok",
        elevenlabs_api_key="elk",
        openai_api_key="oai",
        admin_user_ids=123456789,  # type: ignore[arg-type]
    )
    assert settings.admin_user_ids == [123456789]


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


def test_dashboard_url(monkeypatch: object) -> None:
    import pytest

    mp: pytest.MonkeyPatch = monkeypatch  # type: ignore[assignment]
    keys = {"telegram_bot_token": "tok", "elevenlabs_api_key": "elk", "openai_api_key": "oai"}
    mp.delenv("PUBLIC_URL", raising=False)
    mp.delenv("RAILWAY_PUBLIC_DOMAIN", raising=False)
    assert Settings(**keys, _env_file=None).dashboard_url is None  # type: ignore[call-arg]

    mp.setenv("RAILWAY_PUBLIC_DOMAIN", "bot.up.railway.app")
    assert (
        Settings(**keys, _env_file=None).dashboard_url  # type: ignore[call-arg]
        == "https://bot.up.railway.app/admin"
    )

    mp.setenv("PUBLIC_URL", "https://bot.example.com/")
    assert (
        Settings(**keys, _env_file=None).dashboard_url  # type: ignore[call-arg]
        == "https://bot.example.com/admin"
    )
