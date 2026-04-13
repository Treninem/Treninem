"""Настройки поведения бота."""
from __future__ import annotations

from zoneinfo import ZoneInfo

APP_NAME = "PUBG Clan Bot"
APP_VERSION = "1.0.0"
DEFAULT_TIMEZONE = "Europe/Amsterdam"
DEFAULT_TZINFO = ZoneInfo(DEFAULT_TIMEZONE)

# Время ежедневного теста.
DAILY_TEST_HOUR = 10
DAILY_TEST_MINUTE = 0
REMINDER_MINUTES_BEFORE_TEST = 15

# Технические настройки.
HTTP_TIMEOUT = 20
PUBG_PLATFORM_SHARD = "steam"
LOG_LEVEL = "INFO"
ENABLE_YANDEX_INTEGRATION = False

# Настройки long polling.
DROP_PENDING_UPDATES = True
ALLOWED_UPDATES = ["message", "callback_query", "chat_member", "my_chat_member"]

# Сколько новостей показывать.
DEFAULT_NEWS_COUNT = 5
DEFAULT_EVENTS_COUNT = 5
DEFAULT_PATCHES_COUNT = 5

# Время жизни ссылок и вспомогательных значений.
TEMP_GROUP_CHAT_NAME = "PUBG Friends Chat"
TICKET_PREFIX = "PUBG-TICKET"
