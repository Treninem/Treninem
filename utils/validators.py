"""Проверка пользовательских данных."""

from __future__ import annotations

import re
from datetime import datetime


# Поддерживаем:
# - обычный PUBG nickname
# - PUBG player ID формата account.xxxxx
PUBG_NAME_RE = re.compile(r"^[A-Za-z0-9_\-\.]{3,80}$")


def validate_pubg_name(value: str) -> bool:
    """Проверить формат PUBG имени / ID игрока."""
    return bool(PUBG_NAME_RE.match(value.strip()))


def validate_age(value: str) -> tuple[bool, int | None]:
    """Возраст должен быть числом и 13+."""
    try:
        age = int(value)
    except ValueError:
        return False, None
    return age >= 13, age


def validate_hours_per_week(value: str) -> tuple[bool, int | None]:
    """Часы игры в неделю: 1..168."""
    try:
        hours = int(value)
    except ValueError:
        return False, None
    return 1 <= hours <= 168, hours


def parse_datetime_string(value: str) -> datetime | None:
    """Разбор даты формата YYYY-MM-DD HH:MM."""
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        return None
