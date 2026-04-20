FROM python:3.11-slim

# Install system dependencies required by moviepy (ffmpeg) and imageio
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Generate config.ini from environment variables at startup and run the bot
CMD ["sh", "-c", "\
    printf '[telegram]\nbot_token = %s\n\n[credentials]\napi_key = %s\n\n[security]\nvoice_threshold = %s\n' \
        \"${TELEGRAM_BOT_TOKEN}\" \
        \"${OPENAI_API_KEY}\" \
        \"${VOICE_THRESHOLD:-300}\" \
    > config.ini && \
    python telegram_bot.py"]
