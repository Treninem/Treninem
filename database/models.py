"""SQLAlchemy ORM модели."""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from config.credentials import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    pubg_player_id = Column(String(255), nullable=True)
    pubg_nickname = Column(String(255), nullable=True)
    pubg_rank = Column(String(100), nullable=True)
    age = Column(Integer, nullable=True)
    weekly_hours = Column(Integer, default=0)
    timezone = Column(String(64), default="Europe/Amsterdam")
    is_registered = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    premium_until = Column(DateTime, nullable=True)
    is_mentor = Column(Boolean, default=False)
    mentor_specialization = Column(String(255), nullable=True)
    mentor_schedule = Column(Text, nullable=True)
    mentor_style = Column(Text, nullable=True)
    points = Column(Integer, default=0)
    bot_rank = Column(String(100), default="Новичок")
    last_activity_at = Column(DateTime, default=datetime.utcnow)

    mentor_students = relationship("Mentorship", foreign_keys="Mentorship.mentor_user_id", back_populates="mentor")
    student_mentor = relationship("Mentorship", foreign_keys="Mentorship.student_user_id", back_populates="student")


class Chat(Base, TimestampMixin):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True, nullable=False)
    title = Column(String(255), nullable=True)
    chat_type = Column(String(50), nullable=False, default="private")
    members_count = Column(Integer, default=0)
    added_by_user_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)


class BotMessage(Base, TimestampMixin):
    __tablename__ = "bot_messages"

    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, nullable=False)
    message_id = Column(Integer, nullable=False)
    purpose = Column(String(100), nullable=True)


class Friendship(Base, TimestampMixin):
    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("owner_user_id", "friend_user_id", name="uq_friendship"),)

    id = Column(Integer, primary_key=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    friend_pubg_id = Column(String(255), nullable=True)


class Mentorship(Base, TimestampMixin):
    __tablename__ = "mentorships"
    __table_args__ = (UniqueConstraint("mentor_user_id", "student_user_id", name="uq_mentorship"),)

    id = Column(Integer, primary_key=True)
    mentor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    student_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)

    mentor = relationship("User", foreign_keys=[mentor_user_id], back_populates="mentor_students")
    student = relationship("User", foreign_keys=[student_user_id], back_populates="student_mentor")


class Training(Base, TimestampMixin):
    __tablename__ = "trainings"

    id = Column(Integer, primary_key=True)
    mentor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    difficulty = Column(String(100), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    topic = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False)


class TrainingParticipant(Base, TimestampMixin):
    __tablename__ = "training_participants"
    __table_args__ = (UniqueConstraint("training_id", "user_id", name="uq_training_participant"),)

    id = Column(Integer, primary_key=True)
    training_id = Column(Integer, ForeignKey("trainings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    attended = Column(Boolean, default=False)
    warned_absence = Column(Boolean, default=False)


class MentorTask(Base, TimestampMixin):
    __tablename__ = "mentor_tasks"

    id = Column(Integer, primary_key=True)
    mentor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    student_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    deadline = Column(DateTime, nullable=True)
    reward_points = Column(Integer, default=50)
    status = Column(String(50), default="active")


class PointTransaction(Base, TimestampMixin):
    __tablename__ = "point_transactions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    reason = Column(String(100), nullable=False)
    comment = Column(Text, nullable=True)


class Achievement(Base, TimestampMixin):
    __tablename__ = "achievements"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)


class DailyTestResult(Base, TimestampMixin):
    __tablename__ = "daily_test_results"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    test_date = Column(String(20), nullable=False)
    correct_answers = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    bonus_correct = Column(Boolean, default=False)
    details_json = Column(Text, nullable=True)


class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticket_type = Column(String(50), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    screenshot_file_id = Column(String(255), nullable=True)
    status = Column(String(50), default="new")


def init_db() -> None:
    """Создает все таблицы, если их еще нет."""
    Base.metadata.create_all(bind=engine)
