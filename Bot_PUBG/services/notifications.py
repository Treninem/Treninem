"""Отправка уведомлений и напоминаний."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from telegram import Bot
from telegram.ext import Application

from database.queries import get_user_by_telegram_id, list_active_chats
from features.daily_tests.test_generator import generate_daily_test_for_user

logger = logging.getLogger(__name__)


async def send_daily_test(context) -> None:
    """Ежедневная отправка тестов всем зарегистрированным пользователям.
    В этой реализации отправка происходит только для пользователей,
    которым уже взаимодействовали с ботом и имеют запись в БД.
    """
    from database.queries import get_session
    from database.models import User

    with get_session() as session:
        users = session.query(User).filter(User.is_registered == True).all()
        for user in users:
            questions = generate_daily_test_for_user(user.telegram_id)
            lines = ["🧠 Ваш ежедневный тест PUBG:"]
            for idx, q in enumerate(questions, start=1):
                lines.append(f"\n{idx}. {q['question']}")
                for option_idx, opt in enumerate(q['options'], start=1):
                    lines.append(f"   {option_idx}) {opt}")
            try:
                await context.bot.send_message(chat_id=user.telegram_id, text="\n".join(lines))
            except Exception as exc:
                logger.warning("Не удалось отправить тест пользователю %s: %s", user.telegram_id, exc)


async def send_test_reminders(context) -> None:
    from database.queries import get_session
    from database.models import User

    with get_session() as session:
        users = session.query(User).filter(User.is_registered == True).all()
        for user in users:
            try:
                await context.bot.send_message(chat_id=user.telegram_id, text="⏰ Напоминание: через 15 минут придет ваш ежедневный тест PUBG.")
            except Exception as exc:
                logger.warning("Не удалось отправить напоминание пользователю %s: %s", user.telegram_id, exc)


async def notify_admin(bot: Bot, text: str, admin_chat_id: int) -> None:
    try:
        await bot.send_message(chat_id=admin_chat_id, text=text)
    except Exception as exc:
        logger.warning("Не удалось отправить сообщение администратору: %s", exc)


async def notify_chat_added(bot: Bot, title: str, chat_id: int, admin_chat_id: int) -> None:
    await notify_admin(bot, f"✅ Бот добавлен в новый чат:\nНазвание: {title}\nID: {chat_id}", admin_chat_id)
