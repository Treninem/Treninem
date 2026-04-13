"""Начисление и списание баллов."""

from __future__ import annotations

from database.queries import add_point_transaction, create_achievement


def apply_points(session, user, amount: int, reason: str, meta: dict | None = None):
    old_rank = user.bot_rank
    trx = add_point_transaction(session, user=user, amount=amount, reason=reason, meta=meta)
    if user.bot_rank != old_rank:
        create_achievement(
            session,
            user.id,
            title=f"Новый ранг: {user.bot_rank}",
            description=f"Пользователь получил новый ранг в боте за счёт накопленных баллов.",
        )
    return trx
