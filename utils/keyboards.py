"""Фабрики клавиатур reply/inline."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from config.constants import (
    BACK_TO_MAIN,
    CANCEL_ACTION,
    FEEDBACK_MENU_BUTTONS,
    FRIENDS_MENU_BUTTONS,
    GROUPS_MENU_BUTTONS,
    MAIN_MENU_FEEDBACK,
    MAIN_MENU_GROUPS,
    MAIN_MENU_MENTORSHIP,
    MAIN_MENU_NEWS,
    MAIN_MENU_PREMIUM,
    MAIN_MENU_PROFILE,
    MAIN_MENU_FRIENDS,
    MENTOR_MENU_BUTTONS,
    NEWS_MENU_BUTTONS,
    PREMIUM_MENU_BUTTONS,
    PROFILE_MENU_BUTTONS,
)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(MAIN_MENU_PROFILE), KeyboardButton(MAIN_MENU_MENTORSHIP)],
            [KeyboardButton(MAIN_MENU_NEWS), KeyboardButton(MAIN_MENU_PREMIUM)],
            [KeyboardButton(MAIN_MENU_FRIENDS), KeyboardButton(MAIN_MENU_GROUPS)],
            [KeyboardButton(MAIN_MENU_FEEDBACK)],
        ],
        resize_keyboard=True,
    )


def submenu_keyboard(items: list[str]) -> ReplyKeyboardMarkup:
    rows = []
    for i in range(0, len(items), 2):
        rows.append([KeyboardButton(items[i]), *( [KeyboardButton(items[i + 1])] if i + 1 < len(items) else [] )])
    rows.append([KeyboardButton(BACK_TO_MAIN), KeyboardButton(CANCEL_ACTION)])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def profile_menu_keyboard() -> ReplyKeyboardMarkup:
    return submenu_keyboard(PROFILE_MENU_BUTTONS)


def mentorship_menu_keyboard() -> ReplyKeyboardMarkup:
    return submenu_keyboard(MENTOR_MENU_BUTTONS)


def news_menu_keyboard() -> ReplyKeyboardMarkup:
    return submenu_keyboard(NEWS_MENU_BUTTONS)


def premium_menu_keyboard() -> ReplyKeyboardMarkup:
    return submenu_keyboard(PREMIUM_MENU_BUTTONS)


def friends_menu_keyboard() -> ReplyKeyboardMarkup:
    return submenu_keyboard(FRIENDS_MENU_BUTTONS)


def groups_menu_keyboard() -> ReplyKeyboardMarkup:
    return submenu_keyboard(GROUPS_MENU_BUTTONS)


def feedback_menu_keyboard() -> ReplyKeyboardMarkup:
    return submenu_keyboard(FEEDBACK_MENU_BUTTONS)


def mentor_search_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Все", callback_data="mentor_filter:all"),
                InlineKeyboardButton("По специализации", callback_data="mentor_filter:spec"),
            ]
        ]
    )


def group_leave_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Выйти из чата", callback_data=f"group_leave:{chat_id}")]]
    )


def groups_leave_list_keyboard(chats: list) -> InlineKeyboardMarkup | None:
    rows = []
    for chat in chats[:10]:
        title = getattr(chat, 'title', None) or str(getattr(chat, 'chat_id', 'chat'))
        button_text = f"🚪 {title[:24]}"
        rows.append([InlineKeyboardButton(button_text, callback_data=f"group_leave:{chat.chat_id}")])
    return InlineKeyboardMarkup(rows) if rows else None


def news_link_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Открыть новость", url=url)]]
    )


def news_digest_keyboard(items: list[dict]) -> InlineKeyboardMarkup | None:
    rows = []
    for idx, item in enumerate(items[:5], start=1):
        if not item.get('url'):
            continue
        rows.append([InlineKeyboardButton(f"Новость {idx}", url=item['url'])])
    return InlineKeyboardMarkup(rows) if rows else None


def test_question_keyboard(session_id: int, q_index: int, options: list[str]) -> InlineKeyboardMarkup:
    rows = []
    for idx, option in enumerate(options):
        rows.append([InlineKeyboardButton(option, callback_data=f"test:{session_id}:{q_index}:{idx}")])
    return InlineKeyboardMarkup(rows)


def task_complete_keyboard(task_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ Отметить выполненным", callback_data=f"task_complete:{task_id}")]]
    )


def mentor_assign_keyboard(mentor_user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Выбрать наставника", callback_data=f"mentor_assign:{mentor_user_id}")]]
    )


def mentor_assign_list_keyboard(mentor_ids: list[int]) -> InlineKeyboardMarkup | None:
    rows = []
    for idx, mentor_id in enumerate(mentor_ids[:10], start=1):
        rows.append([InlineKeyboardButton(f"Выбрать наставника #{idx}", callback_data=f"mentor_assign:{mentor_id}")])
    return InlineKeyboardMarkup(rows) if rows else None
