"""Resolve social media links (Instagram reels) to a downloadable media file.

The resolver talks to a RapidAPI Instagram downloader, which returns JSON
containing a direct CDN URL for the video. Providers differ in their exact
response shape, so the first playable media URL found anywhere in the JSON
is used. Host, path, HTTP method and parameter name are configurable so the
provider can be swapped without code changes.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import uuid
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

INSTAGRAM_LINK_RE = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:[\w.]+/)?(?:reels?|p|tv)/[\w-]+",
    re.IGNORECASE,
)

_MEDIA_URL_RE = re.compile(r"^https?://\S+\.(?:mp4|m4a|mp3|m4v|mov)(?:\?|$)", re.IGNORECASE)
_MEDIA_KEY_HINTS = ("video", "media", "download", "url", "src")


class MediaDownloadError(RuntimeError):
    """Raised when a link cannot be resolved or downloaded."""


def find_link(text: str) -> str | None:
    """Return the first supported media link in `text`, if any."""
    match = INSTAGRAM_LINK_RE.search(text)
    return match.group(0) if match else None


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
    """Resolves Instagram links to direct media URLs via a RapidAPI provider."""

    def __init__(
        self,
        api_key: str,
        *,
        host: str,
        path: str,
        query_param: str,
        method: str = "POST",
        timeout: int = 60,
    ) -> None:
        self._api_key = api_key
        self._host = host
        self._path = path if path.startswith("/") else f"/{path}"
        self._query_param = query_param
        self._method = method.upper()
        self._timeout = timeout

    async def resolve(self, link: str) -> str:
        """Return a direct media URL for `link`."""
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
    url: str, *, timeout: int = 120, max_bytes: int = 100 * 1024 * 1024
) -> str:
    """Download `url` to a temp file and return its path."""
    suffix = os.path.splitext(url.split("?")[0])[1] or ".mp4"
    file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}{suffix}")
    downloaded = 0
    client_timeout = aiohttp.ClientTimeout(total=timeout)
    try:
        async with aiohttp.ClientSession(timeout=client_timeout) as session:
            async with session.get(url) as response:
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
