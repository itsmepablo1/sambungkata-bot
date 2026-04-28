"""
admin.py — Admin-only commands: /resetgame, /addskor, /delskor, /setskor, /addnyawa

Admin yang bisa pakai command skor & nyawa ditentukan
berdasarkan user_id yang sudah dikonfigurasi di config.BOT_ADMINS.
Bukan berdasarkan status admin grup Telegram.
"""
from __future__ import annotations

import logging

import aiosqlite
from telegram import Update, ChatMember
from telegram.ext import ContextTypes
from telegram.constants import ChatType, ParseMode

import config
from game.manager import game_manager
from game.session import GameState
from utils.database import add_player_score, set_player_score, get_player_stats

logger = logging.getLogger(__name__)

MD = ParseMode.MARKDOWN


# ── Guard helpers ─────────────────────────────────────────────

def _is_bot_admin(user_id: int) -> bool:
    """Cek apakah user_id ada di daftar BOT_ADMINS (config.py)."""
    return user_id in config.BOT_ADMINS


async def _is_group_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Cek apakah pengirim adalah admin/owner grup Telegram."""
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id,
        )
        return member.status in (ChatMember.ADMINISTRATOR, ChatMember.OWNER)
    except Exception:
        return False


# ── Shared: resolve target user dari mention / reply ──────────

async def _resolve_target(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    args: list[str],
) -> tuple[int, str, str] | None:
    """
    Resolve target pemain dari:
      1. Reply ke pesan  → gunakan reply.from_user
      2. text_mention    → user tanpa username (entity.user)
      3. @username       → lookup di leaderboard DB

    Return (user_id, username, first_name) atau None jika gagal.
    Pesan error sudah dikirim ke chat jika None.
    """
    reply = update.message.reply_to_message

    # ── 1. Reply ke pesan ─────────────────────────────────────
    if reply and reply.from_user and not reply.from_user.is_bot:
        u = reply.from_user
        return u.id, u.username or "", u.first_name or str(u.id)

    # ── 2. Mention via entity ──────────────────────────────────
    for entity in (update.message.entities or []):
        if entity.type == "text_mention" and entity.user:
            u = entity.user
            return u.id, u.username or "", u.first_name or str(u.id)

        if entity.type == "mention":
            # @username ada di args[0]
            raw = args[0].lstrip("@") if args else ""
            if not raw:
                break
            async with aiosqlite.connect(config.DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT user_id, username, first_name FROM leaderboard "
                    "WHERE chat_id = ? AND LOWER(username) = LOWER(?)",
                    (chat_id, raw),
                ) as cursor:
                    row = await cursor.fetchone()

            if not row:
                await update.message.reply_text(
                    f"❌ Pemain `@{raw}` tidak ditemukan di leaderboard grup ini.\n"
                    "Pastikan mereka pernah bermain, atau coba reply ke pesan mereka.",
                    parse_mode=MD,
                )
                return None

            return row["user_id"], row["username"] or "", row["first_name"] or raw

    # Tidak ada target sama sekali
    return None


# ── /resetgame ────────────────────────────────────────────────

async def cmd_resetgame(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset sesi game. Hanya admin grup Telegram."""
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    if not await _is_group_admin(update, context):
        await update.message.reply_text(
            "⛔ Hanya admin grup yang bisa reset game.", parse_mode=MD
        )
        return

    game_manager.reset_session(update.effective_chat.id)
    await update.message.reply_text(
        "🔄 Game di-reset oleh admin. Ketik /join untuk mulai sesi baru!",
        parse_mode=MD,
    )


# ── /addskor ──────────────────────────────────────────────────

async def cmd_addskor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Tambah skor pemain di leaderboard. Hanya BOT_ADMINS.

    Penggunaan:
      /addskor @username 50
      reply ke pesan lalu /addskor 50
    """
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    if not _is_bot_admin(update.effective_user.id):
        await update.message.reply_text(
            "⛔ Kamu tidak punya izin untuk menggunakan command ini.", parse_mode=MD
        )
        return

    chat_id = update.effective_chat.id
    args = context.args or []

    # Tentukan letak delta: args[0] jika reply, args[1] jika mention
    reply = update.message.reply_to_message
    has_reply_target = reply and reply.from_user and not reply.from_user.is_bot
    delta_str = args[0] if has_reply_target else (args[1] if len(args) > 1 else None)

    if delta_str is None:
        await update.message.reply_text(
            "⚠️ *Cara pakai /addskor:*\n"
            "`/addskor @username 50` — tambah 50 poin\n"
            "Atau reply ke pesan pemain: `/addskor 50`",
            parse_mode=MD,
        )
        return

    try:
        delta = int(delta_str)
    except ValueError:
        await update.message.reply_text(
            f"❌ `{delta_str}` bukan angka valid.", parse_mode=MD
        )
        return

    if delta == 0:
        await update.message.reply_text("⚠️ Nilai tidak boleh 0.", parse_mode=MD)
        return

    target = await _resolve_target(update, context, chat_id, args)
    if target is None:
        if not has_reply_target:
            await update.message.reply_text(
                "⚠️ *Cara pakai /addskor:*\n"
                "`/addskor @username 50` — tambah 50 poin\n"
                "Atau reply ke pesan pemain: `/addskor 50`",
                parse_mode=MD,
            )
        return

    uid, uname, fname = target
    await add_player_score(chat_id=chat_id, user_id=uid, username=uname,
                           first_name=fname, score_delta=delta)

    display = f"@{uname}" if uname else fname
    sign = "+" if delta > 0 else ""
    after = await get_player_stats(chat_id, uid)
    new_total = after["total_score"] if after else "?"

    await update.message.reply_text(
        f"✅ Skor *{display}* berhasil diubah!\n"
        f"➕ Perubahan: *{sign}{delta} poin*\n"
        f"🏆 Total sekarang: *{new_total} poin*",
        parse_mode=MD,
    )


# ── /delskor ──────────────────────────────────────────────────

async def cmd_delskor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Kurangi skor pemain di leaderboard. Hanya BOT_ADMINS.
    Delta selalu diperlakukan positif lalu dibalik jadi negatif.

    Penggunaan:
      /delskor @username 50
      reply ke pesan lalu /delskor 50
    """
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    if not _is_bot_admin(update.effective_user.id):
        await update.message.reply_text(
            "⛔ Kamu tidak punya izin untuk menggunakan command ini.", parse_mode=MD
        )
        return

    chat_id = update.effective_chat.id
    args = context.args or []

    reply = update.message.reply_to_message
    has_reply_target = reply and reply.from_user and not reply.from_user.is_bot
    delta_str = args[0] if has_reply_target else (args[1] if len(args) > 1 else None)

    if delta_str is None:
        await update.message.reply_text(
            "⚠️ *Cara pakai /delskor:*\n"
            "`/delskor @username 50` — kurangi 50 poin\n"
            "Atau reply ke pesan pemain: `/delskor 50`",
            parse_mode=MD,
        )
        return

    try:
        delta = abs(int(delta_str))   # selalu positif, lalu dibalik
    except ValueError:
        await update.message.reply_text(
            f"❌ `{delta_str}` bukan angka valid.", parse_mode=MD
        )
        return

    if delta == 0:
        await update.message.reply_text("⚠️ Nilai tidak boleh 0.", parse_mode=MD)
        return

    target = await _resolve_target(update, context, chat_id, args)
    if target is None:
        if not has_reply_target:
            await update.message.reply_text(
                "⚠️ *Cara pakai /delskor:*\n"
                "`/delskor @username 50` — kurangi 50 poin\n"
                "Atau reply ke pesan pemain: `/delskor 50`",
                parse_mode=MD,
            )
        return

    uid, uname, fname = target
    await add_player_score(chat_id=chat_id, user_id=uid, username=uname,
                           first_name=fname, score_delta=-delta)

    display = f"@{uname}" if uname else fname
    after = await get_player_stats(chat_id, uid)
    new_total = after["total_score"] if after else "?"

    await update.message.reply_text(
        f"✅ Skor *{display}* berhasil diubah!\n"
        f"➖ Perubahan: *-{delta} poin*\n"
        f"🏆 Total sekarang: *{new_total} poin*",
        parse_mode=MD,
    )


# ── /setskor ──────────────────────────────────────────────────

async def cmd_setskor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Set skor pemain ke nilai tertentu. Hanya BOT_ADMINS.

    Penggunaan:
      /setskor @username 100
      reply ke pesan lalu /setskor 100
    """
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    if not _is_bot_admin(update.effective_user.id):
        await update.message.reply_text(
            "⛔ Kamu tidak punya izin untuk menggunakan command ini.", parse_mode=MD
        )
        return

    chat_id = update.effective_chat.id
    args = context.args or []

    reply = update.message.reply_to_message
    has_reply_target = reply and reply.from_user and not reply.from_user.is_bot
    score_str = args[0] if has_reply_target else (args[1] if len(args) > 1 else None)

    if score_str is None:
        await update.message.reply_text(
            "⚠️ *Cara pakai /setskor:*\n"
            "`/setskor @username 100` — set skor ke 100\n"
            "Atau reply ke pesan pemain: `/setskor 100`",
            parse_mode=MD,
        )
        return

    try:
        score = int(score_str)
    except ValueError:
        await update.message.reply_text(
            f"❌ `{score_str}` bukan angka valid.", parse_mode=MD
        )
        return

    if score < 0:
        await update.message.reply_text(
            "❌ Skor tidak boleh negatif.", parse_mode=MD
        )
        return

    target = await _resolve_target(update, context, chat_id, args)
    if target is None:
        if not has_reply_target:
            await update.message.reply_text(
                "⚠️ *Cara pakai /setskor:*\n"
                "`/setskor @username 100` — set skor ke 100\n"
                "Atau reply ke pesan pemain: `/setskor 100`",
                parse_mode=MD,
            )
        return

    uid, uname, fname = target
    await set_player_score(chat_id=chat_id, user_id=uid, username=uname,
                           first_name=fname, score=score)

    display = f"@{uname}" if uname else fname

    await update.message.reply_text(
        f"✅ Skor *{display}* berhasil di-set!\n"
        f"🏆 Total sekarang: *{score} poin*",
        parse_mode=MD,
    )


# ── /addnyawa ─────────────────────────────────────────────────

async def cmd_addnyawa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Tambah nyawa pemain di sesi game yang sedang berjalan. Hanya BOT_ADMINS.

    Nyawa bersifat in-session (tidak disimpan ke DB).
    Jumlah nyawa maksimum dibatasi 2x MAX_LIVES.

    Penggunaan:
      /addnyawa @username 2
      reply ke pesan pemain lalu /addnyawa 1
    """
    if update.effective_chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    if not _is_bot_admin(update.effective_user.id):
        await update.message.reply_text(
            "\u26d4 Kamu tidak punya izin untuk menggunakan command ini.", parse_mode=MD
        )
        return

    chat_id = update.effective_chat.id
    session = game_manager.get_session(chat_id)

    if not session or session.state != GameState.RUNNING:
        await update.message.reply_text(
            "\u274c Tidak ada game yang sedang berjalan saat ini.", parse_mode=MD
        )
        return

    args = context.args or []
    reply = update.message.reply_to_message
    has_reply_target = reply and reply.from_user and not reply.from_user.is_bot
    amount_str = args[0] if has_reply_target else (args[1] if len(args) > 1 else None)

    if amount_str is None:
        await update.message.reply_text(
            "\u26a0\ufe0f *Cara pakai /addnyawa:*\n"
            "`/addnyawa @username 2` \u2014 tambah 2 nyawa\n"
            "Atau reply ke pesan pemain: `/addnyawa 1`",
            parse_mode=MD,
        )
        return

    try:
        amount = int(amount_str)
    except ValueError:
        await update.message.reply_text(
            f"\u274c `{amount_str}` bukan angka valid.", parse_mode=MD
        )
        return

    if amount <= 0:
        await update.message.reply_text(
            "\u26a0\ufe0f Jumlah nyawa harus lebih dari 0.", parse_mode=MD
        )
        return

    # Resolve target — harus pemain yang sedang aktif di sesi ini
    target = await _resolve_target(update, context, chat_id, args)
    if target is None:
        if not has_reply_target:
            await update.message.reply_text(
                "\u26a0\ufe0f *Cara pakai /addnyawa:*\n"
                "`/addnyawa @username 2` \u2014 tambah 2 nyawa\n"
                "Atau reply ke pesan pemain: `/addnyawa 1`",
                parse_mode=MD,
            )
        return

    uid, uname, fname = target
    player = session.player_map.get(uid)

    if player is None:
        display_t = f"@{uname}" if uname else fname
        await update.message.reply_text(
            f"\u274c *{display_t}* tidak ada dalam sesi game ini.", parse_mode=MD
        )
        return

    # Batas maksimum nyawa = 2x MAX_LIVES
    max_lives = config.MAX_LIVES * 2
    before = player.lives
    player.lives = min(max_lives, player.lives + amount)
    added = player.lives - before

    # Jika sebelumnya eliminated karena nyawa 0, hidupkan kembali
    if player.is_eliminated and player.lives > 0:
        player.is_eliminated = False

    display = f"@{uname}" if uname else fname
    hearts = "\u2764\ufe0f" * player.lives

    await update.message.reply_text(
        f"\u2764\ufe0f Nyawa *{display}* ditambah *+{added}*!\n"
        f"Nyawa sekarang: {hearts} (*{player.lives}*)",
        parse_mode=MD,
    )
