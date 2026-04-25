"""
game_handler.py — Handler pesan teks untuk menerima kata selama game.
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatType, ParseMode

import config
from game.manager import game_manager
from game.rules import is_long_word, get_chain_suffix
from kbbi.validator import kbbi
from utils import messages
from handlers.commands import _start_turn_timer, _finalize_game

logger = logging.getLogger(__name__)
MD = ParseMode.MARKDOWN


async def handle_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler pesan kata selama game berlangsung."""
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    message = update.message
    if not message or not message.text:
        return

    text = message.text.strip()

    # Abaikan command dan pesan lebih dari satu kata
    if text.startswith("/") or " " in text:
        return

    # Abaikan jika terlalu pendek
    if len(text) < config.MIN_WORD_LENGTH:
        return

    chat_id = update.effective_chat.id
    session = game_manager.get_session(chat_id)

    if not session or not session.is_running:
        return

    user = update.effective_user
    if not user:
        return

    cp = session.current_player

    # ── FIX BUG 2: Non-current player → balas dengan pesan sopan (jangan diam) ──
    if cp is None:
        return

    if cp.user_id != user.id:
        # Cek apakah user ini adalah pemain yang terdaftar
        if user.id in session.player_map:
            suffix = get_chain_suffix(session.last_word)
            n = config.CHAIN_LETTERS
            label = f"{n} huruf" if n > 1 else "huruf"
            await message.reply_text(
                f"\u23f3 Sabar! Sekarang giliran {cp.display_name}.\n"
                f"\U0001f524 Awali dengan {label}: *{suffix.upper()}*",
                parse_mode=MD,
            )
        # Bukan pemain → diam saja
        return

    # ── FIX BUG 3: Cancel timer SEKARANG sebelum ada await apapun ──
    # Ini mencegah race condition di mana timer fire saat sedang memproses kata
    session._cancel_timer()

    word = text.lower()

    # Validasi KBBI
    is_kbbi = kbbi.is_valid(word)

    # Proses kata
    success, msg, next_player = session.process_word(
        user_id=user.id,
        word=word,
        kbbi_valid=is_kbbi,
    )

    if not success:
        await message.reply_text(msg, parse_mode=MD)
        # Cek apakah setelah penalti duplikat, game langsung berakhir
        if session.check_game_over():
            await _finalize_game(context, chat_id, session, update=update)
        else:
            _start_turn_timer(context, chat_id, session)
        return

    # ✅ Kata diterima
    bonus = config.SCORE_LONG_WORD if is_long_word(word) else 0
    total_pts = config.SCORE_CORRECT + bonus
    bonus_str = f" (+{bonus} bonus kata panjang!)" if bonus else ""

    # Cek game over
    if session.check_game_over():
        await message.reply_text(
            f"✅ *{word}* diterima! +{total_pts} poin{bonus_str}",
            parse_mode=MD,
        )
        await _finalize_game(context, chat_id, session, update=update)
        return

    # Game lanjut
    if next_player:
        suffix = get_chain_suffix(word)
        n = config.CHAIN_LETTERS
        label = f"{n} huruf" if n > 1 else "huruf"
        reply = (
            f"\u2705 *{word}* diterima! +{total_pts} poin{bonus_str}\n\n"
            f"\U0001f3af Giliran: {next_player.display_name}\n"
            f"\U0001f524 Awali dengan {label}: *{suffix.upper()}*\n"
            f"\u23f1 {config.TURN_TIMEOUT_SECONDS} detik..."
        )
        await message.reply_text(reply, parse_mode=MD)
        _start_turn_timer(context, chat_id, session)
