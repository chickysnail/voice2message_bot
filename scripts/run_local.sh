#!/bin/bash

# Voice Transcriber Bot - Local Development Runner

set -e

echo "Voice Transcriber Bot - Local Development"
echo "=========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    exit 1
fi

# Load environment variables
echo "Loading environment variables from .env..."
export $(grep -v '^#' .env | xargs)

# Check required variables
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "Error: TELEGRAM_BOT_TOKEN not set in .env"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY not set in .env"
    exit 1
fi

if [ -z "$ADMIN_IDS" ]; then
    echo "Error: ADMIN_IDS not set in .env"
    exit 1
fi

echo "Configuration loaded successfully"
echo ""
echo "Building application..."
cargo build --release

echo ""
echo "Starting Voice Transcriber Bot..."
echo "Press Ctrl+C to stop"
echo ""

cargo run --release
