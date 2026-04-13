"""Раздел «Друзья»."""

from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from sqlalchemy import select

from config.constants import (
    BACK_TO_MAIN,
    CANCEL_ACTION,
    FRIENDS_ADD,
    FRIENDS_CHAT,
    FRIENDS_INVITE,
    FRIENDS_LIST,
    FRIENDS_PROMO,
    FRIENDS_RATING,
    FRIENDS_TOP,
)
from database import get_session
from database.models import User
from database.queries import (
    add_friend,
    ensure_referral_code,
    get_referral_stats,
    get_user_by_telegram_id,
    list_friends,
    list_top_referrers,
)
from services.pubg_api import PUBGAPIError, pubg_client
from utils.helpers import build_referral_link, reply_tracked_message
from utils.validators import validate_pubg_name

FRIEND_NAME = 100


async def add_friend_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся.")
            return ConversationHandler.END

    await reply_tracked_message(update, context, "🧭 Введи PUBG nickname или PUBG ID друга.")
    return FRIEND_NAME


async def add_friend_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.effective_message.text or "").strip()
    if not validate_pubg_name(name):
        await reply_tracked_message(update, context, "Некорректный PUBG ID. Повтори ввод.")
        return FRIEND_NAME

    try:
        profile = pubg_client.resolve_player_profile(name)
    except PUBGAPIError as exc:
        await reply_tracked_message(update, context, f"Не удалось найти друга: {exc}")
        return FRIEND_NAME

    with get_session() as session:
        owner = get_user_by_telegram_id(session, update.effective_user.id)
        linked_user = session.execute(select(User).where(User.pubg_player_id == profile.player_id)).scalar_one_or_none()
        add_friend(
            session=session,
            user_id=owner.id,
            friend_pubg_player_id=profile.player_id,
            friend_pubg_name=profile.nickname,
            friend_pubg_rank=profile.rank,
            friend_kd=profile.kd,
            linked_user_id=linked_user.id if linked_user else None,
        )

    await reply_tracked_message(
        update,
        context,
        (
            "✅ Друг добавлен в список!\n\n"
            f"🎮 Ник: {profile.nickname}\n"
            f"🏅 Ранг: {profile.rank}\n"
            f"⚔️ K/D: {profile.kd or '—'}\n"
            f"📊 Матчи: {profile.total_matches}\n"
            f"🏆 Победы: {profile.total_wins}"
        ),
    )
    return ConversationHandler.END


async def friends_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        owner = get_user_by_telegram_id(session, update.effective_user.id)
        if not owner or not owner.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся.")
            return
        friends = list_friends(session, owner.id)

    if not friends:
        await reply_tracked_message(update, context, "У тебя пока нет друзей в списке.")
        return

    lines = ["👥 Твой отряд\n"]
    for item in friends[:20]:
        lines.append(
            f"• {item.friend_pubg_name} | 🏅 {item.friend_pubg_rank or '—'} | ⚔️ K/D: {item.friend_kd or '—'}"
        )
    await reply_tracked_message(update, context, "\n".join(lines))


async def friends_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "🗣️ Чат с друзьями\n\n"
        "Telegram Bot API не умеет программно создавать новый групповой чат между пользователями по одному клику. "
        "Поэтому лучший рабочий вариант такой:\n"
        "1) Создай группу вручную в Telegram\n"
        "2) Добавь туда друзей\n"
        "3) Добавь туда этого бота\n"
        "4) Выдай боту нужные права для чистки и сервисных сообщений\n\n"
        "После этого группа появится в разделе «Группы с ботом», а бот сможет помогать уже внутри неё."
    )
    await reply_tracked_message(update, context, text)


async def friends_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        owner = get_user_by_telegram_id(session, update.effective_user.id)
        if not owner or not owner.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся.")
            return
        friends = list_friends(session, owner.id)

        ranked = []
        for friend in friends:
            if friend.linked_user_id:
                linked_user = session.execute(select(User).where(User.id == friend.linked_user_id)).scalar_one_or_none()
                if linked_user:
                    ranked.append((friend.friend_pubg_name, linked_user.points, linked_user.bot_rank))

    if not ranked:
        await reply_tracked_message(update, context, "Среди друзей пока нет зарегистрированных пользователей бота.")
        return

    ranked.sort(key=lambda item: item[1], reverse=True)
    lines = ["🏅 Рейтинг друзей\n"]
    for idx, (name, points, rank) in enumerate(ranked, start=1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "•"
        lines.append(f"{medal} {idx}. {name} — {points} баллов ({rank})")
    await reply_tracked_message(update, context, "\n".join(lines))


async def invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся — ссылка станет доступна после привязки профиля.")
            return
        referral_code = ensure_referral_code(session, user)
        stats = get_referral_stats(session, user.id)

    link = build_referral_link(context.bot.username or "", referral_code)
    text = (
        "🎁 Персональная ссылка приглашения\n\n"
        f"🔗 {link}\n\n"
        "Как это работает:\n"
        "• отправь ссылку другу\n"
        "• друг нажимает /start по твоей ссылке\n"
        "• после полной регистрации ты получаешь +30 баллов\n\n"
        f"👥 Всего пришло по ссылке: {stats['total']}\n"
        f"✅ Полностью зарегистрировались: {stats['registered']}\n"
        f"⏳ Ещё не завершили регистрацию: {stats['pending']}"
    )
    await reply_tracked_message(update, context, text)


async def promo_pack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся.")
            return
        referral_code = ensure_referral_code(session, user)

    link = build_referral_link(context.bot.username or "", referral_code)
    text = (
        "📣 Промо-набор для приглашения друзей\n\n"
        "Вариант 1 — коротко:\n"
        "Присоединяйся к нашему PUBG-боту: статистика, тесты, наставники и клановая прокачка.\n"
        f"{link}\n\n"
        "Вариант 2 — для кланового чата:\n"
        "Запускаем клановую прокачку в Telegram: привязка PUBG, баллы, тренировки, задания и рейтинг. "
        f"Залетай по ссылке: {link}\n\n"
        "Вариант 3 — личное приглашение:\n"
        "Я уже внутри кланового PUBG-бота. Там можно отслеживать прогресс, проходить тесты и искать наставников. "
        f"Подключайся: {link}"
    )
    await reply_tracked_message(update, context, text)


async def top_referrers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with get_session() as session:
        rows = list_top_referrers(session, limit=10)

    if not rows:
        await reply_tracked_message(update, context, "Пока ещё никто не привёл зарегистрированных игроков.")
        return

    lines = ["🔥 Топ приглашений\n"]
    for idx, (user, invites) in enumerate(rows, start=1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "•"
        name = user.pubg_name or user.first_name or user.username or str(user.telegram_id)
        lines.append(f"{medal} {idx}. {name} — {invites} приглашений | {user.points} баллов")
    await reply_tracked_message(update, context, "\n".join(lines))


async def cancel_friend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await reply_tracked_message(update, context, "Добавление друга отменено.")
    return ConversationHandler.END



def register(application) -> None:
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{FRIENDS_ADD}$"), add_friend_entry)],
        states={FRIEND_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_friend_save)]},
        fallbacks=[
            MessageHandler(filters.Regex(f"^{CANCEL_ACTION}$"), cancel_friend),
            MessageHandler(filters.Regex(f"^{BACK_TO_MAIN}$"), cancel_friend),
        ],
    )
    application.add_handler(CommandHandler("invite", invite_link), group=5)
    application.add_handler(CommandHandler("promo", promo_pack), group=5)
    application.add_handler(conv, group=5)
    application.add_handler(MessageHandler(filters.Regex(f"^{FRIENDS_LIST}$"), friends_list), group=5)
    application.add_handler(MessageHandler(filters.Regex(f"^{FRIENDS_CHAT}$"), friends_chat), group=5)
    application.add_handler(MessageHandler(filters.Regex(f"^{FRIENDS_RATING}$"), friends_rating), group=5)
    application.add_handler(MessageHandler(filters.Regex(f"^{FRIENDS_INVITE}$"), invite_link), group=5)
    application.add_handler(MessageHandler(filters.Regex(f"^{FRIENDS_PROMO}$"), promo_pack), group=5)
    application.add_handler(MessageHandler(filters.Regex(f"^{FRIENDS_TOP}$"), top_referrers), group=5)
