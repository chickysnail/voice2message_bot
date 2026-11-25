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

## Admin dashboard

Send `/admin` to the bot (admins only). It answers with two buttons: one opens
the dashboard inside Telegram as a Mini App, the other in a browser (that link
works for 24 hours). The dashboard shows, per day or hour and per user:
transcriptions, audio minutes, new and active users, data downloaded and sent
to ElevenLabs, OpenAI tokens, estimated API cost, Stars donations, errors, and
the ElevenLabs account's remaining credits.

It is served by the same HTTP server as `/health`, so it needs a public HTTPS
address: in Railway, open the service → *Settings → Networking → Generate
Domain* and point it at `HEALTH_PORT` (8080). Railway then sets
`RAILWAY_PUBLIC_DOMAIN`; elsewhere, set `PUBLIC_URL`. No extra secret is needed:
Mini App requests are checked against Telegram's signature, browser links are
signed with the bot token, and only `ADMIN_USER_IDS` get data.

What is stored: one row per transcription or summary — user id, username, time,
source, audio length, byte counts, token counts, estimated cost. Never the audio
or the text.

Costs are estimates. ElevenLabs bills audio duration against the plan's
credits, so set `ELEVENLABS_USD_PER_HOUR` to your plan's price divided by its
included hours. The credits card reads the real quota from ElevenLabs; that
needs the API key's *User → Read* permission.

### Donations

Donations stay voluntary. Every `DONATION_NUDGE_USD` of estimated spend on a
user (and at most once per `DONATION_NUDGE_INTERVAL_DAYS`), the bot tells them
how much audio they've transcribed and roughly what it cost, with Stars
buttons. `/stats` shows the same estimate. Donations are recorded, reset the
nudge, and are reported to admins.

## Deployment (Railway)

1. Connect this repo to Railway
2. Set branch to `master`
3. Add a **Volume** mounted at `/data`
4. Set environment variables:
   - `TELEGRAM_BOT_TOKEN`
   - `ELEVENLABS_API_KEY`
   - `OPENAI_API_KEY`
   - `DATABASE_PATH=/data/stats.db`
   - `ADMIN_USER_IDS=your_telegram_user_id`

### Files over 20 MB

The cloud Bot API won't let bots download files over 20 MB. When
`TELEGRAM_API_ID` and `TELEGRAM_API_HASH` are set, the bot starts a
[local Telegram Bot API server](https://github.com/tdlib/telegram-bot-api)
(`telegram-bot-api --local`) inside the same container and talks to Telegram
through it, which raises the limit to 2000 MB.

1. Create an app at <https://my.telegram.org> → *API development tools* and copy
   its `api_id` and `api_hash`.
2. Set on Railway:
   - `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`
   - `FILE_DOWNLOAD_TIMEOUT=600` (the server downloads the whole file before it
     answers, so large files need longer than the default 60 s)
   - optional `TELEGRAM_BOT_API_DIR` (default `/data/telegram-bot-api`, on the
     Volume, so the bot stays logged in across redeploys)
3. Once the new deployment is up, log the bot out of the cloud Bot API once,
   otherwise Telegram may keep delivering some updates there:
   `https://api.telegram.org/bot<TOKEN>/logOut`

To go back, remove `TELEGRAM_API_ID`/`TELEGRAM_API_HASH`. The cloud Bot API
accepts the bot again 10 minutes after the `logOut`.

## Architecture

```
src/bot/
├── main.py              # Entry point
├── config.py            # Settings (pydantic-settings)
├── handlers.py          # Telegram handlers
├── keyboards.py         # Inline keyboards
├── admin/
│   ├── auth.py          # Mini App initData + signed browser links
│   ├── data.py          # Dashboard queries
│   ├── web.py           # /admin routes on the health server
│   └── dashboard.html   # The dashboard page
├── services/
│   ├── pricing.py       # API cost estimates
│   ├── transcription.py # ElevenLabs Scribe v2
│   ├── summarization.py # OpenAI GPT-4o-mini
│   ├── audio.py         # ffmpeg audio extraction
│   ├── local_bot_api.py # Local Bot API server for files over 20 MB
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
