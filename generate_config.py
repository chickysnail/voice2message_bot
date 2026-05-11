#!/usr/bin/env python3
"""Generate config.ini from environment variables before starting the bot."""

import os
import sys
import configparser

REQUIRED_ENV_VARS = {
    "TELEGRAM_BOT_TOKEN": "telegram bot token (obtain from @BotFather)",
    "OPENAI_API_KEY": "OpenAI API key (obtain from https://platform.openai.com/api-keys)",
}

def check_env_vars():
    """Validate that all required environment variables are set. Exit with a
    descriptive error message if any are missing."""
    missing = []
    for var, description in REQUIRED_ENV_VARS.items():
        if not os.environ.get(var):
            missing.append((var, description))

    if missing:
        print("ERROR: The following required environment variables are not set:", file=sys.stderr)
        for var, description in missing:
            print(f"  {var}  —  {description}", file=sys.stderr)
        print(
            "\nSet these variables in your Railway service settings (or .env file for "
            "local development) and redeploy.",
            file=sys.stderr,
        )
        sys.exit(1)

def generate_config():
    """Build config.ini from environment variables and write it to disk."""
    config = configparser.ConfigParser()

    config["telegram"] = {
        "bot_token": os.environ["TELEGRAM_BOT_TOKEN"],
    }

    config["credentials"] = {
        "api_key": os.environ["OPENAI_API_KEY"],
    }

    config["security"] = {
        "voice_threshold": os.environ.get("VOICE_THRESHOLD", "3600"),
    }

    config_path = "config.ini"
    try:
        with open(config_path, "w") as f:
            config.write(f)
    except OSError as exc:
        print(f"ERROR: Could not write {config_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"config.ini generated successfully (voice_threshold={config['security']['voice_threshold']}).")

if __name__ == "__main__":
    check_env_vars()
    generate_config()
