"""Проверки для активации наставника."""

from __future__ import annotations

from config.constants import PUBG_RANK_ORDER
from services.pubg_api import pubg_client


def normalize_rank(rank_name: str | None) -> str:
    if not rank_name:
        return "unranked"
    return rank_name.lower().split()[0]


def can_be_mentor(rank_name: str | None) -> bool:
    return pubg_client.is_mentor_rank(rank_name)


def mentor_can_teach_student(mentor_rank: str | None, student_rank: str | None) -> bool:
    mentor_value = PUBG_RANK_ORDER.get(normalize_rank(mentor_rank), 0)
    student_value = PUBG_RANK_ORDER.get(normalize_rank(student_rank), 0)
    return mentor_value > student_value
