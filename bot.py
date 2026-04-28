"""
bot.py — Entry point utama bot Sambung Kata KBBI.
Jalankan: python bot.py
"""
from __future__ import annotations

import asyncio
import logging
import os

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

import config
from kbbi.validator import kbbi
from utils.database import init_db
from handlers.commands import (
    cmd_start, cmd_help, cmd_join, cmd_mulai,
    cmd_stop, cmd_skip, cmd_skor, cmd_info,
    cmd_leaderboard, cmd_stats,
)
from handlers.admin import cmd_resetgame, cmd_addskor, cmd_delskor, cmd_setskor, cmd_addnyawa
from handlers.game_handler import handle_word

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def build_application() -> Application:
    if not config.BOT_TOKEN:
        raise RuntimeError(
            "❌ BOT_TOKEN tidak ditemukan!\n"
            "Salin .env.example → .env lalu isi token bot kamu."
        )

    app = Application.builder().token(config.BOT_TOKEN).build()

    # ── Command Handlers ──────────────────────────────────────
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("help",        cmd_help))
    app.add_handler(CommandHandler("join",        cmd_join))
    app.add_handler(CommandHandler("mulai",       cmd_mulai))
    app.add_handler(CommandHandler("stop",        cmd_stop))
    app.add_handler(CommandHandler("skip",        cmd_skip))
    app.add_handler(CommandHandler("skor",        cmd_skor))
    app.add_handler(CommandHandler("info",        cmd_info))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("stats",       cmd_stats))
    app.add_handler(CommandHandler("resetgame",   cmd_resetgame))
    app.add_handler(CommandHandler("addskor",     cmd_addskor))
    app.add_handler(CommandHandler("delskor",     cmd_delskor))
    app.add_handler(CommandHandler("setskor",     cmd_setskor))
    app.add_handler(CommandHandler("addnyawa",    cmd_addnyawa))

    # ── Message Handler (kata game) ────────────────────────────
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND,
            handle_word,
        )
    )

    return app


async def main() -> None:
    # Pastikan folder data ada
    os.makedirs("data", exist_ok=True)

    # Init database leaderboard
    logger.info("🗄️  Inisialisasi database...")
    await init_db()

    # Cek kamus KBBI — auto-download jika belum ada
    total_words = kbbi.count()
    if total_words == 0:
        logger.info("Kamus KBBI belum ada. Mendownload otomatis...")
        try:
            import subprocess, sys
            subprocess.run(
                [sys.executable, "-X", "utf8", "kbbi/data/build_kbbi.py"],
                check=True,
            )
            # Reload kamus
            kbbi._words.clear()
            kbbi._load()
            logger.info(f"Kamus KBBI: {kbbi.count():,} kata siap")
        except Exception as e:
            logger.error(f"Gagal download kamus: {e}. Bot tetap jalan dengan kamus kosong.")
    else:
        logger.info(f"Kamus KBBI: {total_words:,} kata siap")

    # Build & jalankan bot
    app = build_application()
    logger.info("🤖 Bot Sambung Kata KBBI mulai berjalan...")

    await app.initialize()
    await app.start()
    # allowed_updates: pastikan bot terima semua pesan grup
    await app.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=[
            "message",
            "edited_message",
            "callback_query",
            "chat_member",
            "my_chat_member",
        ],
    )

    logger.info("✅ Bot aktif. Tekan Ctrl+C untuk berhenti.")
    logger.info("")
    logger.info("=" * 55)
    logger.info("PENTING: Pastikan PRIVACY MODE bot sudah OFF!")
    logger.info("Cara: BotFather -> /mybots -> Bot kamu ->")
    logger.info("      Bot Settings -> Group Privacy -> TURN OFF")
    logger.info("Tanpa ini, bot tidak bisa terima pesan biasa di grup!")
    logger.info("=" * 55)

    # Tunggu sampai dihentikan
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        logger.info("🛑 Menghentikan bot...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
