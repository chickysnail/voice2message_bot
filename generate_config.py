#!/usr/bin/env python3
"""Generate config.ini from environment variables before starting the bot."""

import os
import configparser

config = configparser.ConfigParser()

config["telegram"] = {
    "bot_token": os.environ["TELEGRAM_BOT_TOKEN"],
}

config["credentials"] = {
    "api_key": os.environ["OPENAI_API_KEY"],
}

config["security"] = {
    "voice_threshold": os.environ.get("VOICE_THRESHOLD", "300"),
}

with open("config.ini", "w") as f:
    config.write(f)

print("config.ini generated successfully.")
