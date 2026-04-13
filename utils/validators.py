"""Валидация пользовательских данных."""
from __future__ import annotations

import re

from config.constants import MIN_AGE


PUBG_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-\.]{3,32}$")


def validate_pubg_id(pubg_id: str) -> bool:
    return bool(PUBG_ID_PATTERN.match(pubg_id.strip()))


def validate_age(age_text: str) -> tuple[bool, int | None]:
    if not age_text.isdigit():
        return False, None
    age = int(age_text)
    return age >= MIN_AGE, age


def validate_weekly_hours(hours_text: str) -> tuple[bool, int | None]:
    if not hours_text.isdigit():
        return False, None
    value = int(hours_text)
    return 0 <= value <= 168, value
