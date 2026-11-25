import logging
from dataclasses import dataclass
from typing import Protocol

import openai

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = (
    "Rewrite the following transcript as if it were a text message. "
    "Make the text more readable. Keep the main point of the message. "
    "The message will be read by the user. The user only speaks the language "
    "they recorded the audio in. Preserve user's language."
)


@dataclass
class SummaryResult:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


class SummarizationClient(Protocol):
    """Protocol for summarization clients (enables mocking)."""

    def summarize(self, text: str) -> SummaryResult: ...


class OpenAISummarizer:
    """Summarization service using OpenAI GPT-4o-mini."""

    def __init__(
        self, api_key: str, *, timeout: int = 60
    ) -> None:
        self._client = openai.OpenAI(
            api_key=api_key, timeout=timeout
        )

    def summarize(self, text: str) -> SummaryResult:
        """Summarize a transcript and return it with the tokens it used.

        Raises RuntimeError on API failure.
        """
        try:
            completion = self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SUMMARIZE_PROMPT},
                    {"role": "user", "content": text},
                ],
            )
            content = completion.choices[0].message.content
            if not content:
                raise RuntimeError("Summarization returned empty content")
            logger.info("Summarized text (%d chars -> %d chars)", len(text), len(content))
            usage = completion.usage
            return SummaryResult(
                text=content,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
            )
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"OpenAI summarization failed: {e}") from e
