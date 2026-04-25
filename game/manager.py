"""
manager.py — Mengelola semua sesi game aktif (per grup/chat_id).
"""
from __future__ import annotations

from typing import Optional
from game.session import GameSession, GameState


class GameManager:
    """
    Singleton manager yang menyimpan semua sesi aktif.
    Satu sesi per chat_id (grup Telegram).
    """

    def __init__(self) -> None:
        self._sessions: dict[int, GameSession] = {}

    def get_session(self, chat_id: int) -> Optional[GameSession]:
        return self._sessions.get(chat_id)

    def get_or_create(self, chat_id: int) -> GameSession:
        if chat_id not in self._sessions:
            self._sessions[chat_id] = GameSession(chat_id)
        return self._sessions[chat_id]

    def has_active_game(self, chat_id: int) -> bool:
        session = self._sessions.get(chat_id)
        if session is None:
            return False
        return session.state in (GameState.JOINING, GameState.RUNNING)

    def destroy_session(self, chat_id: int) -> None:
        session = self._sessions.pop(chat_id, None)
        if session:
            session.reset()

    def reset_session(self, chat_id: int) -> GameSession:
        self.destroy_session(chat_id)
        return self.get_or_create(chat_id)

    def active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.is_running)


# ── Instance global (dipakai oleh semua handlers) ─────────────
game_manager = GameManager()
