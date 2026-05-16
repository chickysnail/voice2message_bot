from src.bot.services.export import generate_srt, generate_txt
from src.bot.services.transcription import WordData


def test_generate_txt() -> None:
    assert generate_txt("Hello world") == "Hello world"


def test_generate_txt_multiline() -> None:
    text = "Speaker 1: Hi\nSpeaker 2: Hello"
    assert generate_txt(text) == text


def test_generate_srt_basic() -> None:
    words = [
        WordData(text="Hello", start=0.0, end=0.5, type="word"),
        WordData(text="world", start=0.5, end=1.0, type="word"),
    ]
    srt = generate_srt(words)
    assert "1\n" in srt
    assert "00:00:00,000 --> 00:00:01,000" in srt
    assert "Hello world" in srt


def test_generate_srt_multiple_blocks() -> None:
    words = [
        WordData(text=f"word{i}", start=float(i), end=float(i + 1), type="word")
        for i in range(15)
    ]
    srt = generate_srt(words, max_words_per_sub=10)
    assert "1\n" in srt
    assert "2\n" in srt


def test_generate_srt_with_speaker() -> None:
    words = [
        WordData(
            text="Hi", start=0.0, end=0.5, speaker_id="speaker_0", type="word"
        ),
        WordData(
            text="there", start=0.5, end=1.0, speaker_id="speaker_0", type="word"
        ),
    ]
    srt = generate_srt(words)
    assert "[speaker_0]" in srt


def test_generate_srt_no_timed_words() -> None:
    words = [
        WordData(text="Hello", start=None, end=None, type="word"),
    ]
    srt = generate_srt(words)
    assert srt == ""


def test_generate_srt_skips_non_words() -> None:
    words = [
        WordData(text="Hello", start=0.0, end=0.5, type="word"),
        WordData(text=" ", start=None, end=None, type="spacing"),
        WordData(text="world", start=0.5, end=1.0, type="word"),
    ]
    srt = generate_srt(words)
    assert "Hello world" in srt


def test_generate_srt_timestamp_format() -> None:
    words = [
        WordData(text="test", start=3661.5, end=3662.0, type="word"),
    ]
    srt = generate_srt(words)
    assert "01:01:01,500" in srt
