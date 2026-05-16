from src.bot.utils.text import format_duration, split_message


def test_split_short_message() -> None:
    result = split_message("Hello world")
    assert result == ["Hello world"]


def test_split_long_message() -> None:
    text = "word " * 1000
    result = split_message(text, max_length=100)
    assert all(len(chunk) <= 100 for chunk in result)
    assert "".join(chunk.strip() for chunk in result).replace("  ", " ") != ""


def test_split_preserves_content() -> None:
    text = "line one\nline two\nline three"
    result = split_message(text, max_length=20)
    joined = "\n".join(result)
    assert "line one" in joined
    assert "line two" in joined
    assert "line three" in joined


def test_format_duration_seconds() -> None:
    assert format_duration(45) == "45s"


def test_format_duration_minutes() -> None:
    assert format_duration(125) == "2m 5s"


def test_format_duration_hours() -> None:
    assert format_duration(3661) == "1h 1m"
