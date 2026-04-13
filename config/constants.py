"""Константы проекта PUBG Telegram Bot."""
from __future__ import annotations

# Ранги PUBG в порядке возрастания.
PUBG_RANK_ORDER = [
    "Бронза",
    "Серебро",
    "Золото",
    "Платина",
    "Алмаз",
    "Корона",
    "Ас",
    "Завоеватель",
]

# Минимальный ранг PUBG для наставника.
MIN_MENTOR_PUBG_RANK = "Корона"

# Ранги внутри бота по количеству баллов.
BOT_RANKS = {
    "Новичок": (0, 100),
    "Стрелок": (101, 300),
    "Тактик": (301, 600),
    "Ветеран": (601, 1000),
    "Легенда": (1001, 10**9),
}

# Начисление баллов.
POINTS_DAILY_TEST = 10
POINTS_TRAINING = 20
POINTS_MENTOR_TASK = 50
POINTS_INVITE_FRIEND = 30
POINTS_BONUS_QUESTION = 15

# Списание баллов.
PENALTY_MISSED_TRAINING = -20
PENALTY_INACTIVITY = -10
PENALTY_RULES = -50

# Ограничения и служебные параметры.
MIN_AGE = 13
MAX_FRIENDS_IN_CHAT = 10
NEWS_LIMIT = 5
NEWS_AUTO_DELETE_SECONDS = 3600
CHAT_DATA_DELETE_SECONDS = 10
MAX_MENTOR_STUDENTS = 10

# События начисления баллов.
POINT_EVENTS = {
    "daily_test": POINTS_DAILY_TEST,
    "training": POINTS_TRAINING,
    "mentor_task": POINTS_MENTOR_TASK,
    "invite_friend": POINTS_INVITE_FRIEND,
    "bonus_question": POINTS_BONUS_QUESTION,
    "missed_training": PENALTY_MISSED_TRAINING,
    "inactivity": PENALTY_INACTIVITY,
    "rule_violation": PENALTY_RULES,
}

PREMIUM_DAY_COST_POINTS = 500
DEFAULT_PREMIUM_PRIVILEGES = [
    "Увеличенные лимиты",
    "Расширенная статистика",
    "Приоритетная поддержка",
]

FEEDBACK_TYPES = ["отзыв", "жалоба", "вопрос", "предложение"]
COMPLAINT_TYPES = ["наставник", "игрок", "баг"]

# Словарь для визуального сравнения рангов.
PUBG_RANK_WEIGHT = {rank: idx for idx, rank in enumerate(PUBG_RANK_ORDER)}
