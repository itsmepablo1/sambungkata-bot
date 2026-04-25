"""
commands.py — Semua command handler Telegram.
Seluruh pesan menggunakan ParseMode.MARKDOWN (v1) — konsisten & tidak ribet escape.
"""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatType, ParseMode

import config
from game.manager import game_manager
from game.session import GameState
from kbbi.validator import kbbi
from utils import messages
from utils.database import get_leaderboard, get_player_stats, update_player_stats

logger = logging.getLogger(__name__)

MD = ParseMode.MARKDOWN  # shortcut


# ── Guard: hanya grup ─────────────────────────────────────────

def _is_group(update: Update) -> bool:
    return update.effective_chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)


async def _reject_private(update: Update) -> None:
    await update.message.reply_text(messages.msg_group_only(), parse_mode=MD)


# ── /start ────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_group(update):
        await _reject_private(update)
        return
    await update.message.reply_text(messages.msg_welcome(), parse_mode=MD)


# ── /help ─────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(messages.msg_help(), parse_mode=MD)


# ── /join ─────────────────────────────────────────────────────

async def cmd_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_group(update):
        await _reject_private(update)
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    session = game_manager.get_or_create(chat_id)

    if session.state == GameState.RUNNING:
        await update.message.reply_text(
            messages.msg_game_running_cannot_join(), parse_mode=MD
        )
        return

    ok, reason = session.add_player(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "Pemain",
    )

    if ok:
        await update.message.reply_text(
            messages.msg_joined(
                session.player_map[user.id].display_name,
                len(session.players),
            ),
            parse_mode=MD,
        )
    else:
        await update.message.reply_text(reason, parse_mode=MD)


# ── /mulai ────────────────────────────────────────────────────

async def cmd_mulai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_group(update):
        await _reject_private(update)
        return

    chat_id = update.effective_chat.id
    session = game_manager.get_or_create(chat_id)

    if session.state == GameState.RUNNING:
        await update.message.reply_text(
            "⚠️ Game sudah berjalan! Tunggu selesai dulu.", parse_mode=MD
        )
        return

    if session.state == GameState.IDLE or not session.players:
        await update.message.reply_text(
            "⚠️ Belum ada yang /join!", parse_mode=MD
        )
        return

    if len(session.players) < config.MIN_PLAYERS:
        await update.message.reply_text(
            messages.msg_need_more_players(config.MIN_PLAYERS), parse_mode=MD
        )
        return

    starter_word = kbbi.random_word(min_len=4, max_len=7)
    ok, reason = session.start(starter_word)
    if not ok:
        await update.message.reply_text(reason, parse_mode=MD)
        return

    session.starter_id = update.effective_user.id
    first_player = session.current_player

    await update.message.reply_text(
        messages.msg_game_started(session.players, first_player, starter_word),
        parse_mode=MD,
    )
    _start_turn_timer(context, chat_id, session)


# ── /stop ─────────────────────────────────────────────────────

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_group(update):
        await _reject_private(update)
        return

    chat_id = update.effective_chat.id
    session = game_manager.get_session(chat_id)

    if not session or session.state not in (GameState.RUNNING, GameState.JOINING):
        await update.message.reply_text(
            "❌ Tidak ada game yang berjalan saat ini.", parse_mode=MD
        )
        return

    winner = session.get_winner()
    scoreboard = session.get_scoreboard()
    session.stop()

    await update.message.reply_text(
        messages.msg_game_over(winner, scoreboard), parse_mode=MD
    )

    for p in session.players:
        await update_player_stats(
            chat_id=chat_id, user_id=p.user_id,
            username=p.username, first_name=p.first_name,
            score=p.score, words=p.words_submitted,
        )
    game_manager.destroy_session(chat_id)


# ── /skip ─────────────────────────────────────────────────────

async def cmd_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_group(update):
        await _reject_private(update)
        return

    chat_id = update.effective_chat.id
    session = game_manager.get_session(chat_id)

    if not session or not session.is_running:
        await update.message.reply_text(
            "❌ Tidak ada game yang berjalan.", parse_mode=MD
        )
        return

    ok, msg = session.do_skip(update.effective_user.id)
    await update.message.reply_text(msg, parse_mode=MD)

    if ok:
        await _check_game_end(update, context, chat_id, session)


# ── /skor ─────────────────────────────────────────────────────

async def cmd_skor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_group(update):
        await _reject_private(update)
        return

    chat_id = update.effective_chat.id
    session = game_manager.get_session(chat_id)

    if not session or session.state not in (GameState.RUNNING, GameState.JOINING):
        await update.message.reply_text(
            "❌ Tidak ada game aktif saat ini.", parse_mode=MD
        )
        return

    await update.message.reply_text(
        messages.msg_scoreboard(session.get_scoreboard()), parse_mode=MD
    )


# ── /info ─────────────────────────────────────────────────────

async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_group(update):
        await _reject_private(update)
        return

    chat_id = update.effective_chat.id
    session = game_manager.get_session(chat_id)

    if not session or not session.is_running:
        await update.message.reply_text(
            "❌ Tidak ada game yang berjalan.", parse_mode=MD
        )
        return

    await update.message.reply_text(
        messages.msg_game_info(
            last_word=session.last_word,
            current_player=session.current_player,
            round_num=session.round_number,
            used_count=len(session.used_words),
        ),
        parse_mode=MD,
    )


# ── /leaderboard ──────────────────────────────────────────────

async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_group(update):
        await _reject_private(update)
        return

    chat_id = update.effective_chat.id
    rows = await get_leaderboard(chat_id, limit=10)

    if not rows:
        await update.message.reply_text(
            "📊 Belum ada data leaderboard untuk grup ini. Ayo main dulu!",
            parse_mode=MD,
        )
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 *Leaderboard All-Time Grup Ini*\n"]
    for i, r in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = f"@{r['username']}" if r["username"] else r["first_name"]
        lines.append(
            f"{medal} {name} — *{r['total_score']} poin* "
            f"({r['total_words']} kata, {r['games_played']} game)"
        )

    await update.message.reply_text("\n".join(lines), parse_mode=MD)


# ── /stats ────────────────────────────────────────────────────

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_group(update):
        await _reject_private(update)
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    row = await get_player_stats(chat_id, user.id)

    if not row:
        await update.message.reply_text(
            "📊 Kamu belum pernah bermain di grup ini!", parse_mode=MD
        )
        return

    name = f"@{row['username']}" if row["username"] else row["first_name"]
    avg = round(row["total_score"] / row["games_played"], 1) if row["games_played"] else 0
    text = (
        f"📊 *Statistik: {name}*\n\n"
        f"🏆 Total Poin: *{row['total_score']}*\n"
        f"📝 Total Kata: *{row['total_words']}*\n"
        f"🎮 Game Dimainkan: *{row['games_played']}*\n"
        f"📈 Rata-rata Poin/Game: *{avg}*"
    )
    await update.message.reply_text(text, parse_mode=MD)


# ── Internal Helpers ──────────────────────────────────────────

def _start_turn_timer(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    session,
) -> None:
    """Mulai timer auto-skip untuk giliran saat ini."""
    async def on_timeout():
        s = game_manager.get_session(chat_id)
        if not s or not s.is_running:
            return
        msg, next_player = s.timeout_skip()
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=MD)
        if s.check_game_over():
            await _finalize_game(context, chat_id, s)
        elif next_player:
            await context.bot.send_message(
                chat_id=chat_id,
                text=messages.msg_your_turn(next_player, s.last_word),
                parse_mode=MD,
            )
            _start_turn_timer(context, chat_id, s)

    session.start_timer(on_timeout)


async def _check_game_end(update, context, chat_id, session) -> None:
    if session.check_game_over():
        await _finalize_game(context, chat_id, session, update=update)
    else:
        np = session.current_player
        if np:
            await update.message.reply_text(
                messages.msg_your_turn(np, session.last_word), parse_mode=MD
            )
            _start_turn_timer(context, chat_id, session)


async def _finalize_game(context, chat_id, session, update=None) -> None:
    winner = session.get_winner()
    scoreboard = session.get_scoreboard()
    session.stop()

    text = messages.msg_game_over(winner, scoreboard)
    if update:
        await update.message.reply_text(text, parse_mode=MD)
    else:
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=MD)

    for p in session.players:
        await update_player_stats(
            chat_id=chat_id, user_id=p.user_id,
            username=p.username, first_name=p.first_name,
            score=p.score, words=p.words_submitted,
        )
    game_manager.destroy_session(chat_id)
