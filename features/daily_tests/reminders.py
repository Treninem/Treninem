"""Планирование напоминаний о тестах."""
from __future__ import annotations

from datetime import time

from config.settings import DAILY_TEST_HOUR, DAILY_TEST_MINUTE, REMINDER_MINUTES_BEFORE_TEST
from services.notifications import send_daily_test, send_test_reminders


def setup_daily_test_jobs(application) -> None:
    """Регистрирует ежедневные задачи в JobQueue python-telegram-bot."""
    job_queue = application.job_queue
    if not job_queue:
        return

    # Отправка самого теста.
    job_queue.run_daily(
        send_daily_test,
        time=time(hour=DAILY_TEST_HOUR, minute=DAILY_TEST_MINUTE, second=0),
        name="daily_test_job",
    )

    reminder_minute = DAILY_TEST_MINUTE - REMINDER_MINUTES_BEFORE_TEST
    reminder_hour = DAILY_TEST_HOUR
    if reminder_minute < 0:
        reminder_hour = (reminder_hour - 1) % 24
        reminder_minute += 60

    # Напоминание за 15 минут.
    job_queue.run_daily(
        send_test_reminders,
        time=time(hour=reminder_hour, minute=reminder_minute, second=0),
        name="daily_test_reminder_job",
    )
