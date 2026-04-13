"""Справочник персонажей, предметов, питомцев и шаблонов игровых сущностей."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config import RARITY_NAMES

CATEGORY_CODES = {
    "food": 10,
    "material": 20,
    "equipment": 30,
    "elixir": 40,
    "scroll": 50,
    "currency": 60,
    "recipe": 70,
}
CATEGORY_NAMES = {
    "food": "Еда",
    "material": "Материалы",
    "equipment": "Экипировка",
    "elixir": "Эликсиры",
    "scroll": "Свитки",
    "currency": "Валюта",
    "recipe": "Рецепты",
}
SLOT_TITLES = {
    "head": "Голова",
    "body": "Тело",
    "paws": "Лапы",
    "legs": "Ноги",
    "accessory": "Аксессуар",
}
SLOT_ORDER = ["head", "body", "paws", "legs", "accessory"]


def make_id(category: str, rarity: int, seq: int) -> int:
    return CATEGORY_CODES[category] * 10_000 + rarity * 1_000 + seq


def rarity_stars(rarity: int) -> str:
    return "★" * rarity + "☆" * (6 - rarity)


ITEMS: dict[int, dict[str, Any]] = {}


def add_item(
    category: str,
    rarity: int,
    seq: int,
    name: str,
    *,
    emoji: str,
    price: int,
    weight: int = 1,
    slot: str | None = None,
    stats: dict[str, int] | None = None,
    buffs: dict[str, int] | None = None,
    hp_restore: int = 0,
    energy_restore: int = 0,
    max_durability: int = 0,
    description: str = "",
    tags: list[str] | None = None,
) -> int:
    item_id = make_id(category, rarity, seq)
    ITEMS[item_id] = {
        "id": item_id,
        "category": category,
        "category_name": CATEGORY_NAMES[category],
        "rarity": rarity,
        "rarity_name": RARITY_NAMES[rarity],
        "name": name,
        "emoji": emoji,
        "price": price,
        "weight": weight,
        "slot": slot,
        "stats": stats or {},
        "buffs": buffs or {},
        "hp_restore": hp_restore,
        "energy_restore": energy_restore,
        "max_durability": max_durability,
        "description": description,
        "tags": tags or [],
    }
    return item_id


# Валюта.
CURRENCY_ID = add_item(
    "currency", 1, 1, "Монета стаи", emoji="💰", price=1, weight=0, description="Основная игровая валюта."
)
PREMIUM_ID = add_item(
    "currency", 5, 2, "Лунный кристалл", emoji="💎", price=250, weight=0, description="Премиальная валюта для владельца и ивентов."
)
TOKEN_ID = add_item(
    "currency", 4, 3, "Жетон сезона", emoji="🎟", price=120, weight=0, description="Токен сезонных наград."
)

# Персонажи.
CHARACTERS = {
    "wolf": {
        "title": "Волк",
        "emoji": "🐺",
        "lore": "Лидер стаи и мастер затяжных боёв.",
        "stats": {"hp": 108, "energy": 104, "attack": 14, "defense": 10, "speed": 12, "luck": 9},
        "abilities": [
            ("Кровавый след", "Накладывает кровотечение и усиливает преследование цели."),
            ("Вой стаи", "Даёт шанс получить щит и бонус атаки."),
        ],
    },
    "lion": {
        "title": "Лев",
        "emoji": "🦁",
        "lore": "Король арены, силовой доминатор с рывком урона.",
        "stats": {"hp": 112, "energy": 96, "attack": 15, "defense": 11, "speed": 10, "luck": 8},
        "abilities": [
            ("Рёв прайда", "Пугает противника и может оглушить."),
            ("Королевский натиск", "Сильный стартовый удар с бонусом рейтинга в арене."),
        ],
    },
    "fox": {
        "title": "Лиса",
        "emoji": "🦊",
        "lore": "Манёвренный охотник, критические удары и уловки.",
        "stats": {"hp": 96, "energy": 116, "attack": 12, "defense": 9, "speed": 15, "luck": 13},
        "abilities": [
            ("Хитрая тень", "Повышает уклонение и шанс контратаки."),
            ("Лисья уловка", "Крадёт часть энергии цели и снижает её защиту."),
        ],
    },
    "bear": {
        "title": "Медведь",
        "emoji": "🐻",
        "lore": "Танк с высоким запасом здоровья и яростью выживания.",
        "stats": {"hp": 126, "energy": 88, "attack": 13, "defense": 14, "speed": 8, "luck": 7},
        "abilities": [
            ("Толстая шкура", "Поглощает часть входящего урона."),
            ("Гнев берлоги", "Чем ниже HP, тем выше урон."),
        ],
    },
    "eagle": {
        "title": "Орёл",
        "emoji": "🦅",
        "lore": "Быстрый разведчик и снайпер дальнего боя.",
        "stats": {"hp": 92, "energy": 108, "attack": 13, "defense": 9, "speed": 16, "luck": 11},
        "abilities": [
            ("Коготь с высоты", "Первая атака получает сильный множитель."),
            ("Небесное зрение", "Повышает шанс лута и шанс уклонения."),
        ],
    },
    "crocodile": {
        "title": "Крокодил",
        "emoji": "🐊",
        "lore": "Контроль и медленное истощение противника.",
        "stats": {"hp": 118, "energy": 94, "attack": 13, "defense": 12, "speed": 9, "luck": 10},
        "abilities": [
            ("Болотный захват", "Снижает скорость цели и даёт шанс оглушения."),
            ("Холодная кровь", "Снимает часть дебаффов и усиливает защиту."),
        ],
    },
    "rhino": {
        "title": "Носорог",
        "emoji": "🦏",
        "lore": "Прорывной фронтлайнер с пробитием защиты.",
        "stats": {"hp": 120, "energy": 90, "attack": 14, "defense": 13, "speed": 9, "luck": 8},
        "abilities": [
            ("Таран", "Пробивает броню и наносит дополнительный урон."),
            ("Несокрушимость", "Даёт временный щит и сопротивление контролю."),
        ],
    },
}

SPECIALIZATIONS = {
    "berserk": {"title": "Берсерк", "bonus": {"attack_pct": 12, "speed_pct": 4, "defense_pct": -4}},
    "guardian": {"title": "Страж", "bonus": {"defense_pct": 12, "hp_pct": 10}},
    "ranger": {"title": "Следопыт", "bonus": {"speed_pct": 10, "luck_pct": 8}},
    "sage": {"title": "Шаман", "bonus": {"energy_pct": 12, "luck_pct": 4, "attack_pct": 4}},
}

FACTIONS = {
    "forest": {
        "title": "Хранители Леса",
        "emoji": "🌲",
        "bonus": {"luck_pct": 6, "xp_pct": 4},
        "description": "Лучше видят добычу, быстрее учатся и чаще приносят редкий лут.",
        "daily_category": "food",
    },
    "mountain": {
        "title": "Каменный Хребет",
        "emoji": "⛰️",
        "bonus": {"defense_pct": 8, "hp_pct": 6},
        "description": "Стойкие фронтлайнеры, которые выдерживают долгие бои и осады.",
        "daily_category": "material",
    },
    "swamp": {
        "title": "Болотная Тень",
        "emoji": "🪷",
        "bonus": {"speed_pct": 5, "luck_pct": 4, "status_pct": 8},
        "description": "Хитрые контрабандисты и мастера ядов, живущие на тонких бонусах.",
        "daily_category": "elixir",
    },
    "storm": {
        "title": "Буревой Коготь",
        "emoji": "⚡",
        "bonus": {"attack_pct": 8, "speed_pct": 4},
        "description": "Агрессивная боевая фракция с упором на давление и быстрые рейды.",
        "daily_category": "equipment",
    },
}

TALENTS = {
    "savage_claws": {"title": "Свирепые когти", "emoji": "🩸", "max_rank": 3, "bonus_per_rank": {"attack_pct": 6}, "desc": "Повышает атаку."},
    "iron_hide": {"title": "Железная шкура", "emoji": "🛡️", "max_rank": 3, "bonus_per_rank": {"defense_pct": 6}, "desc": "Повышает защиту."},
    "wind_step": {"title": "Шаг ветра", "emoji": "💨", "max_rank": 3, "bonus_per_rank": {"speed_pct": 5}, "desc": "Повышает скорость."},
    "moon_instinct": {"title": "Лунный инстинкт", "emoji": "🌙", "max_rank": 3, "bonus_per_rank": {"luck_pct": 5}, "desc": "Повышает удачу."},
    "vital_core": {"title": "Сердце стаи", "emoji": "❤️", "max_rank": 3, "bonus_per_rank": {"hp_pct": 6}, "desc": "Повышает здоровье."},
    "merchant_nose": {"title": "Нюх торговца", "emoji": "💰", "max_rank": 3, "bonus_per_rank": {"gold_gain_pct": 5}, "desc": "Увеличивает приток золота."},
    "scholar_paws": {"title": "Учёные лапы", "emoji": "📘", "max_rank": 3, "bonus_per_rank": {"xp_gain_pct": 5}, "desc": "Увеличивает получаемый опыт."},
    "boss_slayer": {"title": "Палач титанов", "emoji": "🗡️", "max_rank": 3, "bonus_per_rank": {"boss_damage_pct": 8}, "desc": "Повышает урон по мировым боссам."},
    "trailblazer": {"title": "Прокладыватель троп", "emoji": "🧭", "max_rank": 3, "bonus_per_rank": {"expedition_pct": 5}, "desc": "Повышает шанс успеха экспедиций."},
    "delver": {"title": "Глубинный мастер", "emoji": "🏰", "max_rank": 3, "bonus_per_rank": {"dungeon_pct": 5}, "desc": "Повышает шанс успеха подземелий."},
}

CONTRACT_TEMPLATES = [
    {"code": "hunt_alpha", "title": "Охота на альфу", "emoji": "🐺", "base_chance": 0.58, "gold": 70, "xp": 90, "loot_category": "equipment", "desc": "Выслеживание крупного хищника ради трофея."},
    {"code": "escort", "title": "Охрана каравана", "emoji": "🚚", "base_chance": 0.66, "gold": 88, "xp": 80, "loot_category": "material", "desc": "Безопасно провести торговый караван через опасную тропу."},
    {"code": "ruins", "title": "Руины предков", "emoji": "🏛️", "base_chance": 0.52, "gold": 92, "xp": 104, "loot_category": "recipe", "desc": "Исследование руин со скрытыми тайниками."},
    {"code": "herbs", "title": "Сбор ночных трав", "emoji": "🌿", "base_chance": 0.72, "gold": 60, "xp": 70, "loot_category": "elixir", "desc": "Найти редкие травы до рассвета."},
    {"code": "mine", "title": "Шахтёрский заказ", "emoji": "⛏️", "base_chance": 0.63, "gold": 76, "xp": 84, "loot_category": "material", "desc": "Добыча руды для ремесленников союза."},
    {"code": "smuggle", "title": "Теневая доставка", "emoji": "🌑", "base_chance": 0.49, "gold": 108, "xp": 98, "loot_category": "scroll", "desc": "Рискованная доставка для чёрного рынка."},
    {"code": "totem", "title": "Пробуждение тотема", "emoji": "🗿", "base_chance": 0.44, "gold": 118, "xp": 120, "loot_category": "equipment", "desc": "Защитить древний тотем и отбиться от налётчиков."},
    {"code": "rift", "title": "Разлом Бури", "emoji": "⚡", "base_chance": 0.37, "gold": 138, "xp": 145, "loot_category": "recipe", "desc": "Эндгейм-контракт на стабилизацию Грозового Разлома."},
]

PET_SPECIES = {
    "spark": {"title": "Искрёнок", "emoji": "✨", "bonus": {"luck_pct": 4}},
    "mole": {"title": "Крот-рудокоп", "emoji": "🦦", "bonus": {"material_drop_pct": 8}},
    "owl": {"title": "Лесная сова", "emoji": "🦉", "bonus": {"xp_pct": 6}},
    "beetle": {"title": "Бронежук", "emoji": "🪲", "bonus": {"defense_pct": 6}},
    "ferret": {"title": "Шустрый хорёк", "emoji": "🦫", "bonus": {"speed_pct": 6}},
    "frog": {"title": "Ядовитая квакша", "emoji": "🐸", "bonus": {"status_pct": 6}},
}

WORLD_BOSS_TEMPLATES = [
    {"code": "storm_alpha", "title": "Альфа Бури", "emoji": "🌩", "hp": 15000, "attack": 56, "defense": 28},
    {"code": "amber_titan", "title": "Янтарный Титан", "emoji": "🪨", "hp": 18000, "attack": 48, "defense": 36},
    {"code": "moon_serpent", "title": "Лунный Змей", "emoji": "🌙", "hp": 16500, "attack": 52, "defense": 30},
]

TITLES = [
    ("Новобранец", lambda p: p.get("level", 1) >= 1),
    ("Следопыт", lambda p: p.get("level", 1) >= 15),
    ("Ветеран", lambda p: p.get("level", 1) >= 80),
    ("Хозяин троп", lambda p: p.get("level", 1) >= 180),
    ("Властелин охоты", lambda p: p.get("level", 1) >= 320),
    ("Апекс", lambda p: p.get("level", 1) >= 500),
    ("Аренач", lambda p: p.get("wins", 0) >= 25),
    ("Богач", lambda p: p.get("gold", 0) >= 5000),
    ("Опора стаи", lambda p: p.get("reputation", 0) >= 120),
    ("Кошмарный охотник", lambda p: p.get("dungeon_hard_wins", 0) >= 10),
    ("Легенда сезона", lambda p: p.get("season_points", 0) >= 500),
]

REFERRAL_REWARD_ITEMS: list[int] = []
DAILY_TASK_POOL = []
WEEKLY_TASK_POOL = []
DEFAULT_MONETIZATION_PACKS = [
    {"code": "starter_pack", "name": "Стартовый набор", "price_rub": 99, "reward": {"gold": 250, "premium": 3}},
    {"code": "hunter_pass", "name": "Охотничий пропуск", "price_rub": 199, "reward": {"gold": 600, "premium": 8}},
    {"code": "clan_bundle", "name": "Набор стаи", "price_rub": 299, "reward": {"gold": 900, "premium": 12}},
]

FOOD_ADJ = ["Лесн", "Дымн", "Пряный", "Сочный", "Тёплый", "Ягодный", "Грибной", "Речной", "Теневой", "Янтарный"]
FOOD_BASE = ["ый кусок", "ый рулет", "ый пирог", "ая похлёбка", "ый шашлык", "ый сок"]
MAT_ADJ = ["Сырой", "Крепкий", "Сухой", "Тонкий", "Шероховатый", "Чистый", "Лунный", "Янтарный", "Буревой", "Дикий"]
MAT_BASE = ["камень", "корень", "лист", "слиток", "клык", "кристалл", "пластина", "шкура", "нить", "пыль"]
EQUIP_ADJ = ["Охотнич", "Боевой", "Теневой", "Грозовой", "Лунный", "Яростный", "Стальной", "Скалистый", "Ловкий", "Тотемный"]
EQUIP_BASE = ["шлем", "доспех", "наручи", "поножи", "амулет"]
ELIXIR_ADJ = ["Малая", "Средняя", "Большая", "Точная", "Яростная", "Лёгкая", "Твёрдая", "Удачливая", "Теневая", "Временная"]
ELIXIR_BASE = ["микстура жизни", "микстура энергии", "настойка", "сыворотка", "эссенция", "капсула"]
SCROLL_ADJ = ["Свиток", "Печать", "Грамота", "Хартия", "Знак", "Руна"]
SCROLL_BASE = ["силы", "скорости", "защиты", "удачи", "мастерства", "ремесла", "воровства", "шпионажа", "обмена", "перерождения"]
RECIPE_ADJ = ["Черновой", "Редкий", "Старинный", "Охотничий", "Кузнечный", "Алхимический", "Лунный", "Буревой", "Тотемный", "Тайный"]
RECIPE_BASE = ["рецепт", "свиток рецепта", "чертёж", "манускрипт", "кодекс"]


# Базовые природные материалы для крафта и экономики.
BASE_MATERIAL_IDS = []
for idx, (name, rarity, price) in enumerate([
    ("Вода", 1, 3), ("Ветка", 1, 4), ("Камень", 1, 5), ("Верёвка", 1, 6), ("Гриб", 1, 7),
    ("Малина", 1, 7), ("Трава", 1, 8), ("Перо", 2, 9), ("Кость", 2, 10), ("Кожа", 2, 12),
    ("Железная руда", 2, 14), ("Кристалл", 3, 18), ("Клык", 3, 20), ("Толстая шкура", 3, 22),
    ("Сталь", 4, 28), ("Янтарь", 4, 30), ("Лунная пыль", 5, 42), ("Пластина титана", 5, 46),
    ("Сердце бури", 6, 65), ("Слеза луны", 6, 72),
], start=1):
    BASE_MATERIAL_IDS.append(add_item("material", rarity, idx, name, emoji="🧱", price=price, weight=2, description="Базовый ресурс для крафта."))


# Дополнительные 50+ предметов в каждой категории.
food_seq_start = 21
for i in range(60):
    rarity = 1 + (i // 12)
    name = f"{FOOD_ADJ[i % len(FOOD_ADJ)]}{FOOD_BASE[i % len(FOOD_BASE)]}".replace("ный", "ный")
    add_item(
        "food", rarity, food_seq_start + i, name,
        emoji="🍖" if i % 2 == 0 else "🍓",
        price=8 + rarity * 4 + i,
        weight=1 + rarity // 2,
        hp_restore=10 + rarity * 8 + i % 7,
        energy_restore=8 + rarity * 7 + (i * 2) % 9,
        description="Еда восстанавливает здоровье и энергию.",
        tags=["food", "restore"],
    )

material_seq_start = 21
for i in range(60):
    rarity = 1 + (i // 12)
    name = f"{MAT_ADJ[i % len(MAT_ADJ)]} {MAT_BASE[i % len(MAT_BASE)]}"
    add_item(
        "material", rarity, material_seq_start + i, name,
        emoji="🪵" if i % 3 else "🪨",
        price=5 + rarity * 5 + i,
        weight=2 + rarity,
        description="Материал для крафта, ремонта и рынка.",
        tags=["material"],
    )

slots = ["head", "body", "paws", "legs", "accessory"]
equipment_seq_start = 1
for i in range(60):
    rarity = 1 + (i // 12)
    slot = slots[i % len(slots)]
    name = f"{EQUIP_ADJ[i % len(EQUIP_ADJ)]} {EQUIP_BASE[i % len(EQUIP_BASE)]}"
    stats = {
        "attack": 1 + rarity + (1 if slot in {"paws", "accessory"} else 0),
        "defense": 1 + rarity + (1 if slot in {"body", "head"} else 0),
        "speed": max(0, rarity - 1 + (1 if slot in {"legs", "accessory"} else 0)),
        "luck": max(0, rarity - 2 + (1 if slot == "accessory" else 0)),
        "hp": rarity * (6 if slot in {"body", "head"} else 3),
        "energy": rarity * (4 if slot in {"legs", "accessory"} else 2),
    }
    add_item(
        "equipment", rarity, equipment_seq_start + i, name,
        emoji="🛡" if slot in {"head", "body"} else "⚔️",
        price=30 + rarity * 22 + i * 3,
        weight=3 + rarity,
        slot=slot,
        stats=stats,
        max_durability=60 + rarity * 25,
        description=f"Экипировка для слота: {SLOT_TITLES[slot]}",
        tags=["equipment", slot],
    )

elixir_seq_start = 1
for i in range(60):
    rarity = 1 + (i // 12)
    name = f"{ELIXIR_ADJ[i % len(ELIXIR_ADJ)]} {ELIXIR_BASE[i % len(ELIXIR_BASE)]}"
    buffs = {
        "attack_pct": rarity * 2 if i % 5 == 0 else 0,
        "defense_pct": rarity * 2 if i % 5 == 1 else 0,
        "speed_pct": rarity * 2 if i % 5 == 2 else 0,
        "luck_pct": rarity * 2 if i % 5 == 3 else 0,
        "xp_pct": rarity * 2 if i % 5 == 4 else 0,
        "duration_min": 20 + rarity * 8,
    }
    add_item(
        "elixir", rarity, elixir_seq_start + i, name,
        emoji="🧪",
        price=18 + rarity * 15 + i * 2,
        weight=1,
        hp_restore=4 + rarity * 4 if i % 2 == 0 else 0,
        energy_restore=4 + rarity * 4 if i % 2 == 1 else 0,
        buffs=buffs,
        description="Одноразовый эликсир с восстановлением и временными бонусами.",
        tags=["elixir", "consumable"],
    )

scroll_seq_start = 1
scroll_effect_cycle = [
    {"slots_plus": 8}, {"weight_plus": 250}, {"attack_pct": 8}, {"defense_pct": 8}, {"speed_pct": 8},
    {"luck_pct": 8}, {"steal": 1}, {"spy": 1}, {"gift_bonus": 1}, {"reroll": 1},
]
for i in range(60):
    rarity = 1 + (i // 12)
    name = f"{SCROLL_ADJ[i % len(SCROLL_ADJ)]} {SCROLL_BASE[i % len(SCROLL_BASE)]}"
    buffs = {**scroll_effect_cycle[i % len(scroll_effect_cycle)], "duration_min": 15 + rarity * 10}
    add_item(
        "scroll", rarity, scroll_seq_start + i, name,
        emoji="📜",
        price=22 + rarity * 20 + i * 2,
        weight=1,
        buffs=buffs,
        description="Одноразовый свиток с сервисным или боевым эффектом.",
        tags=["scroll", "consumable"],
    )

recipe_seq_start = 1
for i in range(60):
    rarity = 1 + (i // 12)
    name = f"{RECIPE_ADJ[i % len(RECIPE_ADJ)]} {RECIPE_BASE[i % len(RECIPE_BASE)]} #{i+1}"
    add_item(
        "recipe", rarity, recipe_seq_start + i, name,
        emoji="📘",
        price=16 + rarity * 12 + i,
        weight=1,
        description="Коллекционный рецепт. Может быть нужен для редких крафтов и кодекса.",
        tags=["recipe"],
    )

# Реферальный предмет.
REFERRAL_GIFT_ITEM = add_item(
    "scroll", 3, 201, "Реферальный свиток удачи", emoji="🎁", price=65, weight=1,
    buffs={"luck_pct": 10, "duration_min": 60}, description="Небольшая награда за приглашение игрока.", tags=["referral"]
)
REFERRAL_REWARD_ITEMS.append(REFERRAL_GIFT_ITEM)

# Ивентовые и сервисные предметы.
PET_TOKEN_ID = add_item("scroll", 4, 202, "Жетон приручения", emoji="🐾", price=120, weight=1, description="Позволяет выбрать питомца.", buffs={"pet_token": 1})
CHEST_ID = add_item("scroll", 4, 203, "Запечатанный трофей", emoji="🎒", price=160, weight=1, description="Редкий контейнер для событий и админ-наград.")

DAILY_TASK_POOL.extend([
    {"code": "expeditions", "title": "Пройди экспедиции", "target": 2, "kind": "daily", "reward_gold": 28, "reward_xp": 30},
    {"code": "dungeons", "title": "Пройди подземелья", "target": 1, "kind": "daily", "reward_gold": 32, "reward_xp": 36},
    {"code": "pvp", "title": "Проведи PvP-бои", "target": 2, "kind": "daily", "reward_gold": 26, "reward_xp": 34},
    {"code": "craft", "title": "Скрафти предметы", "target": 2, "kind": "daily", "reward_gold": 24, "reward_xp": 28},
    {"code": "buy_market", "title": "Купи на рынке", "target": 1, "kind": "daily", "reward_gold": 20, "reward_xp": 22},
    {"code": "gift", "title": "Подари предмет", "target": 1, "kind": "daily", "reward_gold": 22, "reward_xp": 22},
    {"code": "boss", "title": "Ударь мирового босса", "target": 1, "kind": "daily", "reward_gold": 30, "reward_xp": 35},
    {"code": "request_help", "title": "Помоги с запросом", "target": 1, "kind": "daily", "reward_gold": 22, "reward_xp": 20},
])
WEEKLY_TASK_POOL.extend([
    {"code": "expeditions", "title": "Экспедиции недели", "target": 10, "kind": "weekly", "reward_gold": 120, "reward_xp": 140},
    {"code": "dungeons", "title": "Подземелья недели", "target": 6, "kind": "weekly", "reward_gold": 150, "reward_xp": 170},
    {"code": "pvp", "title": "Поборись на арене", "target": 12, "kind": "weekly", "reward_gold": 160, "reward_xp": 180},
    {"code": "craft", "title": "Ремесленник недели", "target": 12, "kind": "weekly", "reward_gold": 135, "reward_xp": 160},
    {"code": "boss", "title": "Охота на босса", "target": 5, "kind": "weekly", "reward_gold": 170, "reward_xp": 190},
    {"code": "wealth", "title": "Собери золото", "target": 800, "kind": "weekly", "reward_gold": 200, "reward_xp": 120},
])


def get_item(item_id: int) -> dict[str, Any]:
    return ITEMS[item_id]


def is_equipment(item_id: int) -> bool:
    return ITEMS[item_id]["category"] == "equipment"


def is_food(item_id: int) -> bool:
    return ITEMS[item_id]["category"] == "food"


def is_elixir(item_id: int) -> bool:
    return ITEMS[item_id]["category"] == "elixir"


def is_scroll(item_id: int) -> bool:
    return ITEMS[item_id]["category"] == "scroll"


def is_consumable(item_id: int) -> bool:
    return ITEMS[item_id]["category"] in {"food", "elixir", "scroll"}


def category_items(category: str) -> list[int]:
    return [item_id for item_id, data in ITEMS.items() if data["category"] == category]


def readable_item(item_id: int, amount: int = 1) -> str:
    item = get_item(item_id)
    return f"{item['emoji']} {item['name']} x{amount} [{item_id}]"
