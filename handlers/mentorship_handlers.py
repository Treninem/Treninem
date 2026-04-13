"""Раздел «Наставничество»."""

from __future__ import annotations

from datetime import datetime

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from sqlalchemy import select

from config.constants import (
    BACK_TO_MAIN,
    CANCEL_ACTION,
    MENTOR_APPLY,
    MENTOR_CREATE_TASK,
    MENTOR_CREATE_TRAINING,
    MENTOR_SEARCH,
    MENTOR_STUDENTS,
    MENTOR_TASKS,
    MENTOR_TRAININGS,
    POINTS_TASK_COMPLETED,
)
from database import get_session
from database.models import MentorTask, Training, User
from database.queries import (
    assign_student_to_mentor,
    get_mentor_profile,
    get_or_create_user,
    get_user_by_telegram_id,
    list_active_mentors,
    list_mentor_students,
    list_user_tasks,
    list_user_trainings,
    upsert_mentor_profile,
)
from features.mentorship.mentor_validator import can_be_mentor, mentor_can_teach_student
from features.mentorship.task_manager import complete_task_and_reward, create_task_for_student
from features.mentorship.training_scheduler import create_training_and_schedule
from services.notifications import schedule_training_reminder
from utils.helpers import format_dt, get_user_display_name, reply_tracked_message
from utils.keyboards import mentor_assign_keyboard, mentor_assign_list_keyboard, task_complete_keyboard
from utils.validators import parse_datetime_string

APPLY_SPEC, APPLY_SCHEDULE, APPLY_STYLE = range(20, 23)
TRAIN_TITLE, TRAIN_DIFFICULTY, TRAIN_DATETIME, TRAIN_DESC = range(30, 34)
TASK_STUDENT_ID, TASK_TITLE, TASK_DESC, TASK_DUE = range(40, 44)


async def mentor_apply_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся в разделе профиля.")
            return ConversationHandler.END

        if not can_be_mentor(user.pubg_rank):
            await reply_tracked_message(
                update,
                context,
                f"Твой текущий PUBG ранг ({user.pubg_rank or 'неизвестен'}) пока не подходит для наставника. Нужен ранг уровня «Корона» и выше.",
            )
            return ConversationHandler.END

    await reply_tracked_message(update, context, "Укажи свою специализацию как наставника.")
    return APPLY_SPEC


async def mentor_apply_spec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["mentor_specialization"] = update.effective_message.text.strip()
    await reply_tracked_message(update, context, "Опиши удобное расписание. Пример: Пн-Пт 19:00-22:00")
    return APPLY_SCHEDULE


async def mentor_apply_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["mentor_schedule"] = update.effective_message.text.strip()
    await reply_tracked_message(update, context, "Опиши свой стиль обучения.")
    return APPLY_STYLE


async def mentor_apply_style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    style = update.effective_message.text.strip()
    specialization = context.user_data.get("mentor_specialization")
    schedule_text = context.user_data.get("mentor_schedule")

    with get_session() as session:
        user = get_or_create_user(session, update.effective_user)
        upsert_mentor_profile(session, user, specialization=specialization, schedule_text=schedule_text, teaching_style=style)

    context.user_data.pop("mentor_specialization", None)
    context.user_data.pop("mentor_schedule", None)

    await reply_tracked_message(update, context, "✅ Статус наставника активирован.")
    return ConversationHandler.END


async def mentor_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        student = get_user_by_telegram_id(session, update.effective_user.id)
        if not student or not student.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся.")
            return
        mentors = list_active_mentors(session)

    if not mentors:
        await reply_tracked_message(update, context, "Сейчас активных наставников нет.")
        return

    lines = ["👨‍🏫 Доступные наставники\n"]
    mentor_ids: list[int] = []
    for idx, (mentor_user, profile) in enumerate(mentors[:10], start=1):
        mentor_ids.append(mentor_user.id)
        lines.append(
            f"#{idx} {mentor_user.pubg_name or mentor_user.first_name}\n"
            f"PUBG ранг: {mentor_user.pubg_rank or '—'}\n"
            f"Специализация: {profile.specialization}\n"
            f"Стиль: {profile.teaching_style}\n"
            f"Свободные места: {profile.free_slots}\n"
        )

    await reply_tracked_message(
        update,
        context,
        "\n".join(lines),
        reply_markup=mentor_assign_list_keyboard(mentor_ids),
    )


async def mentor_assign_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    mentor_user_id = int(query.data.split(":")[1])

    with get_session() as session:
        student = get_user_by_telegram_id(session, query.from_user.id)
        mentor = session.execute(select(User).where(User.id == mentor_user_id)).scalar_one_or_none()
        if not student or not student.is_registered:
            await query.edit_message_text("Сначала зарегистрируйся в боте.")
            return
        if not mentor:
            await query.edit_message_text("Наставник не найден.")
            return
        if not mentor_can_teach_student(mentor.pubg_rank, student.pubg_rank):
            await query.edit_message_text("Этот наставник может обучать только игроков с более низким рангом.")
            return

        assign_student_to_mentor(session, mentor_user_id=mentor.id, student_user_id=student.id)
        profile = get_mentor_profile(session, mentor.id)
        if profile and profile.free_slots > 0:
            profile.free_slots -= 1

    await query.edit_message_text("✅ Наставник закреплён за тобой.")


async def mentor_students(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        mentor = get_user_by_telegram_id(session, update.effective_user.id)
        if not mentor or not mentor.is_mentor:
            await reply_tracked_message(update, context, "Раздел доступен только наставникам.")
            return
        students = list_mentor_students(session, mentor.id)

    if not students:
        await reply_tracked_message(update, context, "У тебя пока нет подопечных.")
        return

    lines = ["👥 Мои подопечные\n"]
    for student in students:
        lines.append(
            f"• {get_user_display_name(student)} | PUBG: {student.pubg_rank or '—'} | Баллы: {student.points}"
        )
    lines.append("\nРекомендации можно отправлять обычным сообщением лично пользователю.")
    await reply_tracked_message(update, context, "\n".join(lines))


async def trainings_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся.")
            return
        trainings = list_user_trainings(session, user.id)

    if not trainings:
        await reply_tracked_message(update, context, "Тренировок пока нет.")
        return

    lines = ["🎯 Мои тренировки\n"]
    for item in trainings[:20]:
        lines.append(
            f"• #{item.id} | {item.title} | {format_dt(item.training_at)} | Сложность: {item.difficulty} | Статус: {item.status}"
        )
    await reply_tracked_message(update, context, "\n".join(lines))


async def create_training_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_mentor:
            await reply_tracked_message(update, context, "Создавать тренировки могут только наставники.")
            return ConversationHandler.END
    await reply_tracked_message(update, context, "Введи тему тренировки.")
    return TRAIN_TITLE


async def create_training_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["training_title"] = update.effective_message.text.strip()
    await reply_tracked_message(update, context, "Введи уровень сложности. Пример: beginner / intermediate / advanced")
    return TRAIN_DIFFICULTY


async def create_training_difficulty(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["training_difficulty"] = update.effective_message.text.strip()
    await reply_tracked_message(update, context, "Введи дату и время: YYYY-MM-DD HH:MM")
    return TRAIN_DATETIME


async def create_training_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dt = parse_datetime_string(update.effective_message.text or "")
    if not dt:
        await reply_tracked_message(update, context, "Неверный формат. Используй YYYY-MM-DD HH:MM")
        return TRAIN_DATETIME
    context.user_data["training_dt"] = dt
    await reply_tracked_message(update, context, "Теперь опиши тему / план тренировки.")
    return TRAIN_DESC


async def create_training_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    description = update.effective_message.text.strip()
    with get_session() as session:
        mentor = get_user_by_telegram_id(session, update.effective_user.id)
        training = create_training_and_schedule(
            session=session,
            job_queue=context.job_queue,
            mentor_user=mentor,
            title=context.user_data["training_title"],
            difficulty=context.user_data["training_difficulty"],
            description=description,
            training_at=context.user_data["training_dt"],
        )

    schedule_training_reminder(
        context.job_queue,
        chat_id=update.effective_user.id,
        title=training.title,
        training_at=training.training_at,
        mentor_name=mentor.pubg_name or mentor.first_name or "Наставник",
    )

    for key in ("training_title", "training_difficulty", "training_dt"):
        context.user_data.pop(key, None)

    await reply_tracked_message(
        update,
        context,
        f"✅ Тренировка создана.\nID: {training.id}\nТема: {training.title}\nДата: {format_dt(training.training_at)}",
    )
    return ConversationHandler.END


async def tasks_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся.")
            return
        tasks = list_user_tasks(session, user.id)

    if not tasks:
        await reply_tracked_message(update, context, "Активных заданий нет.")
        return

    for item in tasks[:10]:
        text = (
            f"📝 Задание #{item.id}\n"
            f"{item.title}\n\n"
            f"{item.description}\n\n"
            f"Срок: {format_dt(item.due_at)}\n"
            f"Награда: {item.reward_points} баллов\n"
            f"Статус: {item.status}"
        )
        markup = task_complete_keyboard(item.id) if item.status != "completed" else None
        await reply_tracked_message(update, context, text, reply_markup=markup, replace_screen=False)


async def task_complete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    task_id = int(query.data.split(":")[1])

    with get_session() as session:
        user = get_user_by_telegram_id(session, query.from_user.id)
        task = session.execute(select(MentorTask).where(MentorTask.id == task_id)).scalar_one_or_none()
        if not user or not task or task.student_user_id != user.id:
            await query.edit_message_text("Задание не найдено или доступ запрещён.")
            return
        complete_task_and_reward(session, task_id=task_id, user=user)

    await query.edit_message_text("✅ Задание отмечено выполненным, баллы начислены.")


async def create_task_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    with get_session() as session:
        mentor = get_user_by_telegram_id(session, update.effective_user.id)
        if not mentor or not mentor.is_mentor:
            await reply_tracked_message(update, context, "Создавать задания могут только наставники.")
            return ConversationHandler.END
    await reply_tracked_message(update, context, "Введи Telegram ID подопечного.")
    return TASK_STUDENT_ID


async def create_task_student(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        student_tg_id = int(update.effective_message.text.strip())
    except ValueError:
        await reply_tracked_message(update, context, "Нужно ввести числовой Telegram ID.")
        return TASK_STUDENT_ID

    with get_session() as session:
        mentor = get_user_by_telegram_id(session, update.effective_user.id)
        student = get_user_by_telegram_id(session, student_tg_id)
        if not student or not student.is_registered:
            await reply_tracked_message(update, context, "Подопечный не найден.")
            return TASK_STUDENT_ID
        if not mentor_can_teach_student(mentor.pubg_rank, student.pubg_rank):
            await reply_tracked_message(update, context, "Нельзя выдать задание игроку с равным или более высоким рангом.")
            return TASK_STUDENT_ID

    context.user_data["task_student_tg_id"] = student_tg_id
    await reply_tracked_message(update, context, "Введи название задания.")
    return TASK_TITLE


async def create_task_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["task_title"] = update.effective_message.text.strip()
    await reply_tracked_message(update, context, "Опиши задание.")
    return TASK_DESC


async def create_task_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["task_desc"] = update.effective_message.text.strip()
    await reply_tracked_message(update, context, "Введи срок в формате YYYY-MM-DD HH:MM или напиши 'нет'.")
    return TASK_DUE


async def create_task_due(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.effective_message.text.strip().lower()
    due_at = None if raw == "нет" else parse_datetime_string(raw)
    if raw != "нет" and not due_at:
        await reply_tracked_message(update, context, "Неверный формат. Используй YYYY-MM-DD HH:MM или 'нет'.")
        return TASK_DUE

    with get_session() as session:
        mentor = get_user_by_telegram_id(session, update.effective_user.id)
        student = get_user_by_telegram_id(session, context.user_data["task_student_tg_id"])
        task = create_task_for_student(
            session=session,
            mentor_user_id=mentor.id,
            student_user_id=student.id,
            title=context.user_data["task_title"],
            description=context.user_data["task_desc"],
            due_at=due_at,
            reward_points=POINTS_TASK_COMPLETED,
        )

    for key in ("task_student_tg_id", "task_title", "task_desc"):
        context.user_data.pop(key, None)

    await reply_tracked_message(update, context, f"✅ Задание #{task.id} создано.")
    return ConversationHandler.END


async def mentorship_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    for key in [
        "mentor_specialization",
        "mentor_schedule",
        "training_title",
        "training_difficulty",
        "training_dt",
        "task_student_tg_id",
        "task_title",
        "task_desc",
    ]:
        context.user_data.pop(key, None)
    await reply_tracked_message(update, context, "Действие отменено.")
    return ConversationHandler.END


def register(application) -> None:
    mentor_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{MENTOR_APPLY}$"), mentor_apply_entry)],
        states={
            APPLY_SPEC: [MessageHandler(filters.TEXT & ~filters.COMMAND, mentor_apply_spec)],
            APPLY_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, mentor_apply_schedule)],
            APPLY_STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, mentor_apply_style)],
        },
        fallbacks=[
            MessageHandler(filters.Regex(f"^{CANCEL_ACTION}$"), mentorship_cancel),
            MessageHandler(filters.Regex(f"^{BACK_TO_MAIN}$"), mentorship_cancel),
        ],
    )

    training_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{MENTOR_CREATE_TRAINING}$"), create_training_entry)],
        states={
            TRAIN_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_training_title)],
            TRAIN_DIFFICULTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_training_difficulty)],
            TRAIN_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_training_datetime)],
            TRAIN_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_training_desc)],
        },
        fallbacks=[
            MessageHandler(filters.Regex(f"^{CANCEL_ACTION}$"), mentorship_cancel),
            MessageHandler(filters.Regex(f"^{BACK_TO_MAIN}$"), mentorship_cancel),
        ],
    )

    task_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{MENTOR_CREATE_TASK}$"), create_task_entry)],
        states={
            TASK_STUDENT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_task_student)],
            TASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_task_title)],
            TASK_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_task_desc)],
            TASK_DUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_task_due)],
        },
        fallbacks=[
            MessageHandler(filters.Regex(f"^{CANCEL_ACTION}$"), mentorship_cancel),
            MessageHandler(filters.Regex(f"^{BACK_TO_MAIN}$"), mentorship_cancel),
        ],
    )

    application.add_handler(mentor_conv, group=2)
    application.add_handler(training_conv, group=2)
    application.add_handler(task_conv, group=2)
    application.add_handler(MessageHandler(filters.Regex(f"^{MENTOR_SEARCH}$"), mentor_search), group=2)
    application.add_handler(MessageHandler(filters.Regex(f"^{MENTOR_STUDENTS}$"), mentor_students), group=2)
    application.add_handler(MessageHandler(filters.Regex(f"^{MENTOR_TRAININGS}$"), trainings_list), group=2)
    application.add_handler(MessageHandler(filters.Regex(f"^{MENTOR_TASKS}$"), tasks_list), group=2)
    application.add_handler(CallbackQueryHandler(mentor_assign_callback, pattern=r"^mentor_assign:\d+$"), group=2)
    application.add_handler(CallbackQueryHandler(task_complete_callback, pattern=r"^task_complete:\d+$"), group=2)
