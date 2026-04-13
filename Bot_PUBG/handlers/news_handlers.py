"""Обработчики раздела «Новости»."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from config.constants import NEWS_AUTO_DELETE_SECONDS
from services.pubg_api import PUBGAPIClient


async def latest_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = PUBGAPIClient()
    news = client.get_news(5)
    messages = []
    for item in news:
        msg = await update.message.reply_text(f"📣 {item['title']}\n{item['description']}\n{item['url']}")
        messages.append(msg)
        context.job_queue.run_once(delete_news_message_job, NEWS_AUTO_DELETE_SECONDS, data={"chat_id": msg.chat_id, "message_id": msg.message_id})


async def events_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = PUBGAPIClient()
    items = client.get_events(5)
    text = "🗓️ События:\n\n" + "\n".join(f"• {i['title']} — {i['description']}\n{i['url']}" for i in items)
    await update.message.reply_text(text)


async def game_updates(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    client = PUBGAPIClient()
    patches = client.get_patches(5)
    text = "🎮 Обновления игры:\n\n" + "\n".join(f"• {p['version']} | {p['date']}\n{p['changes']}" for p in patches)
    await update.message.reply_text(text)


async def delete_news_message_job(context) -> None:
    data = context.job.data
    try:
        await context.bot.delete_message(chat_id=data["chat_id"], message_id=data["message_id"])
    except Exception:
        pass


def register(application) -> None:
    application.add_handler(MessageHandler(filters.Regex(r"^📣 Последние новости$"), latest_news))
    application.add_handler(MessageHandler(filters.Regex(r"^🗓️ События$"), events_news))
    application.add_handler(MessageHandler(filters.Regex(r"^🎮 Обновления игры$"), game_updates))
