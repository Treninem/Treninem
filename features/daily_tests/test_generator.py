"""Генерация случайных ежедневных тестов."""
from __future__ import annotations

import random

QUESTION_BANK = [
    {
        "topic": "карты",
        "question": "На какой карте PUBG расположен город Пикадо?",
        "options": ["Erangel", "Miramar", "Sanhok", "Vikendi"],
        "correct_index": 1,
        "explanation": "Пикадо находится на карте Miramar.",
    },
    {
        "topic": "оружие",
        "question": "Какой тип патронов использует M416?",
        "options": ["7.62mm", "5.56mm", ".45 ACP", "9mm"],
        "correct_index": 1,
        "explanation": "M416 использует патроны 5.56mm.",
    },
    {
        "topic": "тактика",
        "question": "Что лучше делать перед входом в здание с врагом?",
        "options": ["Бежать без проверки", "Бросить гранату/осмотреть углы", "Лечь у двери", "Стрелять в потолок"],
        "correct_index": 1,
        "explanation": "Безопаснее сначала зачистить углы и использовать гранаты.",
    },
    {
        "topic": "карты",
        "question": "Какая карта чаще всего ассоциируется со снегом?",
        "options": ["Deston", "Vikendi", "Taego", "Karakin"],
        "correct_index": 1,
        "explanation": "Vikendi — снежная карта PUBG.",
    },
    {
        "topic": "оружие",
        "question": "Какое навесное обычно помогает уменьшить вертикальную отдачу?",
        "options": ["Глушитель", "Вертикальная рукоятка", "Коллиматор", "Магазин"],
        "correct_index": 1,
        "explanation": "Вертикальная рукоятка уменьшает вертикальную отдачу.",
    },
    {
        "topic": "тактика",
        "question": "Что важнее в поздней зоне?",
        "options": ["Открытое поле", "Позиция и укрытие", "Количество бинтов", "Наличие мотоцикла"],
        "correct_index": 1,
        "explanation": "Позиция и укрытие в поздней зоне критически важны.",
    },
    {
        "topic": "бонус",
        "question": "Бонус: какой предмет позволяет быстро ставить дымовую завесу?",
        "options": ["Светошумовая граната", "Дымовая граната", "Коктейль Молотова", "Липкая бомба"],
        "correct_index": 1,
        "explanation": "Дымовая граната создает укрытие и закрывает обзор.",
    },
]


def generate_daily_test_for_user(user_id: int) -> list[dict]:
    """Возвращает 5 случайных вопросов + 1 бонусный.
    user_id добавлен в функцию, чтобы при желании можно было ввести персонализированный seed.
    """
    random.seed(f"daily-test-{user_id}")
    regular = [q for q in QUESTION_BANK if q["topic"] != "бонус"]
    bonus = [q for q in QUESTION_BANK if q["topic"] == "бонус"]
    selected = random.sample(regular, k=min(5, len(regular)))
    if bonus:
        selected.append(random.choice(bonus))
    return selected
