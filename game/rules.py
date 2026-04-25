"""
rules.py — Validasi aturan sambung kata.
Mendukung sambung 1, 2, atau 3 huruf sesuai config.CHAIN_LETTERS.
"""
import config


def get_chain_suffix(word: str) -> str:
    """Ambil N huruf terakhir dari kata (sebagai sambungan)."""
    n = min(config.CHAIN_LETTERS, len(word))
    return word[-n:]


def get_chain_prefix(word: str) -> str:
    """Ambil N huruf pertama dari kata."""
    n = min(config.CHAIN_LETTERS, len(word))
    return word[:n]


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
        return False, "❌ Kata hanya boleh mengandung huruf (a-z)."

    required = get_chain_suffix(last_word)
    actual = get_chain_prefix(new_word)

    if actual != required:
        n = config.CHAIN_LETTERS
        label = f"{n} huruf" if n > 1 else "huruf"
        return False, (
            f"❌ Kata harus diawali *{required.upper()}* "
            f"({label} terakhir dari *{last_word}*)."
        )

    return True, "ok"


def is_long_word(word: str) -> bool:
    """True jika kata >= 8 huruf (eligible bonus poin)."""
    return len(word) >= 8
