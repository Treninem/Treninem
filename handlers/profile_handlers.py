"""Раздел «Профиль»: регистрация, прогресс, баллы, достижения и привязка PUBG."""

from __future__ import annotations

import json

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from config.constants import (
    BACK_TO_MAIN,
    CANCEL_ACTION,
    PROFILE_ACHIEVEMENTS,
    PROFILE_BINDING,
    PROFILE_CARD,
    PROFILE_POINTS,
    PROFILE_PROGRESS,
    PROFILE_REGISTER,
    PROFILE_SYNC,
)
from config.settings import DELETE_PRIVATE_DATA_AFTER_SECONDS
from database import get_session
from database.models import MentorTask, TrainingParticipant
from database.queries import (
    ensure_referral_code,
    get_or_create_user,
    get_points_by_day,
    get_referral_stats,
    get_user_achievements,
    get_user_by_pubg_player_id,
    get_user_by_telegram_id,
    grant_milestone_achievements,
    grant_registration_and_referral_rewards,
    sync_user_pubg_profile,
    update_user_registration,
)
from features.daily_tests.reminders import schedule_user_daily_jobs
from services.notifications import schedule_message_deletion
from services.pubg_api import ExtendedPlayerProfile, PUBGAPIError, pubg_client
from utils.helpers import (
    build_profile_card_text,
    build_progress_chart,
    format_dt,
    format_privileges,
    reply_tracked_message,
    send_tracked_photo,
)
from utils.validators import validate_age, validate_hours_per_week, validate_pubg_name

REG_PUBG_NAME, REG_AGE, REG_HOURS = range(3)



def _safe_num(value, digits: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)



def _build_registration_preview(profile: ExtendedPlayerProfile) -> str:
    return (
        "🎮 Игрок найден!\n\n"
        f"🏷️ Ник: {profile.nickname}\n"
        f"🆔 PUBG ID: {profile.player_id}\n"
        f"🏅 Ранг: {profile.rank}\n"
        f"⭐ Уровень: {_safe_num(profile.level, 0)}\n"
        f"🎯 Матчи: {profile.total_matches}\n"
        f"🏆 Победы: {profile.total_wins}\n"
        f"🥇 Топ-10: {profile.top10s}\n"
        f"💥 Убийства: {profile.total_kills}\n"
        f"⚔️ K/D: {profile.kd or '—'}\n"
        f"🔥 Урон: {_safe_num(profile.total_damage)}\n"
        f"📈 Средний урон: {_safe_num(profile.avg_damage)}\n"
        f"📊 Винрейт: {_safe_num(profile.win_rate)}%\n"
        f"🎯 Хедшоты: {profile.headshot_kills}\n\n"
        "Теперь введи возраст (13+)."
    )



def _build_binding_text(user, referral_stats: dict[str, int]) -> str:
    pubg_stats = []
    pubg_stats.append(f"Ник PUBG: {user.pubg_name or '—'}")
    pubg_stats.append(f"PUBG player ID: {user.pubg_player_id or '—'}")
    pubg_stats.append(f"Shard: {user.pubg_shard or '—'}")
    pubg_stats.append(f"Ранг PUBG: {user.pubg_rank or '—'}")
    pubg_stats.append(f"Уровень: {_safe_num(user.pubg_level, 0)}")
    pubg_stats.append(f"Матчи: {_safe_num(user.pubg_total_matches, 0)}")
    pubg_stats.append(f"Победы: {_safe_num(user.pubg_total_wins, 0)}")
    pubg_stats.append(f"Топ-10: {_safe_num(user.pubg_top10s, 0)}")
    pubg_stats.append(f"K/D: {user.pubg_kd or '—'}")
    pubg_stats.append(f"Убийства: {_safe_num(user.pubg_total_kills, 0)}")
    pubg_stats.append(f"Урон: {_safe_num(user.pubg_total_damage)}")
    pubg_stats.append(f"Средний урон: {_safe_num(user.pubg_avg_damage)}")
    pubg_stats.append(f"Винрейт: {_safe_num(user.pubg_win_rate)}%")
    pubg_stats.append(f"Синхронизировано: {format_dt(user.pubg_last_sync_at)}")
    pubg_stats.append(f"Привязано: {format_dt(user.pubg_bound_at)}")

    return (
        "🆔 Моя привязка\n\n"
        "Telegram:\n"
        f"• Telegram ID: {user.telegram_id}\n"
        f"• Username: @{user.username if user.username else 'не задан'}\n"
        f"• Имя: {user.first_name or '—'} {user.last_name or ''}\n"
        f"• Реферальный код: {user.referral_code or '—'}\n\n"
        f"👥 Приглашено игроков: {referral_stats.get('registered', 0)}\n\n"
        "PUBG:\n"
        + "\n".join(f"• {line}" for line in pubg_stats)
    )


async def register_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Старт регистрации: просим PUBG nickname или PUBG player ID."""
    with get_session() as session:
        get_or_create_user(session, update.effective_user)

    msg = await reply_tracked_message(
        update,
        context,
        "🆕 Регистрация бойца\n\n"
        "Введи PUBG nickname или PUBG player ID.\n"
        "Пример ника: ProPlayer123\n"
        "Пример ID: account.1234567890abcdef",
    )
    schedule_message_deletion(context.job_queue, msg.chat_id, msg.message_id, DELETE_PRIVATE_DATA_AFTER_SECONDS)
    return REG_PUBG_NAME


async def register_pubg_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Шаг 1: найти игрока в PUBG API и проверить, не привязан ли он к другому Telegram."""
    value = (update.effective_message.text or "").strip()
    if not validate_pubg_name(value):
        msg = await reply_tracked_message(update, context, "Некорректный PUBG nickname / ID. Повтори ввод.")
        schedule_message_deletion(context.job_queue, msg.chat_id, msg.message_id, DELETE_PRIVATE_DATA_AFTER_SECONDS)
        return REG_PUBG_NAME

    try:
        profile = pubg_client.resolve_player_profile(value)
    except PUBGAPIError as exc:
        msg = await reply_tracked_message(update, context, f"Не удалось найти игрока: {exc}")
        schedule_message_deletion(context.job_queue, msg.chat_id, msg.message_id, DELETE_PRIVATE_DATA_AFTER_SECONDS)
        return REG_PUBG_NAME

    with get_session() as session:
        existing_owner = get_user_by_pubg_player_id(session, profile.player_id)
        if existing_owner and existing_owner.telegram_id != update.effective_user.id:
            msg = await reply_tracked_message(
                update,
                context,
                "Этот PUBG аккаунт уже привязан к другому Telegram аккаунту.\n"
                "Для безопасности повторная привязка запрещена.",
            )
            schedule_message_deletion(context.job_queue, msg.chat_id, msg.message_id, DELETE_PRIVATE_DATA_AFTER_SECONDS)
            return REG_PUBG_NAME

    context.user_data["reg_profile"] = {
        "player_id": profile.player_id,
        "nickname": profile.nickname,
        "rank": profile.rank,
        "kd": profile.kd,
        "shard": profile.shard,
        "level": profile.level,
        "total_matches": profile.total_matches,
        "total_wins": profile.total_wins,
        "total_kills": profile.total_kills,
        "total_damage": profile.total_damage,
        "headshot_kills": profile.headshot_kills,
        "avg_damage": profile.avg_damage,
        "win_rate": profile.win_rate,
        "top10s": profile.top10s,
        "raw_stats": profile.raw_stats,
    }

    try:
        schedule_message_deletion(
            context.job_queue,
            update.effective_chat.id,
            update.effective_message.message_id,
            DELETE_PRIVATE_DATA_AFTER_SECONDS,
        )
    except Exception:
        pass

    msg = await reply_tracked_message(update, context, _build_registration_preview(profile))
    schedule_message_deletion(context.job_queue, msg.chat_id, msg.message_id, DELETE_PRIVATE_DATA_AFTER_SECONDS)
    return REG_AGE


async def register_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Шаг 2: сохранить возраст."""
    ok, age = validate_age(update.effective_message.text or "")
    if not ok or age is None:
        msg = await reply_tracked_message(update, context, "Возраст должен быть числом и не меньше 13.")
        schedule_message_deletion(context.job_queue, msg.chat_id, msg.message_id, DELETE_PRIVATE_DATA_AFTER_SECONDS)
        return REG_AGE

    context.user_data["reg_age"] = age
    try:
        schedule_message_deletion(
            context.job_queue,
            update.effective_chat.id,
            update.effective_message.message_id,
            DELETE_PRIVATE_DATA_AFTER_SECONDS,
        )
    except Exception:
        pass

    msg = await reply_tracked_message(update, context, "⏱️ Сколько часов в неделю ты играешь в PUBG?")
    schedule_message_deletion(context.job_queue, msg.chat_id, msg.message_id, DELETE_PRIVATE_DATA_AFTER_SECONDS)
    return REG_HOURS


async def register_hours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Шаг 3: завершить регистрацию пользователя с привязкой Telegram ID ↔ PUBG ID."""
    ok, hours = validate_hours_per_week(update.effective_message.text or "")
    if not ok or hours is None:
        msg = await reply_tracked_message(update, context, "Введите количество часов от 1 до 168.")
        schedule_message_deletion(context.job_queue, msg.chat_id, msg.message_id, DELETE_PRIVATE_DATA_AFTER_SECONDS)
        return REG_HOURS

    profile = context.user_data.get("reg_profile")
    age = context.user_data.get("reg_age")
    if not profile or age is None:
        await reply_tracked_message(update, context, "Сессия регистрации устарела. Начни заново.")
        return ConversationHandler.END

    try:
        with get_session() as session:
            get_or_create_user(session, update.effective_user)
            user = update_user_registration(
                session=session,
                telegram_id=update.effective_user.id,
                pubg_player_id=profile["player_id"],
                pubg_name=profile["nickname"],
                pubg_rank=profile["rank"],
                pubg_kd=profile["kd"],
                pubg_shard=profile["shard"],
                age=age,
                hours_per_week=hours,
                pubg_level=profile.get("level"),
                pubg_total_matches=profile.get("total_matches"),
                pubg_total_wins=profile.get("total_wins"),
                pubg_total_kills=profile.get("total_kills"),
                pubg_total_damage=profile.get("total_damage"),
                pubg_headshot_kills=profile.get("headshot_kills"),
                pubg_avg_damage=profile.get("avg_damage"),
                pubg_win_rate=profile.get("win_rate"),
                pubg_top10s=profile.get("top10s"),
                pubg_stats_json=json.dumps(profile.get("raw_stats", {}), ensure_ascii=False),
            )
            ensure_referral_code(session, user)
            grant_registration_and_referral_rewards(session, user)
            grant_milestone_achievements(session, user)
            schedule_user_daily_jobs(context.application, user)
            referral_stats = get_referral_stats(session, user.id)
    except ValueError as exc:
        await reply_tracked_message(update, context, str(exc))
        return ConversationHandler.END

    try:
        schedule_message_deletion(
            context.job_queue,
            update.effective_chat.id,
            update.effective_message.message_id,
            DELETE_PRIVATE_DATA_AFTER_SECONDS,
        )
    except Exception:
        pass

    await reply_tracked_message(
        update,
        context,
        "✅ Регистрация завершена!\n\n"
        f"🎮 Ник: {profile['nickname']}\n"
        f"🆔 PUBG ID: {profile['player_id']}\n"
        f"🏅 Ранг PUBG: {profile['rank']}\n"
        f"⭐ Уровень: {_safe_num(profile.get('level'), 0)}\n"
        f"🎯 Матчи: {profile.get('total_matches', 0)}\n"
        f"🏆 Победы: {profile.get('total_wins', 0)}\n"
        f"💥 Убийства: {profile.get('total_kills', 0)}\n"
        f"⚔️ K/D: {profile['kd'] or '—'}\n"
        f"👤 Возраст: {age}\n"
        f"⏱️ Часов в неделю: {hours}\n"
        f"🎁 Приглашено игроков: {referral_stats['registered']}\n\n"
        "Привязка Telegram ↔ PUBG сохранена.\n"
        "Ты получил welcome-бонус и открыл базовые достижения.\n"
        "Ежедневные тесты будут приходить в 10:00 по локальному времени.",
    )

    context.user_data.pop("reg_profile", None)
    context.user_data.pop("reg_age", None)
    return ConversationHandler.END


async def profile_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать прогресс и график за 7 дней."""
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся через раздел профиля.")
            return

        grant_milestone_achievements(session, user)
        points_by_day = get_points_by_day(session, user.id, days=7)
        tasks_completed = session.query(MentorTask).filter(
            MentorTask.student_user_id == user.id,
            MentorTask.status == "completed",
        ).count()
        trainings_count = session.query(TrainingParticipant).filter(
            TrainingParticipant.user_id == user.id
        ).count()

    chart = build_progress_chart(points_by_day)
    caption = (
        "📊 Мой прогресс\n\n"
        f"🎯 Выполнено заданий: {tasks_completed}\n"
        f"🎓 Тренировок: {trainings_count}\n"
        f"🔥 Баллы: {user.points}\n"
        f"🎮 Матчи PUBG: {user.pubg_total_matches or 0}\n"
        f"📡 Последняя синхронизация PUBG: {format_dt(user.pubg_last_sync_at)}"
    )
    await send_tracked_photo(context, update.effective_chat.id, chart, caption=caption)


async def profile_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать баллы, ранг и привилегии."""
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся через раздел профиля.")
            return
        grant_milestone_achievements(session, user)

        text = (
            "🏆 Мои баллы\n\n"
            f"🔥 Баллы: {user.points}\n"
            f"🏅 Ранг в боте: {user.bot_rank}\n"
            f"🎁 Привилегии:\n{format_privileges(user.bot_rank)}\n\n"
            f"💎 Премиум до: {format_dt(user.premium_until)}\n"
            f"🎮 PUBG ник: {user.pubg_name or '—'}\n"
            f"🏅 PUBG ранг: {user.pubg_rank or '—'}\n"
            f"⭐ PUBG уровень: {_safe_num(user.pubg_level, 0)}"
        )
    await reply_tracked_message(update, context, text)


async def profile_achievements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать достижения пользователя."""
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся через раздел профиля.")
            return
        grant_milestone_achievements(session, user)
        achievements = get_user_achievements(session, user.id)

    if not achievements:
        await reply_tracked_message(update, context, "🎯 У тебя пока нет достижений.")
        return

    lines = ["🎯 Мои достижения\n"]
    for item in achievements[:20]:
        lines.append(f"• {item.title} — {item.description}")
    await reply_tracked_message(update, context, "\n".join(lines))


async def profile_binding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать жёсткую привязку Telegram аккаунта и PUBG аккаунта."""
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся через раздел профиля.")
            return
        ensure_referral_code(session, user)
        referral_stats = get_referral_stats(session, user.id)
        text = _build_binding_text(user, referral_stats)
    await reply_tracked_message(update, context, text)


async def profile_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать красивую карточку игрока."""
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся через раздел профиля.")
            return
        ensure_referral_code(session, user)
        grant_milestone_achievements(session, user)
        stats = get_referral_stats(session, user.id)
        text = build_profile_card_text(user, stats)
    await reply_tracked_message(update, context, text)


async def profile_sync(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обновить данные PUBG через API для уже привязанного аккаунта."""
    with get_session() as session:
        user = get_user_by_telegram_id(session, update.effective_user.id)
        if not user or not user.is_registered:
            await reply_tracked_message(update, context, "Сначала зарегистрируйся через раздел профиля.")
            return
        pubg_player_id = user.pubg_player_id
        pubg_name = user.pubg_name
        pubg_shard = user.pubg_shard or "steam"

    if not pubg_player_id and not pubg_name:
        await reply_tracked_message(update, context, "Нет привязанного PUBG аккаунта. Пройди регистрацию заново.")
        return

    try:
        profile = (
            pubg_client.get_extended_profile_by_id(pubg_player_id, shard=pubg_shard)
            if pubg_player_id
            else pubg_client.get_extended_profile_by_name(pubg_name, shard=pubg_shard)
        )
    except PUBGAPIError as exc:
        await reply_tracked_message(update, context, f"Не удалось обновить PUBG-данные: {exc}")
        return

    try:
        with get_session() as session:
            user = get_user_by_telegram_id(session, update.effective_user.id)
            sync_user_pubg_profile(session, user, profile)
            grant_milestone_achievements(session, user)
            text = (
                "📡 PUBG-данные обновлены\n\n"
                f"🎮 Ник: {profile.nickname}\n"
                f"🆔 PUBG ID: {profile.player_id}\n"
                f"🏅 Ранг: {profile.rank}\n"
                f"⭐ Уровень: {_safe_num(profile.level, 0)}\n"
                f"🎯 Матчи: {profile.total_matches}\n"
                f"🏆 Победы: {profile.total_wins}\n"
                f"🥇 Топ-10: {profile.top10s}\n"
                f"💥 Убийства: {profile.total_kills}\n"
                f"⚔️ K/D: {profile.kd or '—'}\n"
                f"📈 Средний урон: {_safe_num(profile.avg_damage)}\n"
                f"📊 Винрейт: {_safe_num(profile.win_rate)}%"
            )
    except ValueError as exc:
        await reply_tracked_message(update, context, str(exc))
        return

    await reply_tracked_message(update, context, text)


async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена регистрации."""
    context.user_data.pop("reg_profile", None)
    context.user_data.pop("reg_age", None)
    await reply_tracked_message(update, context, "Регистрация отменена.")
    return ConversationHandler.END


async def sync_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /sync_profile для ручного обновления PUBG-данных."""
    await profile_sync(update, context)


async def binding_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /binding для быстрого просмотра привязки."""
    await profile_binding(update, context)


async def profile_card_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await profile_card(update, context)



def register(application) -> None:
    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(f"^{PROFILE_REGISTER}$"), register_entry)],
        states={
            REG_PUBG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_pubg_name)],
            REG_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_age)],
            REG_HOURS: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_hours)],
        },
        fallbacks=[
            MessageHandler(filters.Regex(f"^{CANCEL_ACTION}$"), cancel_registration),
            MessageHandler(filters.Regex(f"^{BACK_TO_MAIN}$"), cancel_registration),
        ],
        per_chat=True,
        per_user=True,
    )
    application.add_handler(conv, group=1)
    application.add_handler(CommandHandler("sync_profile", sync_command), group=1)
    application.add_handler(CommandHandler("binding", binding_command), group=1)
    application.add_handler(CommandHandler("profilecard", profile_card_command), group=1)
    application.add_handler(MessageHandler(filters.Regex(f"^{PROFILE_PROGRESS}$"), profile_progress), group=1)
    application.add_handler(MessageHandler(filters.Regex(f"^{PROFILE_POINTS}$"), profile_points), group=1)
    application.add_handler(MessageHandler(filters.Regex(f"^{PROFILE_ACHIEVEMENTS}$"), profile_achievements), group=1)
    application.add_handler(MessageHandler(filters.Regex(f"^{PROFILE_BINDING}$"), profile_binding), group=1)
    application.add_handler(MessageHandler(filters.Regex(f"^{PROFILE_SYNC}$"), profile_sync), group=1)
    application.add_handler(MessageHandler(filters.Regex(f"^{PROFILE_CARD}$"), profile_card), group=1)
