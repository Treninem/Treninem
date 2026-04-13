"""Логика тренировок."""

from __future__ import annotations

from database.queries import add_training_participant, create_training
from services.notifications import schedule_training_reminder
from utils.helpers import format_dt


def create_training_and_schedule(
    session,
    job_queue,
    mentor_user,
    title: str,
    difficulty: str,
    description: str,
    training_at,
):
    training = create_training(
        session=session,
        mentor_user_id=mentor_user.id,
        title=title,
        difficulty=difficulty,
        description=description,
        training_at=training_at,
    )
    return training


def join_training(session, training_id: int, user_id: int):
    return add_training_participant(session, training_id=training_id, user_id=user_id)
