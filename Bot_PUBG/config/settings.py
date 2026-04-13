"""Общие настройки бота: планировщик, часовые пояса, лимиты, интервалы."""

from __future__ import annotations

import os

# Часовой пояс самого приложения.
BOT_TIMEZONE = os.getenv("BOT_TIMEZONE", "Europe/Moscow")

# Часовой пояс пользователя по умолчанию.
DEFAULT_USER_TIMEZONE = os.getenv("DEFAULT_USER_TIMEZONE", "Europe/Moscow")

# Время ежедневного теста.
DAILY_TEST_HOUR = int(os.getenv("DAILY_TEST_HOUR", "10"))
DAILY_TEST_MINUTE = int(os.getenv("DAILY_TEST_MINUTE", "0"))
DAILY_TEST_REMINDER_MINUTES = int(os.getenv("DAILY_TEST_REMINDER_MINUTES", "15"))

# Автоудаление данных регистрации.
DELETE_PRIVATE_DATA_AFTER_SECONDS = int(os.getenv("DELETE_PRIVATE_DATA_AFTER_SECONDS", "10"))

# Автоудаление новостей, отправленных ботом.
NEWS_DELETE_AFTER_SECONDS = int(os.getenv("NEWS_DELETE_AFTER_SECONDS", "3600"))

# Автоудаление временных сообщений бота.
TRANSIENT_MESSAGE_TTL_SECONDS = int(os.getenv("TRANSIENT_MESSAGE_TTL_SECONDS", "90"))

# Время жизни меню, если пользователь долго ничего не делает.
MENU_MESSAGE_TTL_SECONDS = int(os.getenv("MENU_MESSAGE_TTL_SECONDS", "300"))


# Время жизни итогов теста после завершения.
DAILY_TEST_RESULT_TTL_SECONDS = int(os.getenv("DAILY_TEST_RESULT_TTL_SECONDS", "600"))

# Время жизни напоминания о тесте.
DAILY_TEST_REMINDER_TTL_SECONDS = int(os.getenv("DAILY_TEST_REMINDER_TTL_SECONDS", "1800"))

# Интервал проверки неактивности пользователей.
INACTIVITY_CHECK_HOURS = int(os.getenv("INACTIVITY_CHECK_HOURS", "24"))
INACTIVITY_DAYS_LIMIT = int(os.getenv("INACTIVITY_DAYS_LIMIT", "7"))

# Ограничения.
MAX_NEWS_ITEMS = int(os.getenv("MAX_NEWS_ITEMS", "5"))
MAX_FRIENDS = int(os.getenv("MAX_FRIENDS", "100"))
MAX_TRAINING_PARTICIPANTS = int(os.getenv("MAX_TRAINING_PARTICIPANTS", "10"))

# PUBG shard по умолчанию.
DEFAULT_PUBG_SHARD = os.getenv("DEFAULT_PUBG_SHARD", "steam")

# Текстовые настройки.
BOT_NAME = os.getenv("BOT_NAME", "Клановый PUBG бот")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "logs/bot.log")

# Режим отладки.
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
