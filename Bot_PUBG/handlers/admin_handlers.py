"""Команды владельца и администраторов чатов."""

from __future__ import annotations

from datetime import datetime, timedelta

from telegram import ChatMemberUpdated, Update
from telegram.ext import ChatMemberHandler, CommandHandler, ContextTypes

from config.credentials import OWNER_CHAT_ID
from database import get_session
from database.models import User
from database.queries import (
    delete_tracked_bot_messages,
    get_user_by_telegram_id,
    list_bot_messages,
    upsert_chat_info,
)
from utils.helpers import is_owner, reply_tracked_message


async def p_up(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Скрытая команда владельца: выдать премиум на N дней пользователю.

    Использование:
    /p_up <telegram_id> <days>
    """
    if not is_owner(update.effective_user.id):
        return

    if len(context.args) < 2:
        await reply_tracked_message(update, context, "Использование: /p_up <telegram_id> <days>")
        return

    target_telegram_id = int(context.args[0])
    days = int(context.args[1])

    with get_session() as session:
        user = get_user_by_telegram_id(session, target_telegram_id)
        if not user:
            await reply_tracked_message(update, context, "Пользователь не найден.")
            return

        base = user.premium_until if user.premium_until and user.premium_until > datetime.utcnow() else datetime.utcnow()
        user.premium_until = base + timedelta(days=days)

    await reply_tracked_message(
        update,
        context,
        f"✅ Пользователю {target_telegram_id} добавлено {days} дн. премиума.",
    )


async def p_dn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Скрытая команда владельца: убрать N дней премиума у пользователя.

    Использование:
    /p_dn <telegram_id> <days>
    """
    if not is_owner(update.effective_user.id):
        return

    if len(context.args) < 2:
        await reply_tracked_message(update, context, "Использование: /p_dn <telegram_id> <days>")
        return

    target_telegram_id = int(context.args[0])
    days = int(context.args[1])

    with get_session() as session:
        user = get_user_by_telegram_id(session, target_telegram_id)
        if not user:
            await reply_tracked_message(update, context, "Пользователь не найден.")
            return

        if not user.premium_until:
            await reply_tracked_message(update, context, "У пользователя нет активного премиума.")
            return

        user.premium_until = user.premium_until - timedelta(days=days)

    await reply_tracked_message(
        update,
        context,
        f"✅ У пользователя {target_telegram_id} списано {days} дн. премиума.",
    )


async def clear_bot_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда администратора чата: удалить сообщения бота из текущего чата."""
    chat = update.effective_chat
    user = update.effective_user

    member = await context.bot.get_chat_member(chat.id, user.id)
    if member.status not in ("administrator", "creator"):
        await reply_tracked_message(update, context, "Эта команда доступна только администраторам чата.")
        return

    with get_session() as session:
        messages = list_bot_messages(session, chat.id)

    deleted = 0
    for item in messages:
        try:
            await context.bot.delete_message(chat.id, item.message_id)
            deleted += 1
        except Exception:
            pass

    with get_session() as session:
        delete_tracked_bot_messages(session, chat.id)

    await reply_tracked_message(update, context, f"🧹 Удалено сообщений бота: {deleted}")


async def track_bot_added(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отслеживание добавления бота в новый чат и уведомление владельца."""
    chat_member_update = update.my_chat_member
    if not chat_member_update:
        return

    new_status = chat_member_update.new_chat_member.status
    old_status = chat_member_update.old_chat_member.status
    chat = chat_member_update.chat

    if old_status in ("left", "kicked") and new_status in ("member", "administrator"):
        try:
            members_count = await context.bot.get_chat_member_count(chat.id)
        except Exception:
            members_count = None

        with get_session() as session:
            upsert_chat_info(
                session=session,
                chat_id=chat.id,
                title=chat.title,
                chat_type=chat.type,
                members_count=members_count,
                added_by_user_id=chat_member_update.from_user.id if chat_member_update.from_user else None,
            )

        text = (
            "📥 Бот добавлен в новый чат\n\n"
            f"Название: {chat.title or 'Без названия'}\n"
            f"ID: {chat.id}\n"
            f"Тип: {chat.type}\n"
            f"Участников: {members_count or 'неизвестно'}"
        )
        try:
            await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=text)
        except Exception:
            pass


def register(application) -> None:
    application.add_handler(CommandHandler("p_up", p_up))
    application.add_handler(CommandHandler("p_dn", p_dn))
    application.add_handler(CommandHandler("clear_bot_messages", clear_bot_messages))
    application.add_handler(ChatMemberHandler(track_bot_added, ChatMemberHandler.MY_CHAT_MEMBER))
