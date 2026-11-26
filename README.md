# Voice2Message Bot v3

A Telegram bot that transcribes voice messages, audio files, and video notes using **ElevenLabs Scribe v2** and optionally summarizes them using **OpenAI GPT-4o-mini**.

## Features

- **Instant transcription** — send audio, get text immediately
- **Summarization** — one-tap summary of any transcription
- **Multi-format support** — voice messages, audio files, video notes
- **Privacy-first** — transcriptions auto-expire after 10 minutes, never persisted to disk
- **Usage statistics** — persistent stats via SQLite (Railway Volume compatible)
- **Admin notifications** — get DM'd when something goes wrong
- **Voiceover** — any text can be read out in the bot author's ElevenLabs voice

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

## Voiceover in the author's voice

When someone sends plain text (no link), the bot gives its usual "I work with
voice messages" reply plus a **🗣 Voice it** button; a `.txt`/`.md` file gets
the button too. Tapping it reads the text out in the ElevenLabs voice
`TTS_VOICE_ID` (the author's professional voice clone) with `TTS_MODEL`
(`eleven_v4`, ElevenLabs' best model) and sends it back as a voice message.
Long texts are voiced in pieces of up to 4,000 characters and joined into one
voice message.

Speech costs about $0.08 per 1,000 characters (`TTS_USD_PER_1K_CHARS`), and a
minute of speech is roughly 900 characters, so a minute costs about $0.07 and
one full Telegram message (4,096 characters) about $0.33.

- **Everyone else** gets `TTS_USER_QUOTA_MINUTES` (10) minutes of speech per
  `TTS_QUOTA_DAYS` (30) days, about $0.70. Admins get a DM about every
  voiceover: who, how long, characters, credits and cost, and how much of the
  quota is used. They never see the text. `TTS_NOTIFY_ADMINS=false` turns the
  DMs off.
- **Admins** have no quota. Each voiceover ends with its length, characters,
  the credits ElevenLabs charged and the cost. A voiceover estimated above
  `TTS_CONFIRM_USD` ($1, about 14 minutes, so only big `.txt` files) asks
  first.

The ElevenLabs API key needs the **Text to Speech** permission. Without it,
every voiceover fails with `HTTP 401 missing_permissions`.

Voiceovers are usage events of kind `speech`. They count in the dashboard's
cost but not in its transcribed-audio minutes. An empty `TTS_VOICE_ID` turns
the feature off.

The professional clone sounds right only on models it has been fine-tuned
for. If it sounds off on `eleven_v4`, check the voice's page in ElevenLabs and
set `TTS_MODEL=eleven_multilingual_v2`.

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
   - optionally `ELEVENLABS_BACKUP_API_KEY` (see below)

### Backup ElevenLabs key

`ELEVENLABS_BACKUP_API_KEY` can hold a key from a second ElevenLabs account.
When ElevenLabs refuses the main key with HTTP 401, 402, 403 or 429 (out of
credits, plan expired, missing permission, rate limited), the bot retries the
same request with the backup key and uses the backup for the next hour.
After that it tries the main key again. Transcription and voiceover switch
independently. Admins get a DM when the bot switches to the backup key and
when it's back on the main one.

Give both keys the same permissions: Speech to Text, Text to Speech and
User → Read. The dashboard's credits card shows the main key's account.

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
├── voiceover.py         # "Voice it": text read out in the author's voice
├── keyboards.py         # Inline keyboards
├── admin/
│   ├── auth.py          # Mini App initData + signed browser links
│   ├── data.py          # Dashboard queries
│   ├── web.py           # /admin routes on the health server
│   └── dashboard.html   # The dashboard page
├── services/
│   ├── pricing.py       # API cost estimates
│   ├── transcription.py # ElevenLabs Scribe v2
│   ├── tts.py           # ElevenLabs text to speech
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
