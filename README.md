# Voice Transcriber Bot 🎤

A minimal, robust Telegram bot written in Rust that transcribes voice messages using OpenAI Whisper API.

## Features

- 🎙️ Transcribes voice messages and audio files using OpenAI Whisper
- 📊 Real-time progress messages showing transcription stages
- ✂️ Automatic message chunking for long transcriptions (splits at sentence boundaries)
- 🔄 Automatic retry logic with exponential backoff and jitter
- ⚡ Concurrent transcription support (configurable limit)
- 🏥 Health check endpoint for monitoring
- 📝 Structured logging with file output option
- 🔒 Secure file handling with automatic cleanup
- 📊 Admin notifications for rejected audio files and errors
- 🎯 Inline keyboard support for future features (Summarize button)
- ⏱️ Extended timeout support (10 minutes) for long audio processing

## Quick Start

### Prerequisites

- Rust 1.71 or later
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- OpenAI API Key (from [OpenAI Platform](https://platform.openai.com))

### Local Development

1. **Clone the repository**

```bash
git clone https://github.com/chickysnail/voice2message_bot.git
cd voice2message_bot
```

2. **Configure environment variables**

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

3. **Build and run**

```bash
cargo build --release
cargo run --release
```

Or use the provided script:

```bash
chmod +x scripts/run_local.sh
./scripts/run_local.sh
```

## Configuration

All configuration is done through environment variables. You can use a `.env` file for local development.

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token from BotFather | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `OPENAI_API_KEY` | OpenAI API key for Whisper API | `sk-...` |
| `ADMIN_IDS` | Comma-separated list of admin Telegram user IDs | `123456789,987654321` |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUDIO_MAX_SECONDS` | `3600` | Maximum audio duration in seconds (1 hour) |
| `TEMP_DIR` | `/tmp/voicebot` | Directory for temporary audio files |
| `LOG_LEVEL` | `info` | Log level (trace, debug, info, warn, error) |
| `SAVE_LOG_FILE` | `true` | Whether to save logs to file |
| `CONCURRENCY_LIMIT` | `4` | Maximum concurrent transcription requests |
| `HTTP_BIND` | `0.0.0.0` | Health check server bind address |
| `HTTP_PORT` | `8080` | Health check server port |
| `OPENAI_TIMEOUT_SECONDS` | `600` | Timeout for OpenAI API requests (10 minutes for long audio) |

## Usage

### Commands

- `/start` - Display welcome message
- `/help` - Show help information
- `/settings` - Display current bot settings

### Transcribing Audio

1. Send a voice message or audio file to the bot
2. The bot will display real-time progress messages showing:
   - 📥 Receiving your audio file...
   - 🔍 Checking file information...
   - ⬇️ Downloading audio file...
   - 💾 Saving audio file...
   - 🎤 Transcribing audio... (This may take several minutes for long recordings)
   - ✅ Transcription complete! Sending results...
3. Receive the transcription text (split into multiple messages if longer than 4096 characters)
4. The progress message will be automatically deleted after completion
5. Long transcriptions are split at sentence boundaries (by ".") for better readability

### Limitations

- **Maximum audio duration**: 1 hour (3600 seconds)
- **Maximum file size**: 50 MB (Telegram's bot API limit for file delivery)
- **Processing time**: Long audio files (30+ minutes) may take 5-10 minutes to transcribe
- **Message length**: Transcriptions longer than 4096 characters are automatically split into multiple messages
- Audio files exceeding these limits will be rejected with a helpful error message
- Admins will be notified when users attempt to send oversized files or encounter errors

### Error Messages

The bot provides clear, user-friendly error messages for common issues:

- **File too large**: "⚠️ This audio file is too large for Telegram to deliver to bots."
- **Duration exceeded**: "⚠️ Audio is too long (max 1 hour)"
- **Transcription timeout**: "⏱️ Transcription took too long. Please try again later or send a shorter audio file."
- **API errors**: "❌ The transcription service failed. Please try again later."
- **Rate limiting**: "⚠️ The transcription service is currently rate limited. Please try again in a few minutes."

## Architecture

The bot is designed with modularity and extensibility in mind:

```
src/
├── main.rs              # Application entry point
├── config.rs            # Configuration management
├── logger.rs            # Logging setup
├── errors.rs            # Error types (TranscribeError, WhisperError, TelegramError)
├── utils.rs             # Utility functions (backoff, duration formatting)
├── telegram_api.rs      # Telegram file operations and size checks
├── whisper_api.rs       # OpenAI Whisper integration with retry logic
├── admin_notifier.rs    # Admin notification system
├── bot/
│   ├── handlers.rs      # Message and command handlers with progress updates
│   └── polling.rs       # Long polling setup
├── transcriber/
│   ├── trait.rs         # Transcriber trait
│   └── openai.rs        # Legacy OpenAI implementation
├── storage/
│   └── file_store.rs    # Temporary file management
└── http/
    └── health.rs        # Health check endpoint
```

### Key Design Patterns

- **Trait-based abstraction**: The `Transcriber` trait allows easy addition of new transcription providers
- **Async/await**: Full async implementation using Tokio
- **Concurrency control**: Semaphore-based limiting to respect API rate limits
- **Error handling**: Comprehensive error types with retry logic and specific error variants
- **Clean resource management**: Automatic cleanup of temporary files
- **Progress tracking**: Real-time user feedback through editable progress messages
- **Smart chunking**: Automatic message splitting at sentence boundaries for readability

### Reliability Features

The bot includes several features to handle long audio files (up to 6 minutes tested):

1. **Extended Timeouts**
   - 600-second (10 minute) request timeout for OpenAI Whisper API
   - 30-second connect timeout
   - 300-second timeout for Telegram file downloads

2. **Retry Logic with Exponential Backoff**
   - Up to 3 retry attempts for transient failures
   - Exponential backoff with jitter to prevent thundering herd
   - Retries only on: timeouts, connection resets, HTTP 429, HTTP 5xx
   - No retries on: invalid API key, unsupported audio format, file download failures

3. **File Size Validation**
   - Pre-download file size check using Telegram's `getFile` API
   - 50 MB limit enforcement (Telegram's bot API constraint)
   - Clear error messages for oversized files

4. **Admin Notifications**
   - Oversized file attempts
   - Transcription timeouts
   - API errors and failures
   - Structured notification format with timestamps

5. **Message Chunking**
   - Automatic splitting of long transcriptions (>4096 characters)
   - Smart splitting at sentence boundaries (by ".")
   - Fallback to word-level splitting for very long sentences
   - Part counters for multi-part messages

## Extending the Bot

### Adding a New Transcription Provider

Implement the `Transcriber` trait:

```rust
use async_trait::async_trait;
use crate::transcriber::Transcriber;
use crate::errors::TranscribeError;

pub struct MyTranscriber {
    // Your fields
}

#[async_trait]
impl Transcriber for MyTranscriber {
    async fn transcribe(&self, file_path: &Path) -> Result<String, TranscribeError> {
        // Your implementation
    }
}
```

### Adding Summarization

The inline keyboard already includes a "Summarize" button. To implement summarization:

1. Store transcriptions in memory or a database
2. Implement the callback handler in `bot/handlers.rs`
3. Call OpenAI Chat Completions API with the transcription text
4. Return the summary to the user

Example stub is already present in `handle_callback_query`.

## Testing

### Unit and Integration Tests

Run all tests with:

```bash
cargo test
```

Run with verbose output:

```bash
cargo test -- --nocapture
```

### Testing with Long Audio Files

The repository includes a test audio file (`tests/testaudio`, ~6 minutes, ~2.4 MB) for integration testing.

**Important**: To avoid excessive API usage:
- Limit Whisper API calls to **10 per development session**
- The test file is for manual testing and validation
- Use mocking for automated tests where possible

### Test Coverage

Tests include:
- Configuration parsing and defaults
- File size validation and chunking logic
- Retry mechanism with exponential backoff
- Error message formatting
- Duration and timeout calculations
- Admin notification formatting
- Message chunking by sentence boundaries

## Building for Production

### Optimized Release Build

```bash
cargo build --release
```

The binary will be at `target/release/voice-transcriber-bot`.

## Monitoring

### Health Check

The bot exposes a health check endpoint at `/health`:

```bash
curl http://localhost:8080/health
```

Response:
```json
{"status":"ok"}
```

### Logs

Logs are written to:
- **stdout**: Always enabled
- **File**: `./logs/voicebot.log` (if `SAVE_LOG_FILE=true`)

Log format includes timestamps, levels, and structured context.

## Security

- **Secrets**: Never commit `.env` files with actual credentials
- **GitHub Secrets**: Use GitHub Secrets for CI/CD deployments
- **File Permissions**: Temp directory created with `0700` permissions (Unix)
- **API Keys**: Not logged or exposed in error messages

## Development Tools

### Linting

```bash
cargo clippy -- -D warnings
```

### Formatting

```bash
cargo fmt
```

### Build All

```bash
make build        # Build binary
make test         # Run tests
```

## Troubleshooting

### Bot doesn't respond

1. Check that the bot token is correct
2. Verify the bot is running: `curl http://localhost:8080/health`
3. Check logs for errors

### Transcription fails

1. Verify OpenAI API key is valid
2. Check OpenAI API status
3. Review logs for specific error messages
4. Ensure audio file is in a supported format (OGG, MP3, M4A)
5. Check that audio duration is under 1 hour
6. For long audio files, ensure timeout is set to at least 600 seconds

### Transcription times out

For long audio files (30+ minutes), transcription can take 5-10 minutes:
1. Increase `OPENAI_TIMEOUT_SECONDS` to 600 (10 minutes) or higher
2. Check network connectivity and stability
3. Monitor logs for retry attempts
4. Consider splitting very long audio files

### File too large errors

Telegram's bot API has a 50 MB limit for file downloads:
1. Compress audio files before sending
2. Use lower bitrate audio encoding
3. Split long recordings into smaller segments

### Progress message not showing

1. Ensure bot has permission to send messages in the chat
2. Check for Telegram API rate limiting
3. Review logs for message sending errors

### Permission errors

1. Ensure `TEMP_DIR` is writable
2. Check file system permissions

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run `cargo fmt` and `cargo clippy`
6. Submit a pull request

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Roadmap

- [ ] Summarization feature using OpenAI Chat Completions
- [ ] Support for local Whisper models
- [ ] Database integration for transcript history
- [ ] Multi-language support
- [ ] Voice message synthesis (text-to-speech)
- [ ] Rate limiting per user
- [ ] Analytics dashboard

## Credits

Built with:
- [Teloxide](https://github.com/teloxide/teloxide) - Telegram Bot framework
- [Tokio](https://tokio.rs/) - Async runtime
- [Reqwest](https://github.com/seanmonstar/reqwest) - HTTP client
- [Axum](https://github.com/tokio-rs/axum) - Web framework
- [Tracing](https://github.com/tokio-rs/tracing) - Structured logging

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact the maintainers via Telegram (admin IDs in config)
