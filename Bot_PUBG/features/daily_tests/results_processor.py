"""Обработка результатов ежедневных тестов."""
from __future__ import annotations

import json
from datetime import date

from config.constants import POINTS_BONUS_QUESTION, POINTS_DAILY_TEST
from database.queries import add_points, save_daily_test_result


def process_test_answers(telegram_id: int, questions: list[dict], answers: list[int]) -> dict:
    correct = 0
    bonus_correct = False
    details = []

    for idx, (question, answer) in enumerate(zip(questions, answers), start=1):
        is_correct = answer == question["correct_index"]
        if is_correct:
            correct += 1
        if idx == len(questions) and is_correct:
            bonus_correct = True
        details.append(
            {
                "question": question["question"],
                "selected_index": answer,
                "correct_index": question["correct_index"],
                "is_correct": is_correct,
                "explanation": question["explanation"],
            }
        )

    add_points(telegram_id, POINTS_DAILY_TEST, "daily_test", f"Пройден тест, правильных ответов: {correct}")
    if bonus_correct:
        add_points(telegram_id, POINTS_BONUS_QUESTION, "bonus_question", "Правильный ответ на бонусный вопрос")

    save_daily_test_result(
        telegram_id=telegram_id,
        test_date=str(date.today()),
        correct_answers=correct,
        total_questions=len(questions),
        bonus_correct=bonus_correct,
        details_json=json.dumps(details, ensure_ascii=False),
    )

    return {
        "correct": correct,
        "total": len(questions),
        "bonus_correct": bonus_correct,
        "details": details,
    }
