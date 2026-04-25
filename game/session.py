"""
session.py — State satu sesi permainan di sebuah grup.
"""
from __future__ import annotations

import asyncio
import random
from enum import Enum, auto
from typing import Optional, Callable, Awaitable

import config
from game.player import Player
from game.rules import validate_chain, is_long_word


class GameState(Enum):
    IDLE = auto()        # Tidak ada game
    JOINING = auto()     # Fase join (menunggu pemain)
    RUNNING = auto()     # Game sedang berjalan
    FINISHED = auto()    # Game selesai


class GameSession:
    """
    Merepresentasikan satu sesi game sambung kata dalam sebuah grup.
    """

    def __init__(self, chat_id: int) -> None:
        self.chat_id = chat_id
        self.state: GameState = GameState.IDLE
        self.players: list[Player] = []
        self.player_map: dict[int, Player] = {}   # user_id -> Player
        self.current_index: int = 0
        self.last_word: str = ""
        self.used_words: set[str] = set()
        self.word_history: list[tuple[str, str]] = []  # (kata, display_name)
        self.round_number: int = 0
        self._timer_task: Optional[asyncio.Task] = None
        self.starter_id: Optional[int] = None   # user_id yang mulai game

    # ── Properti ──────────────────────────────────────────────

    @property
    def active_players(self) -> list[Player]:
        return [p for p in self.players if not p.is_eliminated]

    @property
    def current_player(self) -> Optional[Player]:
        ap = self.active_players
        if not ap:
            return None
        return ap[self.current_index % len(ap)]

    @property
    def is_running(self) -> bool:
        return self.state == GameState.RUNNING

    @property
    def is_joining(self) -> bool:
        return self.state == GameState.JOINING

    # ── Manajemen Pemain ──────────────────────────────────────

    def add_player(self, user_id: int, username: str, first_name: str) -> tuple[bool, str]:
        if self.state not in (GameState.IDLE, GameState.JOINING):
            return False, "⚠️ Game sudah berjalan, tidak bisa join sekarang."
        if user_id in self.player_map:
            return False, "ℹ️ Kamu sudah terdaftar."
        if len(self.players) >= config.MAX_PLAYERS:
            return False, f"⚠️ Maksimal {config.MAX_PLAYERS} pemain."

        player = Player(user_id=user_id, username=username, first_name=first_name)
        self.players.append(player)
        self.player_map[user_id] = player
        self.state = GameState.JOINING
        return True, "ok"

    def remove_player(self, user_id: int) -> bool:
        if user_id not in self.player_map:
            return False
        player = self.player_map.pop(user_id)
        self.players.remove(player)
        return True

    # ── Kontrol Game ──────────────────────────────────────────

    def start(self, starter_word: str) -> tuple[bool, str]:
        if self.state != GameState.JOINING:
            return False, "⚠️ Belum ada pemain yang join."
        if len(self.active_players) < config.MIN_PLAYERS:
            return False, f"⚠️ Minimal {config.MIN_PLAYERS} pemain untuk mulai."

        random.shuffle(self.players)
        self.state = GameState.RUNNING
        self.last_word = starter_word.lower()
        self.used_words.add(self.last_word)
        self.current_index = 0
        self.round_number = 1
        return True, "ok"

    def stop(self) -> None:
        self._cancel_timer()
        self.state = GameState.FINISHED

    def reset(self) -> None:
        self._cancel_timer()
        self.__init__(self.chat_id)

    # ── Proses Kata ───────────────────────────────────────────

    def process_word(
        self,
        user_id: int,
        word: str,
        kbbi_valid: bool,
    ) -> tuple[bool, str, Optional[Player]]:
        """
        Validasi & proses kata dari pemain.
        Returns (success, message, current_player_after_turn)
        """
        word = word.lower().strip()

        cp = self.current_player
        if cp is None or cp.user_id != user_id:
            return False, "⏳ Bukan giliran kamu!", None

        # Cek sudah dipakai → kena penalti poin + nyawa
        if word in self.used_words:
            cp.add_score(-config.SCORE_DUPLICATE_PENALTY)
            dead = cp.lose_life()
            if dead:
                self._advance_turn()
                return (
                    False,
                    f"💀 *{word}* sudah pernah dipakai!\n"
                    f"-{config.SCORE_DUPLICATE_PENALTY} poin | Nyawa habis!\n"
                    f"{cp.display_name} *ELIMINATED!*",
                    None,
                )
            return (
                False,
                f"❌ *{word}* sudah pernah dipakai!\n"
                f"-{config.SCORE_DUPLICATE_PENALTY} poin | "
                f"Nyawa tersisa: {cp.lives_display}",
                None,
            )

        # Cek aturan sambung
        valid_chain, reason = validate_chain(word, self.last_word)
        if not valid_chain:
            return False, reason, None

        # Cek KBBI
        if not kbbi_valid:
            return False, f"❌ *{word}* tidak ditemukan dalam kamus KBBI.", None

        # ✅ Valid
        bonus = config.SCORE_LONG_WORD if is_long_word(word) else 0
        cp.add_score(config.SCORE_CORRECT + bonus)
        cp.record_word()
        self.used_words.add(word)
        self.word_history.append((word, cp.display_name))
        self.last_word = word
        self._advance_turn()

        msg = f"✅ *{word}* diterima! (+{config.SCORE_CORRECT}"
        if bonus:
            msg += f" +{bonus} bonus kata panjang"
        msg += ")"
        return True, msg, self.current_player

    def do_skip(self, user_id: int) -> tuple[bool, str]:
        """Pemain memilih skip giliran."""
        cp = self.current_player
        if cp is None or cp.user_id != user_id:
            return False, "⏳ Bukan giliran kamu!"

        cp.record_skip()
        cp.add_score(-config.SCORE_SKIP_PENALTY)

        if cp.skip_count >= config.MAX_SKIPS:
            cp.eliminate()
            msg = (
                f"💀 {cp.display_name} telah di-*eliminated* "
                f"karena skip {config.MAX_SKIPS}x!"
            )
        else:
            remaining = config.MAX_SKIPS - cp.skip_count
            msg = (
                f"⏩ {cp.display_name} skip! "
                f"(-{config.SCORE_SKIP_PENALTY} poin | "
                f"sisa {remaining}x skip sebelum eliminated)"
            )

        self._advance_turn()
        return True, msg

    def timeout_skip(self) -> tuple[str, Optional[Player]]:
        """Timer habis, auto-skip giliran saat ini."""
        cp = self.current_player
        if cp is None:
            return "", None

        cp.record_skip()
        cp.add_score(-config.SCORE_SKIP_PENALTY)

        if cp.skip_count >= config.MAX_SKIPS:
            cp.eliminate()
            msg = (
                f"⏰ Waktu habis! {cp.display_name} di-*eliminated* "
                f"karena skip {config.MAX_SKIPS}x berturut-turut!"
            )
        else:
            remaining = config.MAX_SKIPS - cp.skip_count
            msg = (
                f"⏰ Waktu habis! {cp.display_name} di-skip otomatis. "
                f"(-{config.SCORE_SKIP_PENALTY} poin | sisa {remaining}x)"
            )

        self._advance_turn()
        return msg, self.current_player

    # ── Internal ──────────────────────────────────────────────

    def _advance_turn(self) -> None:
        if self.active_players:
            self.current_index = (self.current_index + 1) % len(self.active_players)
            self.round_number += 1

    def check_game_over(self) -> bool:
        """True jika sisa pemain aktif < 2."""
        return len(self.active_players) < 2

    # ── Timer ─────────────────────────────────────────────────

    def start_timer(self, callback: Callable[[], Awaitable[None]]) -> None:
        self._cancel_timer()
        self._timer_task = asyncio.create_task(self._run_timer(callback))

    def _cancel_timer(self) -> None:
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        self._timer_task = None

    async def _run_timer(self, callback: Callable[[], Awaitable[None]]) -> None:
        await asyncio.sleep(config.TURN_TIMEOUT_SECONDS)
        await callback()

    # ── Scoreboard ────────────────────────────────────────────

    def get_scoreboard(self) -> list[Player]:
        return sorted(self.players, key=lambda p: p.score, reverse=True)

    def get_winner(self) -> Optional[Player]:
        active = self.active_players
        if len(active) == 1:
            return active[0]
        # Jika game dihentikan manual, pemenang = skor tertinggi
        scores = self.get_scoreboard()
        return scores[0] if scores else None
