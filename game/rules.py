"""
rules.py — Validasi aturan sambung kata.
"""
import config


def validate_chain(new_word: str, last_word: str) -> tuple[bool, str]:
    """
    Cek apakah new_word valid disambung dari last_word.
    Returns (valid: bool, reason: str)
    """
    new_word = new_word.lower().strip()
    last_word = last_word.lower().strip()

    if len(new_word) < config.MIN_WORD_LENGTH:
        return False, f"❌ Kata terlalu pendek! Minimal {config.MIN_WORD_LENGTH} huruf."

    if not new_word.isalpha():
        return False, "❌ Kata hanya boleh mengandung huruf (a–z)."

    required_start = last_word[-1]
    if new_word[0] != required_start:
        return False, (
            f"❌ Kata harus diawali huruf "
            f"*{required_start.upper()}* "
            f"(huruf terakhir dari *{last_word}*)."
        )

    return True, "ok"


def is_long_word(word: str) -> bool:
    """True jika kata >= 8 huruf (eligible bonus poin)."""
    return len(word) >= 8
