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

# Run the bot
CMD ["python", "telegram_bot.py"]
