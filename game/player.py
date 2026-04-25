"""
player.py — Model data pemain dalam satu sesi game.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import config


@dataclass
class Player:
    """Merepresentasikan satu pemain dalam sesi game."""

    user_id: int
    username: str
    first_name: str

    # Statistik sesi
    score: int = 0
    words_submitted: int = 0
    skip_count: int = 0
    is_eliminated: bool = False

    # Sistem nyawa
    lives: int = field(default_factory=lambda: config.MAX_LIVES)

    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        return self.first_name

    @property
    def lives_display(self) -> str:
        """Tampilan nyawa dengan emoji hati."""
        hearts = "❤️" * self.lives
        lost = "🖤" * (config.MAX_LIVES - self.lives)
        return hearts + lost

    def add_score(self, points: int) -> None:
        self.score = max(0, self.score + points)

    def record_word(self) -> None:
        self.words_submitted += 1

    def record_skip(self) -> None:
        self.skip_count += 1

    def lose_life(self) -> bool:
        """
        Kurangi 1 nyawa. Return True jika nyawa habis (eliminated).
        """
        self.lives = max(0, self.lives - 1)
        if self.lives == 0:
            self.eliminate()
            return True
        return False

    def eliminate(self) -> None:
        self.is_eliminated = True

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "score": self.score,
            "words_submitted": self.words_submitted,
            "skip_count": self.skip_count,
            "lives": self.lives,
        }
