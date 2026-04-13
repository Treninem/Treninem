"""Секреты и параметры подключения.

ВАЖНО:
1. Файл уже содержит значения, которые были переданы пользователем, поэтому проект
   может стартовать "как есть".
2. Для продакшена настоятельно рекомендуется задавать эти значения через переменные
   окружения Bothost, а токены после первого запуска перевыпустить.
"""

from __future__ import annotations

import os

# Токен Telegram-бота.
BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    "8757727969:AAGxRVCfAsXLjj4C3qW_TqOulw3AwVTctZQ",
)

# API-ключ PUBG.
PUBG_API_KEY = os.getenv(
    "PUBG_API_KEY",
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJqdGkiOiJiNDBhMzhhMC1mNzgzLTAxM2UtMGM1NS00YTJiZjdjMDA0NDYiLCJpc3MiOiJnYW1lbG9ja2VyIiwiaWF0IjoxNzcyMzU5MzU4LCJwdWIiOiJibHVlaG9sZSIsInRpdGxlIjoicHViZyIsImFwcCI6IjQ0OTExNzc2LWU3YzEtNDUzMi1hYzllLTk3NzI3MTYyZmYxZCJ9.W5cL2EZA3eHzku9Rk-Pz1hwcUq4pqtcH4RyUYPcLmy8",
)

# ID владельца бота.
OWNER_ID = int(os.getenv("OWNER_ID", "2097006037"))

# Username владельца без @.
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "Treninem")

# ID текущего чата владельца, можно использовать для сервисных уведомлений.
OWNER_CHAT_ID = int(os.getenv("OWNER_CHAT_ID", "2097006037"))

# URL базы данных.
# Для Bothost удобно оставить SQLite, чтобы запуск был максимально простым.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot_pubg.db")

# Директория локального хранилища файлов.
STORAGE_DIR = os.getenv("STORAGE_DIR", "storage")

# Необязательные параметры для совместимости с Object Storage / S3.
YC_S3_ENDPOINT = os.getenv("YC_S3_ENDPOINT", "")
YC_S3_ACCESS_KEY = os.getenv("YC_S3_ACCESS_KEY", "")
YC_S3_SECRET_KEY = os.getenv("YC_S3_SECRET_KEY", "")
YC_S3_BUCKET = os.getenv("YC_S3_BUCKET", "")
