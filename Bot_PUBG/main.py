"""Точка входа в проект Bot_PUBG."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pytz
from sqlalchemy import select
from telegram import BotCommand, Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, Defaults

from config.constants import PENALTY_INACTIVITY
from config.credentials import BOT_TOKEN
from config.settings import BOT_TIMEZONE, INACTIVITY_CHECK_HOURS, INACTIVITY_DAYS_LIMIT
from database import get_session, init_db
from database.models import PointTransaction, User
from features.daily_tests import reminders as daily_test_reminders
from features.points_system.calculator import apply_points
from handlers import (
    admin_handlers,
    base_handlers,
    feedback_handlers,
    friends_handlers,
    groups_handlers,
    mentorship_handlers,
    news_handlers,
    premium_handlers,
    profile_handlers,
)
from services.monitoring import setup_logging
from utils.helpers import send_tracked_message

logger = logging.getLogger("bot_pubg.main")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок."""
    logger.exception("Ошибка при обработке обновления: %s", context.error)
    if isinstance(update, Update) and update.effective_chat:
        try:
            await send_tracked_message(
                context,
                chat_id=update.effective_chat.id,
                text="⚠️ Произошла внутренняя ошибка. Попробуй ещё раз позже.",
            )
        except Exception:
            pass


async def inactivity_penalty_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ежедневная проверка неактивности.

    Логика:
    - если пользователь не проявлял активность >= 7 дней
    - и текущая длина неактивности кратна 7 дням
    - и за сегодня ещё не было списания по этой причине
    то списываем -10 баллов.
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    with get_session() as session:
        users = list(session.execute(select(User).where(User.is_registered.is_(True))).scalars())
        for user in users:
            days_inactive = (datetime.utcnow() - (user.last_activity or user.created_at)).days
            if days_inactive < INACTIVITY_DAYS_LIMIT:
                continue
            if days_inactive % INACTIVITY_DAYS_LIMIT != 0:
                continue

            already_today = session.execute(
                select(PointTransaction).where(
                    PointTransaction.user_id == user.id,
                    PointTransaction.reason == "Неактивность",
                    PointTransaction.created_at >= today_start,
                )
            ).scalar_one_or_none()

            if already_today:
                continue

            apply_points(
                session=session,
                user=user,
                amount=PENALTY_INACTIVITY,
                reason="Неактивность",
                meta={"days_inactive": days_inactive},
            )
            try:
                await context.bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "⚠️ Зафиксирована неактивность 7+ дней.\n"
                        f"Списано {abs(PENALTY_INACTIVITY)} баллов."
                    ),
                )
            except Exception:
                pass


async def post_init(application: Application) -> None:
    """Действия после инициализации приложения."""
    await application.bot.set_my_commands(
        [
            BotCommand("start", "Запустить бота"),
            BotCommand("help", "Помощь"),
            BotCommand("menu", "Открыть меню"),
            BotCommand("binding", "Показать привязку Telegram ↔ PUBG"),
            BotCommand("sync_profile", "Обновить PUBG-данные из API"),
            BotCommand("profilecard", "Красивая карточка игрока"),
            BotCommand("invite", "Получить ссылку приглашения"),
            BotCommand("promo", "Готовые тексты для приглашения"),
        ]
    )

    # Восстановить ежедневные тесты для всех зарегистрированных пользователей.
    daily_test_reminders.bootstrap_daily_test_jobs(application)

    # Поставить периодическую проверку неактивности.
    application.job_queue.run_repeating(
        inactivity_penalty_job,
        interval=timedelta(hours=INACTIVITY_CHECK_HOURS),
        first=30,
        name="inactivity_penalty_job",
    )

    logger.info("Post-init завершён: команды, тесты и фоновая проверка запущены.")


def build_application() -> Application:
    """Собрать Telegram Application."""
    defaults = Defaults(tzinfo=pytz.timezone(BOT_TIMEZONE))

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .defaults(defaults)
        .post_init(post_init)
        .build()
    )

    # Регистрация обработчиков.
    base_handlers.register(application)
    admin_handlers.register(application)
    profile_handlers.register(application)
    mentorship_handlers.register(application)
    news_handlers.register(application)
    premium_handlers.register(application)
    friends_handlers.register(application)
    groups_handlers.register(application)
    feedback_handlers.register(application)

    # Регистрация callback-логики ежедневных тестов.
    daily_test_reminders.register(application)

    application.add_error_handler(error_handler)
    return application


def main() -> None:
    """Точка запуска из консоли."""
    setup_logging()
    logger.info("Запуск Bot_PUBG...")
    init_db()
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
