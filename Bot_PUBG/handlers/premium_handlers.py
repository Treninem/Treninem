"""Обработчики раздела «Премиум»."""
from __future__ import annotations

from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from config.credentials import OWNER_USERNAME
from database.queries import get_user_by_telegram_id
from utils.helpers import premium_privileges_text


async def premium_about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("💎 Премиум-статус дает:\n" + premium_privileges_text())


async def premium_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"💳 Для оформления премиум-статуса напишите {OWNER_USERNAME}")


async def premium_privileges(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text("Пользователь не найден.")
        return
    if user.is_premium:
        await update.message.reply_text("🎁 Ваши активные привилегии:\n" + premium_privileges_text())
    else:
        await update.message.reply_text("У вас пока нет активного премиум-статуса.")


async def premium_expiry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user or not user.premium_until:
        await update.message.reply_text("Премиум не активирован.")
        return
    remaining = user.premium_until - datetime.utcnow()
    await update.message.reply_text(f"⏱️ До окончания премиума осталось: {remaining}")


def register(application) -> None:
    application.add_handler(MessageHandler(filters.Regex(r"^💎 О премиум-статусе$"), premium_about))
    application.add_handler(MessageHandler(filters.Regex(r"^💳 Оформить/продлить$"), premium_buy))
    application.add_handler(MessageHandler(filters.Regex(r"^🎁 Мои привилегии$"), premium_privileges))
    application.add_handler(MessageHandler(filters.Regex(r"^⏱️ Срок действия$"), premium_expiry))
