"""Обработчики команд владельца и администраторов чата."""
from __future__ import annotations

from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import CommandHandler, ContextTypes

from config.credentials import OWNER_ID
from database.queries import add_points, delete_bot_messages_records, list_bot_messages


async def is_chat_admin(update: Update, user_id: int) -> bool:
    member = await update.effective_chat.get_member(user_id)
    return member.status in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}


async def power_up(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        return
    if not context.args:
        await update.message.reply_text("Использование: /p_up <telegram_id>")
        return
    target = int(context.args[0])
    user = add_points(target, 100, "owner_bonus", "Добавлено владельцем")
    await update.message.reply_text("Баллы начислены." if user else "Пользователь не найден.")


async def power_down(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        return
    if not context.args:
        await update.message.reply_text("Использование: /p_dn <telegram_id>")
        return
    target = int(context.args[0])
    user = add_points(target, -100, "owner_penalty", "Списано владельцем")
    await update.message.reply_text("Баллы списаны." if user else "Пользователь не найден.")


async def clear_bot_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_chat_admin(update, update.effective_user.id):
        await update.message.reply_text("Команда доступна только администраторам чата.")
        return
    chat_id = update.effective_chat.id
    rows = list_bot_messages(chat_id)
    deleted = 0
    for row in rows:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=row.message_id)
            deleted += 1
        except Exception:
            pass
    delete_bot_messages_records(chat_id)
    await update.message.reply_text(f"Удалено сообщений бота: {deleted}")


def register(application) -> None:
    application.add_handler(CommandHandler("p_up", power_up))
    application.add_handler(CommandHandler("p_dn", power_down))
    application.add_handler(CommandHandler("clear_bot_messages", clear_bot_messages))
