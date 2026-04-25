"""
validator.py — Validasi kata ke kamus KBBI (dari file lokal).

Kamus di-load sekali ke memori sebagai Python set untuk
lookup O(1) yang sangat cepat.
"""
from __future__ import annotations

import os
import random
import logging

logger = logging.getLogger(__name__)

_KBBI_FILE = os.path.join(os.path.dirname(__file__), "data", "kbbi_words.txt")


class KBBIValidator:
    """
    Memuat kamus KBBI dari file teks dan menyediakan
    fungsi validasi & pencarian kata.
    """

    def __init__(self) -> None:
        self._words: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not os.path.exists(_KBBI_FILE):
            logger.error(f"File kamus tidak ditemukan: {_KBBI_FILE}")
            return
        with open(_KBBI_FILE, encoding="utf-8") as f:
            for line in f:
                word = line.strip().lower()
                if word and word.isalpha():
                    self._words.add(word)
        logger.info(f"✅ Kamus KBBI dimuat: {len(self._words):,} kata")

    def is_valid(self, word: str) -> bool:
        return word.lower().strip() in self._words

    def count(self) -> int:
        return len(self._words)

    def random_word(self, min_len: int = 4, max_len: int = 8) -> str:
        """Ambil kata acak dari kamus (untuk kata awal game)."""
        candidates = [
            w for w in self._words
            if min_len <= len(w) <= max_len
        ]
        if not candidates:
            return "makan"
        return random.choice(candidates)

    def words_starting_with(self, letter: str) -> list[str]:
        """Semua kata yang diawali huruf tertentu (untuk hint)."""
        return [w for w in self._words if w.startswith(letter.lower())]


# ── Instance global ────────────────────────────────────────────
kbbi = KBBIValidator()
