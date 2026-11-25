import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

# usage_events.kind
KIND_TRANSCRIPTION = "transcription"
KIND_SUMMARIZATION = "summarization"


@dataclass(frozen=True)
class UsageEvent:
    """One billable thing the bot did for a user.

    Holds metadata only — never the audio or the transcript itself.
    """

    user_id: int
    username: str | None
    kind: str
    # Where the audio came from: voice, video_note, audio, video, document,
    # instagram, youtube, secretary; "summary" for summaries.
    source: str
    audio_seconds: float = 0
    # Bytes the bot fetched (from Telegram or a link) and sent to the API.
    download_bytes: int = 0
    upload_bytes: int = 0
    # Characters of text sent back to the user.
    output_chars: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0


class StatisticsDB:
    """Async SQLite database for user statistics."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS user_statistics (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                total_transcriptions INTEGER DEFAULT 0,
                total_audio_duration_seconds INTEGER DEFAULT 0,
                first_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS error_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                username TEXT,
                error_detail TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Secretary usage stats (separate from direct usage)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS secretary_statistics (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                total_transcriptions INTEGER DEFAULT 0,
                total_audio_duration_seconds INTEGER DEFAULT 0,
                first_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Active secretary connections (persisted across restarts)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS secretary_connections (
                user_id INTEGER PRIMARY KEY,
                connection_id TEXT NOT NULL,
                username TEXT,
                connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Untranscribed manual prompts awaiting auto-deletion.
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS secretary_pending_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_id TEXT NOT NULL,
                chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # One row per transcription/summary, for usage over time per user.
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS usage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER NOT NULL,
                username TEXT,
                kind TEXT NOT NULL,
                source TEXT NOT NULL,
                audio_seconds REAL NOT NULL DEFAULT 0,
                download_bytes INTEGER NOT NULL DEFAULT 0,
                upload_bytes INTEGER NOT NULL DEFAULT 0,
                output_chars INTEGER NOT NULL DEFAULT 0,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                completion_tokens INTEGER NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0
            )
        """)
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_events_created "
            "ON usage_events(created_at)"
        )
        await self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_usage_events_user "
            "ON usage_events(user_id, created_at)"
        )
        # Telegram Stars donations.
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER NOT NULL,
                username TEXT,
                stars INTEGER NOT NULL,
                charge_id TEXT UNIQUE
            )
        """)
        # When each user last saw the "here's what you've cost" nudge (or
        # donated), and their running cost at that moment.
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS donation_nudges (
                user_id INTEGER PRIMARY KEY,
                last_nudged_at TIMESTAMP,
                cost_at_last_nudge REAL NOT NULL DEFAULT 0
            )
        """)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def record_usage(
        self, user_id: int, username: str | None, audio_duration: int
    ) -> None:
        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO user_statistics (user_id, username, total_transcriptions,
                                         total_audio_duration_seconds, first_used_at, last_used_at)
            VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(?, username),
                total_transcriptions = total_transcriptions + 1,
                total_audio_duration_seconds = total_audio_duration_seconds + ?,
                last_used_at = CURRENT_TIMESTAMP
            """,
            (user_id, username, audio_duration, username, audio_duration),
        )
        await self._db.commit()

    async def get_user_stats(
        self, user_id: int
    ) -> tuple[int, int, str | None, str | None] | None:
        """Returns (total_transcriptions, total_duration, first_used, last_used) or None."""
        assert self._db is not None
        async with self._db.execute(
            """
            SELECT total_transcriptions, total_audio_duration_seconds,
                   first_used_at, last_used_at
            FROM user_statistics WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return (row[0], row[1], row[2], row[3])

    async def get_all_stats(
        self,
    ) -> list[tuple[int, str | None, int, int, str | None, str | None]]:
        """Returns list of (user_id, username, transcriptions, duration, first, last)."""
        assert self._db is not None
        async with self._db.execute(
            """
            SELECT user_id, username, total_transcriptions,
                   total_audio_duration_seconds, first_used_at, last_used_at
            FROM user_statistics ORDER BY last_used_at DESC
            """
        ) as cursor:
            rows = await cursor.fetchall()
        return [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in rows]

    async def get_all_user_ids(self) -> list[int]:
        """Return distinct user IDs the bot can DM (everyone who has
        interacted with it directly or via secretary mode)."""
        assert self._db is not None
        async with self._db.execute(
            """
            SELECT user_id FROM user_statistics
            UNION
            SELECT user_id FROM secretary_statistics
            UNION
            SELECT user_id FROM secretary_connections
            """
        ) as cursor:
            rows = await cursor.fetchall()
        return [r[0] for r in rows]

    async def record_error(
        self,
        error_type: str,
        username: str | None = None,
        error_detail: str | None = None,
    ) -> None:
        """Record an error occurrence."""
        assert self._db is not None
        await self._db.execute(
            "INSERT INTO error_statistics (error_type, username, error_detail) "
            "VALUES (?, ?, ?)",
            (error_type, username, error_detail),
        )
        await self._db.commit()

    async def get_error_stats(
        self,
    ) -> tuple[int, dict[str, int], str | None]:
        """Returns (total_errors, {error_type: count}, last_error_time)."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT COUNT(*) FROM error_statistics"
        ) as cursor:
            row = await cursor.fetchone()
        total = row[0] if row else 0

        async with self._db.execute(
            "SELECT error_type, COUNT(*) FROM error_statistics GROUP BY error_type"
        ) as cursor:
            type_rows = await cursor.fetchall()
        by_type = {r[0]: r[1] for r in type_rows}

        async with self._db.execute(
            "SELECT created_at FROM error_statistics ORDER BY id DESC LIMIT 1"
        ) as cursor:
            last_row = await cursor.fetchone()
        last_error = last_row[0] if last_row else None

        return total, by_type, last_error

    # --- Secretary pending prompts (auto-deletion) ---

    async def add_pending_prompt(
        self, connection_id: str, chat_id: int, message_id: int
    ) -> None:
        """Record an untranscribed prompt so it can be auto-deleted later."""
        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO secretary_pending_prompts
                (connection_id, chat_id, message_id)
            VALUES (?, ?, ?)
            """,
            (connection_id, chat_id, message_id),
        )
        await self._db.commit()

    async def remove_pending_prompt(
        self, connection_id: str, message_id: int
    ) -> None:
        """Remove a prompt once it has been transcribed or deleted."""
        assert self._db is not None
        await self._db.execute(
            """
            DELETE FROM secretary_pending_prompts
            WHERE connection_id = ? AND message_id = ?
            """,
            (connection_id, message_id),
        )
        await self._db.commit()

    async def get_expired_pending_prompts(
        self, older_than_seconds: int
    ) -> list[tuple[str, int, int]]:
        """Return (connection_id, chat_id, message_id) for prompts older
        than the given age."""
        assert self._db is not None
        async with self._db.execute(
            """
            SELECT connection_id, chat_id, message_id
            FROM secretary_pending_prompts
            WHERE created_at <= datetime('now', ?)
            """,
            (f"-{int(older_than_seconds)} seconds",),
        ) as cursor:
            rows = await cursor.fetchall()
        return [(r[0], r[1], r[2]) for r in rows]

    # --- Secretary usage stats ---

    async def record_secretary_usage(
        self, user_id: int, username: str | None, audio_duration: int
    ) -> None:
        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO secretary_statistics
                (user_id, username, total_transcriptions,
                 total_audio_duration_seconds, first_used_at, last_used_at)
            VALUES (?, ?, 1, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(?, username),
                total_transcriptions = total_transcriptions + 1,
                total_audio_duration_seconds = total_audio_duration_seconds + ?,
                last_used_at = CURRENT_TIMESTAMP
            """,
            (user_id, username, audio_duration, username, audio_duration),
        )
        await self._db.commit()

    async def get_secretary_stats(
        self, user_id: int
    ) -> tuple[int, int, str | None, str | None] | None:
        """Returns (total_transcriptions, total_duration, first_used, last_used) or None."""
        assert self._db is not None
        async with self._db.execute(
            """
            SELECT total_transcriptions, total_audio_duration_seconds,
                   first_used_at, last_used_at
            FROM secretary_statistics WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return (row[0], row[1], row[2], row[3])

    async def get_all_secretary_stats(
        self,
    ) -> list[tuple[int, str | None, int, int, str | None, str | None]]:
        """Returns list of (user_id, username, transcriptions, duration, first, last)."""
        assert self._db is not None
        async with self._db.execute(
            """
            SELECT user_id, username, total_transcriptions,
                   total_audio_duration_seconds, first_used_at, last_used_at
            FROM secretary_statistics ORDER BY last_used_at DESC
            """
        ) as cursor:
            rows = await cursor.fetchall()
        return [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in rows]

    # --- Secretary connections ---

    async def save_secretary_connection(
        self, user_id: int, connection_id: str, username: str | None
    ) -> None:
        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO secretary_connections
                (user_id, connection_id, username)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                connection_id = ?, username = COALESCE(?, username),
                connected_at = CURRENT_TIMESTAMP
            """,
            (user_id, connection_id, username, connection_id, username),
        )
        await self._db.commit()

    async def remove_secretary_connection(self, user_id: int) -> None:
        assert self._db is not None
        await self._db.execute(
            "DELETE FROM secretary_connections WHERE user_id = ?",
            (user_id,),
        )
        await self._db.commit()

    async def get_all_secretary_connections(
        self,
    ) -> list[tuple[int, str]]:
        """Returns list of (user_id, connection_id) for active connections."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT user_id, connection_id FROM secretary_connections"
        ) as cursor:
            rows = await cursor.fetchall()
        return [(r[0], r[1]) for r in rows]

    async def is_user_secretary_connected(self, user_id: int) -> bool:
        assert self._db is not None
        async with self._db.execute(
            "SELECT 1 FROM secretary_connections WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row is not None

    # --- Usage events (per user, over time) ---

    async def record_event(self, event: UsageEvent) -> None:
        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO usage_events
                (user_id, username, kind, source, audio_seconds,
                 download_bytes, upload_bytes, output_chars,
                 prompt_tokens, completion_tokens, cost_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.user_id, event.username, event.kind, event.source,
                event.audio_seconds, event.download_bytes, event.upload_bytes,
                event.output_chars, event.prompt_tokens,
                event.completion_tokens, event.cost_usd,
            ),
        )
        await self._db.commit()

    async def fetchall(
        self, sql: str, params: Iterable[Any] = ()
    ) -> list[tuple[Any, ...]]:
        """Run a read-only query; used by the admin dashboard."""
        assert self._db is not None
        async with self._db.execute(sql, tuple(params)) as cursor:
            rows = await cursor.fetchall()
        return [tuple(r) for r in rows]

    async def get_total_audio_seconds(self, user_id: int) -> int:
        """All audio ever transcribed for this user, direct and secretary."""
        rows = await self.fetchall(
            """
            SELECT COALESCE(SUM(total_audio_duration_seconds), 0) FROM (
                SELECT total_audio_duration_seconds FROM user_statistics
                WHERE user_id = ?
                UNION ALL
                SELECT total_audio_duration_seconds FROM secretary_statistics
                WHERE user_id = ?
            )
            """,
            (user_id, user_id),
        )
        return int(rows[0][0])

    async def get_summarization_cost(self, user_id: int) -> float:
        rows = await self.fetchall(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM usage_events "
            "WHERE user_id = ? AND kind = ?",
            (user_id, KIND_SUMMARIZATION),
        )
        return float(rows[0][0])

    # --- Donations ---

    async def record_donation(
        self, user_id: int, username: str | None, stars: int, charge_id: str | None
    ) -> None:
        assert self._db is not None
        await self._db.execute(
            "INSERT OR IGNORE INTO donations (user_id, username, stars, charge_id) "
            "VALUES (?, ?, ?, ?)",
            (user_id, username, stars, charge_id),
        )
        await self._db.commit()

    async def get_donated_stars(self, user_id: int) -> int:
        rows = await self.fetchall(
            "SELECT COALESCE(SUM(stars), 0) FROM donations WHERE user_id = ?",
            (user_id,),
        )
        return int(rows[0][0])

    async def get_nudge_state(self, user_id: int) -> tuple[float | None, float]:
        """Returns (seconds since the last nudge, cost at that nudge);
        (None, 0) if the user was never nudged."""
        rows = await self.fetchall(
            "SELECT (julianday('now') - julianday(last_nudged_at)) * 86400, "
            "cost_at_last_nudge FROM donation_nudges WHERE user_id = ?",
            (user_id,),
        )
        if not rows:
            return None, 0.0
        return float(rows[0][0]), float(rows[0][1])

    async def save_nudge(self, user_id: int, cost: float) -> None:
        """Remember that the user was just nudged (or just donated) at `cost`."""
        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO donation_nudges (user_id, last_nudged_at, cost_at_last_nudge)
            VALUES (?, CURRENT_TIMESTAMP, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                last_nudged_at = CURRENT_TIMESTAMP,
                cost_at_last_nudge = ?
            """,
            (user_id, cost, cost),
        )
        await self._db.commit()
