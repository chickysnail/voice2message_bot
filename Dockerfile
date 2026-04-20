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
CMD ["sh", "-c", "set -e; python generate_config.py && python telegram_bot.py"]
