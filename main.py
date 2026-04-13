"""Точка входа в приложение.

Что делает этот файл:
1. Настраивает логирование.
2. Создает таблицы в базе данных.
3. Инициализирует Telegram Application.
4. Регистрирует все обработчики.
5. Регистрирует ежедневные задачи и напоминания.
6. Запускает long polling.
"""
from __future__ import annotations

import logging

from telegram.ext import Application

from config.credentials import TELEGRAM_BOT_TOKEN
from config.settings import ALLOWED_UPDATES, DROP_PENDING_UPDATES
from database.models import init_db
from features.daily_tests.reminders import setup_daily_test_jobs
from handlers import register_all_handlers
from services.monitoring import setup_logging


def build_application() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    register_all_handlers(app)
    setup_daily_test_jobs(app)
    return app


def main() -> None:
    setup_logging()
    init_db()
    app = build_application()
    logging.getLogger(__name__).info("Бот запускается...")
    app.run_polling(drop_pending_updates=DROP_PENDING_UPDATES, allowed_updates=ALLOWED_UPDATES)


if __name__ == "__main__":
    main()
