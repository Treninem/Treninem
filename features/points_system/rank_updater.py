"""Обновление рангов пользователя по количеству баллов."""
from __future__ import annotations

from config.constants import BOT_RANKS


def resolve_bot_rank(points: int) -> str:
    for rank_name, (left, right) in BOT_RANKS.items():
        if left <= points <= right:
            return rank_name
    return "Новичок"
