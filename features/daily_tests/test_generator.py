"""Генерация случайных тестов из встроенного банка вопросов."""

from __future__ import annotations

import random
from datetime import date

QUESTION_BANK = [
    {
        "topic": "maps",
        "question": "На какой карте чаще встречаются длинные открытые прострелы?",
        "options": ["Sanhok", "Erangel", "Karakin", "Paramo"],
        "correct": 1,
        "explanation": "Erangel часто даёт длинные дистанции и открытые поля.",
        "bonus": False,
    },
    {
        "topic": "maps",
        "question": "Какая карта наиболее компактная и провоцирует быстрые столкновения?",
        "options": ["Miramar", "Karakin", "Erangel", "Vikendi"],
        "correct": 1,
        "explanation": "Karakin очень компактная и агрессивная по темпу.",
        "bonus": False,
    },
    {
        "topic": "weapons",
        "question": "Какой параметр в первую очередь снижает вертикальную отдачу?",
        "options": ["Компенсатор", "Глушитель", "Магазин", "Коллиматор"],
        "correct": 0,
        "explanation": "Компенсатор помогает лучше контролировать отдачу.",
        "bonus": False,
    },
    {
        "topic": "weapons",
        "question": "Что важнее при стрельбе на средней дистанции?",
        "options": ["Спам без контроля", "Контроль отдачи и короткие очереди", "Стрельба только от бедра", "Прыжки во время стрельбы"],
        "correct": 1,
        "explanation": "На средней дистанции эффективнее короткие очереди и контроль прицела.",
        "bonus": False,
    },
    {
        "topic": "tactics",
        "question": "Когда лучше занимать центр следующей зоны?",
        "options": ["Когда есть информация и транспорт", "Всегда сразу", "Никогда", "Только пешком по краю"],
        "correct": 0,
        "explanation": "Ротация в центр полезна, если есть информация и безопасный путь.",
        "bonus": False,
    },
    {
        "topic": "tactics",
        "question": "Главная цель смоков в late game?",
        "options": ["Украшение позиции", "Скрытие ротации и реса", "Шум", "Подсветка врага"],
        "correct": 1,
        "explanation": "Смоки прикрывают перемещение, подъем союзника и смену позиции.",
        "bonus": False,
    },
    {
        "topic": "maps",
        "question": "На какой карте рельеф и высоты особенно важны для контроля перестрелок?",
        "options": ["Miramar", "Sanhok", "Haven", "Karakin"],
        "correct": 0,
        "explanation": "Miramar богата холмами и перепадами высот.",
        "bonus": False,
    },
    {
        "topic": "weapons",
        "question": "Для чего нужен DMR в команде?",
        "options": ["Для ближнего раша", "Для добивания и давления на дистанции", "Только для автоогня", "Чтобы носить лишние патроны"],
        "correct": 1,
        "explanation": "DMR хорошо работает для давления и добивания на дистанции.",
        "bonus": False,
    },
    {
        "topic": "tactics",
        "question": "Что делать после нока противника на открытом пространстве?",
        "options": ["Сразу бежать лутать", "Давить информацию и контролировать союзников нокнутого", "Лечь на месте", "Уйти в лобби"],
        "correct": 1,
        "explanation": "После нока важно ожидать пик союзников и контролировать пространство.",
        "bonus": False,
    },
    {
        "topic": "weapons",
        "question": "Какой тип оружия обычно удобнее новичкам для стабильного контроля?",
        "options": ["AR с компенсатором", "Две снайперки", "Пистолет", "Арбалет"],
        "correct": 0,
        "explanation": "AR остаётся самым универсальным вариантом.",
        "bonus": False,
    },
    {
        "topic": "tactics",
        "question": "Как лучше входить в дом, где может сидеть враг?",
        "options": ["По одному без информации", "С гранатой/флешкой и разменом углов", "Только прыжком в окно", "С оружием в кобуре"],
        "correct": 1,
        "explanation": "Утилити и координация повышают шанс безопасного входа.",
        "bonus": False,
    },
    {
        "topic": "maps",
        "question": "Какая стратегия чаще полезна на Sanhok?",
        "options": ["Очень долгие дальние перестрелки", "Быстрые решения и плотная работа по укрытиям", "Только игра в транспорте", "Всегда край синей"],
        "correct": 1,
        "explanation": "Sanhok компактна, стычки там случаются быстро.",
        "bonus": False,
    },
    {
        "topic": "bonus",
        "question": "Бонус: что даёт больше шансов выжить в финальной зоне?",
        "options": ["Рандомный раш", "Позиция + инфа + утилити", "Стрельба в воздух", "Игнорирование зоны"],
        "correct": 1,
        "explanation": "Комбинация позиции, информации и утилити критична в late game.",
        "bonus": True,
    },
    {
        "topic": "bonus",
        "question": "Бонус: лучший способ расти как игроку?",
        "options": ["Играть без анализа", "Разбирать ошибки после матчей", "Менять сенсу каждый день", "Играть без звука"],
        "correct": 1,
        "explanation": "Анализ ошибок помогает расти быстрее всего.",
        "bonus": True,
    },
]


def generate_daily_test(seed_value: int | None = None) -> list[dict]:
    """Сформировать 5 обычных вопросов и 1 бонусный."""
    seed = seed_value if seed_value is not None else int(date.today().strftime("%Y%m%d"))
    rnd = random.Random(seed)

    regular = [item for item in QUESTION_BANK if not item["bonus"]]
    bonus = [item for item in QUESTION_BANK if item["bonus"]]

    selected_regular = rnd.sample(regular, k=min(5, len(regular)))
    selected_bonus = rnd.sample(bonus, k=1)

    return selected_regular + selected_bonus
