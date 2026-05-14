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
