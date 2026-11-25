# Self-hosted Telegram Bot API server, used when TELEGRAM_API_ID and
# TELEGRAM_API_HASH are set to lift the 20 MB download limit. It is published
# prebuilt only for Alpine, so the bot runs on Alpine too.
FROM aiogram/telegram-bot-api:latest AS telegram-bot-api

FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1

# ffmpeg/ffprobe for audio; libstdc++ and openssl for telegram-bot-api
RUN apk add --no-cache ffmpeg libstdc++ openssl
COPY --from=telegram-bot-api /usr/local/bin/telegram-bot-api /usr/local/bin/telegram-bot-api
# Fail the build rather than the deploy if a binary is missing a library or
# ffmpeg lacks the Opus encoder that audio extraction uses. If
# telegram-bot-api fails here, it was built on a newer Alpine than this image:
# bump the python base image.
RUN telegram-bot-api --version \
    && ffprobe -version > /dev/null \
    && ffmpeg -hide_banner -encoders | grep -q libopus

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir . && python -c "import src.bot.main"

CMD ["python", "-m", "src.bot.main"]
