"""CRUD и бизнес-запросы к БД."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from database.models import (
    Achievement,
    BotMessage,
    Chat,
    DailyTestResult,
    Friendship,
    MentorTask,
    Mentorship,
    PointTransaction,
    SessionLocal,
    Ticket,
    Training,
    TrainingParticipant,
    User,
)


@contextmanager
def get_session() -> Iterable[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_or_create_user(
    telegram_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> User:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            session.add(user)
            session.flush()
        else:
            user.username = username or user.username
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
            user.last_activity_at = datetime.utcnow()
        session.expunge(user)
        return user


def get_user_by_telegram_id(telegram_id: int) -> Optional[User]:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            session.expunge(user)
        return user


def update_user_profile(telegram_id: int, **kwargs) -> Optional[User]:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return None
        for key, value in kwargs.items():
            setattr(user, key, value)
        user.last_activity_at = datetime.utcnow()
        session.flush()
        session.expunge(user)
        return user


def save_bot_message(chat_id: int, message_id: int, purpose: str | None = None) -> None:
    with get_session() as session:
        session.add(BotMessage(chat_id=chat_id, message_id=message_id, purpose=purpose))


def list_bot_messages(chat_id: int) -> list[BotMessage]:
    with get_session() as session:
        rows = session.query(BotMessage).filter(BotMessage.chat_id == chat_id).all()
        for row in rows:
            session.expunge(row)
        return rows


def delete_bot_messages_records(chat_id: int) -> int:
    with get_session() as session:
        count = session.query(BotMessage).filter(BotMessage.chat_id == chat_id).delete()
        return count


def upsert_chat(chat_id: int, title: str | None, chat_type: str, members_count: int = 0, added_by_user_id: int | None = None) -> None:
    with get_session() as session:
        chat = session.query(Chat).filter(Chat.chat_id == chat_id).first()
        if not chat:
            chat = Chat(chat_id=chat_id, title=title, chat_type=chat_type, members_count=members_count, added_by_user_id=added_by_user_id)
            session.add(chat)
        else:
            chat.title = title or chat.title
            chat.chat_type = chat_type
            chat.members_count = members_count
            chat.added_by_user_id = added_by_user_id or chat.added_by_user_id
            chat.is_active = True


def deactivate_chat(chat_id: int) -> None:
    with get_session() as session:
        chat = session.query(Chat).filter(Chat.chat_id == chat_id).first()
        if chat:
            chat.is_active = False


def list_active_chats() -> list[Chat]:
    with get_session() as session:
        chats = session.query(Chat).filter(Chat.is_active == True).order_by(Chat.created_at.desc()).all()
        for row in chats:
            session.expunge(row)
        return chats


def add_points(telegram_id: int, amount: int, reason: str, comment: str | None = None) -> Optional[User]:
    from features.points_system.rank_updater import resolve_bot_rank
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return None
        user.points = max(0, (user.points or 0) + amount)
        user.bot_rank = resolve_bot_rank(user.points)
        user.last_activity_at = datetime.utcnow()
        session.add(PointTransaction(user_id=user.id, amount=amount, reason=reason, comment=comment))
        session.flush()
        session.expunge(user)
        return user


def get_point_history(telegram_id: int, limit: int = 20) -> list[PointTransaction]:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return []
        history = (
            session.query(PointTransaction)
            .filter(PointTransaction.user_id == user.id)
            .order_by(desc(PointTransaction.created_at))
            .limit(limit)
            .all()
        )
        for row in history:
            session.expunge(row)
        return history


def add_achievement(telegram_id: int, title: str, description: str = "") -> None:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            session.add(Achievement(user_id=user.id, title=title, description=description))


def list_achievements(telegram_id: int) -> list[Achievement]:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return []
        items = session.query(Achievement).filter(Achievement.user_id == user.id).order_by(desc(Achievement.created_at)).all()
        for row in items:
            session.expunge(row)
        return items


def create_or_update_registration(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    pubg_player_id: str,
    pubg_nickname: str,
    pubg_rank: str,
    age: int,
    weekly_hours: int,
    timezone: str = "Europe/Amsterdam",
) -> User:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(telegram_id=telegram_id)
            session.add(user)
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.pubg_player_id = pubg_player_id
        user.pubg_nickname = pubg_nickname
        user.pubg_rank = pubg_rank
        user.age = age
        user.weekly_hours = weekly_hours
        user.timezone = timezone
        user.is_registered = True
        user.last_activity_at = datetime.utcnow()
        session.flush()
        session.expunge(user)
        return user


def save_daily_test_result(telegram_id: int, test_date: str, correct_answers: int, total_questions: int, bonus_correct: bool, details_json: str) -> None:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            session.add(DailyTestResult(
                user_id=user.id,
                test_date=test_date,
                correct_answers=correct_answers,
                total_questions=total_questions,
                bonus_correct=bonus_correct,
                details_json=details_json,
            ))


def get_test_results_last_days(telegram_id: int, limit: int = 7) -> list[DailyTestResult]:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return []
        items = session.query(DailyTestResult).filter(DailyTestResult.user_id == user.id).order_by(desc(DailyTestResult.created_at)).limit(limit).all()
        for row in items:
            session.expunge(row)
        return list(reversed(items))


def create_ticket(telegram_id: int, ticket_type: str, subject: str, message: str, screenshot_file_id: str | None = None) -> Ticket | None:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return None
        ticket = Ticket(user_id=user.id, ticket_type=ticket_type, subject=subject, message=message, screenshot_file_id=screenshot_file_id)
        session.add(ticket)
        session.flush()
        session.expunge(ticket)
        return ticket


def apply_mentor_status(telegram_id: int, specialization: str, schedule: str, style: str) -> Optional[User]:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return None
        user.is_mentor = True
        user.mentor_specialization = specialization
        user.mentor_schedule = schedule
        user.mentor_style = style
        session.flush()
        session.expunge(user)
        return user


def list_mentors(rank_filter: str | None = None, specialization_filter: str | None = None) -> list[User]:
    with get_session() as session:
        query = session.query(User).filter(User.is_mentor == True, User.is_registered == True)
        if rank_filter:
            query = query.filter(User.pubg_rank == rank_filter)
        if specialization_filter:
            query = query.filter(User.mentor_specialization.ilike(f"%{specialization_filter}%"))
        mentors = query.order_by(desc(User.points)).all()
        for row in mentors:
            session.expunge(row)
        return mentors


def create_mentorship(mentor_telegram_id: int, student_telegram_id: int) -> bool:
    with get_session() as session:
        mentor = session.query(User).filter(User.telegram_id == mentor_telegram_id).first()
        student = session.query(User).filter(User.telegram_id == student_telegram_id).first()
        if not mentor or not student:
            return False
        exists = session.query(Mentorship).filter(Mentorship.mentor_user_id == mentor.id, Mentorship.student_user_id == student.id).first()
        if exists:
            return True
        session.add(Mentorship(mentor_user_id=mentor.id, student_user_id=student.id, is_active=True))
        return True


def list_students_for_mentor(mentor_telegram_id: int) -> list[User]:
    with get_session() as session:
        mentor = session.query(User).filter(User.telegram_id == mentor_telegram_id).first()
        if not mentor:
            return []
        students = (
            session.query(User)
            .join(Mentorship, Mentorship.student_user_id == User.id)
            .filter(Mentorship.mentor_user_id == mentor.id, Mentorship.is_active == True)
            .all()
        )
        for row in students:
            session.expunge(row)
        return students


def create_training(mentor_telegram_id: int, title: str, difficulty: str, scheduled_at: datetime, topic: str = "") -> Training | None:
    with get_session() as session:
        mentor = session.query(User).filter(User.telegram_id == mentor_telegram_id).first()
        if not mentor:
            return None
        training = Training(mentor_user_id=mentor.id, title=title, difficulty=difficulty, scheduled_at=scheduled_at, topic=topic)
        session.add(training)
        session.flush()
        session.expunge(training)
        return training


def list_trainings_for_user(telegram_id: int) -> list[Training]:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return []
        trainings = session.query(Training).filter(Training.mentor_user_id == user.id).order_by(desc(Training.scheduled_at)).all()
        for row in trainings:
            session.expunge(row)
        return trainings


def create_mentor_task(mentor_telegram_id: int, student_telegram_id: int, title: str, description: str, deadline: datetime | None, reward_points: int = 50) -> MentorTask | None:
    with get_session() as session:
        mentor = session.query(User).filter(User.telegram_id == mentor_telegram_id).first()
        student = session.query(User).filter(User.telegram_id == student_telegram_id).first()
        if not mentor or not student:
            return None
        task = MentorTask(
            mentor_user_id=mentor.id,
            student_user_id=student.id,
            title=title,
            description=description,
            deadline=deadline,
            reward_points=reward_points,
        )
        session.add(task)
        session.flush()
        session.expunge(task)
        return task


def list_tasks_for_user(telegram_id: int) -> list[MentorTask]:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return []
        items = session.query(MentorTask).filter(MentorTask.student_user_id == user.id).order_by(desc(MentorTask.created_at)).all()
        for row in items:
            session.expunge(row)
        return items


def complete_task(task_id: int) -> bool:
    with get_session() as session:
        task = session.query(MentorTask).filter(MentorTask.id == task_id).first()
        if not task:
            return False
        task.status = "completed"
        return True


def add_friend(owner_telegram_id: int, friend_telegram_id: int, friend_pubg_id: str | None = None) -> bool:
    with get_session() as session:
        owner = session.query(User).filter(User.telegram_id == owner_telegram_id).first()
        friend = session.query(User).filter(User.telegram_id == friend_telegram_id).first()
        if not owner or not friend:
            return False
        exists = session.query(Friendship).filter(Friendship.owner_user_id == owner.id, Friendship.friend_user_id == friend.id).first()
        if exists:
            return True
        session.add(Friendship(owner_user_id=owner.id, friend_user_id=friend.id, friend_pubg_id=friend_pubg_id))
        return True


def list_friends(owner_telegram_id: int) -> list[User]:
    with get_session() as session:
        owner = session.query(User).filter(User.telegram_id == owner_telegram_id).first()
        if not owner:
            return []
        friends = (
            session.query(User)
            .join(Friendship, Friendship.friend_user_id == User.id)
            .filter(Friendship.owner_user_id == owner.id)
            .order_by(desc(User.points))
            .all()
        )
        for row in friends:
            session.expunge(row)
        return friends


def list_top_friends(owner_telegram_id: int) -> list[User]:
    return list_friends(owner_telegram_id)


def get_statistics(telegram_id: int) -> dict:
    with get_session() as session:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return {}
        completed_tasks = session.query(func.count(MentorTask.id)).filter(MentorTask.student_user_id == user.id, MentorTask.status == "completed").scalar() or 0
        trainings = session.query(func.count(Training.id)).filter(Training.mentor_user_id == user.id).scalar() or 0
        achievements = session.query(func.count(Achievement.id)).filter(Achievement.user_id == user.id).scalar() or 0
        return {
            "points": user.points,
            "bot_rank": user.bot_rank,
            "completed_tasks": completed_tasks,
            "trainings": trainings,
            "achievements": achievements,
        }
