"""Раздел «Новости»."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from config.constants import NEWS_EVENTS, NEWS_LATEST, NEWS_PATCHES
from config.settings import MAX_NEWS_ITEMS, NEWS_DELETE_AFTER_SECONDS
from database import get_session
from database.queries import cache_news_item
from services.notifications import schedule_message_deletion
from services.pubg_api import pubg_client
from utils.helpers import reply_tracked_message
from utils.keyboards import news_digest_keyboard


async def _send_news(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str | None = None) -> None:
    items = pubg_client.fetch_latest_news(count=MAX_NEWS_ITEMS)
    if category:
        items = [item for item in items if item["category"] == category]
    if not items:
        await reply_tracked_message(update, context, "Сейчас новости не найдены.")
        return

    selected_items = items[:MAX_NEWS_ITEMS]
    for item in selected_items:
        with get_session() as session:
            cache_news_item(
                session=session,
                title=item["title"],
                description=item["description"],
                url=item["url"],
                category=item["category"],
                published_at=item["published_at"],
            )

    lines = ["📰 Новости PUBG\n"]
    for idx, item in enumerate(selected_items, start=1):
        published = item["published_at"].strftime("%Y-%m-%d %H:%M") if item["published_at"] else "—"
        lines.append(
            f"{idx}. {item['title']}\n"
            f"{item['description'][:220]}\n"
            f"Категория: {item['category']} | Дата: {published}\n"
        )

    msg = await reply_tracked_message(
        update,
        context,
        "\n".join(lines),
        reply_markup=news_digest_keyboard(selected_items),
    )
    schedule_message_deletion(context.job_queue, msg.chat_id, msg.message_id, NEWS_DELETE_AFTER_SECONDS)


async def latest_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_news(update, context, category=None)


async def event_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_news(update, context, category="event")


async def patch_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_news(update, context, category="patch")


def register(application) -> None:
    application.add_handler(MessageHandler(filters.Regex(f"^{NEWS_LATEST}$"), latest_news), group=3)
    application.add_handler(MessageHandler(filters.Regex(f"^{NEWS_EVENTS}$"), event_news), group=3)
    application.add_handler(MessageHandler(filters.Regex(f"^{NEWS_PATCHES}$"), patch_news), group=3)
