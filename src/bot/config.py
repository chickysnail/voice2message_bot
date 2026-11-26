from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    elevenlabs_api_key: str
    # Optional key from another ElevenLabs account, used while ElevenLabs
    # refuses the main one (out of credits, plan expired, missing permission).
    elevenlabs_backup_api_key: str = ""
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

    # Voiceover: anyone who sends text (or a .txt file) can have it read out
    # in this ElevenLabs voice. Empty TTS_VOICE_ID turns the feature off.
    tts_voice_id: str = "WTn2eCRCpoFAC50VD351"
    tts_model: str = "eleven_v4"
    # USD per 1,000 voiced characters, for cost estimates.
    tts_usd_per_1k_chars: float = 0.08
    # Everyone but admins gets this many minutes of speech per TTS_QUOTA_DAYS.
    tts_user_quota_minutes: float = 10
    tts_quota_days: int = 30
    # Admins have no limit, but are asked first when one voiceover would cost
    # more than this.
    tts_confirm_usd: float = 1.0
    # DM admins whenever someone else uses the voice.
    tts_notify_admins: bool = True
    tts_timeout: int = 300

    # Self-hosted Telegram Bot API server. The cloud Bot API won't let bots
    # download files over 20 MB; with both credentials set (from
    # https://my.telegram.org), the bot starts telegram-bot-api --local next to
    # itself, which downloads files up to 2000 MB.
    telegram_api_id: str = ""
    telegram_api_hash: str = ""
    # That server's session and downloads. Keep it on the Railway Volume so the
    # bot stays logged in to it across redeploys.
    telegram_bot_api_dir: str = "/data/telegram-bot-api"

    # Public HTTPS address of this service, e.g. https://bot.up.railway.app.
    # The admin dashboard lives at <public_url>/admin. Falls back to the domain
    # Railway generates for the service.
    public_url: str = ""
    railway_public_domain: str = ""

    # Rough API prices, for the dashboard and the donation nudge.
    # ElevenLabs bills audio duration: plan price / included hours.
    elevenlabs_usd_per_hour: float = 0.40
    # What one Telegram Star pays out to the bot owner.
    star_usd: float = 0.013

    # Every this many dollars of API spend on a user, tell them so and offer a
    # donation — but at most once per interval. 0 turns the nudge off.
    donation_nudge_usd: float = 1.0
    donation_nudge_interval_days: int = 14

    # Timeouts in seconds
    transcription_timeout: int = 900  # 15 min (long audio can take a while)
    summarization_timeout: int = 60
    ffmpeg_timeout: int = 120
    file_download_timeout: int = 60

    @property
    def dashboard_url(self) -> str | None:
        base = self.public_url or (
            f"https://{self.railway_public_domain}" if self.railway_public_domain else ""
        )
        return f"{base.rstrip('/')}/admin" if base else None

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
