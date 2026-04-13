"""Все клавиатуры бота."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("👤 Профиль"), KeyboardButton("👨‍🏫 Наставничество")],
        [KeyboardButton("📰 Новости"), KeyboardButton("💎 Премиум")],
        [KeyboardButton("🤝 Друзья"), KeyboardButton("🌐 Группы с ботом")],
        [KeyboardButton("💬 Обратная связь")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def profile_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("🆕 Зарегистрироваться / Редактировать"), KeyboardButton("📊 Мой прогресс")],
        [KeyboardButton("🏆 Мои баллы"), KeyboardButton("🎯 Мои достижения")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def mentorship_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("👨‍🏫 Стать наставником"), KeyboardButton("🔎 Поиск наставников")],
        [KeyboardButton("👥 Мои подопечные"), KeyboardButton("🎯 Мои тренировки")],
        [KeyboardButton("📝 Мои задания")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def news_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("📣 Последние новости"), KeyboardButton("🗓️ События")],
        [KeyboardButton("🎮 Обновления игры")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def premium_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("💎 О премиум-статусе"), KeyboardButton("💳 Оформить/продлить")],
        [KeyboardButton("🎁 Мои привилегии"), KeyboardButton("⏱️ Срок действия")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def friends_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("👥 Список друзей"), KeyboardButton("➕ Добавить друга")],
        [KeyboardButton("🗣️ Чат с друзьями"), KeyboardButton("🏅 Рейтинг друзей")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def groups_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("📋 Список чатов"), KeyboardButton("ℹ️ Информация о чате")],
        [KeyboardButton("🚪 Выйти из чата")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def feedback_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("📝 Оставить отзыв"), KeyboardButton("⚠️ Пожаловаться")],
        [KeyboardButton("❓ Задать вопрос"), KeyboardButton("📢 Предложения")],
        [KeyboardButton("⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def mentors_inline_keyboard(mentors: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"{m.pubg_nickname or m.username} | {m.pubg_rank}", callback_data=f"mentor_select:{m.telegram_id}")]
        for m in mentors
    ]
    if not buttons:
        buttons = [[InlineKeyboardButton("Нет доступных наставников", callback_data="noop")]]
    return InlineKeyboardMarkup(buttons)
