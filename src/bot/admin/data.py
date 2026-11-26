"""Queries behind the admin dashboard.

Per-event history (usage over time, bytes, tokens, cost) only exists from the
moment usage events were introduced; the older per-user totals still cover
all-time counts, audio and first/last use.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from src.bot.services.pricing import Pricing
from src.bot.storage.statistics import KIND_SUMMARIZATION, KIND_TRANSCRIPTION, StatisticsDB

SQL_TIME = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class Range:
    key: str
    # strftime format of one bucket, and the Python step between buckets.
    bucket_format: str
    step: timedelta
    span: timedelta | None  # None: everything


RANGES = {
    "24h": Range("24h", "%Y-%m-%d %H:00", timedelta(hours=1), timedelta(hours=24)),
    "7d": Range("7d", "%Y-%m-%d", timedelta(days=1), timedelta(days=7)),
    "30d": Range("30d", "%Y-%m-%d", timedelta(days=1), timedelta(days=30)),
    "90d": Range("90d", "%Y-%m-%d", timedelta(days=1), timedelta(days=90)),
    "all": Range("all", "%Y-%m-%d", timedelta(days=1), None),
}
DEFAULT_RANGE = "30d"


def _floor(moment: datetime, rng: Range) -> datetime:
    if rng.step == timedelta(hours=1):
        return moment.replace(minute=0, second=0, microsecond=0)
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def _parse_sql_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value[:19], SQL_TIME).replace(tzinfo=UTC)
    except ValueError:
        return None


async def _first_activity(db: StatisticsDB) -> datetime | None:
    rows = await db.fetchall(
        """
        SELECT MIN(t) FROM (
            SELECT MIN(first_used_at) AS t FROM user_statistics
            UNION ALL SELECT MIN(first_used_at) FROM secretary_statistics
            UNION ALL SELECT MIN(created_at) FROM usage_events
        )
        """
    )
    return _parse_sql_time(rows[0][0]) if rows else None


async def build_dashboard(
    db: StatisticsDB,
    pricing: Pricing,
    range_key: str = DEFAULT_RANGE,
    user_id: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    rng = RANGES.get(range_key, RANGES[DEFAULT_RANGE])
    now = now or datetime.now(UTC)
    end = _floor(now, rng)
    if rng.span is not None:
        start = end - rng.span + rng.step
    else:
        first = await _first_activity(db)
        start = _floor(first, rng) if first else end
        # Keep "all" readable: at most ~2 years of daily bars.
        start = max(start, end - timedelta(days=730))
    since = start.strftime(SQL_TIME)

    buckets: list[str] = []
    cursor = start
    while cursor <= end:
        buckets.append(cursor.strftime(rng.bucket_format))
        cursor += rng.step

    user_filter = " AND user_id = ?" if user_id is not None else ""
    user_params: tuple[Any, ...] = (user_id,) if user_id is not None else ()
    fmt = rng.bucket_format

    # --- usage over time ---
    series: dict[str, dict[str, float]] = {
        b: {
            "transcriptions": 0, "summaries": 0, "audio_seconds": 0,
            "download_bytes": 0, "upload_bytes": 0, "output_chars": 0,
            "tokens": 0, "cost_usd": 0.0, "active_users": 0,
            "new_users": 0, "donations_stars": 0, "errors": 0,
        }
        for b in buckets
    }
    rows = await db.fetchall(
        f"""
        SELECT strftime('{fmt}', created_at) AS b,
               SUM(kind = ?), SUM(kind = ?),
               SUM(CASE WHEN kind = ? THEN audio_seconds ELSE 0 END),
               SUM(download_bytes), SUM(upload_bytes), SUM(output_chars),
               SUM(prompt_tokens + completion_tokens), SUM(cost_usd),
               COUNT(DISTINCT user_id)
        FROM usage_events
        WHERE created_at >= ?{user_filter}
        GROUP BY b
        """,
        (KIND_TRANSCRIPTION, KIND_SUMMARIZATION, KIND_TRANSCRIPTION, since, *user_params),
    )
    for b, tr, su, sec, dl, ul, chars, tok, cost, users in rows:
        if b in series:
            series[b].update(
                transcriptions=tr, summaries=su, audio_seconds=sec,
                download_bytes=dl, upload_bytes=ul, output_chars=chars,
                tokens=tok, cost_usd=cost, active_users=users,
            )

    # New users come from first-use dates, which go back to the start.
    first_use_rows = await db.fetchall(
        f"""
        SELECT strftime('{fmt}', MIN(first_used_at)), user_id FROM (
            SELECT user_id, first_used_at FROM user_statistics
            UNION ALL
            SELECT user_id, first_used_at FROM secretary_statistics
        )
        WHERE 1 = 1{user_filter}
        GROUP BY user_id
        """,
        user_params,
    )
    for b, _ in first_use_rows:
        if b in series:
            series[b]["new_users"] += 1

    for b, stars in await db.fetchall(
        f"SELECT strftime('{fmt}', created_at), SUM(stars) FROM donations "
        f"WHERE created_at >= ?{user_filter} GROUP BY 1",
        (since, *user_params),
    ):
        if b in series:
            series[b]["donations_stars"] = stars

    username: str | None = None
    if user_id is not None:
        name_rows = await db.fetchall(
            """
            SELECT username FROM (
                SELECT username, last_used_at AS t FROM user_statistics WHERE user_id = ?
                UNION ALL
                SELECT username, last_used_at FROM secretary_statistics WHERE user_id = ?
                UNION ALL
                SELECT username, created_at FROM usage_events WHERE user_id = ?
            ) WHERE username IS NOT NULL ORDER BY t DESC LIMIT 1
            """,
            (user_id, user_id, user_id),
        )
        username = name_rows[0][0] if name_rows else None

    # Errors are stored by username only.
    error_filter = ""
    error_params: tuple[str | None, ...] = ()
    if user_id is not None:
        error_filter, error_params = " AND username IS ?", (username,)
    for b, count in await db.fetchall(
        f"SELECT strftime('{fmt}', created_at), COUNT(*) FROM error_statistics "
        f"WHERE created_at >= ?{error_filter} GROUP BY 1",
        (since, *error_params),
    ):
        if b in series:
            series[b]["errors"] = count

    totals: dict[str, float] = {
        key: sum(point[key] for point in series.values())
        for key in next(iter(series.values()))
    }
    active = await db.fetchall(
        f"SELECT COUNT(DISTINCT user_id) FROM usage_events "
        f"WHERE created_at >= ?{user_filter}",
        (since, *user_params),
    )
    totals["active_users"] = active[0][0]
    totals["donations_usd"] = pricing.stars_to_usd(int(totals["donations_stars"]))

    by_source = [
        {
            "source": source, "count": count, "audio_seconds": sec,
            "download_bytes": dl, "cost_usd": cost,
        }
        for source, count, sec, dl, cost in await db.fetchall(
            f"""
            SELECT source, COUNT(*), SUM(audio_seconds), SUM(download_bytes),
                   SUM(cost_usd)
            FROM usage_events WHERE kind = ? AND created_at >= ?{user_filter}
            GROUP BY source ORDER BY COUNT(*) DESC
            """,
            (KIND_TRANSCRIPTION, since, *user_params),
        )
    ]

    users = await _users(db, pricing, since)
    if user_id is not None:
        users = [u for u in users if u["user_id"] == user_id]
    secretary_connections = (
        await db.fetchall("SELECT COUNT(*) FROM secretary_connections")
    )[0][0]
    all_time = {
        "users": len(users),
        "transcriptions": sum(u["all_time"]["transcriptions"] for u in users),
        "audio_seconds": sum(u["all_time"]["audio_seconds"] for u in users),
        "cost_usd": sum(u["all_time"]["cost_usd"] for u in users),
        "donations_stars": sum(u["donated_stars"] for u in users),
        "secretary_connections": (
            sum(u["secretary"] for u in users) if user_id is not None
            else secretary_connections
        ),
    }
    all_time["donations_usd"] = pricing.stars_to_usd(all_time["donations_stars"])

    recent_errors = [
        {"created_at": c, "type": et, "username": un, "detail": (d or "")[:300]}
        for c, et, un, d in await db.fetchall(
            f"SELECT created_at, error_type, username, error_detail "
            f"FROM error_statistics WHERE 1 = 1{error_filter} "
            f"ORDER BY created_at DESC, id DESC LIMIT 20",
            error_params,
        )
    ]
    tracking = await db.fetchall("SELECT MIN(created_at) FROM usage_events")

    return {
        "generated_at": now.strftime(SQL_TIME),
        "range": rng.key,
        "bucket": "hour" if rng.step == timedelta(hours=1) else "day",
        "tracking_since": tracking[0][0] if tracking else None,
        "pricing": {
            "elevenlabs_usd_per_hour": pricing.elevenlabs_usd_per_hour,
            "star_usd": pricing.star_usd,
        },
        "user": (
            {"user_id": user_id, "username": username} if user_id is not None else None
        ),
        "series": [{"t": b, **series[b]} for b in buckets],
        "totals": totals,
        "all_time": all_time,
        "by_source": by_source,
        "users": users,
        "recent_errors": recent_errors,
    }


async def _users(
    db: StatisticsDB, pricing: Pricing, since: str
) -> list[dict[str, Any]]:
    """Everyone who ever used the bot, with all-time and in-range numbers."""
    people: dict[int, dict[str, Any]] = {}

    def person(uid: int, name: str | None) -> dict[str, Any]:
        entry = people.setdefault(uid, {
            "user_id": uid, "username": None, "secretary": False,
            "donated_stars": 0,
            "all_time": {
                "transcriptions": 0, "secretary_transcriptions": 0,
                "audio_seconds": 0, "summary_cost_usd": 0.0, "cost_usd": 0.0,
                "first_used": None, "last_used": None,
            },
            "range": {
                "transcriptions": 0, "summaries": 0, "audio_seconds": 0,
                "bytes": 0, "tokens": 0, "cost_usd": 0.0,
            },
        })
        if name and not entry["username"]:
            entry["username"] = name
        return entry

    for table, secretary in (("user_statistics", False), ("secretary_statistics", True)):
        for uid, name, count, sec, first, last in await db.fetchall(
            f"SELECT user_id, username, total_transcriptions, "
            f"total_audio_duration_seconds, first_used_at, last_used_at FROM {table}"
        ):
            entry = person(uid, name)
            at = entry["all_time"]
            at["transcriptions"] += count
            at["audio_seconds"] += sec
            if secretary:
                at["secretary_transcriptions"] += count
            if first and (at["first_used"] is None or first < at["first_used"]):
                at["first_used"] = first
            if last and (at["last_used"] is None or last > at["last_used"]):
                at["last_used"] = last

    for (uid,) in await db.fetchall("SELECT user_id FROM secretary_connections"):
        person(uid, None)["secretary"] = True

    for uid, stars in await db.fetchall(
        "SELECT user_id, SUM(stars) FROM donations GROUP BY user_id"
    ):
        person(uid, None)["donated_stars"] = stars

    for uid, cost in await db.fetchall(
        "SELECT user_id, SUM(cost_usd) FROM usage_events WHERE kind = ? GROUP BY user_id",
        (KIND_SUMMARIZATION,),
    ):
        person(uid, None)["all_time"]["summary_cost_usd"] = cost

    for uid, name, tr, su, sec, nbytes, tok, cost in await db.fetchall(
        """
        SELECT user_id, MAX(username), SUM(kind = ?), SUM(kind = ?),
               SUM(CASE WHEN kind = ? THEN audio_seconds ELSE 0 END),
               SUM(download_bytes),
               SUM(prompt_tokens + completion_tokens), SUM(cost_usd)
        FROM usage_events WHERE created_at >= ? GROUP BY user_id
        """,
        (KIND_TRANSCRIPTION, KIND_SUMMARIZATION, KIND_TRANSCRIPTION, since),
    ):
        person(uid, name)["range"] = {
            "transcriptions": tr, "summaries": su, "audio_seconds": sec,
            "bytes": nbytes, "tokens": tok, "cost_usd": cost,
        }

    for entry in people.values():
        at = entry["all_time"]
        at["cost_usd"] = (
            pricing.transcription_cost(at["audio_seconds"]) + at["summary_cost_usd"]
        )
        entry["donated_usd"] = pricing.stars_to_usd(entry["donated_stars"])

    return sorted(
        people.values(),
        key=lambda e: e["all_time"]["last_used"] or "",
        reverse=True,
    )
