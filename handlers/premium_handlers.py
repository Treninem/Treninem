"""Раздел «Премиум»."""

from __future__ import annotations

from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from config.constants import (
    PREMIUM_BUY,
    PREMIUM_EXCHANGE,
    PREMIUM_EXPIRES,
    PREMIUM_INFO,
    PREMIUM_PRIVILEGES,
    PREMIUM_EXCHANGE_DAYS_COST,
)
from config.credentials import OWNER_USERNAME
from database import get_session
from database.queries import get_user_by_telegram_id
from features.points_system.calculator import apply_points
from utils.helpers import format_dt, format_privileges, reply_tracked_message


async def premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "💎 О премиум-статусе\n\n"
        "Премиум даёт:\n"
        "• увеличенные лимиты\n"
        "• расширенную статистику\n"
        "• приоритетную поддержку"
    )
    await reply_tracked_message(update, context, text)


async def premium_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply_tracked_message(
        update,
        context,
        f"💳 Для оформления или продления премиум-статуса напишите @{OWNER_USERNAME}",
    )


async def premium_privileges(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user:
            await reply_tracked_message(update, context, "Сначала открой /start.")
            return
        text = (
            "🎁 Мои привилегии\n\n"
            f"Ранг: {user.bot_rank}\n"
            f"Привилегии ранга:\n{format_privileges(user.bot_rank)}\n\n"
            f"Премиум активен: {'Да' if user.premium_until and user.premium_until > datetime.utcnow() else 'Нет'}"
        )
    await reply_tracked_message(update, context, text)


async def premium_expires(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user:
            await reply_tracked_message(update, context, "Сначала открой /start.")
            return

        if user.premium_until and user.premium_until > datetime.utcnow():
            delta = user.premium_until - datetime.utcnow()
            text = (
                "⏱️ Срок действия премиума\n\n"
                f"Активен до: {format_dt(user.premium_until)}\n"
                f"Осталось: {delta.days} дн. {delta.seconds // 3600} ч."
            )
        else:
            text = "⏱️ Премиум сейчас не активен."
    await reply_tracked_message(update, context, text)


async def premium_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся.")
            return

        if user.bot_rank != "Легенда":
            await reply_tracked_message(update, context, "Обмен баллов на премиум доступен только для ранга «Легенда».")
            return

        if user.points < PREMIUM_EXCHANGE_DAYS_COST:
            await reply_tracked_message(
                update,
                context,
                f"Недостаточно баллов. Нужно минимум {PREMIUM_EXCHANGE_DAYS_COST}.",
            )
            return

        apply_points(
            session=session,
            user=user,
            amount=-PREMIUM_EXCHANGE_DAYS_COST,
            reason="Обмен баллов на премиум",
            meta={"premium_days": 1},
        )
        base = user.premium_until if user.premium_until and user.premium_until > datetime.utcnow() else datetime.utcnow()
        user.premium_until = base + timedelta(days=1)

    await reply_tracked_message(update, context, "✅ Обмен выполнен: +1 день премиума.")


def register(application) -> None:
    application.add_handler(MessageHandler(filters.Regex(f"^{PREMIUM_INFO}$"), premium_info), group=4)
    application.add_handler(MessageHandler(filters.Regex(f"^{PREMIUM_BUY}$"), premium_buy), group=4)
    application.add_handler(MessageHandler(filters.Regex(f"^{PREMIUM_PRIVILEGES}$"), premium_privileges), group=4)
    application.add_handler(MessageHandler(filters.Regex(f"^{PREMIUM_EXPIRES}$"), premium_expires), group=4)
    application.add_handler(MessageHandler(filters.Regex(f"^{PREMIUM_EXCHANGE}$"), premium_exchange), group=4)
