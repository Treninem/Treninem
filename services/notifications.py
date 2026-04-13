"""Уведомления, напоминания и удаление сообщений."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from telegram import Bot

logger = logging.getLogger("bot_pubg.notifications")


async def delete_message_job(context) -> None:
    """Удалить сообщение по расписанию JobQueue."""
    data = context.job.data or {}
    chat_id = data.get("chat_id")
    message_id = data.get("message_id")
    if not chat_id or not message_id:
        return

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as exc:  # pragma: no cover
        logger.debug("Не удалось удалить сообщение %s/%s: %s", chat_id, message_id, exc)


def schedule_message_deletion(job_queue, chat_id: int, message_id: int, delay_seconds: int) -> None:
    """Поставить задачу на удаление сообщения."""
    if not job_queue:
        return
    job_queue.run_once(
        delete_message_job,
        when=delay_seconds,
        data={"chat_id": chat_id, "message_id": message_id},
        name=f"delete:{chat_id}:{message_id}",
    )


async def send_simple_notification(bot: Bot, chat_id: int, text: str) -> None:
    """Отправить короткое уведомление."""
    await bot.send_message(chat_id=chat_id, text=text)


async def send_training_reminder_job(context) -> None:
    """Напоминание о тренировке за час."""
    data = context.job.data or {}
    chat_id = data.get("chat_id")
    title = data.get("title")
    training_at = data.get("training_at")
    mentor_name = data.get("mentor_name")

    if not chat_id:
        return

    text = (
        "⏰ Напоминание о тренировке\n\n"
        f"Тема: {title}\n"
        f"Время: {training_at}\n"
        f"Наставник: {mentor_name}"
    )
    await context.bot.send_message(chat_id=chat_id, text=text)


def schedule_training_reminder(job_queue, chat_id: int, title: str, training_at: datetime, mentor_name: str) -> None:
    """Поставить напоминание о тренировке за 1 час до начала."""
    if not job_queue:
        return

    remind_at = training_at - timedelta(hours=1)
    if remind_at <= datetime.utcnow():
        return

    job_queue.run_once(
        send_training_reminder_job,
        when=remind_at,
        data={
            "chat_id": chat_id,
            "title": title,
            "training_at": training_at.strftime("%Y-%m-%d %H:%M"),
            "mentor_name": mentor_name,
        },
        name=f"training_reminder:{chat_id}:{title}:{int(training_at.timestamp())}",
    )
