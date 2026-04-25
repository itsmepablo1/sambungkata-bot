import os
from dotenv import load_dotenv

load_dotenv()

# ─── Bot Config ───────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# ─── Game Settings ─────────────────────────────────────────────
TURN_TIMEOUT_SECONDS: int = 60       # Waktu per giliran (detik)
MIN_PLAYERS: int = 2                  # Minimal pemain untuk mulai
MAX_PLAYERS: int = 20                 # Maksimal pemain per sesi
MIN_WORD_LENGTH: int = 3              # Panjang kata minimum
JOIN_WAIT_SECONDS: int = 60          # Waktu tunggu join sebelum mulai
CHAIN_LETTERS: int = 2               # Jumlah huruf sambung (1, 2, atau 3)

# ─── Scoring ───────────────────────────────────────────────────
SCORE_CORRECT: int = 10              # Poin kata benar
SCORE_LONG_WORD: int = 5             # Bonus kata panjang (>= 8 huruf)
SCORE_SKIP_PENALTY: int = 5          # Penalti skip
SCORE_DUPLICATE_PENALTY: int = 5     # Penalti kata duplikat
MAX_SKIPS: int = 3                   # Maks skip sebelum eliminated
MAX_LIVES: int = 3                   # Jumlah nyawa tiap pemain

# ─── Database ──────────────────────────────────────────────────
DB_PATH: str = "data/leaderboard.db"
