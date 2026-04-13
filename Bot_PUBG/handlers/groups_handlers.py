"""Раздел «Группы с ботом»."""

from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes, MessageHandler, filters

from config.constants import GROUPS_INFO, GROUPS_LEAVE, GROUPS_LIST
from database import get_session
from database.queries import list_chats
from utils.helpers import format_dt, reply_tracked_message
from utils.keyboards import groups_leave_list_keyboard


async def groups_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        chats = list_chats(session)

    if not chats:
        await reply_tracked_message(update, context, "Бот пока не добавлен ни в один чат.")
        return

    lines = ["🌐 Чаты с ботом\n"]
    for idx, chat in enumerate(chats[:10], start=1):
        lines.append(
            f"{idx}. {chat.title or 'Без названия'}\n"
            f"ID: {chat.chat_id} | Тип: {chat.chat_type or '—'} | Участников: {chat.members_count or '—'} | Добавлен: {format_dt(chat.added_at)}\n"
        )

    await reply_tracked_message(
        update,
        context,
        "\n".join(lines),
        reply_markup=groups_leave_list_keyboard(chats),
    )


async def groups_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        chats = list_chats(session)

    if not chats:
        await reply_tracked_message(update, context, "Информация о чатах пока отсутствует.")
        return

    lines = ["ℹ️ Информация о чатах\n"]
    for chat in chats[:20]:
        lines.append(
            f"• {chat.title or 'Без названия'} | ID: {chat.chat_id} | Участников: {chat.members_count or '—'} | Добавлен: {format_dt(chat.added_at)}"
        )
    await reply_tracked_message(update, context, "\n".join(lines))


async def groups_leave_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply_tracked_message(
        update,
        context,
        "Открой «Список чатов» и нажми кнопку выхода под нужным чатом. Бот проверит, что ты администратор этого чата.",
    )


async def group_leave_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    chat_id = int(query.data.split(":")[1])

    try:
        member = await context.bot.get_chat_member(chat_id, query.from_user.id)
    except Exception:
        await query.edit_message_text("Не удалось проверить права в чате.")
        return

    if member.status not in ("administrator", "creator"):
        await query.edit_message_text("Только администратор этого чата может удалить из него бота.")
        return

    try:
        await context.bot.leave_chat(chat_id)
    except Exception as exc:
        await query.edit_message_text(f"Не удалось выйти из чата: {exc}")
        return

    await query.edit_message_text("✅ Бот вышел из чата.")


def register(application) -> None:
    application.add_handler(MessageHandler(filters.Regex(f"^{GROUPS_LIST}$"), groups_list), group=6)
    application.add_handler(MessageHandler(filters.Regex(f"^{GROUPS_INFO}$"), groups_info), group=6)
    application.add_handler(MessageHandler(filters.Regex(f"^{GROUPS_LEAVE}$"), groups_leave_info), group=6)
    application.add_handler(CallbackQueryHandler(group_leave_callback, pattern=r"^group_leave:-?\d+$"), group=6)
