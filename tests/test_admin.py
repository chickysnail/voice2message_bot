"""Admin dashboard: auth, queries, and the HTTP API."""

import hashlib
import hmac
import json
import os
import tempfile
import time
from datetime import UTC, datetime
from urllib.parse import urlencode

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from src.bot.admin.auth import (
    authenticate,
    make_link_token,
    validate_init_data,
    validate_link_token,
)
from src.bot.admin.data import build_dashboard
from src.bot.admin.web import AdminDashboard
from src.bot.services.pricing import Pricing
from src.bot.storage.statistics import (
    KIND_SUMMARIZATION,
    KIND_TRANSCRIPTION,
    StatisticsDB,
    UsageEvent,
)

BOT_TOKEN = "123456:TEST-TOKEN"
ADMIN_ID = 111


def _init_data(user_id: int, auth_date: int, token: str = BOT_TOKEN) -> str:
    """initData signed the way Telegram documents it."""
    fields = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps({"id": user_id, "first_name": "A"}),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


@pytest.fixture
async def db() -> StatisticsDB:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    stats_db = StatisticsDB(path)
    await stats_db.initialize()
    yield stats_db  # type: ignore[misc]
    await stats_db.close()
    os.unlink(path)


# --- auth ---


def test_init_data_valid() -> None:
    now = time.time()
    assert validate_init_data(_init_data(42, int(now)), BOT_TOKEN, now=now) == 42


def test_init_data_wrong_token() -> None:
    data = _init_data(42, int(time.time()), token="999:OTHER")
    assert validate_init_data(data, BOT_TOKEN) is None


def test_init_data_tampered_user() -> None:
    data = _init_data(42, int(time.time())).replace("42", "43")
    assert validate_init_data(data, BOT_TOKEN) is None


def test_init_data_expired() -> None:
    now = time.time()
    data = _init_data(42, int(now - 2 * 86400))
    assert validate_init_data(data, BOT_TOKEN, now=now) is None


def test_init_data_without_hash() -> None:
    assert validate_init_data("auth_date=1&user=%7B%7D", BOT_TOKEN) is None


def test_link_token_round_trip() -> None:
    token = make_link_token(7, BOT_TOKEN, ttl_seconds=60, now=1000)
    assert validate_link_token(token, BOT_TOKEN, now=1030) == 7


def test_link_token_expires() -> None:
    token = make_link_token(7, BOT_TOKEN, ttl_seconds=60, now=1000)
    assert validate_link_token(token, BOT_TOKEN, now=1061) is None


def test_link_token_cannot_change_user_or_expiry() -> None:
    token = make_link_token(7, BOT_TOKEN, ttl_seconds=60, now=1000)
    _, expires, sig = token.split(".")
    assert validate_link_token(f"8.{expires}.{sig}", BOT_TOKEN, now=1000) is None
    assert validate_link_token(f"7.99999.{sig}", BOT_TOKEN, now=1000) is None
    assert validate_link_token("garbage", BOT_TOKEN) is None


def test_authenticate_schemes() -> None:
    token = make_link_token(5, BOT_TOKEN, ttl_seconds=60)
    assert authenticate(f"Link {token}", BOT_TOKEN) == 5
    assert authenticate(f"tma {_init_data(6, int(time.time()))}", BOT_TOKEN) == 6
    assert authenticate(f"Bearer {token}", BOT_TOKEN) is None
    assert authenticate("", BOT_TOKEN) is None


# --- queries ---


async def _seed(db: StatisticsDB) -> None:
    await db.record_usage(1, "alice", 600)
    await db.record_usage(2, "bob", 60)
    await db.record_secretary_usage(1, "alice", 300)
    await db.save_secretary_connection(1, "conn_1", "alice")
    await db.record_event(UsageEvent(
        user_id=1, username="alice", kind=KIND_TRANSCRIPTION, source="voice",
        audio_seconds=600, download_bytes=1_000_000, upload_bytes=900_000,
        output_chars=5000, cost_usd=0.0667,
    ))
    await db.record_event(UsageEvent(
        user_id=1, username="alice", kind=KIND_SUMMARIZATION, source="summary",
        prompt_tokens=1000, completion_tokens=200, cost_usd=0.00027,
    ))
    await db.record_event(UsageEvent(
        user_id=2, username="bob", kind=KIND_TRANSCRIPTION, source="instagram",
        audio_seconds=60, download_bytes=5_000_000, upload_bytes=100_000,
        output_chars=300, cost_usd=0.0067,
    ))
    await db.record_donation(2, "bob", 100, "charge_1")
    await db.record_error("Transcription", "bob", "boom")


async def test_dashboard_totals_and_series(db: StatisticsDB) -> None:
    await _seed(db)
    data = await build_dashboard(db, Pricing(), "7d")

    assert len(data["series"]) == 7
    today = data["series"][-1]
    assert today["t"] == datetime.now(UTC).strftime("%Y-%m-%d")
    assert today["transcriptions"] == 2
    assert today["summaries"] == 1
    assert today["new_users"] == 2
    assert today["donations_stars"] == 100
    assert today["errors"] == 1

    totals = data["totals"]
    assert totals["audio_seconds"] == 660
    assert totals["download_bytes"] == 6_000_000
    assert totals["tokens"] == 1200
    assert totals["active_users"] == 2
    assert totals["cost_usd"] == pytest.approx(0.0667 + 0.00027 + 0.0067)

    assert data["all_time"]["users"] == 2
    assert data["all_time"]["transcriptions"] == 3
    assert data["all_time"]["audio_seconds"] == 960
    assert data["all_time"]["secretary_connections"] == 1
    assert {s["source"] for s in data["by_source"]} == {"voice", "instagram"}
    assert data["recent_errors"][0]["detail"] == "boom"


async def test_dashboard_users(db: StatisticsDB) -> None:
    await _seed(db)
    data = await build_dashboard(db, Pricing(elevenlabs_usd_per_hour=0.36), "30d")
    users = {u["user_id"]: u for u in data["users"]}

    alice = users[1]
    assert alice["secretary"] is True
    assert alice["all_time"]["transcriptions"] == 2
    assert alice["all_time"]["secretary_transcriptions"] == 1
    # 900 s at $0.36/h plus the summary.
    assert alice["all_time"]["cost_usd"] == pytest.approx(0.09 + 0.00027)
    assert alice["range"]["tokens"] == 1200
    assert alice["range"]["bytes"] == 1_000_000

    assert users[2]["donated_stars"] == 100


async def test_dashboard_for_one_user(db: StatisticsDB) -> None:
    await _seed(db)
    data = await build_dashboard(db, Pricing(), "24h", user_id=2)

    assert data["user"] == {"user_id": 2, "username": "bob"}
    assert len(data["series"]) == 24
    assert data["totals"]["transcriptions"] == 1
    assert data["totals"]["tokens"] == 0
    assert [u["user_id"] for u in data["users"]] == [2]
    assert data["all_time"]["users"] == 1
    assert data["totals"]["errors"] == 1


async def test_dashboard_empty_db(db: StatisticsDB) -> None:
    data = await build_dashboard(db, Pricing(), "all")
    assert data["users"] == []
    assert data["totals"]["transcriptions"] == 0
    assert data["tracking_since"] is None
    assert len(data["series"]) == 1


async def test_unknown_range_falls_back(db: StatisticsDB) -> None:
    data = await build_dashboard(db, Pricing(), "forever")
    assert data["range"] == "30d"
    assert len(data["series"]) == 30


# --- HTTP ---


@pytest.fixture
async def client(db: StatisticsDB) -> TestClient:  # type: ignore[type-arg]
    app = web.Application()
    AdminDashboard(db, Pricing(), BOT_TOKEN, [ADMIN_ID]).register(app)
    async with TestClient(TestServer(app)) as c:
        yield c  # type: ignore[misc]


async def test_page_is_public_and_holds_no_data(client: TestClient) -> None:  # type: ignore[type-arg]
    resp = await client.get("/admin")
    assert resp.status == 200
    assert "text/html" in resp.headers["Content-Type"]
    assert "/admin/api/dashboard" in await resp.text()


async def test_api_requires_auth(client: TestClient) -> None:  # type: ignore[type-arg]
    resp = await client.get("/admin/api/dashboard")
    assert resp.status == 401


async def test_api_rejects_non_admin(client: TestClient) -> None:  # type: ignore[type-arg]
    token = make_link_token(999, BOT_TOKEN, ttl_seconds=60)
    resp = await client.get(
        "/admin/api/dashboard", headers={"Authorization": f"Link {token}"}
    )
    assert resp.status == 401


async def test_api_serves_admin(client: TestClient, db: StatisticsDB) -> None:  # type: ignore[type-arg]
    await _seed(db)
    init_data = _init_data(ADMIN_ID, int(time.time()))
    resp = await client.get(
        "/admin/api/dashboard?range=7d&user=1",
        headers={"Authorization": f"tma {init_data}"},
    )
    assert resp.status == 200
    assert resp.headers["Cache-Control"] == "no-store"
    data = await resp.json()
    assert data["range"] == "7d"
    assert data["user"]["user_id"] == 1


async def test_api_bad_user_param(client: TestClient) -> None:  # type: ignore[type-arg]
    token = make_link_token(ADMIN_ID, BOT_TOKEN, ttl_seconds=60)
    resp = await client.get(
        "/admin/api/dashboard?user=abc", headers={"Authorization": f"Link {token}"}
    )
    assert resp.status == 400


async def test_elevenlabs_without_key(client: TestClient) -> None:  # type: ignore[type-arg]
    token = make_link_token(ADMIN_ID, BOT_TOKEN, ttl_seconds=60)
    resp = await client.get(
        "/admin/api/elevenlabs", headers={"Authorization": f"Link {token}"}
    )
    assert resp.status == 200
    assert "error" in await resp.json()
