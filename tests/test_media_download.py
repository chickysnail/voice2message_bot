from src.bot.services.media_download import extract_media_url, find_link


def test_find_link_matches_reel_and_post_urls() -> None:
    assert find_link("look at this https://www.instagram.com/reel/C8Qlt-mvSm8h/?igsh=1") == (
        "https://www.instagram.com/reel/C8Qlt-mvSm8h"
    )
    assert find_link("https://instagram.com/p/ABC123") == "https://instagram.com/p/ABC123"
    assert find_link("https://www.instagram.com/someuser/reel/ABC123/") == (
        "https://www.instagram.com/someuser/reel/ABC123"
    )


def test_find_link_ignores_unsupported_text() -> None:
    assert find_link("just a message") is None
    assert find_link("https://www.instagram.com/someuser/") is None


def test_extract_media_url_prefers_media_keys() -> None:
    payload = {
        "data": {
            "thumbnail": "https://cdn.example.com/thumb.jpg",
            "items": [{"video_url": "https://cdn.example.com/clip.mp4?token=1"}],
        }
    }
    assert extract_media_url(payload) == "https://cdn.example.com/clip.mp4?token=1"


def test_extract_media_url_returns_none_without_media() -> None:
    assert extract_media_url({"error": "not found"}) is None
