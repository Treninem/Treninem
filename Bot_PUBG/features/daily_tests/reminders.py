"""Планирование и проведение ежедневных тестов."""

from __future__ import annotations

import logging
from datetime import datetime, time as dtime

import pytz
from sqlalchemy import select
from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from config.settings import DAILY_TEST_HOUR, DAILY_TEST_MINUTE, DAILY_TEST_REMINDER_MINUTES, DAILY_TEST_REMINDER_TTL_SECONDS, DAILY_TEST_RESULT_TTL_SECONDS
from database import get_session
from database.models import User
from database.queries import (
    create_daily_test_session,
    get_all_registered_users,
    get_daily_test_session,
    get_user_by_telegram_id,
    save_test_answers,
)
from features.daily_tests.results_processor import evaluate_test
from features.daily_tests.test_generator import generate_daily_test
from features.points_system.calculator import apply_points
from services.notifications import schedule_message_deletion
from utils.helpers import loads_json, send_tracked_message
from utils.keyboards import test_question_keyboard

logger = logging.getLogger("bot_pubg.daily_tests")


async def send_test_question(context: ContextTypes.DEFAULT_TYPE, chat_id: int, session_id: int, q_index: int) -> None:
    """Отправить пользователю конкретный вопрос теста."""
    with get_session() as session:
        test_session = get_daily_test_session(session, session_id)
        if not test_session:
            return
        payload = loads_json(test_session.test_payload_json, default=[])

    if q_index >= len(payload):
        return

    question = payload[q_index]
    text = (
        f"📝 Ежедневный тест\n\n"
        f"Вопрос {q_index + 1} из {len(payload)}\n"
        f"Тема: {question['topic']}\n\n"
        f"{question['question']}"
    )
    await send_tracked_message(
        context,
        chat_id=chat_id,
        text=text,
        keep=True,
        reply_markup=test_question_keyboard(session_id, q_index, question["options"]),
    )


async def daily_test_reminder_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Напоминание о скорой отправке теста."""
    data = context.job.data or {}
    chat_id = data.get("chat_id")
    if not chat_id:
        return
    await send_tracked_message(
        context,
        chat_id=chat_id,
        text="⏰ Через 15 минут придёт твой ежедневный тест PUBG.",
        ttl_seconds=DAILY_TEST_REMINDER_TTL_SECONDS,
    )


async def daily_test_delivery_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Создать и отправить пользователю новый ежедневный тест."""
    data = context.job.data or {}
    chat_id = data.get("chat_id")
    user_id = data.get("telegram_id")
    if not chat_id or not user_id:
        return

    with get_session() as session:
        user = get_user_by_telegram_id(session, user_id)
        if not user or not user.is_registered:
            return

        day_seed = int(datetime.utcnow().strftime("%d%m%Y"))
        test_payload = generate_daily_test(seed_value=user.telegram_id + day_seed)
        test_session = create_daily_test_session(
            session=session,
            user_id=user.id,
            scheduled_for=datetime.utcnow(),
            test_payload=test_payload,
        )
        session_id = test_session.id

    await send_test_question(context, chat_id=chat_id, session_id=session_id, q_index=0)


def _build_times(user_timezone: str):
    tz = pytz.timezone(user_timezone or "Europe/Moscow")
    total_test_minutes = DAILY_TEST_HOUR * 60 + DAILY_TEST_MINUTE
    reminder_total = max(0, total_test_minutes - DAILY_TEST_REMINDER_MINUTES)

    reminder_hour = reminder_total // 60
    reminder_minute = reminder_total % 60

    reminder_time = dtime(hour=reminder_hour, minute=reminder_minute, tzinfo=tz)
    test_time = dtime(hour=DAILY_TEST_HOUR, minute=DAILY_TEST_MINUTE, tzinfo=tz)
    return reminder_time, test_time


def schedule_user_daily_jobs(application, user) -> None:
    """Создать 2 ежедневные задачи на пользователя:
    1. Напоминание за 15 минут.
    2. Сам тест в 10:00 локального времени пользователя.
    """
    reminder_time, test_time = _build_times(user.timezone or "Europe/Moscow")

    # Удаляем старые задачи, чтобы не копились дубликаты после повторной регистрации/редактирования.
    for name in [f"daily_test_reminder:{user.telegram_id}", f"daily_test_delivery:{user.telegram_id}"]:
        for job in application.job_queue.get_jobs_by_name(name):
            job.schedule_removal()

    application.job_queue.run_daily(
        daily_test_reminder_job,
        time=reminder_time,
        data={"chat_id": user.telegram_id, "telegram_id": user.telegram_id},
        name=f"daily_test_reminder:{user.telegram_id}",
    )
    application.job_queue.run_daily(
        daily_test_delivery_job,
        time=test_time,
        data={"chat_id": user.telegram_id, "telegram_id": user.telegram_id},
        name=f"daily_test_delivery:{user.telegram_id}",
    )


def bootstrap_daily_test_jobs(application) -> None:
    """Восстановить ежедневные задачи для всех зарегистрированных пользователей."""
    with get_session() as session:
        users = get_all_registered_users(session)
        for user in users:
            schedule_user_daily_jobs(application, user)


async def handle_test_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатия на вариант ответа."""
    query = update.callback_query
    await query.answer()

    _, session_id_str, q_index_str, selected_idx_str = query.data.split(":")
    session_id = int(session_id_str)
    q_index = int(q_index_str)
    selected_idx = int(selected_idx_str)

    with get_session() as session:
        test_session = get_daily_test_session(session, session_id)
        if not test_session:
            await query.edit_message_text("Сессия теста не найдена.")
            return

        payload = loads_json(test_session.test_payload_json, default=[])
        answers = loads_json(test_session.answers_json, default=[])

        while len(answers) <= q_index:
            answers.append(-1)
        answers[q_index] = selected_idx

        if q_index + 1 < len(payload):
            save_test_answers(session, test_session, answers=answers)
            next_question = payload[q_index + 1]
            await query.edit_message_text(
                text=(
                    f"✅ Ответ сохранён.\n\n"
                    f"Вопрос {q_index + 2} из {len(payload)}\n"
                    f"Тема: {next_question['topic']}\n\n"
                    f"{next_question['question']}"
                ),
                reply_markup=test_question_keyboard(session_id, q_index + 1, next_question["options"]),
            )
            return

        result = evaluate_test(payload, answers)
        user = session.execute(select(User).where(User.id == test_session.user_id)).scalar_one()
        if result["score"] > 0:
            apply_points(
                session=session,
                user=user,
                amount=result["score"],
                reason="Ежедневный тест PUBG",
                meta={"daily_test_session_id": test_session.id},
            )

        save_test_answers(
            session,
            test_session,
            answers=answers,
            score=result["score"],
            bonus_correct=result["bonus_correct"],
            completed=True,
        )

    recommendations = "\n".join(f"• {item}" for item in result["recommendations"])
    await query.edit_message_text(
        text=(
            "🏁 Тест завершён!\n\n"
            f"Правильных основных ответов: {result['correct_regular']} / 5\n"
            f"Бонусный вопрос: {'✅' if result['bonus_correct'] else '❌'}\n"
            f"Начислено баллов: {result['score']}\n\n"
            f"Рекомендации:\n{recommendations}"
        )
    )
    if DAILY_TEST_RESULT_TTL_SECONDS > 0:
        schedule_message_deletion(
            context.job_queue,
            query.message.chat_id,
            query.message.message_id,
            DAILY_TEST_RESULT_TTL_SECONDS,
        )


def register(application) -> None:
    application.add_handler(CallbackQueryHandler(handle_test_answer, pattern=r"^test:\d+:\d+:\d+$"), group=20)
