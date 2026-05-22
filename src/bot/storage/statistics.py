import logging

import aiosqlite

logger = logging.getLogger(__name__)


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
        # Secretary mode settings (auto/manual per user)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS secretary_settings (
                user_id INTEGER PRIMARY KEY,
                mode TEXT NOT NULL DEFAULT 'auto'
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

    # --- Secretary mode settings ---

    async def get_secretary_mode(self, user_id: int) -> str:
        """Returns 'auto' or 'manual'. Defaults to 'manual'."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT mode FROM secretary_settings WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else "manual"

    async def set_secretary_mode(self, user_id: int, mode: str) -> None:
        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO secretary_settings (user_id, mode) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET mode = ?
            """,
            (user_id, mode, mode),
        )
        await self._db.commit()

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
