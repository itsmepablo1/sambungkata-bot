"""
admin.py — Admin-only commands: /resetgame, /addskor
"""
from __future__ import annotations

import logging

import aiosqlite
from telegram import Update, ChatMember
from telegram.ext import ContextTypes
from telegram.constants import ChatType, ParseMode

import config
from game.manager import game_manager
from utils.database import add_player_score, get_player_stats

logger = logging.getLogger(__name__)


async def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in (
            ChatMember.ADMINISTRATOR, ChatMember.OWNER
        )
    except Exception:
        return False


async def cmd_resetgame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    if not await _is_admin(update, context):
        await update.message.reply_text(
            "⛔ Hanya admin grup yang bisa reset game.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    chat_id = update.effective_chat.id
    game_manager.reset_session(chat_id)
    await update.message.reply_text(
        "🔄 Game di-reset oleh admin. Ketik /join untuk mulai sesi baru!",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cmd_addskor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tambah / kurangi skor pemain di leaderboard. Hanya admin.

    Penggunaan:
      /addskor @username 50    — tambah 50 poin ke @username
      /addskor @username -20   — kurangi 20 poin dari @username
      (atau reply ke pesan pengguna) /addskor 50
    """
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await update.message.reply_text(
            "❌ Command ini hanya bisa dipakai di grup.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not await _is_admin(update, context):
        await update.message.reply_text(
            "⛔ Hanya admin grup yang bisa menggunakan /addskor.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    chat_id = update.effective_chat.id
    args = context.args or []
    reply = update.message.reply_to_message

    # ── Parse target user & delta ─────────────────────────────
    target_user = None
    delta_str: str | None = None

    if reply and reply.from_user and not reply.from_user.is_bot:
        # Mode reply: /addskor <delta>
        target_user = reply.from_user
        delta_str = args[0] if args else None

    elif args:
        # Mode mention: /addskor @username <delta>
        mention_user = None
        for entity in (update.message.entities or []):
            if entity.type == "text_mention" and entity.user:
                mention_user = entity.user
                delta_str = args[1] if len(args) > 1 else None
                break
            elif entity.type == "mention":
                # @username biasa — delta ada di args[1]
                delta_str = args[1] if len(args) > 1 else None
                break

        if mention_user:
            target_user = mention_user

    # ── Validasi delta ────────────────────────────────────────
    if delta_str is None:
        await update.message.reply_text(
            "⚠️ *Cara pakai:*\n"
            "`/addskor @username 50` — tambah 50 poin\n"
            "`/addskor @username -20` — kurangi 20 poin\n"
            "Atau reply ke pesan pemain: `/addskor 50`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        delta = int(delta_str)
    except ValueError:
        await update.message.reply_text(
            f"❌ `{delta_str}` bukan angka yang valid.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if delta == 0:
        await update.message.reply_text(
            "⚠️ Delta skor tidak boleh 0.", parse_mode=ParseMode.MARKDOWN
        )
        return

    # ── Resolve target dari @username string ──────────────────
    if target_user is None:
        # args[0] adalah @username string, lookup dari DB
        raw = args[0].lstrip("@")
        async with aiosqlite.connect(config.DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT user_id, first_name, username FROM leaderboard "
                "WHERE chat_id = ? AND LOWER(username) = LOWER(?)",
                (chat_id, raw),
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            await update.message.reply_text(
                f"❌ Pemain `@{raw}` tidak ditemukan di leaderboard grup ini.\n"
                "Pastikan mereka pernah bermain, atau gunakan reply ke pesan mereka.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        uid: int = row["user_id"]
        uname: str = row["username"] or ""
        fname: str = row["first_name"] or raw
    else:
        uid = target_user.id
        uname = target_user.username or ""
        fname = target_user.first_name or str(target_user.id)

    # ── Terapkan perubahan skor ───────────────────────────────
    await add_player_score(
        chat_id=chat_id,
        user_id=uid,
        username=uname,
        first_name=fname,
        score_delta=delta,
    )

    display = f"@{uname}" if uname else fname
    sign = "+" if delta > 0 else ""
    row_after = await get_player_stats(chat_id, uid)
    new_total = row_after["total_score"] if row_after else "?"

    await update.message.reply_text(
        f"✅ Skor *{display}* berhasil diubah!\n"
        f"Perubahan: *{sign}{delta} poin*\n"
        f"Total sekarang: *{new_total} poin*",
        parse_mode=ParseMode.MARKDOWN,
    )
