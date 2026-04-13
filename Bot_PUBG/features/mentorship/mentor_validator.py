"""Проверка, можно ли назначить пользователя наставником."""
from __future__ import annotations

from config.constants import MIN_MENTOR_PUBG_RANK, PUBG_RANK_WEIGHT


def is_rank_eligible_for_mentor(pubg_rank: str | None) -> bool:
    if not pubg_rank:
        return False
    return PUBG_RANK_WEIGHT.get(pubg_rank, -1) >= PUBG_RANK_WEIGHT.get(MIN_MENTOR_PUBG_RANK, 999)


def mentor_can_teach_student(mentor_rank: str | None, student_rank: str | None) -> bool:
    if not mentor_rank or not student_rank:
        return False
    return PUBG_RANK_WEIGHT.get(mentor_rank, -1) > PUBG_RANK_WEIGHT.get(student_rank, 999)
