"""Resolve social links (Instagram reels, YouTube videos) to a media file.

Each platform has its own RapidAPI provider, which returns JSON containing a
direct CDN URL for the video or audio track. Providers differ in their exact
response shape, so the first playable media URL found anywhere in the JSON is
used. Host, path, HTTP method and parameter are configurable per platform so
providers can be swapped without code changes.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import tempfile
import uuid
from dataclasses import dataclass
from typing import Any

import aiohttp
from yarl import URL

logger = logging.getLogger(__name__)

INSTAGRAM = "instagram"
YOUTUBE = "youtube"

_LINK_RES = {
    INSTAGRAM: re.compile(
        r"https?://(?:www\.)?instagram\.com/(?:[\w.]+/)?(?:reels?|p|tv)/[\w-]+",
        re.IGNORECASE,
    ),
    YOUTUBE: re.compile(
        r"https?://(?:(?:www\.|m\.)?youtube\.com/(?:watch\?\S*?v=|shorts/|live/|embed/)"
        r"|youtu\.be/)[\w-]{11}",
        re.IGNORECASE,
    ),
}

_YOUTUBE_ID_RE = re.compile(r"(?:v=|youtu\.be/|shorts/|live/|embed/)([\w-]{11})")

_MEDIA_URL_RE = re.compile(r"^https?://\S+\.(?:mp4|m4a|mp3|m4v|mov|webm)(?:\?|$)", re.IGNORECASE)
_MEDIA_KEY_HINTS = ("audio", "video", "media", "download", "link", "url", "src")

# The mp3 hosts behind youtube-mp36 serve 404 unless the request looks like it
# came from a browser on the provider's own page.
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0.0.0 Safari/537.36"
)


class MediaDownloadError(RuntimeError):
    """Raised when a link cannot be resolved or downloaded."""


@dataclass(frozen=True)
class MediaLink:
    """A supported link found in a message."""

    platform: str
    url: str


def find_link(text: str) -> MediaLink | None:
    """Return the first supported media link in `text`, if any."""
    best: MediaLink | None = None
    best_pos = len(text)
    for platform, pattern in _LINK_RES.items():
        match = pattern.search(text)
        if match and match.start() < best_pos:
            best, best_pos = MediaLink(platform, match.group(0)), match.start()
    return best


def youtube_video_id(url: str) -> str | None:
    """Extract the 11-character video id from a YouTube URL."""
    match = _YOUTUBE_ID_RE.search(url)
    return match.group(1) if match else None


def _iter_strings(node: Any, key: str = "") -> list[tuple[str, str]]:
    """Flatten a JSON structure into (key, string value) pairs."""
    if isinstance(node, dict):
        pairs: list[tuple[str, str]] = []
        for k, v in node.items():
            pairs.extend(_iter_strings(v, str(k)))
        return pairs
    if isinstance(node, list):
        pairs = []
        for item in node:
            pairs.extend(_iter_strings(item, key))
        return pairs
    if isinstance(node, str):
        return [(key, node)]
    return []


def extract_media_url(payload: Any) -> str | None:
    """Find the most likely direct media URL in a provider response."""
    candidates = [
        (key, value)
        for key, value in _iter_strings(payload)
        if _MEDIA_URL_RE.match(value)
    ]
    if not candidates:
        return None
    for key, value in candidates:
        if any(hint in key.lower() for hint in _MEDIA_KEY_HINTS):
            return value
    return candidates[0][1]


class RapidAPIMediaResolver:
    """Resolves a link to a direct media URL via a RapidAPI provider.

    `param_value` selects what the provider expects: the full page URL, or
    (YouTube-only APIs) the bare video id.

    Some providers transcode asynchronously and answer HTTP 200 without a link
    while the job runs, so a response without a media URL is retried.
    """

    _RESOLVE_ATTEMPTS = 3
    _RETRY_DELAY = 4.0

    def __init__(
        self,
        api_key: str,
        *,
        host: str,
        path: str,
        query_param: str,
        method: str = "POST",
        param_value: str = "url",
        timeout: int = 60,
    ) -> None:
        self._api_key = api_key
        self._host = host
        self._path = path if path.startswith("/") else f"/{path}"
        self._query_param = query_param
        self._method = method.upper()
        self._param_value = param_value
        self._timeout = timeout

    @property
    def referer(self) -> str:
        """Referer the provider's CDN expects on media downloads."""
        return f"https://{self._host}/"

    async def resolve(self, link: str) -> str:
        """Return a direct media URL for `link`."""
        for attempt in range(self._RESOLVE_ATTEMPTS):
            try:
                return await self._resolve_once(link)
            except MediaDownloadError:
                if attempt == self._RESOLVE_ATTEMPTS - 1:
                    raise
                logger.info("Provider has no media URL yet for %s, retrying", link)
                await asyncio.sleep(self._RETRY_DELAY)
        raise MediaDownloadError(f"could not resolve {link}")

    async def _resolve_once(self, link: str) -> str:
        if self._param_value == "id":
            video_id = youtube_video_id(link)
            if not video_id:
                raise MediaDownloadError(f"could not parse a video id from {link}")
            link = video_id
        endpoint = f"https://{self._host}{self._path}"
        headers = {
            "x-rapidapi-key": self._api_key,
            "x-rapidapi-host": self._host,
        }
        if self._method == "POST":
            kwargs: dict[str, Any] = {"json": {self._query_param: link}}
        else:
            kwargs = {"params": {self._query_param: link}}
        timeout = aiohttp.ClientTimeout(total=self._timeout)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(
                self._method, endpoint, headers=headers, **kwargs
            ) as response:
                body = await response.text()
                if response.status != 200:
                    raise MediaDownloadError(
                        f"provider returned HTTP {response.status}: {body[:200]}"
                    )
                try:
                    payload = await response.json(content_type=None)
                except ValueError as e:
                    raise MediaDownloadError(f"provider returned non-JSON: {e}") from e

        media_url = extract_media_url(payload)
        if not media_url:
            raise MediaDownloadError(f"no media URL in provider response: {body[:200]}")
        return media_url


async def download_media(
    url: str,
    *,
    referer: str | None = None,
    timeout: int = 120,
    max_bytes: int = 100 * 1024 * 1024,
) -> str:
    """Download `url` to a temp file and return its path."""
    headers = {"user-agent": _USER_AGENT}
    if referer:
        headers["referer"] = referer
    suffix = os.path.splitext(url.split("?")[0])[1] or ".mp4"
    file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}{suffix}")
    downloaded = 0
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    try:
        async with aiohttp.ClientSession(timeout=client_timeout) as session:
            # encoded=True: signed CDN links must be sent byte-for-byte,
            # aiohttp would otherwise re-encode the query and invalidate them.
            async with session.get(
                URL(url, encoded=True), headers=headers
            ) as response:
                if response.status != 200:
                    raise MediaDownloadError(f"media download failed: HTTP {response.status}")
                with open(file_path, "wb") as fh:
                    async for chunk in response.content.iter_chunked(64 * 1024):
                        downloaded += len(chunk)
                        if downloaded > max_bytes:
                            raise MediaDownloadError("media file exceeds size limit")
                        fh.write(chunk)
    except aiohttp.ClientError as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise MediaDownloadError(f"media download failed: {e!r}") from e
    except MediaDownloadError:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    except TimeoutError as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise MediaDownloadError(f"media download timed out after {timeout}s") from e

    logger.info("Downloaded media from %s to %s (%d bytes)", url, file_path, downloaded)
    return file_path
