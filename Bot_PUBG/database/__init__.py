"""Инициализация базы данных SQLAlchemy."""

from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from config.credentials import DATABASE_URL

Base = declarative_base()

engine_kwargs = {"future": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
)


@contextmanager
def get_session():
    """Контекстный менеджер для безопасной работы с сессией БД."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


_SQLITE_USER_MIGRATIONS = {
    "pubg_level": "ALTER TABLE users ADD COLUMN pubg_level INTEGER",
    "pubg_total_matches": "ALTER TABLE users ADD COLUMN pubg_total_matches INTEGER",
    "pubg_total_wins": "ALTER TABLE users ADD COLUMN pubg_total_wins INTEGER",
    "pubg_total_kills": "ALTER TABLE users ADD COLUMN pubg_total_kills INTEGER",
    "pubg_total_damage": "ALTER TABLE users ADD COLUMN pubg_total_damage FLOAT",
    "pubg_headshot_kills": "ALTER TABLE users ADD COLUMN pubg_headshot_kills INTEGER",
    "pubg_avg_damage": "ALTER TABLE users ADD COLUMN pubg_avg_damage FLOAT",
    "pubg_win_rate": "ALTER TABLE users ADD COLUMN pubg_win_rate FLOAT",
    "pubg_top10s": "ALTER TABLE users ADD COLUMN pubg_top10s INTEGER",
    "pubg_stats_json": "ALTER TABLE users ADD COLUMN pubg_stats_json TEXT",
    "pubg_last_sync_at": "ALTER TABLE users ADD COLUMN pubg_last_sync_at DATETIME",
    "pubg_bound_at": "ALTER TABLE users ADD COLUMN pubg_bound_at DATETIME",
    "referred_by_user_id": "ALTER TABLE users ADD COLUMN referred_by_user_id INTEGER",
    "referral_code": "ALTER TABLE users ADD COLUMN referral_code VARCHAR(64)",
    "referral_points_paid": "ALTER TABLE users ADD COLUMN referral_points_paid BOOLEAN DEFAULT 0",
}


def _ensure_sqlite_migrations() -> None:
    """Мягко добавить новые колонки в существующую SQLite-базу.

    Это нужно для случаев, когда пользователь обновляет архив поверх старого файла
    bot_pubg.db, а не запускает проект на чистой базе.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "users" not in inspector.get_table_names():
        return

    existing = {item["name"] for item in inspector.get_columns("users")}
    with engine.begin() as conn:
        for column_name, ddl in _SQLITE_USER_MIGRATIONS.items():
            if column_name not in existing:
                conn.execute(text(ddl))
        # Индексы нужны для быстрых проверок привязки PUBG аккаунта и рефералов.
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_pubg_player_id ON users (pubg_player_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_referral_code ON users (referral_code)"))


def init_db() -> None:
    """Создать все таблицы проекта и выполнить мягкие миграции."""
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_migrations()
