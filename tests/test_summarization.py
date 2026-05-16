from unittest.mock import MagicMock, patch

import pytest

from src.bot.services.summarization import OpenAISummarizer


def test_summarize_success() -> None:
    with patch("src.bot.services.summarization.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = "This is a summarized version."
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_completion

        summarizer = OpenAISummarizer(api_key="fake-key")
        result = summarizer.summarize("Long transcript text here...")

        assert result == "This is a summarized version."
        mock_client.chat.completions.create.assert_called_once()


def test_summarize_empty_content() -> None:
    with patch("src.bot.services.summarization.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = ""
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_completion

        summarizer = OpenAISummarizer(api_key="fake-key")

        with pytest.raises(RuntimeError, match="empty content"):
            summarizer.summarize("Some transcript")


def test_summarize_api_error() -> None:
    with patch("src.bot.services.summarization.openai") as mock_openai:
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        mock_client.chat.completions.create.side_effect = Exception("API error")

        summarizer = OpenAISummarizer(api_key="fake-key")

        with pytest.raises(RuntimeError, match="OpenAI summarization failed"):
            summarizer.summarize("Some transcript")
