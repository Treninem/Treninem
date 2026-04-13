"""Обработчики раздела «Обратная связь»."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from config.credentials import DEFAULT_ADMIN_CHAT_ID
from config.settings import TICKET_PREFIX
from database.queries import create_ticket
from services.notifications import notify_admin

FEEDBACK_TEXT, COMPLAINT_TEXT, QUESTION_TEXT, SUGGESTION_TEXT = range(4)


async def feedback_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Напишите ваш отзыв одним сообщением:")
    context.user_data["ticket_type"] = "отзыв"
    return FEEDBACK_TEXT


async def complaint_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Опишите жалобу одним сообщением. При необходимости после этого можно отправить скриншот отдельно.")
    context.user_data["ticket_type"] = "жалоба"
    return COMPLAINT_TEXT


async def question_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите ваш вопрос:")
    context.user_data["ticket_type"] = "вопрос"
    return QUESTION_TEXT


async def suggestion_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите ваше предложение по улучшению:")
    context.user_data["ticket_type"] = "предложение"
    return SUGGESTION_TEXT


async def save_ticket_common(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ticket_type = context.user_data.get("ticket_type", "обращение")
    subject = f"{ticket_type.title()} от пользователя {update.effective_user.id}"
    ticket = create_ticket(update.effective_user.id, ticket_type, subject, update.message.text)
    if not ticket:
        await update.message.reply_text("Сначала зарегистрируйтесь в боте.")
        return ConversationHandler.END
    ticket_code = f"{TICKET_PREFIX}-{ticket.id:06d}"
    await update.message.reply_text(f"✅ Обращение принято. Номер тикета: {ticket_code}")
    await notify_admin(context.bot, f"Новое обращение {ticket_code}\nТип: {ticket_type}\nОт: {update.effective_user.mention_html()}\n\n{update.message.text}", DEFAULT_ADMIN_CHAT_ID)
    context.user_data.pop("ticket_type", None)
    return ConversationHandler.END


def register(application) -> None:
    application.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^📝 Оставить отзыв$"), feedback_start)],
        states={FEEDBACK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_ticket_common)]},
        fallbacks=[],
    ))
    application.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^⚠️ Пожаловаться$"), complaint_start)],
        states={COMPLAINT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_ticket_common)]},
        fallbacks=[],
    ))
    application.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^❓ Задать вопрос$"), question_start)],
        states={QUESTION_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_ticket_common)]},
        fallbacks=[],
    ))
    application.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^📢 Предложения$"), suggestion_start)],
        states={SUGGESTION_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_ticket_common)]},
        fallbacks=[],
    ))
