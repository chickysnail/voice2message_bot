from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    elevenlabs_api_key: str
    openai_api_key: str

    # Instagram reels are fetched with yt-dlp. Optional Netscape-format cookies
    # file from a logged-in browser, for when Instagram refuses anonymous access.
    instagram_cookies_file: str = ""

    # YouTube links go through a RapidAPI provider; disabled without a key.
    rapidapi_key: str = ""

    # YouTube provider. `youtube_rapidapi_param_value` is "id" for APIs that
    # take a bare video id, or "url" for those that take the watch URL.
    youtube_rapidapi_host: str = "youtube-mp36.p.rapidapi.com"
    youtube_rapidapi_path: str = "/dl"
    youtube_rapidapi_query_param: str = "id"
    youtube_rapidapi_method: str = "GET"
    youtube_rapidapi_param_value: str = "id"

    # How long audio downloaded from a link stays on disk for the
    # "Download audio" / "Transcribe" buttons.
    link_audio_ttl: int = 3600

    admin_user_ids: list[int] = []
    database_path: str = "./stats.db"
    max_audio_duration: int = 3600
    transcription_ttl: int = 600
    log_level: str = "INFO"
    health_port: int = 8080

    # Heartbeat monitor URL (Better Stack / UptimeRobot / Healthchecks.io) pinged
    # while the bot is alive; the monitor alerts when the pings stop. Empty
    # disables the heartbeat.
    heartbeat_url: str = ""
    heartbeat_interval_seconds: int = 60

    # Timeouts in seconds
    transcription_timeout: int = 900  # 15 min (long audio can take a while)
    summarization_timeout: int = 60
    ffmpeg_timeout: int = 120
    file_download_timeout: int = 60

    @field_validator("admin_user_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: object) -> list[int]:
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",")]
        if isinstance(v, list):
            return [int(x) for x in v]
        return []

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
