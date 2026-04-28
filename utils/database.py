"""
database.py — SQLite async untuk leaderboard all-time.
"""
from __future__ import annotations

import aiosqlite
import config


async def init_db() -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS leaderboard (
                user_id     INTEGER,
                chat_id     INTEGER,
                username    TEXT,
                first_name  TEXT,
                total_score INTEGER DEFAULT 0,
                total_words INTEGER DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, chat_id)
            )
        """)
        await db.commit()


async def update_player_stats(
    chat_id: int,
    user_id: int,
    username: str,
    first_name: str,
    score: int,
    words: int,
) -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""
            INSERT INTO leaderboard (user_id, chat_id, username, first_name, total_score, total_words, games_played)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                username     = excluded.username,
                first_name   = excluded.first_name,
                total_score  = total_score + excluded.total_score,
                total_words  = total_words + excluded.total_words,
                games_played = games_played + 1
        """, (user_id, chat_id, username, first_name, score, words))
        await db.commit()


async def get_leaderboard(chat_id: int, limit: int = 10) -> list[dict]:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT username, first_name, total_score, total_words, games_played
            FROM leaderboard
            WHERE chat_id = ?
            ORDER BY total_score DESC
            LIMIT ?
        """, (chat_id, limit)) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_player_stats(chat_id: int, user_id: int) -> dict | None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT username, first_name, total_score, total_words, games_played
            FROM leaderboard
            WHERE chat_id = ? AND user_id = ?
        """, (chat_id, user_id)) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None


async def add_player_score(
    chat_id: int,
    user_id: int,
    username: str,
    first_name: str,
    score_delta: int,
) -> None:
    """Tambahkan / kurangi skor pemain secara manual (oleh admin).

    Jika pemain belum ada di leaderboard grup ini, akan diinsert terlebih dahulu.
    games_played tidak diubah agar tidak merusak statistik.
    Skor minimum adalah 0.
    """
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""
            INSERT INTO leaderboard (user_id, chat_id, username, first_name, total_score, total_words, games_played)
            VALUES (?, ?, ?, ?, MAX(0, ?), 0, 0)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                username    = excluded.username,
                first_name  = excluded.first_name,
                total_score = MAX(0, total_score + ?)
        """, (user_id, chat_id, username, first_name, score_delta, score_delta))
        await db.commit()


async def set_player_score(
    chat_id: int,
    user_id: int,
    username: str,
    first_name: str,
    score: int,
) -> None:
    """Set skor pemain ke nilai tertentu secara langsung (oleh admin).

    Jika pemain belum ada di leaderboard, akan diinsert.
    games_played tidak diubah.
    """
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("""
            INSERT INTO leaderboard (user_id, chat_id, username, first_name, total_score, total_words, games_played)
            VALUES (?, ?, ?, ?, ?, 0, 0)
            ON CONFLICT(user_id, chat_id) DO UPDATE SET
                username    = excluded.username,
                first_name  = excluded.first_name,
                total_score = excluded.total_score
        """, (user_id, chat_id, username, first_name, score))
        await db.commit()
