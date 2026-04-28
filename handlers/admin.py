"""
admin.py — Admin-only commands: /resetgame, /addskor, /delskor
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

MD = ParseMode.MARKDOWN


# ── Helpers ───────────────────────────────────────────────────

async def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in (ChatMember.ADMINISTRATOR, ChatMember.OWNER)
    except Exception:
        return False


async def _resolve_and_update_score(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    negate: bool = False,
) -> None:
    """Logika bersama untuk /addskor dan /delskor.

    Parameters
    ----------
    negate : bool
        Jika True (mode /delskor), delta akan dibalik menjadi negatif.
    """
    cmd = "/delskor" if negate else "/addskor"

    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await update.message.reply_text(
            f"❌ Command ini hanya bisa dipakai di grup.", parse_mode=MD
        )
        return

    if not await _is_admin(update, context):
        await update.message.reply_text(
            f"⛔ Hanya admin grup yang bisa menggunakan {cmd}.", parse_mode=MD
        )
        return

    chat_id = update.effective_chat.id
    args = context.args or []
    reply = update.message.reply_to_message

    # ── Parse target & delta ──────────────────────────────────
    target_user = None
    delta_str: str | None = None

    if reply and reply.from_user and not reply.from_user.is_bot:
        # Mode reply: /addskor 50  atau  /delskor 50
        target_user = reply.from_user
        delta_str = args[0] if args else None
    elif args:
        # Mode mention: /addskor @username 50
        mention_user = None
        for entity in (update.message.entities or []):
            if entity.type == "text_mention" and entity.user:
                mention_user = entity.user
                delta_str = args[1] if len(args) > 1 else None
                break
            elif entity.type == "mention":
                delta_str = args[1] if len(args) > 1 else None
                break
        if mention_user:
            target_user = mention_user

    # ── Validasi delta ────────────────────────────────────────
    if delta_str is None:
        if negate:
            usage = (
                "⚠️ *Cara pakai /delskor:*\n"
                "`/delskor @username 50` — kurangi 50 poin\n"
                "Atau reply ke pesan pemain: `/delskor 50`"
            )
        else:
            usage = (
                "⚠️ *Cara pakai /addskor:*\n"
                "`/addskor @username 50` — tambah 50 poin\n"
                "`/addskor @username -20` — kurangi 20 poin\n"
                "Atau reply ke pesan pemain: `/addskor 50`"
            )
        await update.message.reply_text(usage, parse_mode=MD)
        return

    try:
        delta = int(delta_str)
    except ValueError:
        await update.message.reply_text(
            f"❌ `{delta_str}` bukan angka yang valid.", parse_mode=MD
        )
        return

    if delta == 0:
        await update.message.reply_text("⚠️ Nilai tidak boleh 0.", parse_mode=MD)
        return

    # /delskor: pastikan selalu jadi negatif (abs lalu negate)
    if negate:
        delta = -abs(delta)

    # ── Resolve target dari @username string ──────────────────
    if target_user is None:
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
                parse_mode=MD,
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

    emoji = "➕" if delta > 0 else "➖"
    await update.message.reply_text(
        f"✅ Skor *{display}* berhasil diubah!\n"
        f"{emoji} Perubahan: *{sign}{delta} poin*\n"
        f"🏆 Total sekarang: *{new_total} poin*",
        parse_mode=MD,
    )


# ── Commands ──────────────────────────────────────────────────

async def cmd_resetgame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    if not await _is_admin(update, context):
        await update.message.reply_text(
            "⛔ Hanya admin grup yang bisa reset game.", parse_mode=MD
        )
        return

    chat_id = update.effective_chat.id
    game_manager.reset_session(chat_id)
    await update.message.reply_text(
        "🔄 Game di-reset oleh admin. Ketik /join untuk mulai sesi baru!",
        parse_mode=MD,
    )


async def cmd_addskor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tambah skor pemain di leaderboard. Hanya admin."""
    await _resolve_and_update_score(update, context, negate=False)


async def cmd_delskor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kurangi skor pemain di leaderboard. Hanya admin.
    
    Delta selalu diperlakukan sebagai positif lalu dibalik jadi negatif,
    jadi /delskor @user 50 dan /delskor @user -50 hasilnya sama.
    """
    await _resolve_and_update_score(update, context, negate=True)
