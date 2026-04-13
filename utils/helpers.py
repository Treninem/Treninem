"""Вспомогательные функции общего назначения."""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime

from telegram import ReplyKeyboardMarkup, Update
from telegram.constants import ChatType
from telegram.ext import ContextTypes

from config.constants import BOT_RANK_PRIVILEGES
from config.credentials import OWNER_ID
from config.constants import REFERRAL_PREFIX
from config.settings import MENU_MESSAGE_TTL_SECONDS, TRANSIENT_MESSAGE_TTL_SECONDS
from database import get_session
from database.queries import get_user_by_telegram_id, track_bot_message
from services.notifications import schedule_message_deletion

logger = logging.getLogger("bot_pubg.helpers")


def format_dt(value: datetime | None) -> str:
    if not value:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M")


def format_list(items: list[str]) -> str:
    if not items:
        return "—"
    return "\n".join(f"• {item}" for item in items)


def format_privileges(rank_name: str) -> str:
    return format_list(BOT_RANK_PRIVILEGES.get(rank_name, []))


def is_owner(user_id: int) -> bool:
    return int(user_id) == int(OWNER_ID)


def _is_private_chat(update: Update | None) -> bool:
    return bool(update and update.effective_chat and update.effective_chat.type == ChatType.PRIVATE)


async def delete_message_safe(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int) -> bool:
    """Безопасно удалить сообщение без падения обработчика."""
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except Exception as exc:
        logger.debug("Не удалось удалить сообщение %s/%s: %s", chat_id, message_id, exc)
        return False


async def delete_user_message_safe(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    delay_seconds: int = 1,
) -> None:
    """Поставить на автоудаление исходное сообщение пользователя."""
    if not _is_private_chat(update):
        return
    if not update.effective_message:
        return
    schedule_message_deletion(
        context.job_queue,
        update.effective_chat.id,
        update.effective_message.message_id,
        delay_seconds,
    )


async def _maybe_replace_last_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, *, reply_markup) -> None:
    """Удалить старое меню перед отправкой нового, чтобы в чате оставалось одно актуальное меню."""
    if not _is_private_chat(update):
        return
    if not isinstance(reply_markup, ReplyKeyboardMarkup):
        return

    last_menu_message_id = context.chat_data.get("last_menu_message_id")
    if last_menu_message_id:
        await delete_message_safe(context, update.effective_chat.id, last_menu_message_id)


async def _maybe_replace_last_screen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удалить предыдущее экранное сообщение бота в личке.

    Это сокращает мусор: при открытии нового раздела, карточки или отчёта
    бот оставляет только свежий экран, а не длинную ленту служебных ответов.
    """
    if not _is_private_chat(update):
        return

    last_screen_message_id = context.chat_data.get("last_screen_message_id")
    if not last_screen_message_id:
        return

    last_menu_message_id = context.chat_data.get("last_menu_message_id")
    if last_menu_message_id and last_screen_message_id == last_menu_message_id:
        return

    await delete_message_safe(context, update.effective_chat.id, last_screen_message_id)
    context.chat_data.pop("last_screen_message_id", None)


async def _track_and_schedule(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    chat_id: int,
    message_id: int,
    keep: bool,
    ttl_seconds: int | None,
    is_menu_message: bool,
) -> None:
    with get_session() as session:
        track_bot_message(session, chat_id=chat_id, message_id=message_id)

    if keep:
        return

    if ttl_seconds is None:
        ttl_seconds = MENU_MESSAGE_TTL_SECONDS if is_menu_message else TRANSIENT_MESSAGE_TTL_SECONDS

    if ttl_seconds and ttl_seconds > 0:
        schedule_message_deletion(context.job_queue, chat_id, message_id, ttl_seconds)


async def send_tracked_message(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    *,
    keep: bool = False,
    ttl_seconds: int | None = None,
    **kwargs,
):
    """Отправить сообщение и сохранить его ID в БД для будущей очистки."""
    msg = await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
    await _track_and_schedule(
        context,
        chat_id=chat_id,
        message_id=msg.message_id,
        keep=keep,
        ttl_seconds=ttl_seconds,
        is_menu_message=isinstance(kwargs.get("reply_markup"), ReplyKeyboardMarkup),
    )
    return msg


async def reply_tracked_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    *,
    keep: bool = False,
    ttl_seconds: int | None = None,
    delete_trigger: bool = True,
    replace_menu: bool = True,
    replace_screen: bool = True,
    **kwargs,
):
    """Ответить на сообщение пользователя, сохранить ID ответа бота и навести чистоту в чате.

    По умолчанию:
    - старое меню бота удаляется перед отправкой нового;
    - старый экранный ответ бота удаляется перед новым экраном;
    - сообщение пользователя в личке удаляется через 1 секунду;
    - временные ответы бота сами удаляются через TTL.
    """
    reply_markup = kwargs.get("reply_markup")
    is_menu_message = isinstance(reply_markup, ReplyKeyboardMarkup)

    if replace_menu and is_menu_message:
        await _maybe_replace_last_menu(update, context, reply_markup=reply_markup)
        await _maybe_replace_last_screen(update, context)
    elif replace_screen and not is_menu_message:
        await _maybe_replace_last_screen(update, context)

    msg = await update.effective_message.reply_text(text=text, **kwargs)

    if _is_private_chat(update):
        if is_menu_message:
            context.chat_data["last_menu_message_id"] = msg.message_id
        else:
            context.chat_data["last_screen_message_id"] = msg.message_id

    await _track_and_schedule(
        context,
        chat_id=msg.chat_id,
        message_id=msg.message_id,
        keep=keep,
        ttl_seconds=ttl_seconds,
        is_menu_message=is_menu_message,
    )

    if delete_trigger:
        await delete_user_message_safe(update, context)

    return msg


async def send_tracked_photo(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    photo_bytes: bytes,
    caption: str | None = None,
    *,
    keep: bool = False,
    ttl_seconds: int | None = None,
    **kwargs,
):
    """Отправить фото и сохранить его ID в БД."""
    msg = await context.bot.send_photo(
        chat_id=chat_id,
        photo=photo_bytes,
        caption=caption,
        **kwargs,
    )
    await _track_and_schedule(
        context,
        chat_id=msg.chat_id,
        message_id=msg.message_id,
        keep=keep,
        ttl_seconds=ttl_seconds,
        is_menu_message=False,
    )
    return msg


def dumps_json(data) -> str:
    return json.dumps(data, ensure_ascii=False)


def loads_json(data: str, default=None):
    try:
        return json.loads(data)
    except Exception:
        return default if default is not None else []


def build_progress_chart(points_by_day: list[tuple[str, int]]) -> bytes:
    """Построить PNG-график прогресса за 7 дней."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    x = [item[0][5:] for item in points_by_day]
    y = [item[1] for item in points_by_day]

    fig = plt.figure(figsize=(8, 4))
    ax = fig.add_subplot(111)
    ax.plot(x, y, marker="o")
    ax.set_title("Прогресс за 7 дней")
    ax.set_xlabel("Дата")
    ax.set_ylabel("Баллы за день")
    ax.grid(True)

    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def get_user_display_name(user) -> str:
    return user.pubg_name or user.first_name or user.username or str(user.telegram_id)


def ensure_registered_or_none(telegram_id: int):
    with get_session() as session:
        return get_user_by_telegram_id(session, telegram_id)


def build_ratio_bar(value: float | int | None, maximum: float | int, length: int = 10) -> str:
    if value is None or maximum <= 0:
        return "░" * length
    ratio = max(0.0, min(float(value) / float(maximum), 1.0))
    filled = round(ratio * length)
    return "█" * filled + "░" * (length - filled)


def build_referral_link(bot_username: str, referral_code: str) -> str:
    username = (bot_username or "").lstrip("@")
    return f"https://t.me/{username}?start=ref_{referral_code}"



def build_profile_card_text(user, referral_stats: dict[str, int] | None = None) -> str:
    referral_stats = referral_stats or {"registered": 0, "total": 0, "pending": 0}
    kd = user.pubg_kd or "—"
    wr = f"{user.pubg_win_rate:.1f}%" if user.pubg_win_rate is not None else "—"
    avg_damage = f"{user.pubg_avg_damage:.1f}" if user.pubg_avg_damage is not None else "—"
    matches = user.pubg_total_matches or 0
    wins = user.pubg_total_wins or 0
    kills = user.pubg_total_kills or 0
    return (
        "✨ КАРТОЧКА ИГРОКА ✨\n\n"
        f"🎮 Ник: {user.pubg_name or '—'}\n"
        f"🪪 Telegram: @{user.username if user.username else 'не указан'} | ID: {user.telegram_id}\n"
        f"🏅 Ранг PUBG: {user.pubg_rank or '—'}\n"
        f"⭐ Уровень: {user.pubg_level or '—'}\n"
        f"🔥 Ранг бота: {user.bot_rank} | Баллы: {user.points}\n"
        f"💎 Премиум до: {format_dt(user.premium_until)}\n\n"
        "📈 Боевая сводка\n"
        f"• Матчи: {matches}\n"
        f"• Победы: {wins}\n"
        f"• Убийства: {kills}\n"
        f"• K/D: {kd}\n"
        f"• Средний урон: {avg_damage}\n"
        f"• Винрейт: {wr}\n"
        f"• Топ-10: {user.pubg_top10s or 0}\n\n"
        "🏆 Прогресс клана\n"
        f"• Очки: {user.points} {build_ratio_bar(min(user.points, 1000), 1000)}\n"
        f"• Активность: {build_ratio_bar(min(matches, 200), 200)}\n"
        f"• Приглашено бойцов: {referral_stats.get('registered', 0)}\n"
        f"• Последняя синхронизация: {format_dt(user.pubg_last_sync_at)}"
    )

