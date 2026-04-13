"""Обработчики раздела «Группы с ботом»."""
from __future__ import annotations

from telegram import ChatMemberUpdated, Update
from telegram.constants import ChatMemberStatus
from telegram.ext import ChatMemberHandler, ContextTypes, MessageHandler, filters

from config.credentials import DEFAULT_ADMIN_CHAT_ID
from database.queries import deactivate_chat, list_active_chats, upsert_chat
from services.notifications import notify_chat_added


async def my_chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_member_update: ChatMemberUpdated = update.my_chat_member
    chat = chat_member_update.chat
    new_status = chat_member_update.new_chat_member.status
    old_status = chat_member_update.old_chat_member.status

    if new_status in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR} and old_status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:
        members_count = 0
        try:
            members_count = await context.bot.get_chat_member_count(chat.id)
        except Exception:
            pass
        upsert_chat(chat.id, chat.title, chat.type, members_count, update.effective_user.id if update.effective_user else None)
        await notify_chat_added(context.bot, chat.title or str(chat.id), chat.id, DEFAULT_ADMIN_CHAT_ID)
    elif new_status in {ChatMemberStatus.LEFT, ChatMemberStatus.KICKED}:
        deactivate_chat(chat.id)


async def list_chats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chats = list_active_chats()
    if not chats:
        await update.message.reply_text("Бот пока не добавлен ни в один активный чат.")
        return
    text = "🌐 Список чатов с ботом:\n\n" + "\n".join(f"• {c.title or 'Без названия'} | ID: {c.chat_id}" for c in chats)
    await update.message.reply_text(text)


async def chat_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chats = list_active_chats()
    if not chats:
        await update.message.reply_text("Нет активных чатов.")
        return
    text = "ℹ️ Информация о чатах:\n\n" + "\n\n".join(
        f"Название: {c.title or 'Без названия'}\nID: {c.chat_id}\nУчастников: {c.members_count}\nДобавлен: {c.created_at:%Y-%m-%d %H:%M}"
        for c in chats
    )
    await update.message.reply_text(text)


async def leave_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    member = await chat.get_member(update.effective_user.id)
    if member.status not in {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}:
        await update.message.reply_text("Выйти из чата через бота может только администратор этого чата.")
        return
    if chat.type == "private":
        await update.message.reply_text("Эта команда работает только внутри группы/супергруппы.")
        return
    await update.message.reply_text("Бот покидает чат.")
    await context.bot.leave_chat(chat.id)


def register(application) -> None:
    application.add_handler(ChatMemberHandler(my_chat_member_handler, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.Regex(r"^📋 Список чатов$"), list_chats_handler))
    application.add_handler(MessageHandler(filters.Regex(r"^ℹ️ Информация о чате$"), chat_info_handler))
    application.add_handler(MessageHandler(filters.Regex(r"^🚪 Выйти из чата$"), leave_chat_handler))
