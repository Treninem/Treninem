"""Обработчики раздела «Наставничество»."""
from __future__ import annotations

from datetime import datetime

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database.queries import (
    apply_mentor_status,
    create_mentorship,
    get_user_by_telegram_id,
    list_mentors,
    list_students_for_mentor,
    list_tasks_for_user,
    list_trainings_for_user,
)
from features.mentorship.mentor_validator import is_rank_eligible_for_mentor, mentor_can_teach_student
from features.mentorship.task_manager import assign_task
from features.mentorship.training_scheduler import schedule_training
from utils.keyboards import mentors_inline_keyboard

MENTOR_SPEC, MENTOR_SCHEDULE, MENTOR_STYLE = range(3)
TRAIN_TITLE, TRAIN_DIFF, TRAIN_TIME = range(3, 6)


async def mentor_apply_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user or not user.is_registered:
        await update.message.reply_text("Сначала зарегистрируйтесь в профиле.")
        return ConversationHandler.END
    if not is_rank_eligible_for_mentor(user.pubg_rank):
        await update.message.reply_text("Ваш ранг PUBG пока недостаточен. Нужен ранг Корона и выше.")
        return ConversationHandler.END
    await update.message.reply_text("Введите специализацию наставника (например: стрельба, позиционка, тактика):")
    return MENTOR_SPEC


async def mentor_apply_spec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["mentor_form"] = {"specialization": update.message.text.strip()}
    await update.message.reply_text("Введите ваше расписание (например: Пн-Пт 19:00-22:00):")
    return MENTOR_SCHEDULE


async def mentor_apply_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["mentor_form"]["schedule"] = update.message.text.strip()
    await update.message.reply_text("Опишите ваш стиль обучения:")
    return MENTOR_STYLE


async def mentor_apply_style(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    form = context.user_data.get("mentor_form", {})
    apply_mentor_status(
        update.effective_user.id,
        form.get("specialization", ""),
        form.get("schedule", ""),
        update.message.text.strip(),
    )
    await update.message.reply_text("✅ Статус наставника активирован.")
    context.user_data.pop("mentor_form", None)
    return ConversationHandler.END


async def mentor_apply_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("mentor_form", None)
    await update.message.reply_text("Заявка наставника отменена.")
    return ConversationHandler.END


async def search_mentors(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mentors = list_mentors()
    if not mentors:
        await update.message.reply_text("Сейчас наставников нет.")
        return
    text = "🔎 Доступные наставники:\n\n" + "\n".join(
        f"• {m.pubg_nickname or m.username} | Ранг: {m.pubg_rank} | Специализация: {m.mentor_specialization or '-'} | Мест: свободно"
        for m in mentors
    )
    await update.message.reply_text(text, reply_markup=mentors_inline_keyboard(mentors))


async def mentor_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "noop":
        return
    mentor_telegram_id = int(data.split(":", 1)[1])
    mentor = get_user_by_telegram_id(mentor_telegram_id)
    student = get_user_by_telegram_id(update.effective_user.id)
    if not mentor or not student:
        await query.edit_message_text("Не удалось найти пользователя в БД.")
        return
    if not mentor_can_teach_student(mentor.pubg_rank, student.pubg_rank):
        await query.edit_message_text("Этот наставник может обучать только игроков с более низким рангом.")
        return
    create_mentorship(mentor_telegram_id, student.telegram_id)
    await query.edit_message_text(f"✅ Вы записаны к наставнику {mentor.pubg_nickname or mentor.username}.")


async def my_students(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user or not user.is_mentor:
        await update.message.reply_text("Раздел доступен только наставникам.")
        return
    students = list_students_for_mentor(update.effective_user.id)
    if not students:
        await update.message.reply_text("У вас пока нет подопечных.")
        return
    text = "👥 Ваши подопечные:\n\n" + "\n".join(
        f"• {s.pubg_nickname or s.username} | Баллы: {s.points} | Ранг в боте: {s.bot_rank}"
        for s in students
    )
    await update.message.reply_text(text)


async def my_trainings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    trainings = list_trainings_for_user(update.effective_user.id)
    if not trainings:
        await update.message.reply_text("Тренировок пока нет. Наставник может создать новую командой /create_training")
        return
    text = "🎯 Мои тренировки:\n\n" + "\n".join(
        f"• {t.title} | {t.difficulty} | {t.scheduled_at:%Y-%m-%d %H:%M} | Тема: {t.topic or '-'}"
        for t in trainings
    )
    await update.message.reply_text(text)


async def my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tasks = list_tasks_for_user(update.effective_user.id)
    if not tasks:
        await update.message.reply_text("Активных заданий нет.")
        return
    text = "📝 Мои задания:\n\n" + "\n".join(
        f"• #{task.id} {task.title}\n  {task.description}\n  Срок: {task.deadline.strftime('%Y-%m-%d %H:%M') if task.deadline else 'не указан'}\n  Награда: {task.reward_points}\n  Статус: {task.status}"
        for task in tasks
    )
    await update.message.reply_text(text)


async def create_training_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user or not user.is_mentor:
        await update.message.reply_text("Команда доступна только наставнику.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("Использование: /create_training <YYYY-MM-DD_HH:MM> <сложность> <название>")
        return
    scheduled_at = datetime.strptime(context.args[0], "%Y-%m-%d_%H:%M")
    difficulty = context.args[1]
    title = " ".join(context.args[2:])
    training = schedule_training(update.effective_user.id, title, difficulty, scheduled_at, title)
    await update.message.reply_text(f"Тренировка создана: {training.title} на {training.scheduled_at:%Y-%m-%d %H:%M}")


async def create_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user or not user.is_mentor:
        await update.message.reply_text("Команда доступна только наставнику.")
        return
    if len(context.args) < 3:
        await update.message.reply_text("Использование: /create_task <telegram_id_ученика> <название> | <описание>")
        return
    raw = " ".join(context.args)
    student_id_str, rest = raw.split(" ", 1)
    title, description = [part.strip() for part in rest.split("|", 1)]
    task = assign_task(update.effective_user.id, int(student_id_str), title, description, None, 50)
    await update.message.reply_text(f"Задание создано: #{task.id} {task.title}") if task else await update.message.reply_text("Не удалось создать задание.")


def register(application) -> None:
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^👨‍🏫 Стать наставником$"), mentor_apply_start)],
        states={
            MENTOR_SPEC: [MessageHandler(filters.TEXT & ~filters.COMMAND, mentor_apply_spec)],
            MENTOR_SCHEDULE: [MessageHandler(filters.TEXT & ~filters.COMMAND, mentor_apply_schedule)],
            MENTOR_STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, mentor_apply_style)],
        },
        fallbacks=[CommandHandler("cancel", mentor_apply_cancel)],
    )
    application.add_handler(conv)
    application.add_handler(MessageHandler(filters.Regex(r"^🔎 Поиск наставников$"), search_mentors))
    application.add_handler(MessageHandler(filters.Regex(r"^👥 Мои подопечные$"), my_students))
    application.add_handler(MessageHandler(filters.Regex(r"^🎯 Мои тренировки$"), my_trainings))
    application.add_handler(MessageHandler(filters.Regex(r"^📝 Мои задания$"), my_tasks))
    application.add_handler(CallbackQueryHandler(mentor_select_callback, pattern=r"^mentor_select:|^noop$"))
    application.add_handler(CommandHandler("create_training", create_training_command))
    application.add_handler(CommandHandler("create_task", create_task_command))
