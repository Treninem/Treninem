"""CRUD-операции для базы данных."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from config.constants import DEFAULT_MENTOR_FREE_SLOTS, POINTS_FRIEND_INVITE, POINTS_WELCOME_BONUS, REFERRAL_PREFIX
from config.settings import DEFAULT_USER_TIMEZONE
from features.points_system.rank_updater import get_rank_for_points
from .models import (
    Achievement,
    BotMessage,
    ChatInfo,
    DailyTestSession,
    FeedbackTicket,
    Friend,
    MentorProfile,
    MentorStudent,
    MentorTask,
    NewsCache,
    PointTransaction,
    Training,
    TrainingParticipant,
    User,
)


# -----------------------------
# Пользователи
# -----------------------------
def get_user_by_telegram_id(session: Session, telegram_id: int) -> User | None:
    return session.execute(select(User).where(User.telegram_id == telegram_id)).scalar_one_or_none()


def get_user_by_pubg_player_id(session: Session, pubg_player_id: str) -> User | None:
    return session.execute(select(User).where(User.pubg_player_id == pubg_player_id)).scalar_one_or_none()


def get_user_by_referral_code(session: Session, referral_code: str) -> User | None:
    return session.execute(select(User).where(User.referral_code == referral_code)).scalar_one_or_none()


def _make_referral_code(telegram_id: int) -> str:
    return f"{REFERRAL_PREFIX}{telegram_id}"


def ensure_referral_code(session: Session, user: User) -> str:
    if not user.referral_code:
        user.referral_code = _make_referral_code(user.telegram_id)
        session.flush()
    return user.referral_code


def get_or_create_user(session: Session, tg_user) -> User:
    user = get_user_by_telegram_id(session, tg_user.id)
    if user:
        user.username = tg_user.username
        user.first_name = tg_user.first_name
        user.last_name = tg_user.last_name
        user.last_activity = datetime.utcnow()
        ensure_referral_code(session, user)
        session.flush()
        return user

    user = User(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        timezone=DEFAULT_USER_TIMEZONE,
        last_activity=datetime.utcnow(),
    )
    session.add(user)
    session.flush()
    ensure_referral_code(session, user)
    return user


def update_last_activity(session: Session, telegram_id: int) -> None:
    user = get_user_by_telegram_id(session, telegram_id)
    if user:
        user.last_activity = datetime.utcnow()
        session.flush()


def _apply_pubg_stats(user: User, stats: dict[str, Any]) -> None:
    user.pubg_level = stats.get("level")
    user.pubg_total_matches = stats.get("total_matches")
    user.pubg_total_wins = stats.get("total_wins")
    user.pubg_total_kills = stats.get("total_kills")
    user.pubg_total_damage = stats.get("total_damage")
    user.pubg_headshot_kills = stats.get("headshot_kills")
    user.pubg_avg_damage = stats.get("avg_damage")
    user.pubg_win_rate = stats.get("win_rate")
    user.pubg_top10s = stats.get("top10s")
    user.pubg_stats_json = json.dumps(stats.get("raw_stats", {}), ensure_ascii=False)
    user.pubg_last_sync_at = datetime.utcnow()


def update_user_registration(
    session: Session,
    telegram_id: int,
    *,
    pubg_player_id: str,
    pubg_name: str,
    pubg_rank: str,
    pubg_kd: str | None,
    pubg_shard: str,
    age: int,
    hours_per_week: int,
    timezone: str | None = None,
    pubg_level: int | None = None,
    pubg_total_matches: int | None = None,
    pubg_total_wins: int | None = None,
    pubg_total_kills: int | None = None,
    pubg_total_damage: float | None = None,
    pubg_headshot_kills: int | None = None,
    pubg_avg_damage: float | None = None,
    pubg_win_rate: float | None = None,
    pubg_top10s: int | None = None,
    pubg_stats_json: str | None = None,
) -> User:
    user = session.execute(select(User).where(User.telegram_id == telegram_id)).scalar_one()

    bound_user = get_user_by_pubg_player_id(session, pubg_player_id)
    if bound_user and bound_user.telegram_id != telegram_id:
        raise ValueError(
            "Этот PUBG аккаунт уже привязан к другому Telegram аккаунту. "
            "Для безопасности двойная привязка запрещена."
        )

    user.pubg_player_id = pubg_player_id
    user.pubg_name = pubg_name
    user.pubg_rank = pubg_rank
    user.pubg_kd = pubg_kd
    user.pubg_shard = pubg_shard
    user.age = age
    user.hours_per_week = hours_per_week
    user.is_registered = True
    user.last_activity = datetime.utcnow()
    user.pubg_level = pubg_level
    user.pubg_total_matches = pubg_total_matches
    user.pubg_total_wins = pubg_total_wins
    user.pubg_total_kills = pubg_total_kills
    user.pubg_total_damage = pubg_total_damage
    user.pubg_headshot_kills = pubg_headshot_kills
    user.pubg_avg_damage = pubg_avg_damage
    user.pubg_win_rate = pubg_win_rate
    user.pubg_top10s = pubg_top10s
    user.pubg_stats_json = pubg_stats_json
    user.pubg_last_sync_at = datetime.utcnow()
    if not user.pubg_bound_at:
        user.pubg_bound_at = datetime.utcnow()
    if timezone:
        user.timezone = timezone
    session.flush()
    return user


def sync_user_pubg_profile(session: Session, user: User, profile) -> User:
    """Обновить сохранённые PUBG-данные пользователя без повторной регистрации."""
    bound_user = get_user_by_pubg_player_id(session, profile.player_id)
    if bound_user and bound_user.id != user.id:
        raise ValueError(
            "Этот PUBG аккаунт уже привязан к другому Telegram аккаунту. "
            "Синхронизация отменена."
        )

    user.pubg_player_id = profile.player_id
    user.pubg_name = profile.nickname
    user.pubg_rank = profile.rank
    user.pubg_kd = profile.kd
    user.pubg_shard = profile.shard
    _apply_pubg_stats(
        user,
        {
            "level": profile.level,
            "total_matches": profile.total_matches,
            "total_wins": profile.total_wins,
            "total_kills": profile.total_kills,
            "total_damage": profile.total_damage,
            "headshot_kills": profile.headshot_kills,
            "avg_damage": profile.avg_damage,
            "win_rate": profile.win_rate,
            "top10s": profile.top10s,
            "raw_stats": profile.raw_stats,
        },
    )
    if not user.pubg_bound_at:
        user.pubg_bound_at = datetime.utcnow()
    user.last_activity = datetime.utcnow()
    session.flush()
    return user


def get_all_registered_users(session: Session) -> list[User]:
    return list(
        session.execute(select(User).where(User.is_registered.is_(True)).order_by(User.id.asc())).scalars()
    )


def attach_referral_to_user(session: Session, user: User, referral_code: str):
    code = (referral_code or "").strip()
    if not code:
        return False, "Пустой реферальный код."

    inviter = get_user_by_referral_code(session, code)
    if inviter is None:
        return False, "Реферальная ссылка не распознана."
    if inviter.id == user.id:
        return False, "Нельзя использовать собственную ссылку."
    if user.is_registered and not user.referred_by_user_id:
        return False, "Реферальная ссылка должна быть использована до завершения регистрации."
    if user.referred_by_user_id and user.referred_by_user_id != inviter.id:
        return False, "Реферальная ссылка уже была привязана ранее."

    user.referred_by_user_id = inviter.id
    session.flush()
    return True, inviter


def count_registered_referrals(session: Session, inviter_user_id: int) -> int:
    return int(
        session.execute(
            select(func.count(User.id)).where(
                User.referred_by_user_id == inviter_user_id,
                User.is_registered.is_(True),
            )
        ).scalar_one()
        or 0
    )


def count_total_referrals(session: Session, inviter_user_id: int) -> int:
    return int(
        session.execute(select(func.count(User.id)).where(User.referred_by_user_id == inviter_user_id)).scalar_one()
        or 0
    )


def get_referral_stats(session: Session, inviter_user_id: int) -> dict[str, int]:
    total = count_total_referrals(session, inviter_user_id)
    registered = count_registered_referrals(session, inviter_user_id)
    return {
        "total": total,
        "registered": registered,
        "pending": max(total - registered, 0),
    }


def list_top_referrers(session: Session, limit: int = 10) -> list[tuple[User, int]]:
    invited = User.__table__.alias("invited")
    rows = session.execute(
        select(User, func.count(invited.c.id).label("invites"))
        .join(invited, invited.c.referred_by_user_id == User.id)
        .where(invited.c.is_registered == True)  # noqa: E712
        .group_by(User.id)
        .order_by(desc("invites"), desc(User.points))
        .limit(limit)
    ).all()
    return [(row[0], int(row[1] or 0)) for row in rows]


# -----------------------------
# Баллы и достижения
# -----------------------------
def add_point_transaction(
    session: Session,
    user: User,
    amount: int,
    reason: str,
    meta: dict | None = None,
) -> PointTransaction:
    user.points += amount
    user.bot_rank = get_rank_for_points(user.points)
    user.last_activity = datetime.utcnow()

    trx = PointTransaction(
        user_id=user.id,
        amount=amount,
        reason=reason,
        meta_json=json.dumps(meta or {}, ensure_ascii=False),
    )
    session.add(trx)
    session.flush()
    return trx


def create_achievement(session: Session, user_id: int, title: str, description: str) -> Achievement:
    achievement = Achievement(user_id=user_id, title=title, description=description)
    session.add(achievement)
    session.flush()
    return achievement


def maybe_create_achievement(session: Session, user_id: int, title: str, description: str) -> Achievement | None:
    existing = session.execute(
        select(Achievement).where(Achievement.user_id == user_id, Achievement.title == title)
    ).scalar_one_or_none()
    if existing:
        return None
    return create_achievement(session, user_id=user_id, title=title, description=description)


def grant_registration_and_referral_rewards(session: Session, user: User) -> None:
    welcome_tx = session.execute(
        select(PointTransaction).where(
            PointTransaction.user_id == user.id,
            PointTransaction.reason == "Welcome bonus",
        )
    ).scalar_one_or_none()
    if welcome_tx is None:
        add_point_transaction(
            session=session,
            user=user,
            amount=POINTS_WELCOME_BONUS,
            reason="Welcome bonus",
            meta={"source": "registration"},
        )
    maybe_create_achievement(session, user.id, "Добро пожаловать в клан", "Профиль активирован и привязка PUBG сохранена.")

    if user.referred_by_user_id and not user.referral_points_paid:
        inviter = session.execute(select(User).where(User.id == user.referred_by_user_id)).scalar_one_or_none()
        if inviter and inviter.id != user.id:
            add_point_transaction(
                session=session,
                user=inviter,
                amount=POINTS_FRIEND_INVITE,
                reason="Приглашение друга в бот",
                meta={"friend_user_id": user.id},
            )
            maybe_create_achievement(
                session,
                inviter.id,
                "Вербовщик",
                "Ты успешно пригласил первого бойца в клановый бот.",
            )
            maybe_create_achievement(
                session,
                user.id,
                "По приглашению друга",
                "Ты присоединился к боту по персональной ссылке союзника.",
            )
        user.referral_points_paid = True
        session.flush()


def grant_milestone_achievements(session: Session, user: User) -> None:
    maybe_create_achievement(session, user.id, "Боевой профиль", "У тебя есть привязанный PUBG-профиль и базовая статистика.")

    if (user.pubg_total_matches or 0) >= 50:
        maybe_create_achievement(session, user.id, "Разведчик", "Сыграно 50+ матчей PUBG.")
    if (user.pubg_total_wins or 0) >= 10:
        maybe_create_achievement(session, user.id, "Победный старт", "Одержано 10+ побед.")
    if (user.pubg_total_kills or 0) >= 100:
        maybe_create_achievement(session, user.id, "На мушке", "Сделано 100+ убийств.")
    if (user.points or 0) >= 600:
        maybe_create_achievement(session, user.id, "Ветеран клана", "Накоплено 600+ баллов в боте.")
    if (user.points or 0) >= 1001:
        maybe_create_achievement(session, user.id, "Легенда клана", "Ты достиг ранга «Легенда».")
    if count_registered_referrals(session, user.id) >= 3:
        maybe_create_achievement(session, user.id, "Командный магнит", "Ты привёл в бот минимум 3 зарегистрированных игроков.")


def get_user_achievements(session: Session, user_id: int) -> list[Achievement]:
    return list(
        session.execute(
            select(Achievement).where(Achievement.user_id == user_id).order_by(desc(Achievement.created_at))
        ).scalars()
    )


def get_user_points_history(session: Session, user_id: int, limit: int = 20) -> list[PointTransaction]:
    return list(
        session.execute(
            select(PointTransaction)
            .where(PointTransaction.user_id == user_id)
            .order_by(desc(PointTransaction.created_at))
            .limit(limit)
        ).scalars()
    )


def get_points_by_day(session: Session, user_id: int, days: int = 7) -> list[tuple[str, int]]:
    now = datetime.utcnow()
    start = now - timedelta(days=days - 1)
    rows = session.execute(
        select(func.date(PointTransaction.created_at), func.coalesce(func.sum(PointTransaction.amount), 0))
        .where(PointTransaction.user_id == user_id, PointTransaction.created_at >= start)
        .group_by(func.date(PointTransaction.created_at))
        .order_by(func.date(PointTransaction.created_at))
    ).all()

    mapping = {str(day): value for day, value in rows}
    result = []
    for offset in range(days):
        cur = (start + timedelta(days=offset)).date()
        result.append((str(cur), int(mapping.get(str(cur), 0))))
    return result


# -----------------------------
# Наставничество
# -----------------------------
def upsert_mentor_profile(
    session: Session,
    user: User,
    specialization: str,
    schedule_text: str,
    teaching_style: str,
) -> MentorProfile:
    profile = session.execute(select(MentorProfile).where(MentorProfile.user_id == user.id)).scalar_one_or_none()

    if profile is None:
        profile = MentorProfile(
            user_id=user.id,
            specialization=specialization,
            schedule_text=schedule_text,
            teaching_style=teaching_style,
            free_slots=DEFAULT_MENTOR_FREE_SLOTS,
        )
        session.add(profile)
    else:
        profile.specialization = specialization
        profile.schedule_text = schedule_text
        profile.teaching_style = teaching_style

    user.is_mentor = True
    user.mentor_active = True
    session.flush()
    return profile


def get_mentor_profile(session: Session, user_id: int) -> MentorProfile | None:
    return session.execute(select(MentorProfile).where(MentorProfile.user_id == user_id)).scalar_one_or_none()


def list_active_mentors(
    session: Session,
    specialization: str | None = None,
    rank_filter: str | None = None,
) -> list[tuple[User, MentorProfile]]:
    query = (
        select(User, MentorProfile)
        .join(MentorProfile, MentorProfile.user_id == User.id)
        .where(User.is_mentor.is_(True), User.mentor_active.is_(True))
        .order_by(User.points.desc())
    )
    if specialization:
        query = query.where(MentorProfile.specialization.ilike(f"%{specialization}%"))
    if rank_filter:
        query = query.where(User.pubg_rank.ilike(f"%{rank_filter}%"))
    return list(session.execute(query).all())


def assign_student_to_mentor(session: Session, mentor_user_id: int, student_user_id: int) -> MentorStudent:
    relation = session.execute(
        select(MentorStudent).where(
            MentorStudent.mentor_user_id == mentor_user_id,
            MentorStudent.student_user_id == student_user_id,
        )
    ).scalar_one_or_none()
    if relation:
        return relation

    relation = MentorStudent(mentor_user_id=mentor_user_id, student_user_id=student_user_id)
    session.add(relation)
    session.flush()
    return relation


def list_mentor_students(session: Session, mentor_user_id: int) -> list[User]:
    return list(
        session.execute(
            select(User)
            .join(MentorStudent, MentorStudent.student_user_id == User.id)
            .where(MentorStudent.mentor_user_id == mentor_user_id)
            .order_by(User.points.desc())
        ).scalars()
    )


# -----------------------------
# Тренировки
# -----------------------------
def create_training(
    session: Session,
    mentor_user_id: int,
    title: str,
    difficulty: str,
    description: str,
    training_at: datetime,
) -> Training:
    training = Training(
        mentor_user_id=mentor_user_id,
        title=title,
        difficulty=difficulty,
        description=description,
        training_at=training_at,
    )
    session.add(training)
    session.flush()
    return training


def list_user_trainings(session: Session, user_id: int) -> list[Training]:
    return list(
        session.execute(
            select(Training)
            .where(
                or_(
                    Training.mentor_user_id == user_id,
                    Training.id.in_(
                        select(TrainingParticipant.training_id).where(TrainingParticipant.user_id == user_id)
                    ),
                )
            )
            .order_by(desc(Training.training_at))
        ).scalars()
    )


def add_training_participant(session: Session, training_id: int, user_id: int) -> TrainingParticipant:
    participant = session.execute(
        select(TrainingParticipant).where(
            TrainingParticipant.training_id == training_id,
            TrainingParticipant.user_id == user_id,
        )
    ).scalar_one_or_none()
    if participant:
        return participant

    participant = TrainingParticipant(training_id=training_id, user_id=user_id)
    session.add(participant)
    session.flush()
    return participant


def mark_training_attendance(
    session: Session,
    training_id: int,
    user_id: int,
    attended: bool,
    warned_absence: bool = False,
) -> TrainingParticipant | None:
    participant = session.execute(
        select(TrainingParticipant).where(
            TrainingParticipant.training_id == training_id,
            TrainingParticipant.user_id == user_id,
        )
    ).scalar_one_or_none()
    if participant:
        participant.attended = attended
        participant.warned_absence = warned_absence
        session.flush()
    return participant


# -----------------------------
# Задания наставников
# -----------------------------
def create_mentor_task(
    session: Session,
    mentor_user_id: int,
    student_user_id: int,
    title: str,
    description: str,
    reward_points: int,
    due_at: datetime | None,
) -> MentorTask:
    task = MentorTask(
        mentor_user_id=mentor_user_id,
        student_user_id=student_user_id,
        title=title,
        description=description,
        reward_points=reward_points,
        due_at=due_at,
    )
    session.add(task)
    session.flush()
    return task


def list_user_tasks(session: Session, user_id: int) -> list[MentorTask]:
    return list(
        session.execute(
            select(MentorTask).where(MentorTask.student_user_id == user_id).order_by(desc(MentorTask.created_at))
        ).scalars()
    )


def complete_task(session: Session, task_id: int) -> MentorTask | None:
    task = session.execute(select(MentorTask).where(MentorTask.id == task_id)).scalar_one_or_none()
    if not task or task.status == "completed":
        return None
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    session.flush()
    return task


# -----------------------------
# Друзья
# -----------------------------
def add_friend(
    session: Session,
    user_id: int,
    friend_pubg_player_id: str | None,
    friend_pubg_name: str,
    friend_pubg_rank: str | None,
    friend_kd: str | None,
    linked_user_id: int | None = None,
) -> Friend:
    friend = session.execute(
        select(Friend).where(Friend.user_id == user_id, Friend.friend_pubg_name == friend_pubg_name)
    ).scalar_one_or_none()

    if friend:
        friend.friend_pubg_player_id = friend_pubg_player_id
        friend.friend_pubg_rank = friend_pubg_rank
        friend.friend_kd = friend_kd
        friend.linked_user_id = linked_user_id
        session.flush()
        return friend

    friend = Friend(
        user_id=user_id,
        friend_pubg_player_id=friend_pubg_player_id,
        friend_pubg_name=friend_pubg_name,
        friend_pubg_rank=friend_pubg_rank,
        friend_kd=friend_kd,
        linked_user_id=linked_user_id,
    )
    session.add(friend)
    session.flush()
    return friend


def list_friends(session: Session, user_id: int) -> list[Friend]:
    return list(session.execute(select(Friend).where(Friend.user_id == user_id).order_by(Friend.created_at.desc())).scalars())


# -----------------------------
# Обратная связь
# -----------------------------
def create_feedback_ticket(
    session: Session,
    user_id: int,
    ticket_type: str,
    subject: str,
    text: str,
    screenshot_file_id: str | None = None,
) -> FeedbackTicket:
    ticket = FeedbackTicket(
        user_id=user_id,
        ticket_type=ticket_type,
        subject=subject,
        text=text,
        screenshot_file_id=screenshot_file_id,
    )
    session.add(ticket)
    session.flush()
    return ticket


# -----------------------------
# Тесты
# -----------------------------
def create_daily_test_session(
    session: Session,
    user_id: int,
    scheduled_for: datetime,
    test_payload: list[dict],
) -> DailyTestSession:
    item = DailyTestSession(
        user_id=user_id,
        scheduled_for=scheduled_for,
        test_payload_json=json.dumps(test_payload, ensure_ascii=False),
        answers_json="[]",
    )
    session.add(item)
    session.flush()
    return item


def get_daily_test_session(session: Session, session_id: int) -> DailyTestSession | None:
    return session.execute(select(DailyTestSession).where(DailyTestSession.id == session_id)).scalar_one_or_none()


def save_test_answers(
    session: Session,
    item: DailyTestSession,
    answers: list[int],
    score: int | None = None,
    bonus_correct: bool | None = None,
    completed: bool = False,
) -> DailyTestSession:
    item.answers_json = json.dumps(answers, ensure_ascii=False)
    if score is not None:
        item.score = score
    if bonus_correct is not None:
        item.bonus_correct = bonus_correct
    if completed:
        item.completed_at = datetime.utcnow()
    session.flush()
    return item


def list_recent_test_sessions(session: Session, user_id: int, limit: int = 7) -> list[DailyTestSession]:
    return list(
        session.execute(
            select(DailyTestSession)
            .where(DailyTestSession.user_id == user_id)
            .order_by(desc(DailyTestSession.created_at))
            .limit(limit)
        ).scalars()
    )


# -----------------------------
# Чаты и сообщения бота
# -----------------------------
def upsert_chat_info(
    session: Session,
    chat_id: int,
    title: str | None,
    chat_type: str | None,
    members_count: int | None,
    added_by_user_id: int | None = None,
) -> ChatInfo:
    chat = session.execute(select(ChatInfo).where(ChatInfo.chat_id == chat_id)).scalar_one_or_none()
    if chat is None:
        chat = ChatInfo(
            chat_id=chat_id,
            title=title,
            chat_type=chat_type,
            members_count=members_count,
            added_by_user_id=added_by_user_id,
        )
        session.add(chat)
    else:
        chat.title = title
        chat.chat_type = chat_type
        chat.members_count = members_count
        if added_by_user_id is not None:
            chat.added_by_user_id = added_by_user_id
    session.flush()
    return chat


def list_chats(session: Session) -> list[ChatInfo]:
    return list(session.execute(select(ChatInfo).order_by(desc(ChatInfo.updated_at))).scalars())


def track_bot_message(session: Session, chat_id: int, message_id: int) -> BotMessage:
    msg = BotMessage(chat_id=chat_id, message_id=message_id)
    session.add(msg)
    session.flush()
    return msg


def list_bot_messages(session: Session, chat_id: int) -> list[BotMessage]:
    return list(
        session.execute(select(BotMessage).where(BotMessage.chat_id == chat_id).order_by(desc(BotMessage.created_at))).scalars()
    )


def delete_tracked_bot_messages(session: Session, chat_id: int) -> int:
    messages = list_bot_messages(session, chat_id)
    count = len(messages)
    for item in messages:
        session.delete(item)
    session.flush()
    return count


# -----------------------------
# Новости
# -----------------------------
def cache_news_item(
    session: Session,
    title: str,
    description: str | None,
    url: str,
    category: str | None,
    published_at: datetime | None,
) -> NewsCache:
    existing = session.execute(select(NewsCache).where(NewsCache.url == url)).scalar_one_or_none()
    if existing:
        return existing

    item = NewsCache(
        title=title,
        description=description,
        url=url,
        category=category,
        published_at=published_at,
    )
    session.add(item)
    session.flush()
    return item
