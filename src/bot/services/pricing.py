"""What each API call costs the bot, in US dollars.

Prices are estimates: ElevenLabs bills audio duration against the plan's
credits, OpenAI bills tokens. They drive the admin dashboard and the
"here's what you've cost me" donation nudge, not real invoices.
"""

from dataclasses import dataclass

# OpenAI gpt-4o-mini list prices, USD per 1M tokens.
GPT_4O_MINI_INPUT_PER_M = 0.15
GPT_4O_MINI_OUTPUT_PER_M = 0.60


@dataclass(frozen=True)
class Pricing:
    """Rates used to turn usage into dollars."""

    # ElevenLabs Scribe, USD per hour of audio. On a subscription this is
    # roughly the monthly price divided by the included hours.
    elevenlabs_usd_per_hour: float = 0.40
    # What one Telegram Star pays out to the bot owner, in USD.
    star_usd: float = 0.013

    def transcription_cost(self, seconds: float) -> float:
        return max(seconds, 0.0) / 3600 * self.elevenlabs_usd_per_hour

    def stars_to_usd(self, stars: int) -> float:
        return stars * self.star_usd


def summarization_cost(prompt_tokens: int, completion_tokens: int) -> float:
    return (
        prompt_tokens * GPT_4O_MINI_INPUT_PER_M
        + completion_tokens * GPT_4O_MINI_OUTPUT_PER_M
    ) / 1_000_000
