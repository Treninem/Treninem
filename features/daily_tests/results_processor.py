"""Подсчёт результатов тестов и рекомендации."""

from __future__ import annotations

from config.constants import POINTS_BONUS_QUESTION, POINTS_DAILY_TEST


def evaluate_test(test_payload: list[dict], answers: list[int]) -> dict:
    score = POINTS_DAILY_TEST  # за сам факт прохождения ежедневного теста
    correct_answers = 0
    bonus_correct = False
    mistakes_topics: list[str] = []

    for idx, question in enumerate(test_payload):
        if idx >= len(answers):
            mistakes_topics.append(question["topic"])
            continue

        is_correct = answers[idx] == question["correct"]
        if is_correct:
            if question.get("bonus"):
                score += POINTS_BONUS_QUESTION
                bonus_correct = True
            else:
                correct_answers += 1
        else:
            mistakes_topics.append(question["topic"])

    recommendations = []
    if "maps" in mistakes_topics:
        recommendations.append("Повторить знание карт и типовые ротации.")
    if "weapons" in mistakes_topics:
        recommendations.append("Потренировать контроль отдачи и выбор оружия.")
    if "tactics" in mistakes_topics:
        recommendations.append("Повторить позиционирование, утилити и тайминги.")
    if not recommendations:
        recommendations.append("Отличный результат. Продолжай в том же духе!")

    return {
        "correct_regular": correct_answers,
        "bonus_correct": bonus_correct,
        "score": score,
        "recommendations": recommendations,
    }
