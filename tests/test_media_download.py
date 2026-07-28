from src.bot.services.media_download import (
    INSTAGRAM,
    YOUTUBE,
    MediaLink,
    extract_media_url,
    find_link,
    youtube_video_id,
)


def test_find_link_matches_instagram_urls() -> None:
    assert find_link("look at this https://www.instagram.com/reel/C8Qlt-mvSm8h/?igsh=1") == (
        MediaLink(INSTAGRAM, "https://www.instagram.com/reel/C8Qlt-mvSm8h")
    )
    assert find_link("https://instagram.com/p/ABC123") == MediaLink(
        INSTAGRAM, "https://instagram.com/p/ABC123"
    )
    assert find_link("https://www.instagram.com/someuser/reel/ABC123/") == MediaLink(
        INSTAGRAM, "https://www.instagram.com/someuser/reel/ABC123"
    )


def test_find_link_matches_youtube_urls() -> None:
    assert find_link("transcribe https://www.youtube.com/watch?v=jNQXAC9IVRw&t=10") == (
        MediaLink(YOUTUBE, "https://www.youtube.com/watch?v=jNQXAC9IVRw")
    )
    assert find_link("https://youtu.be/jNQXAC9IVRw?si=x") == MediaLink(
        YOUTUBE, "https://youtu.be/jNQXAC9IVRw"
    )
    assert find_link("https://www.youtube.com/shorts/jNQXAC9IVRw") == MediaLink(
        YOUTUBE, "https://www.youtube.com/shorts/jNQXAC9IVRw"
    )


def test_find_link_ignores_unsupported_text() -> None:
    assert find_link("just a message") is None
    assert find_link("https://www.instagram.com/someuser/") is None
    assert find_link("https://www.youtube.com/@someuser") is None


def test_youtube_video_id() -> None:
    assert youtube_video_id("https://www.youtube.com/watch?v=jNQXAC9IVRw") == "jNQXAC9IVRw"
    assert youtube_video_id("https://youtu.be/jNQXAC9IVRw") == "jNQXAC9IVRw"
    assert youtube_video_id("https://www.instagram.com/reel/ABC123") is None


def test_extract_media_url_prefers_media_keys() -> None:
    payload = {
        "data": {
            "thumbnail": "https://cdn.example.com/thumb.jpg",
            "items": [{"video_url": "https://cdn.example.com/clip.mp4?token=1"}],
        }
    }
    assert extract_media_url(payload) == "https://cdn.example.com/clip.mp4?token=1"


def test_extract_media_url_finds_mp3_link() -> None:
    payload = {"link": "https://cdn.example.com/audio.mp3?token=1", "status": "ok"}
    assert extract_media_url(payload) == "https://cdn.example.com/audio.mp3?token=1"


def test_extract_media_url_returns_none_without_media() -> None:
    assert extract_media_url({"error": "not found"}) is None
