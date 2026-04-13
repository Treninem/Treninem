"""Расчет баллов по действиям."""
from __future__ import annotations

from config.constants import POINT_EVENTS


def get_points_for_event(event_name: str) -> int:
    return POINT_EVENTS.get(event_name, 0)
