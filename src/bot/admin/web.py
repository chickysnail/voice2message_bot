"""aiohttp routes for the admin dashboard."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from aiohttp import web
from elevenlabs.client import ElevenLabs
from elevenlabs.core.api_error import ApiError

from src.bot.admin.auth import authenticate
from src.bot.admin.data import DEFAULT_RANGE, build_dashboard
from src.bot.services.pricing import Pricing
from src.bot.storage.statistics import StatisticsDB

logger = logging.getLogger(__name__)

DASHBOARD_HTML = Path(__file__).with_name("dashboard.html")

# The ElevenLabs quota changes slowly; don't hit their API on every refresh.
ELEVENLABS_CACHE_SECONDS = 300

_NO_STORE = {"Cache-Control": "no-store"}


class AdminDashboard:
    """Serves the dashboard page and its admin-only JSON API."""

    def __init__(
        self,
        stats_db: StatisticsDB,
        pricing: Pricing,
        bot_token: str,
        admin_ids: list[int],
        elevenlabs_api_key: str = "",
    ) -> None:
        self._stats_db = stats_db
        self._pricing = pricing
        self._bot_token = bot_token
        self._admin_ids = set(admin_ids)
        self._elevenlabs_api_key = elevenlabs_api_key
        self._elevenlabs_cache: tuple[float, dict[str, Any]] | None = None

    def register(self, app: web.Application) -> None:
        app.router.add_get("/admin", self.page)
        app.router.add_get("/admin/api/dashboard", self.dashboard)
        app.router.add_get("/admin/api/elevenlabs", self.elevenlabs)

    def _admin_id(self, request: web.Request) -> int | None:
        user_id = authenticate(
            request.headers.get("Authorization", ""), self._bot_token
        )
        return user_id if user_id in self._admin_ids else None

    async def page(self, request: web.Request) -> web.Response:
        # The page itself holds no data; everything comes from the API.
        return web.Response(
            text=DASHBOARD_HTML.read_text(encoding="utf-8"),
            content_type="text/html",
            headers={**_NO_STORE, "Referrer-Policy": "no-referrer"},
        )

    async def dashboard(self, request: web.Request) -> web.Response:
        if self._admin_id(request) is None:
            return web.json_response({"error": "unauthorized"}, status=401)
        user_param = request.query.get("user")
        try:
            user_id = int(user_param) if user_param else None
        except ValueError:
            return web.json_response({"error": "bad user id"}, status=400)
        data = await build_dashboard(
            self._stats_db,
            self._pricing,
            range_key=request.query.get("range", DEFAULT_RANGE),
            user_id=user_id,
        )
        return web.json_response(data, headers=_NO_STORE)

    async def elevenlabs(self, request: web.Request) -> web.Response:
        if self._admin_id(request) is None:
            return web.json_response({"error": "unauthorized"}, status=401)
        now = time.monotonic()
        cached = self._elevenlabs_cache
        if cached is None or now - cached[0] > ELEVENLABS_CACHE_SECONDS:
            cached = (now, await asyncio.to_thread(self._fetch_elevenlabs))
            self._elevenlabs_cache = cached
        return web.json_response(cached[1], headers=_NO_STORE)

    def _fetch_elevenlabs(self) -> dict[str, Any]:
        """The account's credit quota, straight from ElevenLabs."""
        if not self._elevenlabs_api_key:
            return {"error": "ELEVENLABS_API_KEY is not set"}
        try:
            sub = ElevenLabs(api_key=self._elevenlabs_api_key).user.subscription.get()
        except ApiError as e:
            if e.status_code in (401, 403):
                return {
                    "error": "The API key may not read the account. In ElevenLabs → "
                    "API keys, give it the User → Read permission."
                }
            logger.warning("ElevenLabs subscription request failed: %s", e)
            return {"error": f"ElevenLabs answered {e.status_code}"}
        except Exception as e:
            logger.warning("ElevenLabs subscription request failed: %s", e)
            return {"error": "Could not reach ElevenLabs"}
        return {
            "tier": sub.tier,
            "status": str(sub.status),
            "used": sub.character_count,
            "limit": sub.character_limit,
            "resets_at": sub.next_character_count_reset_unix,
        }
