"""Определение ранга по количеству баллов."""

from __future__ import annotations

from config.constants import BOT_RANKS


def get_rank_for_points(points: int) -> str:
    for min_points, max_points, rank_name in BOT_RANKS:
        if min_points <= points <= max_points:
            return rank_name
    return "Новичок"
