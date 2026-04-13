"""Утилиты работы с заданиями наставника."""
from __future__ import annotations

from datetime import datetime

from database.queries import complete_task, create_mentor_task


def assign_task(mentor_telegram_id: int, student_telegram_id: int, title: str, description: str, deadline: datetime | None, reward_points: int = 50):
    return create_mentor_task(mentor_telegram_id, student_telegram_id, title, description, deadline, reward_points)


def mark_task_completed(task_id: int) -> bool:
    return complete_task(task_id)
