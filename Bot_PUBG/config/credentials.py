"""Учетные данные проекта.

Важно:
1. В production лучше хранить секреты в переменных окружения.
2. Ниже указаны значения по умолчанию для быстрого старта.
3. При желании вы можете заменить их на os.getenv(...).
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Токен Telegram-бота.
TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "8757727969:AAGxRVCfAsXLjj4C3qW_TqOulw3AwVTctZQ",
)

# Токен PUBG API.
PUBG_API_KEY = os.getenv(
    "PUBG_API_KEY",
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJiNDBhMzhhMC1mNzgzLTAxM2UtMGM1NS00YTJiZjdjMDA0NDYiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNzcyMzU5MzU4LCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6IjQ0OTExNzc2LWU3YzEtNDUzMi1hYzllLTk3NzI3MTYyZmYxZCJ9.W5cL2EZA3eHzku9Rk-Pz1hwcUq4pqtcH4RyUYPcLmy8",
)

# Жестко заданный ID владельца.
OWNER_ID = int(os.getenv("OWNER_ID", "2097006037"))
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "@Treninem")
DEFAULT_ADMIN_CHAT_ID = int(os.getenv("DEFAULT_ADMIN_CHAT_ID", "2097006037"))

# Ссылка на бота.
BOT_USERNAME = os.getenv("BOT_USERNAME", "PUBG_The_clan_bot")
BOT_LINK = f"https://t.me/{BOT_USERNAME}"

# SQLite база для Bothost / локального запуска.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'pubg_bot.sqlite3'}",
)

# Заглушки для Yandex / Object Storage.
YANDEX_CLOUD_FOLDER_ID = os.getenv("YANDEX_CLOUD_FOLDER_ID", "")
YANDEX_STORAGE_BUCKET = os.getenv("YANDEX_STORAGE_BUCKET", "")
YANDEX_ACCESS_KEY = os.getenv("YANDEX_ACCESS_KEY", "")
YANDEX_SECRET_KEY = os.getenv("YANDEX_SECRET_KEY", "")
