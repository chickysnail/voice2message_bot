from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    elevenlabs_api_key: str
    openai_api_key: str

    # Media link downloads (Instagram reels) via a RapidAPI provider.
    # When the key is empty the feature stays off and links get a "not supported" reply.
    rapidapi_key: str = ""
    rapidapi_host: str = "instagram-scraper-api2.p.rapidapi.com"
    rapidapi_path: str = "/v1/post_info"
    rapidapi_query_param: str = "code_or_id_or_url"

    admin_user_ids: list[int] = []
    database_path: str = "./stats.db"
    max_audio_duration: int = 3600
    transcription_ttl: int = 600
    log_level: str = "INFO"
    health_port: int = 8080

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
