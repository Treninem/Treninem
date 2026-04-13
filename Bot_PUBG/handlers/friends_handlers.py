"""Обработчики раздела «Друзья»."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters

from config.constants import MAX_FRIENDS_IN_CHAT
from database.queries import add_friend, get_or_create_user, get_user_by_telegram_id, list_friends, list_top_friends
from services.pubg_api import PUBGAPIClient, PUBGAPIError
from utils.validators import validate_pubg_id

ADD_FRIEND_PUBG_ID = 1


async def friends_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    friends = list_friends(update.effective_user.id)
    if not friends:
        await update.message.reply_text("У вас пока нет друзей в боте.")
        return
    text = "👥 Список друзей:\n\n" + "\n".join(
        f"• {f.pubg_nickname or f.username} | Ранг: {f.pubg_rank or '-'} | Баллы: {f.points}"
        for f in friends
    )
    await update.message.reply_text(text)


async def add_friend_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите PUBG ID друга:")
    return ADD_FRIEND_PUBG_ID


async def add_friend_pubg_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    pubg_id = update.message.text.strip()
    if not validate_pubg_id(pubg_id):
        await update.message.reply_text("Некорректный PUBG ID.")
        return ADD_FRIEND_PUBG_ID
    client = PUBGAPIClient()
    try:
        info = client.find_player(pubg_id)
    except PUBGAPIError as exc:
        await update.message.reply_text(f"Не удалось найти друга: {exc}")
        return ADD_FRIEND_PUBG_ID

    # Создаем карточку друга как локального пользователя, если он еще не взаимодействовал с ботом.
    pseudo_telegram_id = abs(hash(info.player_id)) % 2_000_000_000 + 1
    get_or_create_user(pseudo_telegram_id, info.nickname, info.nickname, "")
    friend_user = get_user_by_telegram_id(pseudo_telegram_id)
    from database.queries import update_user_profile
    update_user_profile(
        pseudo_telegram_id,
        pubg_player_id=info.player_id,
        pubg_nickname=info.nickname,
        pubg_rank=info.rank,
        is_registered=True,
    )
    add_friend(update.effective_user.id, pseudo_telegram_id, info.player_id)
    await update.message.reply_text(f"✅ Друг добавлен: {info.nickname}\nРанг: {info.rank}\nK/D: {info.kd}")
    return ConversationHandler.END


async def create_friends_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    friends = list_friends(update.effective_user.id)
    limited = friends[:MAX_FRIENDS_IN_CHAT]
    if not limited:
        await update.message.reply_text("Сначала добавьте хотя бы одного друга.")
        return
    await update.message.reply_text(
        "🗣️ Telegram Bot API не может сам создать обычную группу без участия пользователя.\n"
        "Что сделать:\n"
        "1) Создайте группу вручную в Telegram.\n"
        f"2) Добавьте туда до {MAX_FRIENDS_IN_CHAT} друзей.\n"
        "3) Добавьте бота в эту группу.\n"
        "4) После этого бот увидит чат в разделе «Группы с ботом»."
    )


async def friends_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    friends = list_top_friends(update.effective_user.id)
    if not friends:
        await update.message.reply_text("Рейтинг пока пуст.")
        return
    lines = [f"{idx}. {f.pubg_nickname or f.username} — {f.points} баллов" for idx, f in enumerate(friends, start=1)]
    await update.message.reply_text("🏅 Рейтинг друзей:\n\n" + "\n".join(lines))


def register(application) -> None:
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^➕ Добавить друга$"), add_friend_start)],
        states={ADD_FRIEND_PUBG_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_friend_pubg_id)]},
        fallbacks=[],
    )
    application.add_handler(MessageHandler(filters.Regex(r"^👥 Список друзей$"), friends_list))
    application.add_handler(conv)
    application.add_handler(MessageHandler(filters.Regex(r"^🗣️ Чат с друзьями$"), create_friends_chat))
    application.add_handler(MessageHandler(filters.Regex(r"^🏅 Рейтинг друзей$"), friends_rating))
