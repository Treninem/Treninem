"""Общие вспомогательные функции."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

import matplotlib.pyplot as plt

from config.constants import DEFAULT_PREMIUM_PRIVILEGES


def format_user_display(user) -> str:
    return user.pubg_nickname or user.first_name or user.username or str(user.telegram_id)


def build_progress_chart(results: list) -> BytesIO:
    """Строит график прогресса за 7 дней и возвращает буфер изображения."""
    dates = [r.test_date for r in results]
    values = [r.correct_answers for r in results]

    fig = plt.figure(figsize=(8, 4))
    plt.plot(dates, values, marker="o")
    plt.title("Прогресс за последние 7 дней")
    plt.xlabel("Дата")
    plt.ylabel("Верные ответы")
    plt.xticks(rotation=45)
    plt.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)
    buffer.seek(0)
    return buffer


def premium_privileges_text() -> str:
    return "\n".join(f"• {item}" for item in DEFAULT_PREMIUM_PRIVILEGES)


def now_utc() -> datetime:
    return datetime.utcnow()
