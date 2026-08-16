# Voice2Message Bot v3

A Telegram bot that transcribes voice messages, audio files, and video notes using **ElevenLabs Scribe v2** and optionally summarizes them using **OpenAI GPT-4o-mini**.

## Features

- **Instant transcription** — send audio, get text immediately
- **Summarization** — one-tap summary of any transcription
- **Multi-format support** — voice messages, audio files, video notes
- **Privacy-first** — transcriptions auto-expire after 10 minutes, never persisted to disk
- **Usage statistics** — persistent stats via SQLite (Railway Volume compatible)
- **Admin notifications** — get DM'd when something goes wrong

## Setup

### Prerequisites

- Python 3.12+
- ffmpeg
- Telegram Bot Token ([BotFather](https://t.me/botfather))
- ElevenLabs API key ([elevenlabs.io](https://elevenlabs.io))
- OpenAI API key ([platform.openai.com](https://platform.openai.com))

### Installation

```bash
git clone https://github.com/chickysnail/voice2message_bot.git
cd voice2message_bot
git checkout v3-development
pip install -e ".[dev]"
```

### Configuration

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

### Run

```bash
python -m src.bot.main
```

### Run tests

```bash
pytest
```

### Type checking

```bash
mypy src/
```

## Knowing when the bot is down

Admins already get a DM on startup (🟢) and now also on a clean shutdown (🔴).
A crash cannot announce itself, so the bot also pings a heartbeat monitor every
`HEARTBEAT_INTERVAL_SECONDS`; when the pings stop, the monitor alerts you. Create a
heartbeat ("cron"/"push") monitor at [Better Stack](https://betterstack.com/uptime),
UptimeRobot or Healthchecks.io and put its ping URL in `HEARTBEAT_URL`.

`GET /health` on `HEALTH_PORT` remains as an independent check for a process that is
alive but no longer serving — point an HTTP monitor or Railway's healthcheck at it.

## Deployment (Railway)

1. Connect this repo to Railway
2. Set branch to `v3-development`
3. Add a **Volume** mounted at `/data`
4. Set environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `ELEVENLABS_API_KEY`
   - `OPENAI_API_KEY`
   - `DATABASE_PATH=/data/stats.db`
   - `ADMIN_USER_IDS=your_telegram_user_id`

## Architecture

```
src/bot/
├── main.py              # Entry point
├── config.py            # Settings (pydantic-settings)
├── handlers.py          # Telegram handlers
├── keyboards.py         # Inline keyboards
├── services/
│   ├── transcription.py # ElevenLabs Scribe v2
│   ├── summarization.py # OpenAI GPT-4o-mini
│   ├── audio.py         # ffmpeg audio extraction
│   ├── monitoring.py    # Heartbeat pings for downtime alerts
│   └── notifier.py      # Admin error notifications
├── storage/
│   ├── transcription_store.py  # In-memory TTL store
│   └── statistics.py           # SQLite stats DB
└── utils/
    └── text.py          # Message splitting
```

## License

MIT
