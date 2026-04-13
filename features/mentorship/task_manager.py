"""Управление заданиями наставников."""

from __future__ import annotations

from config.constants import POINTS_TASK_COMPLETED
from database.queries import complete_task, create_mentor_task
from features.points_system.calculator import apply_points


def create_task_for_student(
    session,
    mentor_user_id: int,
    student_user_id: int,
    title: str,
    description: str,
    due_at,
    reward_points: int = POINTS_TASK_COMPLETED,
):
    return create_mentor_task(
        session=session,
        mentor_user_id=mentor_user_id,
        student_user_id=student_user_id,
        title=title,
        description=description,
        reward_points=reward_points,
        due_at=due_at,
    )


def complete_task_and_reward(session, task_id: int, user):
    task = complete_task(session, task_id=task_id)
    if task and task.status == "completed":
        apply_points(
            session=session,
            user=user,
            amount=task.reward_points,
            reason=f"Выполнение задания наставника #{task.id}",
            meta={"task_id": task.id},
        )
    return task
