"""Утилиты работы с тренировками."""
from __future__ import annotations

from datetime import datetime

from database.queries import create_training


def schedule_training(mentor_telegram_id: int, title: str, difficulty: str, scheduled_at: datetime, topic: str = ""):
    return create_training(mentor_telegram_id, title, difficulty, scheduled_at, topic)
