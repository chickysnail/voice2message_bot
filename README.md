# Voice Transcriber Bot 🎤

A minimal, robust Telegram bot written in Rust that transcribes voice messages using OpenAI Whisper API.

## Features

- 🎙️ Transcribes voice messages and audio files using OpenAI Whisper
- 🔄 Automatic retry logic with exponential backoff
- ⚡ Concurrent transcription support (configurable limit)
- 🏥 Health check endpoint for monitoring
- 📝 Structured logging with file output option
- 🐳 Docker support with multi-stage builds
- 🔒 Secure file handling with automatic cleanup
- 📊 Admin notifications for rejected audio files
- 🎯 Inline keyboard support for future features (Summarize button)

## Quick Start

### Prerequisites

- Rust 1.71 or later (for local development)
- Docker (for containerized deployment)
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

### Docker Deployment

1. **Build the Docker image**

```bash
docker build -t voice-transcriber-bot:latest .
```

2. **Run the container**

```bash
docker run --rm -d \
  -p 8080:8080 \
  -e TELEGRAM_BOT_TOKEN=your_token_here \
  -e OPENAI_API_KEY=your_api_key_here \
  -e ADMIN_IDS=123456789 \
  --name voice-transcriber-bot \
  voice-transcriber-bot:latest
```

3. **Check health**

```bash
curl http://localhost:8080/health
# Should return: {"status":"ok"}
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
| `OPENAI_TIMEOUT_SECONDS` | `120` | Timeout for OpenAI API requests |

## Usage

### Commands

- `/start` - Display welcome message
- `/help` - Show help information
- `/settings` - Display current bot settings

### Transcribing Audio

1. Send a voice message or audio file to the bot
2. The bot will show a "typing..." indicator while processing
3. Receive the transcription text with a "Summarize" button (coming soon)

### Limitations

- Maximum audio duration: 1 hour (3600 seconds)
- Audio files exceeding this limit will be rejected
- Admins will be notified when users attempt to send oversized files

## Architecture

The bot is designed with modularity and extensibility in mind:

```
src/
├── main.rs              # Application entry point
├── config.rs            # Configuration management
├── logger.rs            # Logging setup
├── errors.rs            # Error types
├── utils.rs             # Utility functions
├── bot/
│   ├── handlers.rs      # Message and command handlers
│   └── polling.rs       # Long polling setup
├── transcriber/
│   ├── trait.rs         # Transcriber trait
│   └── openai.rs        # OpenAI implementation
├── storage/
│   └── file_store.rs    # Temporary file management
└── http/
    └── health.rs        # Health check endpoint
```

### Key Design Patterns

- **Trait-based abstraction**: The `Transcriber` trait allows easy addition of new transcription providers
- **Async/await**: Full async implementation using Tokio
- **Concurrency control**: Semaphore-based limiting to respect API rate limits
- **Error handling**: Comprehensive error types with retry logic
- **Clean resource management**: Automatic cleanup of temporary files

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

Run tests with:

```bash
cargo test
```

Run with verbose output:

```bash
cargo test -- --nocapture
```

## Building for Production

### Optimized Release Build

```bash
cargo build --release
```

The binary will be at `target/release/voice-transcriber-bot`.

### Docker Multi-stage Build

The provided Dockerfile uses multi-stage builds for minimal image size:

- Stage 1: Builds the Rust application
- Stage 2: Creates a minimal runtime image with only the binary

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
- **stdout**: Always enabled (Docker-friendly)
- **File**: `./logs/voicebot.log` (if `SAVE_LOG_FILE=true`)

Log format includes timestamps, levels, and structured context.

## Security

- **Secrets**: Never commit `.env` files with actual credentials
- **GitHub Secrets**: Use GitHub Secrets for CI/CD deployments
- **File Permissions**: Temp directory created with `0700` permissions (Unix)
- **Non-root User**: Docker container runs as non-root user `appuser`
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
make docker-build # Build Docker image
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
4. Ensure audio file is in a supported format

### Permission errors

1. Ensure `TEMP_DIR` is writable
2. Check file system permissions
3. Verify Docker volume mounts (if using Docker)

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
