.PHONY: build docker-build run test clean clippy fmt help

help:
	@echo "Voice Transcriber Bot - Makefile"
	@echo "================================="
	@echo ""
	@echo "Available targets:"
	@echo "  build         - Build release binary"
	@echo "  docker-build  - Build Docker image"
	@echo "  run          - Run the bot locally"
	@echo "  test         - Run tests"
	@echo "  clippy       - Run Clippy linter"
	@echo "  fmt          - Format code"
	@echo "  clean        - Clean build artifacts"
	@echo "  help         - Show this help message"

build:
	@echo "Building release binary..."
	cargo build --release

docker-build:
	@echo "Building Docker image..."
	docker build -t voice-transcriber-bot:latest .

run:
	@echo "Running bot..."
	./scripts/run_local.sh

test:
	@echo "Running tests..."
	cargo test

clippy:
	@echo "Running Clippy..."
	cargo clippy -- -D warnings

fmt:
	@echo "Formatting code..."
	cargo fmt

clean:
	@echo "Cleaning build artifacts..."
	cargo clean
	rm -rf logs/
