"""ORM-модели проекта."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from . import Base


class User(Base):
    """Пользователь бота.

    ВАЖНО:
    - telegram_id связывает аккаунт Telegram с профилем в боте.
    - pubg_player_id хранит уникальный ID игрока из PUBG API.
    - расширенные PUBG-поля позволяют хранить быстрый срез статистики,
      чтобы не ходить в API при каждом открытии профиля.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    pubg_player_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    pubg_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pubg_rank: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pubg_kd: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pubg_shard: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Расширенные данные из PUBG API.
    pubg_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pubg_total_matches: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pubg_total_wins: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pubg_total_kills: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pubg_total_damage: Mapped[float | None] = mapped_column(Float, nullable=True)
    pubg_headshot_kills: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pubg_avg_damage: Mapped[float | None] = mapped_column(Float, nullable=True)
    pubg_win_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    pubg_top10s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pubg_stats_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    pubg_last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    pubg_bound_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hours_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timezone: Mapped[str] = mapped_column(String(100), default="Europe/Moscow")

    is_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_mentor: Mapped[bool] = mapped_column(Boolean, default=False)
    mentor_active: Mapped[bool] = mapped_column(Boolean, default=False)

    points: Mapped[int] = mapped_column(Integer, default=0)
    bot_rank: Mapped[str] = mapped_column(String(100), default="Новичок")
    premium_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    referred_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    referral_code: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    referral_points_paid: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    mentor_profile = relationship("MentorProfile", back_populates="user", uselist=False)
    achievements = relationship("Achievement", back_populates="user")
    point_transactions = relationship("PointTransaction", back_populates="user")


class Friend(Base):
    """Друг пользователя, добавленный вручную по PUBG ID."""

    __tablename__ = "friends"
    __table_args__ = (
        UniqueConstraint("user_id", "friend_pubg_player_id", name="uq_user_friend_pubg"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    friend_pubg_player_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    friend_pubg_name: Mapped[str] = mapped_column(String(255), nullable=False)
    friend_pubg_rank: Mapped[str | None] = mapped_column(String(255), nullable=True)
    friend_kd: Mapped[str | None] = mapped_column(String(50), nullable=True)
    linked_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MentorProfile(Base):
    """Профиль наставника."""

    __tablename__ = "mentor_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    specialization: Mapped[str] = mapped_column(String(255))
    schedule_text: Mapped[str] = mapped_column(Text)
    teaching_style: Mapped[str] = mapped_column(Text)
    free_slots: Mapped[int] = mapped_column(Integer, default=3)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="mentor_profile")


class MentorStudent(Base):
    """Связь наставник ↔ подопечный."""

    __tablename__ = "mentor_students"
    __table_args__ = (
        UniqueConstraint("mentor_user_id", "student_user_id", name="uq_mentor_student"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mentor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Training(Base):
    """Тренировка наставника."""

    __tablename__ = "trainings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mentor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    difficulty: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    training_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(50), default="scheduled")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TrainingParticipant(Base):
    """Участник тренировки."""

    __tablename__ = "training_participants"
    __table_args__ = (
        UniqueConstraint("training_id", "user_id", name="uq_training_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    training_id: Mapped[int] = mapped_column(ForeignKey("trainings.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    attended: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    warned_absence: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MentorTask(Base):
    """Задание, выданное наставником."""

    __tablename__ = "mentor_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mentor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reward_points: Mapped[int] = mapped_column(Integer, default=50)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Achievement(Base):
    """Достижения пользователя."""

    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="achievements")


class PointTransaction(Base):
    """История начислений и списаний баллов."""

    __tablename__ = "point_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(255))
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="point_transactions")


class DailyTestSession(Base):
    """Сессия ежедневного теста."""

    __tablename__ = "daily_test_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, index=True)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    test_payload_json: Mapped[str] = mapped_column(Text)
    answers_json: Mapped[str] = mapped_column(Text, default="[]")

    score: Mapped[int] = mapped_column(Integer, default=0)
    bonus_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FeedbackTicket(Base):
    """Тикет обратной связи."""

    __tablename__ = "feedback_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ticket_type: Mapped[str] = mapped_column(String(100))
    subject: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    screenshot_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ChatInfo(Base):
    """Чат, в который был добавлен бот."""

    __tablename__ = "chat_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chat_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    members_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    added_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BotMessage(Base):
    """Сообщения, отправленные ботом, чтобы их можно было массово удалить командой админа."""

    __tablename__ = "bot_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(Integer, index=True)
    message_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NewsCache(Base):
    """Кэш новостей, чтобы не дублировать лишние запросы."""

    __tablename__ = "news_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
