"""Базовые команды и навигация по меню."""

from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from config.constants import (
    BACK_TO_MAIN,
    CANCEL_ACTION,
    MAIN_MENU_FEEDBACK,
    MAIN_MENU_FRIENDS,
    MAIN_MENU_GROUPS,
    MAIN_MENU_MENTORSHIP,
    MAIN_MENU_NEWS,
    MAIN_MENU_PREMIUM,
    MAIN_MENU_PROFILE,
)
from database import get_session
from database.queries import (
    attach_referral_to_user,
    ensure_referral_code,
    get_or_create_user,
    get_referral_stats,
    update_last_activity,
)
from utils.helpers import build_referral_link, reply_tracked_message
from utils.keyboards import (
    feedback_menu_keyboard,
    friends_menu_keyboard,
    groups_menu_keyboard,
    main_menu_keyboard,
    mentorship_menu_keyboard,
    news_menu_keyboard,
    premium_menu_keyboard,
    profile_menu_keyboard,
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start: создать пользователя в БД, обработать реферальный код и показать красивый welcome-экран."""
    referral_note = ""
    referral_link = ""
    registered_referrals = 0

    with get_session() as session:
        user = get_or_create_user(session, update.effective_user)
        referral_code = ensure_referral_code(session, user)

        if context.args:
            arg = (context.args[0] or "").strip()
            if arg.startswith("ref_"):
                ok, payload = attach_referral_to_user(session, user, arg[4:])
                if ok:
                    inviter = payload
                    referral_note = (
                        "🎁 Ты зашёл по персональной ссылке союзника.\n"
                        f"После завершения регистрации пригласивший игрок получит бонус.\n"
                        f"Пригласил: {inviter.pubg_name or inviter.first_name or inviter.username or inviter.telegram_id}\n\n"
                    )
                else:
                    referral_note = f"ℹ️ {payload}\n\n"

        stats = get_referral_stats(session, user.id)
        registered_referrals = stats["registered"]
        referral_link = build_referral_link(context.bot.username or "", referral_code)

    text = (
        "🏆 Добро пожаловать в клановый PUBG-центр!\n\n"
        "Здесь ты можешь:\n"
        "• привязать Telegram ↔ PUBG\n"
        "• получать ежедневные тесты и баллы\n"
        "• искать наставников и создавать тренировки\n"
        "• приглашать друзей по персональной ссылке\n"
        "• следить за новостями, патчами и ивентами\n\n"
        f"{referral_note}"
        "🚀 Быстрый старт:\n"
        "1) Открой 👤 Профиль\n"
        "2) Нажми регистрацию\n"
        "3) Введи PUBG nickname или PUBG player ID\n"
        "4) После регистрации зайди в 🤝 Друзья → 🎁 Пригласить друзей\n\n"
        f"👥 Уже приглашено бойцов: {registered_referrals}\n"
        f"🔗 Твоя ссылка приглашения:\n{referral_link}"
    )
    await reply_tracked_message(update, context, text, reply_markup=main_menu_keyboard(), keep=True)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /help: краткая справка по разделам бота."""
    text = (
        "📘 Помощь по боту\n\n"
        "👤 Профиль — регистрация, привязка Telegram↔PUBG, карточка игрока, прогресс, баллы\n"
        "👨‍🏫 Наставничество — наставники, тренировки, задания\n"
        "📰 Новости — новости, ивенты, патчи\n"
        "💎 Премиум — статус и привилегии\n"
        "🤝 Друзья — список друзей, реферальная ссылка, промо-набор, топ приглашений\n"
        "🌐 Группы с ботом — список чатов, где есть бот\n"
        "💬 Обратная связь — отзывы, жалобы, предложения\n\n"
        "Полезные команды:\n"
        "/binding — привязка аккаунтов\n"
        "/sync_profile — обновить PUBG-данные\n"
        "/invite — получить свою ссылку приглашения\n"
        "/promo — готовые тексты для приглашения\n"
        "/menu — открыть меню\n\n"
        "Команды владельца: /p_up и /p_dn"
    )
    await reply_tracked_message(update, context, text, reply_markup=main_menu_keyboard(), keep=True)


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /menu: повторно показать главное меню."""
    await reply_tracked_message(update, context, "🏠 Главное меню клана:", reply_markup=main_menu_keyboard(), keep=True)


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Роутер по основным разделам через reply-кнопки."""
    text = (update.effective_message.text or "").strip()

    with get_session() as session:
        update_last_activity(session, update.effective_user.id)

    if text in (BACK_TO_MAIN, CANCEL_ACTION):
        await reply_tracked_message(update, context, "⬅️ Возвращаю тебя в главное меню.", reply_markup=main_menu_keyboard(), keep=True)
        return

    if text == MAIN_MENU_PROFILE:
        await reply_tracked_message(update, context, "👤 Раздел «Профиль». Выбери нужное действие ниже.", reply_markup=profile_menu_keyboard(), keep=True)
        return
    if text == MAIN_MENU_MENTORSHIP:
        await reply_tracked_message(update, context, "👨‍🏫 Раздел «Наставничество». Здесь можно стать наставником или найти себе проводника.", reply_markup=mentorship_menu_keyboard(), keep=True)
        return
    if text == MAIN_MENU_NEWS:
        await reply_tracked_message(update, context, "📰 Раздел «Новости». Открой свежие публикации, события и обновления.", reply_markup=news_menu_keyboard(), keep=True)
        return
    if text == MAIN_MENU_PREMIUM:
        await reply_tracked_message(update, context, "💎 Раздел «Премиум». Все бонусы и срок действия собраны здесь.", reply_markup=premium_menu_keyboard(), keep=True)
        return
    if text == MAIN_MENU_FRIENDS:
        await reply_tracked_message(update, context, "🤝 Раздел «Друзья». Управляй списком друзей и приглашай новых игроков.", reply_markup=friends_menu_keyboard(), keep=True)
        return
    if text == MAIN_MENU_GROUPS:
        await reply_tracked_message(update, context, "🌐 Раздел «Группы с ботом». Здесь видны все чаты, где бот уже работает.", reply_markup=groups_menu_keyboard(), keep=True)
        return
    if text == MAIN_MENU_FEEDBACK:
        await reply_tracked_message(update, context, "💬 Раздел «Обратная связь». Отзывы, вопросы, жалобы и предложения.", reply_markup=feedback_menu_keyboard(), keep=True)
        return



def register(application) -> None:
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND
            & filters.Regex(
                f"^({MAIN_MENU_PROFILE}|{MAIN_MENU_MENTORSHIP}|{MAIN_MENU_NEWS}|{MAIN_MENU_PREMIUM}|{MAIN_MENU_FRIENDS}|{MAIN_MENU_GROUPS}|{MAIN_MENU_FEEDBACK}|{BACK_TO_MAIN}|{CANCEL_ACTION})$"
            ),
            menu_router,
        ),
        group=0,
    )
