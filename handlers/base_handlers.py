"""Базовые обработчики: /start, /help, навигация по меню."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

from database.queries import get_or_create_user, save_bot_message
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
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    msg = await update.message.reply_text(
        "Добро пожаловать в PUBG Clan Bot!\nВыберите раздел в меню ниже.",
        reply_markup=main_menu_keyboard(),
    )
    save_bot_message(update.effective_chat.id, msg.message_id, "start")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Доступные команды:\n"
        "/start — запуск бота\n"
        "/help — помощь\n"
        "/clear_bot_messages — очистка сообщений бота в чате (для админов чата)\n"
        "/p_up и /p_dn — скрытые команды владельца"
    )
    await update.message.reply_text(text)


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if text == "👤 Профиль":
        await update.message.reply_text("Меню профиля", reply_markup=profile_menu_keyboard())
    elif text == "👨‍🏫 Наставничество":
        await update.message.reply_text("Меню наставничества", reply_markup=mentorship_menu_keyboard())
    elif text == "📰 Новости":
        await update.message.reply_text("Меню новостей", reply_markup=news_menu_keyboard())
    elif text == "💎 Премиум":
        await update.message.reply_text("Меню премиум", reply_markup=premium_menu_keyboard())
    elif text == "🤝 Друзья":
        await update.message.reply_text("Меню друзей", reply_markup=friends_menu_keyboard())
    elif text == "🌐 Группы с ботом":
        await update.message.reply_text("Меню групп", reply_markup=groups_menu_keyboard())
    elif text == "💬 Обратная связь":
        await update.message.reply_text("Меню обратной связи", reply_markup=feedback_menu_keyboard())
    elif text == "⬅️ Назад":
        await update.message.reply_text("Главное меню", reply_markup=main_menu_keyboard())


def register(application) -> None:
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_router), group=100)
