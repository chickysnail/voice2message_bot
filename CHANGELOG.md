# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-12-05

### Added
- Initial release of Voice Transcriber Bot
- Voice message transcription using OpenAI Whisper API
- Support for audio files in addition to voice messages
- Long polling for receiving Telegram updates
- Configurable maximum audio duration (default 3600 seconds)
- Admin notifications for rejected audio files
- Concurrent transcription with configurable limits (default 4)
- Retry logic with exponential backoff for OpenAI API calls
- Health check endpoint at `/health` for monitoring
- Structured logging with tracing (stdout and file)
- Temporary file management with automatic cleanup
- Docker support with multi-stage builds
- Inline keyboard with "Summarize" button (stub for future feature)
- Commands: `/start`, `/help`, `/settings`
- Comprehensive error handling and logging
- Security: non-root Docker user, secure temp directory permissions

### Technical Details
- Written in Rust with async/await using Tokio
- Uses teloxide for Telegram Bot API
- Uses reqwest for HTTP requests to OpenAI
- Modular architecture with trait-based abstractions
- Configuration via environment variables with .env support

[0.1.0]: https://github.com/chickysnail/voice2message_bot/releases/tag/v0.1.0
