"""Обработчики раздела «Профиль»."""
from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config.constants import CHAT_DATA_DELETE_SECONDS
from database.queries import (
    create_or_update_registration,
    get_statistics,
    get_test_results_last_days,
    get_user_by_telegram_id,
    list_achievements,
)
from services.pubg_api import PUBGAPIClient, PUBGAPIError
from utils.helpers import build_progress_chart
from utils.keyboards import profile_menu_keyboard
from utils.validators import validate_age, validate_pubg_id, validate_weekly_hours

REG_PUBG_ID, REG_AGE, REG_HOURS = range(3)


async def profile_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.text == "👤 Профиль":
        await update.message.reply_text("Вы открыли раздел профиля.", reply_markup=profile_menu_keyboard())


async def registration_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите ваш PUBG ID / никнейм для проверки через API:")
    return REG_PUBG_ID


async def registration_pubg_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pubg_id = update.message.text.strip()
    if not validate_pubg_id(pubg_id):
        await update.message.reply_text("Некорректный PUBG ID. Допустимы латиница, цифры, _, -, .")
        return REG_PUBG_ID

    client = PUBGAPIClient()
    try:
        info = client.find_player(pubg_id)
    except PUBGAPIError as exc:
        await update.message.reply_text(f"Ошибка проверки PUBG ID: {exc}")
        return REG_PUBG_ID

    context.user_data["registration"] = {
        "pubg_player_id": info.player_id,
        "pubg_nickname": info.nickname,
        "pubg_rank": info.rank,
    }
    await update.message.reply_text(
        f"Игрок найден:\nНик: {info.nickname}\nРанг: {info.rank}\nK/D: {info.kd}\n\nТеперь введите возраст (13+):"
    )
    return REG_AGE


async def registration_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    is_valid, age = validate_age(update.message.text.strip())
    if not is_valid or age is None:
        await update.message.reply_text("Возраст должен быть числом и не меньше 13.")
        return REG_AGE
    context.user_data["registration"]["age"] = age
    await update.message.reply_text("Сколько часов в неделю вы играете в PUBG? Введите число:")
    return REG_HOURS


async def registration_hours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    is_valid, hours = validate_weekly_hours(update.message.text.strip())
    if not is_valid or hours is None:
        await update.message.reply_text("Введите корректное количество часов от 0 до 168.")
        return REG_HOURS

    reg = context.user_data.get("registration", {})
    user = update.effective_user
    create_or_update_registration(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        pubg_player_id=reg["pubg_player_id"],
        pubg_nickname=reg["pubg_nickname"],
        pubg_rank=reg["pubg_rank"],
        age=reg["age"],
        weekly_hours=hours,
    )
    await update.message.reply_text(
        f"✅ Регистрация завершена!\nНик: {reg['pubg_nickname']}\nРанг: {reg['pubg_rank']}\nВозраст: {reg['age']}\nЧасов в неделю: {hours}",
        reply_markup=profile_menu_keyboard(),
    )

    # Пытаемся удалить служебные сообщения пользователя через 10 секунд.
    for msg in [update.message]:
        context.job_queue.run_once(delete_message_job, CHAT_DATA_DELETE_SECONDS, data={"chat_id": msg.chat_id, "message_id": msg.message_id})
    context.user_data.pop("registration", None)
    return ConversationHandler.END


async def delete_message_job(context: CallbackContext) -> None:
    data = context.job.data
    try:
        await context.bot.delete_message(chat_id=data["chat_id"], message_id=data["message_id"])
    except Exception:
        pass


async def registration_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("registration", None)
    await update.message.reply_text("Регистрация отменена.", reply_markup=profile_menu_keyboard())
    return ConversationHandler.END


async def my_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user or not user.is_registered:
        await update.message.reply_text("Сначала зарегистрируйтесь.")
        return
    stats = get_statistics(update.effective_user.id)
    results = get_test_results_last_days(update.effective_user.id, 7)
    text = (
        f"📊 Мой прогресс\n"
        f"Баллы: {stats.get('points', 0)}\n"
        f"Ранг в боте: {stats.get('bot_rank', 'Новичок')}\n"
        f"Выполненные задания: {stats.get('completed_tasks', 0)}\n"
        f"Тренировки: {stats.get('trainings', 0)}\n"
        f"Достижения: {stats.get('achievements', 0)}"
    )
    await update.message.reply_text(text)
    if results:
        chart = build_progress_chart(results)
        await update.message.reply_photo(photo=chart, caption="График прогресса за 7 дней")


async def my_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = get_user_by_telegram_id(update.effective_user.id)
    if not user or not user.is_registered:
        await update.message.reply_text("Сначала зарегистрируйтесь.")
        return
    await update.message.reply_text(
        f"🏆 Ваши баллы: {user.points}\nРанг в боте: {user.bot_rank}\nПремиум: {'Да' if user.is_premium else 'Нет'}"
    )


async def my_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    items = list_achievements(update.effective_user.id)
    if not items:
        await update.message.reply_text("🎯 Пока достижений нет.")
        return
    text = "🎯 Ваши достижения:\n\n" + "\n".join(f"• {item.title} — {item.description or 'без описания'}" for item in items)
    await update.message.reply_text(text)


def register(application) -> None:
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^🆕 Зарегистрироваться / Редактировать$"), registration_start)],
        states={
            REG_PUBG_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration_pubg_id)],
            REG_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration_age)],
            REG_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration_hours)],
        },
        fallbacks=[CommandHandler("cancel", registration_cancel)],
        name="profile_registration",
        persistent=False,
    )
    application.add_handler(conv)
    application.add_handler(MessageHandler(filters.Regex(r"^📊 Мой прогресс$"), my_progress))
    application.add_handler(MessageHandler(filters.Regex(r"^🏆 Мои баллы$"), my_points))
    application.add_handler(MessageHandler(filters.Regex(r"^🎯 Мои достижения$"), my_achievements))
