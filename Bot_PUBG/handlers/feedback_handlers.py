"""Раздел «Обратная связь»."""

from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from config.constants import (
    BACK_TO_MAIN,
    CANCEL_ACTION,
    FEEDBACK_QUESTION,
    FEEDBACK_REPORT,
    FEEDBACK_REVIEW,
    FEEDBACK_SUGGESTION,
    FEEDBACK_TYPES,
)
from config.credentials import OWNER_CHAT_ID
from database import get_session
from database.queries import create_feedback_ticket, get_user_by_telegram_id
from utils.helpers import reply_tracked_message

FB_SUBJECT, FB_TEXT, FB_SCREENSHOT = range(200, 203)


async def feedback_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    button_text = update.effective_message.text.strip()
    ticket_type = FEEDBACK_TYPES.get(button_text)
    context.user_data["feedback_type"] = ticket_type

    await reply_tracked_message(update, context, "Введи краткую тему обращения.")
    return FB_SUBJECT


async def feedback_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["feedback_subject"] = update.effective_message.text.strip()
    await reply_tracked_message(update, context, "Теперь подробно опиши обращение.")
    return FB_TEXT


async def feedback_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["feedback_text"] = update.effective_message.text.strip()

    if context.user_data.get("feedback_type") == "report":
        await reply_tracked_message(update, context, "Пришли скриншот одним сообщением или напиши /skip.")
        return FB_SCREENSHOT

    return await _save_feedback(update, context, screenshot_file_id=None)


async def feedback_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo = update.effective_message.photo[-1]
    return await _save_feedback(update, context, screenshot_file_id=photo.file_id)


async def skip_feedback_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _save_feedback(update, context, screenshot_file_id=None)


async def _save_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE, screenshot_file_id: str | None) -> int:
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user:
            await reply_tracked_message(update, context, "Сначала открой /start.")
            return ConversationHandler.END

        ticket = create_feedback_ticket(
            session=session,
            user_id=user.id,
            ticket_type=context.user_data["feedback_type"],
            subject=context.user_data["feedback_subject"],
            text=context.user_data["feedback_text"],
            screenshot_file_id=screenshot_file_id,
        )

    notify_text = (
        "📩 Новый тикет\n\n"
        f"Ticket #{ticket.id}\n"
        f"Тип: {ticket.ticket_type}\n"
        f"От: {update.effective_user.full_name} (@{update.effective_user.username or '—'})\n"
        f"Telegram ID: {update.effective_user.id}\n"
        f"Тема: {ticket.subject}\n\n"
        f"{ticket.text}"
    )
    try:
        await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=notify_text)
        if screenshot_file_id:
            await context.bot.send_photo(chat_id=OWNER_CHAT_ID, photo=screenshot_file_id, caption=f"Скриншот к тикету #{ticket.id}")
    except Exception:
        pass

    for key in ("feedback_type", "feedback_subject", "feedback_text"):
        context.user_data.pop(key, None)

    await reply_tracked_message(update, context, f"✅ Обращение отправлено. Номер тикета: #{ticket.id}")
    return ConversationHandler.END


async def feedback_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    for key in ("feedback_type", "feedback_subject", "feedback_text"):
        context.user_data.pop(key, None)
    await reply_tracked_message(update, context, "Обращение отменено.")
    return ConversationHandler.END


def register(application) -> None:
    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(f"^({FEEDBACK_REVIEW}|{FEEDBACK_REPORT}|{FEEDBACK_QUESTION}|{FEEDBACK_SUGGESTION})$"), feedback_entry)
        ],
        states={
            FB_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_subject)],
            FB_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_text)],
            FB_SCREENSHOT: [
                MessageHandler(filters.PHOTO, feedback_photo),
                CommandHandler("skip", skip_feedback_screenshot),
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex(f"^{CANCEL_ACTION}$"), feedback_cancel),
            MessageHandler(filters.Regex(f"^{BACK_TO_MAIN}$"), feedback_cancel),
        ],
    )
    application.add_handler(conv, group=7)
