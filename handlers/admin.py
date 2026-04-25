"""
admin.py — Admin-only commands: /resetgame
"""
from __future__ import annotations

import logging

from telegram import Update, ChatMember
from telegram.ext import ContextTypes
from telegram.constants import ChatType, ParseMode

from game.manager import game_manager

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
