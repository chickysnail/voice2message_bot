# Voice to Message Bot

A Telegram bot that transcribes voice messages, audio files, and video notes into text using OpenAI's Whisper API and optionally summarizes them using GPT-4.

## Features

- **Voice Message Transcription**: Converts Telegram voice messages to text
- **Video Note Support**: Transcribes audio from video notes (circles)
- **Audio File Support**: Processes uploaded audio files (MP3, WAV, etc.)
- **Video to Audio Conversion**: Automatically extracts audio from video files
- **Two Output Modes**:
  - **Summary**: Rewrites the transcript as a readable text message
  - **Transcript**: Provides the raw transcription
- **Multi-language Support**: Preserves the original language of the audio
- **User Statistics**: Tracks usage statistics per user
- **Message Length Limit**: Configurable limit on voice message duration to control processing costs

## Voice Message Length Limit

The bot has a configurable limit on voice message duration to manage API costs. When a user sends a voice message that exceeds the configured threshold:

- The bot will **not process** the message
- The user receives a notification showing:
  - A message indicating the audio is too long
  - The estimated cost to process that audio length
  - Instructions to contact the bot owner for unlimited access

**Example message:**
```
The audio file is too long.
Processing audio file of this length costs me $X.XX
Please contact me (@chickysnail) to be added to unlimited users
```

The cost calculation is based on OpenAI Whisper API pricing: approximately **$0.006 per minute** of audio.

### Configuring the Length Limit

The voice message duration limit is set in the `config.ini` file under the `[security]` section:

```ini
[security]
voice_threshold = 300  # Maximum duration in seconds (e.g., 300 = 5 minutes)
```

- Set `voice_threshold` to the maximum number of seconds you want to allow
- Default recommendation: 300 seconds (5 minutes)
- Adjust based on your budget and usage patterns
- Users who frequently need longer messages can be added to an unlimited users list (requires code modification)

## Setup

### Prerequisites

- Python 3.7 or higher
- A Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather))
- An OpenAI API key (obtain from [OpenAI Platform](https://platform.openai.com/api-keys))

### Installation

1. Clone the repository:
```bash
git clone https://github.com/chickysnail/voice2message_bot.git
cd voice2message_bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `config.ini` file (see [Configuration](#configuration) section below)

4. Run the bot:
```bash
python telegram_bot.py
```

## Configuration

Create a `config.ini` file in the root directory with the following structure:

```ini
[telegram]
bot_token = YOUR_TELEGRAM_BOT_TOKEN

[credentials]
api_key = YOUR_OPENAI_API_KEY

[security]
voice_threshold = 300
```

Replace:
- `YOUR_TELEGRAM_BOT_TOKEN` with your bot token from BotFather
- `YOUR_OPENAI_API_KEY` with your OpenAI API key
- `300` with your desired maximum voice message duration in seconds

See `config.ini.example` for a template.

## Usage

### Bot Commands

- `/start` - Initialize the bot and see a welcome message
- `/help` - Display help information
- `/stats` - View your usage statistics (message count and total duration)
- `/logs` - (Admin only) Download the bot's log file

### Processing Audio

1. **Send** a voice message, audio file, or video note to the bot
2. **Choose** between:
   - **Summary**: Get a clean, readable text summary
   - **Transcript**: Get the raw transcription
3. **Receive** your text within seconds

The bot supports:
- Voice messages (Telegram native voice messages)
- Video notes (round video messages)
- Audio files (MP3, WAV, OGG, etc.)
- Video files (MP4, MOV, AVI, etc.) - audio will be extracted automatically

## Supported File Types

**Audio Formats:**
- MP3
- WAV
- OGG
- M4A
- FLAC
- And other common audio formats supported by OpenAI Whisper

**Video Formats (audio extraction):**
- MP4
- MPEG
- MOV
- AVI
- WMV

## API Costs

The bot uses two OpenAI APIs:

1. **Whisper API** (Transcription): ~$0.006 per minute of audio
2. **GPT-4o-mini** (Summary): ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens

A typical 1-minute voice message might cost approximately $0.006 - $0.01 total.

## Database

The bot maintains a SQLite database (`statistics.db`) to track:
- User information
- Number of messages transcribed per user
- Total audio duration processed per user

## Logging

Logs are stored in `voice2message_bot.log` with rotation (max 10MB, 5 backup files).

## File Structure

```
voice2message_bot/
├── telegram_bot.py          # Main bot logic
├── voice2message.py         # Audio transcription and rewriting
├── video2audio.py           # Video to audio conversion
├── UserStatisticsDB.py      # User statistics database
├── main.py                  # Standalone CLI tool
├── utils/
│   └── text_helpers.py      # Message splitting utilities
├── requirements.txt         # Python dependencies
├── config.ini               # Configuration (create this, gitignored)
└── README.md               # This file
```

## Multilingual Support

The bot supports multiple languages for:

- **Welcome messages**: English, Russian, Spanish, German
- **Audio transcription**: Automatic language detection by Whisper API
- **Summary generation**: Preserves the original language of the audio

The bot automatically detects the user's Telegram language setting and responds accordingly.

## Development

### Standalone CLI Tool

You can also use the transcription functionality as a standalone tool:

```bash
python main.py config.ini path/to/audio.mp3
```

This will transcribe and summarize the audio file without using Telegram.

## Privacy & Security

- Audio files are temporarily stored during processing and **deleted immediately** after
- User data is stored locally in `statistics.db`
- The bot does not permanently store audio content
- OpenAI's API usage policies apply to all transcriptions

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is open source. Please check the repository for license details.

## Contact

For questions or issues, contact [@chickysnail](https://t.me/chickysnail) on Telegram.
