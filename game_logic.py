"""Чистая игровая логика: баланс, формулы, выпадения и симуляции."""

from __future__ import annotations

import math
import random
import time
from typing import Any

from config import (
    BLACK_MARKET_MULT,
    DUNGEON_LABELS,
    EMOJIS,
    EXPEDITION_LABELS,
    LOAN_INTEREST_RATE,
    RARITY_PRICE_MULT,
    RARITY_WEIGHTS,
    SEASON_ANCHOR_DAY,
    SEASON_LENGTH_DAYS,
    WORLD_BOSS_MAX_ATTACKS_PER_DAY,
    MAX_LEVEL,
    PRESTIGE_STAT_PCT,
    CONTRACTS_PER_DAY,
)
from data_crafts import RECIPES, recipe_lines
from data_items import (
    CHARACTERS,
    CONTRACT_TEMPLATES,
    DAILY_TASK_POOL,
    FACTIONS,
    ITEMS,
    PET_SPECIES,
    SLOT_ORDER,
    SLOT_TITLES,
    SPECIALIZATIONS,
    TALENTS,
    TITLES,
    WORLD_BOSS_TEMPLATES,
    category_items,
    get_item,
    rarity_stars,
)


def now_day() -> int:
    return int(time.time() // 86400)


# -----------------------------
# Прогрессия
# -----------------------------

def xp_for_level(level: int) -> int:
    """Кумулятивная кривая на очень длинный прогресс до 600 уровня."""
    if level <= 1:
        return 0
    x = level - 1
    return int(90 * x + 20 * (x ** 2) + 0.62 * (x ** 2.42) + 0.012 * (x ** 3.05))


def detect_level_from_xp(xp: int) -> int:
    level = 1
    for i in range(2, MAX_LEVEL + 1):
        if xp >= xp_for_level(i):
            level = i
        else:
            break
    return level


def stat_multiplier(level: int) -> float:
    # На 600 уровне итоговый рост остаётся большим, но не ломает боевой баланс.
    progress = max(0.0, min(1.0, (level - 1) / max(1, MAX_LEVEL - 1)))
    return 1.0 + 85.0 * (progress ** 1.14)


def prestige_multiplier(prestige: int) -> float:
    return 1.0 + max(0, prestige) * (PRESTIGE_STAT_PCT / 100)


def sync_level(profile: dict[str, Any]) -> dict[str, Any]:
    new_level = detect_level_from_xp(int(profile.get("xp", 0)))
    old_level = int(profile.get("level", 1))
    return {"old_level": old_level, "new_level": new_level, "level_up": new_level > old_level}


def season_info(ts: int | None = None) -> dict[str, int]:
    if ts is None:
        ts = int(time.time())
    day = ts // 86400
    passed = day - SEASON_ANCHOR_DAY
    season_no = passed // SEASON_LENGTH_DAYS + 1
    start_day = SEASON_ANCHOR_DAY + (season_no - 1) * SEASON_LENGTH_DAYS
    end_day = start_day + SEASON_LENGTH_DAYS - 1
    return {"season_no": int(season_no), "start_day": int(start_day), "end_day": int(end_day), "days_left": int(end_day - day + 1)}


def league_name(rating: int) -> str:
    if rating < 950:
        return "Бронза"
    if rating < 1100:
        return "Серебро"
    if rating < 1280:
        return "Золото"
    if rating < 1500:
        return "Платина"
    return "Алмаз"


def title_for_profile(profile: dict[str, Any]) -> str:
    found = "Новобранец"
    for title, check in TITLES:
        if check(profile):
            found = title
    return found


def pet_bonus(profile: dict[str, Any]) -> dict[str, int]:
    species = profile.get("pet_species") or ""
    if not species or species not in PET_SPECIES:
        return {}
    lvl = int(profile.get("pet_level", 0))
    base = PET_SPECIES[species]["bonus"]
    out: dict[str, int] = {}
    for k, v in base.items():
        out[k] = int(v + max(0, lvl - 1) * 1.5)
    return out


def effective_profile(profile: dict[str, Any], equipment: dict[str, Any], buffs: list[dict[str, Any]], extras: dict[str, Any] | None = None) -> dict[str, Any]:
    character_key = profile.get("character_key") or "wolf"
    char = CHARACTERS.get(character_key, CHARACTERS["wolf"])
    base = dict(char["stats"])
    mul = stat_multiplier(int(profile.get("level", 1)))
    prestige = int((extras or {}).get("prestige", 0))
    prestige_mul = prestige_multiplier(prestige)
    stats = {
        "hp": int(base["hp"] * mul * prestige_mul),
        "energy": int(base["energy"] * (1 + (mul - 1) * 0.45) * (1 + prestige * 0.01)),
        "attack": int(base["attack"] * (1 + (mul - 1) * 0.34) * prestige_mul),
        "defense": int(base["defense"] * (1 + (mul - 1) * 0.34) * prestige_mul),
        "speed": int(base["speed"] * (1 + (mul - 1) * 0.22) * (1 + prestige * 0.008)),
        "luck": int(base["luck"] * (1 + (mul - 1) * 0.18) * (1 + prestige * 0.008)),
        "xp_gain_pct": 0,
        "gold_gain_pct": 0,
        "boss_damage_pct": 0,
        "expedition_pct": 0,
        "dungeon_pct": 0,
        "status_pct": 0,
    }
    for slot in SLOT_ORDER:
        if slot not in equipment:
            continue
        eq = equipment[slot]
        item = eq["item"]
        max_d = item.get("max_durability", 0) or 1
        ratio = max(0.35, min(1.0, eq["durability"] / max_d))
        for key, value in item["stats"].items():
            stats[key] = stats.get(key, 0) + int(value * ratio)
    spec = profile.get("specialization")
    if spec and spec in SPECIALIZATIONS:
        for key, value in SPECIALIZATIONS[spec]["bonus"].items():
            stat_name = key.replace("_pct", "")
            if stat_name in stats:
                stats[stat_name] = int(stats[stat_name] * (1 + value / 100))
    if extras:
        faction_key = extras.get("faction_key") or ""
        if faction_key in FACTIONS:
            for key, value in FACTIONS[faction_key]["bonus"].items():
                if key.endswith("_pct") and key.replace("_pct", "") in stats:
                    stat_name = key.replace("_pct", "")
                    stats[stat_name] = int(stats[stat_name] * (1 + value / 100))
                else:
                    stats[key] = stats.get(key, 0) + value
        talents = dict(extras.get("talents", {}))
        for talent_code, rank in talents.items():
            talent = TALENTS.get(talent_code)
            if not talent or int(rank) <= 0:
                continue
            for key, value in talent["bonus_per_rank"].items():
                total = int(value) * int(rank)
                if key.endswith("_pct") and key.replace("_pct", "") in stats:
                    stat_name = key.replace("_pct", "")
                    stats[stat_name] = int(stats[stat_name] * (1 + total / 100))
                else:
                    stats[key] = stats.get(key, 0) + total
    pet = pet_bonus(profile)
    for key, value in pet.items():
        if key.endswith("_pct"):
            stat_name = key.replace("_pct", "")
            if stat_name in stats:
                stats[stat_name] = int(stats[stat_name] * (1 + value / 100))
            else:
                stats[key] = stats.get(key, 0) + value
        elif key in stats:
            stats[key] += value
        else:
            stats[key] = stats.get(key, 0) + value
    for buff in buffs:
        code = buff["code"]
        power = int(buff["power"])
        if code.endswith("_pct"):
            stat_name = code.replace("_pct", "")
            if stat_name in stats:
                stats[stat_name] = int(stats[stat_name] * (1 + power / 100))
            else:
                stats[code] = stats.get(code, 0) + power
        elif code in stats:
            stats[code] += power
        else:
            stats[code] = stats.get(code, 0) + power
    stats["max_hp"] = stats["hp"]
    stats["max_energy"] = stats["energy"]
    stats["title"] = title_for_profile(profile)
    stats["league"] = league_name(int(profile.get("rating", 1000)))
    stats["character"] = char
    stats["pet"] = pet
    stats["prestige"] = prestige
    return stats


def profile_progress(profile: dict[str, Any]) -> str:
    lvl = int(profile.get("level", 1))
    xp_now = int(profile.get("xp", 0))
    cur_need = xp_for_level(lvl)
    next_need = xp_for_level(min(MAX_LEVEL, lvl + 1))
    if lvl >= MAX_LEVEL:
        return f"Уровень {lvl}: достигнут потолок. Готов к престижу."
    in_level = xp_now - cur_need
    segment = max(1, next_need - cur_need)
    pct = int(min(100, max(0, in_level * 100 / segment)))
    return f"Уровень {lvl}: {pct}% до следующего. XP {xp_now}/{next_need}."


def profile_progress(profile: dict[str, Any]) -> str:
    lvl = int(profile.get("level", 1))
    xp_now = int(profile.get("xp", 0))
    cur_need = xp_for_level(lvl)
    next_need = xp_for_level(min(100, lvl + 1))
    in_level = xp_now - cur_need
    segment = max(1, next_need - cur_need)
    pct = int(min(100, max(0, in_level * 100 / segment)))
    return f"Уровень {lvl}: {pct}% до следующего. XP {xp_now}/{next_need}."


# -----------------------------
# Форматирование
# -----------------------------

def format_seconds(seconds: int) -> str:
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h}ч {m}м"
    if m:
        return f"{m}м {s}с"
    return f"{s}с"


def item_price(item_id: int) -> int:
    item = get_item(item_id)
    return int(item["price"] * RARITY_PRICE_MULT[item["rarity"]])


def format_item_line(item_id: int, amount: int = 1) -> str:
    item = get_item(item_id)
    return f"{item['emoji']} <b>{item['name']}</b> x{amount} · {item['rarity_name']} · [{item_id}]"


BONUS_LABELS = {
    "hp": "здоровье",
    "energy": "энергия",
    "attack": "атака",
    "defense": "защита",
    "speed": "скорость",
    "luck": "удача",
    "gold_gain_pct": "золото",
    "xp_gain_pct": "опыт",
    "xp_pct": "опыт",
    "material_drop_pct": "добыча материалов",
    "boss_damage_pct": "урон по боссу",
    "expedition_pct": "экспедиции",
    "dungeon_pct": "подземелья",
    "status_pct": "сила эффектов",
    "attack_pct": "атака",
    "defense_pct": "защита",
    "speed_pct": "скорость",
    "luck_pct": "удача",
    "energy_pct": "энергия",
    "hp_pct": "здоровье",
    "inventory_slots": "слоты инвентаря",
    "max_weight": "лимит веса",
    "slots_plus": "слоты инвентаря",
    "weight_plus": "лимит веса",
    "steal": "воровство",
    "spy": "шпионаж",
    "gift_bonus": "щедрый подарок",
    "reroll": "смена зверя",
}


def bonus_key_title(key: str) -> str:
    return BONUS_LABELS.get(key, key.replace('_', ' '))


def format_bonus_dict(data: dict[str, int]) -> str:
    parts: list[str] = []
    for key, value in data.items():
        if not value or key == 'duration_min':
            continue
        label = bonus_key_title(key)
        if key in {'steal', 'spy', 'gift_bonus', 'reroll'}:
            parts.append(label)
        elif key.endswith('_pct'):
            parts.append(f"{label} +{value}%")
        else:
            parts.append(f"{label} +{value}")
    return ', '.join(parts)


def item_effect_text(item_id: int) -> str:
    item = get_item(item_id)
    parts = [f"{item['emoji']} <b>{item['name']}</b>", f"Редкость: {item['rarity_name']} {rarity_stars(item['rarity'])}"]
    if item["slot"]:
        parts.append(f"Слот: {SLOT_TITLES.get(item['slot'], item['slot'])}")
    if item["stats"]:
        parts.append("Бонусы: " + format_bonus_dict(item["stats"]))
    if item["hp_restore"] or item["energy_restore"]:
        parts.append(f"Восстановление: здоровье +{item['hp_restore']}, энергия +{item['energy_restore']}")
    buffs = item.get("buffs", {})
    clean_buffs = {k: v for k, v in buffs.items() if v and k != "duration_min"}
    if clean_buffs:
        parts.append("Эффекты: " + format_bonus_dict(clean_buffs))
    if buffs.get("duration_min"):
        parts.append(f"Длительность: {buffs['duration_min']} мин.")
    if item.get("description"):
        parts.append(item["description"])
    return "\n".join(parts)


def choose_task_defs(pool: list[dict[str, Any]], user_id: int, count: int, salt: int) -> list[dict[str, Any]]:
    rnd = random.Random(user_id * 917 + salt * 37)
    picked = pool[:]
    rnd.shuffle(picked)
    return picked[:count]


def league_bonus_gold(rating: int) -> int:
    if rating < 950:
        return 0
    if rating < 1100:
        return 4
    if rating < 1280:
        return 7
    if rating < 1500:
        return 11
    return 15


# -----------------------------
# Магазины
# -----------------------------

def economy_snapshot(day_key: int | None = None) -> dict[str, Any]:
    day_key = now_day() if day_key is None else day_key
    rnd = random.Random(day_key * 313)
    cats = ["food", "material", "equipment", "elixir", "scroll", "recipe"]
    demand = rnd.choice(cats)
    surplus = rnd.choice([c for c in cats if c != demand])
    return {"demand": demand, "surplus": surplus, "discount": 0.12, "premium": 0.18}


def _stock_seed(multiplier: int = 0) -> int:
    # Ротация 4 раза в сутки.
    return int(time.time() // (6 * 3600)) + multiplier


def generate_shop_stock() -> list[dict[str, Any]]:
    rnd = random.Random(_stock_seed())
    eco = economy_snapshot()
    pool = [item_id for item_id, item in ITEMS.items() if item["category"] in {"food", "material", "equipment", "elixir", "scroll"}]
    weighted = []
    for item_id in pool:
        item = get_item(item_id)
        weight = max(1, RARITY_WEIGHTS[item["rarity"]] // 2)
        if item["category"] == eco["surplus"]:
            weight += 2
        weighted.extend([item_id] * weight)
    chosen: list[int] = []
    while len(chosen) < 10 and weighted:
        item_id = rnd.choice(weighted)
        if item_id not in chosen:
            chosen.append(item_id)
    out = []
    for item_id in chosen:
        item = get_item(item_id)
        price = item_price(item_id)
        if item["category"] == eco["surplus"]:
            price = int(price * (1 - eco["discount"]))
        elif item["category"] == eco["demand"]:
            price = int(price * (1 + eco["discount"] / 2))
        out.append({"item_id": item_id, "price": max(1, price)})
    return out


def generate_black_market_stock() -> list[dict[str, Any]]:
    rnd = random.Random(_stock_seed(77))
    eco = economy_snapshot()
    pool = [item_id for item_id, item in ITEMS.items() if item["category"] in {"equipment", "elixir", "scroll", "recipe"} and item["rarity"] >= 3]
    chosen = rnd.sample(pool, min(8, len(pool)))
    out = []
    for item_id in chosen:
        item = get_item(item_id)
        price = int(item_price(item_id) * BLACK_MARKET_MULT)
        if item["category"] == eco["demand"]:
            price = int(price * (1 + eco["premium"]))
        out.append({"item_id": item_id, "price": max(1, price)})
    return out


# -----------------------------
# Экспедиции и подземелья
# -----------------------------

def expedition_success_chance(level: int, difficulty: str, stats: dict[str, Any]) -> float:
    # Баланс под ТЗ: на 1 уровне «кошмар» почти не проходит,
    # а 100% достижимо только далеко позже и только на лёгких режимах.
    start = {"easy": 0.32, "normal": 0.14, "hard": 0.05, "nightmare": 0.015}[difficulty]
    target_level = {"easy": 25, "normal": 50, "hard": 75, "nightmare": 100}[difficulty]
    per_level = (0.92 - start) / max(1, target_level - 1)
    stat_bonus = min(0.10, (stats["attack"] + stats["defense"] + stats["speed"] + stats["luck"]) / 9000)
    talent_bonus = min(0.08, stats.get("expedition_pct", 0) / 100)
    chance = start + max(0, level - 1) * per_level + stat_bonus + talent_bonus
    cap = {"easy": 0.98, "normal": 0.94, "hard": 0.88, "nightmare": 0.78}[difficulty]
    return max(0.01, min(cap, chance))


def expedition_zone(level: int) -> str:
    if level < 20:
        return "Лунный Лес"
    if level < 40:
        return "Каменный Перевал"
    if level < 60:
        return "Болотная Гряда"
    if level < 80:
        return "Янтарные Руины"
    return "Сердце Бури"


def choose_expedition_event(level: int, difficulty: str) -> dict[str, Any]:
    rnd = random.Random(level * 19 + hash(difficulty) + now_day())
    events = [
        {"title": "Заброшенный тайник", "bonus_gold": 18, "bonus_xp": 10, "text": "Ты нашёл тайник охотников."},
        {"title": "Хищник в засаде", "bonus_gold": 0, "bonus_xp": 18, "text": "В засаде пришлось отбиваться от местного хищника."},
        {"title": "Странствующий торговец", "bonus_gold": 12, "bonus_xp": 6, "text": "Торговец обменял слухи на припасы."},
        {"title": "Тропа травника", "bonus_gold": 0, "bonus_xp": 8, "material_bonus": 1, "text": "На тропе травника удалось собрать дополнительные ресурсы."},
        {"title": "Лунная развилка", "bonus_gold": 8, "bonus_xp": 14, "text": "Правильный выбор пути ускорил продвижение."},
    ]
    return rnd.choice(events)


def random_loot_by_rarity(rnd: random.Random, category: str | None = None, min_rarity: int = 1, max_rarity: int = 6) -> int:
    pool = [item_id for item_id, item in ITEMS.items() if (category is None or item["category"] == category) and min_rarity <= item["rarity"] <= max_rarity]
    weights = [RARITY_WEIGHTS[ITEMS[item_id]["rarity"]] for item_id in pool]
    return rnd.choices(pool, weights=weights, k=1)[0]


def run_expedition(profile: dict[str, Any], equipment: dict[str, Any], buffs: list[dict[str, Any]], difficulty: str, extras: dict[str, Any] | None = None) -> dict[str, Any]:
    stats = effective_profile(profile, equipment, buffs, extras)
    level = int(profile.get("level", 1))
    rnd = random.Random(int(time.time()) + int(profile["user_id"]))
    chance = expedition_success_chance(level, difficulty, stats)
    success = rnd.random() <= chance
    zone = expedition_zone(level)
    event = choose_expedition_event(level, difficulty)
    base_gold = {"easy": 22, "normal": 48, "hard": 88, "nightmare": 150}[difficulty]
    base_xp = {"easy": 32, "normal": 70, "hard": 140, "nightmare": 260}[difficulty]
    loot: list[tuple[int, int]] = []
    if success:
        gold = int((base_gold + stats["luck"] // 8 + event.get("bonus_gold", 0)) * (1 + stats.get("gold_gain_pct", 0) / 100))
        xp = int((base_xp + stats["speed"] // 7 + event.get("bonus_xp", 0)) * (1 + stats.get("xp_gain_pct", 0) / 100))
        loot_count = {"easy": 2, "normal": 3, "hard": 4, "nightmare": 5}[difficulty]
        for _ in range(loot_count):
            category = rnd.choice(["food", "material", "elixir", "scroll"])
            min_r = 1 if difficulty in {"easy", "normal"} else 2
            max_r = 4 if difficulty == "easy" else 5 if difficulty == "normal" else 6
            loot.append((random_loot_by_rarity(rnd, category, min_r, max_r), 1))
        if event.get("material_bonus"):
            loot.append((random_loot_by_rarity(rnd, "material", 2, 4), 1))
        status = "Успех"
    else:
        gold = max(6, int((base_gold // 4) * (1 + stats.get("gold_gain_pct", 0) / 120)))
        xp = max(8, int((base_xp // 3) * (1 + stats.get("xp_gain_pct", 0) / 120)))
        loot.append((random_loot_by_rarity(rnd, "material", 1, 2), 1))
        status = "Провал"
    return {
        "success": success,
        "status": status,
        "chance": chance,
        "zone": zone,
        "event": event,
        "gold": gold,
        "xp": xp,
        "loot": loot,
    }


def dungeon_modifier(day_key: int | None = None) -> dict[str, Any]:
    day_key = now_day() if day_key is None else day_key
    rnd = random.Random(day_key * 77)
    modifiers = [
        {"title": "Уплотнённая броня", "monster_def_pct": 12, "reward_pct": 10},
        {"title": "Двойной лут", "reward_pct": 25},
        {"title": "Туман войны", "monster_speed_pct": 10, "reward_pct": 12},
        {"title": "Магия времени", "reward_pct": 15, "player_speed_pct": 6},
        {"title": "Хрупкие враги", "monster_def_pct": -8, "reward_pct": 5},
    ]
    return rnd.choice(modifiers)


def dungeon_success_chance(level: int, difficulty: str, floor: int, stats: dict[str, Any], modifier: dict[str, Any]) -> float:
    # Сложности выровнены так, чтобы лёгкий режим стабильно закрывался ближе к 25 уровню,
    # средний — к 50, сложный — к 75. Этажи усиливают штраф.
    base = {"easy": 0.22, "medium": 0.08, "hard": 0.025}[difficulty]
    target_level = {"easy": 25, "medium": 50, "hard": 75}[difficulty]
    progress = max(0, level - 1) * ((0.88 - base) / max(1, target_level - 1))
    floor_penalty = floor * {"easy": 0.018, "medium": 0.022, "hard": 0.028}[difficulty]
    combat_score = (stats["attack"] * 1.15 + stats["defense"] * 1.05 + stats["speed"] * 0.65 + stats["luck"] * 0.35) / (360 + floor * 18)
    mod = modifier.get("monster_def_pct", 0) / 100
    chance = base + progress + combat_score * 0.07 - floor_penalty - mod * 0.18 + min(0.08, stats.get("dungeon_pct", 0) / 100)
    cap = {"easy": 0.96, "medium": 0.90, "hard": 0.82}[difficulty]
    return max(0.01, min(cap, chance))




def dungeon_entry_requirements(difficulty: str, floor: int) -> dict[str, int]:
    # Доступ к этажам постепенно открывается по уровню.
    diff_base = {"easy": 1, "medium": 20, "hard": 40}[difficulty]
    floor_gate = max(0, floor - 1) * {"easy": 3, "medium": 3, "hard": 4}[difficulty]
    return {"min_level": diff_base + floor_gate}

def run_dungeon(profile: dict[str, Any], equipment: dict[str, Any], buffs: list[dict[str, Any]], difficulty: str, floor: int, extras: dict[str, Any] | None = None) -> dict[str, Any]:
    stats = effective_profile(profile, equipment, buffs, extras)
    modifier = dungeon_modifier()
    chance = dungeon_success_chance(int(profile.get("level", 1)), difficulty, floor, stats, modifier)
    rnd = random.Random(int(time.time()) + floor * 991 + int(profile["user_id"]))
    success = rnd.random() <= chance
    base_gold = {"easy": 28, "medium": 65, "hard": 150}[difficulty] + floor * 4
    base_xp = {"easy": 48, "medium": 110, "hard": 230}[difficulty] + floor * 7
    reward_pct = modifier.get("reward_pct", 0)
    gold = int(base_gold * (1 + reward_pct / 100) * (1 + stats.get("gold_gain_pct", 0) / 100))
    xp = int(base_xp * (1 + reward_pct / 100) * (1 + stats.get("xp_gain_pct", 0) / 100))
    if success:
        loot_count = 1 + floor // 5 + (1 if difficulty != "easy" else 0)
        loot = [(random_loot_by_rarity(rnd, rnd.choice(["equipment", "material", "elixir", "scroll"]), 2, 6 if difficulty == "hard" else 5), 1) for _ in range(loot_count)]
    else:
        loot = [(random_loot_by_rarity(rnd, "material", 1, 3), 1)]
        gold //= 3
        xp //= 2
    return {
        "success": success,
        "chance": chance,
        "modifier": modifier,
        "gold": max(8, gold),
        "xp": max(15, xp),
        "loot": loot,
        "boss_name": f"Страж этажа {floor}",
    }


# -----------------------------
# PvP и боёвка
# -----------------------------

def _apply_status(statuses: dict[str, int], fighter: dict[str, Any], enemy: dict[str, Any], log: list[str]) -> None:
    if statuses.get("bleed"):
        dmg = max(2, fighter["max_hp"] // 40)
        fighter["hp_cur"] -= dmg
        log.append(f"🩸 Кровотечение наносит {dmg} урона.")
        statuses["bleed"] -= 1
    if statuses.get("poison"):
        dmg = max(3, enemy["stats"]["luck"] // 5)
        fighter["hp_cur"] -= dmg
        log.append(f"☠️ Яд наносит {dmg} урона.")
        statuses["poison"] -= 1
    if statuses.get("shield"):
        statuses["shield"] -= 1
    if statuses.get("stun"):
        statuses["stun"] -= 1


def _character_ability(name: str, user_stats: dict[str, Any], enemy_stats: dict[str, Any], rnd: random.Random) -> tuple[int, dict[str, int], str]:
    char_key = name
    extra = 0
    status: dict[str, int] = {}
    text = ""
    if char_key == "wolf":
        extra = max(1, user_stats["attack"] // 8)
        status["bleed"] = 2
        text = "🐺 Волк оставляет кровавый след."
    elif char_key == "lion":
        extra = max(2, user_stats["attack"] // 6)
        if rnd.random() < 0.25:
            status["stun"] = 1
            text = "🦁 Рёв прайда оглушает врага."
        else:
            text = "🦁 Лев усиливает натиск."
    elif char_key == "fox":
        extra = max(1, user_stats["speed"] // 7)
        status["poison"] = 1
        text = "🦊 Лисья уловка ослабляет врага."
    elif char_key == "bear":
        extra = max(0, user_stats["defense"] // 8)
        status["shield"] = 2
        text = "🐻 Медведь поднимает яростный щит."
    elif char_key == "eagle":
        extra = max(1, user_stats["luck"] // 6)
        text = "🦅 Орёл наносит точный удар сверху."
    elif char_key == "crocodile":
        extra = max(1, user_stats["defense"] // 9)
        if rnd.random() < 0.2:
            status["stun"] = 1
        text = "🐊 Крокодил сковывает движение."
    elif char_key == "rhino":
        extra = max(2, user_stats["attack"] // 7)
        text = "🦏 Носорог пробивает защиту."
    return extra, status, text


def resolve_pvp(attacker: dict[str, Any], defender: dict[str, Any], atk_stats: dict[str, Any], def_stats: dict[str, Any], stake_gold: int = 0, ranked: bool = True) -> dict[str, Any]:
    rnd = random.Random(int(time.time()) + int(attacker["user_id"]) + int(defender["user_id"]))
    a = {"user_id": attacker["user_id"], "stats": atk_stats, "hp_cur": atk_stats["max_hp"], "energy_cur": atk_stats["max_energy"], "char": attacker.get("character_key", "wolf")}
    d = {"user_id": defender["user_id"], "stats": def_stats, "hp_cur": def_stats["max_hp"], "energy_cur": def_stats["max_energy"], "char": defender.get("character_key", "wolf")}
    a_status: dict[str, int] = {}
    d_status: dict[str, int] = {}
    log: list[str] = []
    for round_no in range(1, 8):
        log.append(f"<b>Раунд {round_no}</b>")
        for actor, actor_status, target, target_status, label in ((a, a_status, d, d_status, "A"), (d, d_status, a, a_status, "D")):
            _apply_status(actor_status, actor, target, log)
            if actor["hp_cur"] <= 0 or target["hp_cur"] <= 0:
                break
            if actor_status.get("stun", 0) > 0:
                log.append("😵 Боец пропускает ход из-за оглушения.")
                continue
            dodge_chance = min(0.25, target["stats"]["speed"] / (actor["stats"]["speed"] + target["stats"]["speed"] + 120))
            if rnd.random() < dodge_chance:
                log.append("💨 Цель уклонилась от удара.")
                continue
            ability_bonus, status_apply, ability_text = _character_ability(actor["char"], actor["stats"], target["stats"], rnd)
            base = actor["stats"]["attack"] - target["stats"]["defense"] * 0.48
            crit_chance = min(0.35, actor["stats"]["luck"] / 180)
            crit_mult = 1.6 if rnd.random() < crit_chance else 1.0
            dmg = max(4, int((base + ability_bonus + rnd.randint(0, actor["stats"]["speed"] // 8 + 4)) * crit_mult))
            if target_status.get("shield"):
                dmg = int(dmg * 0.78)
            target["hp_cur"] -= dmg
            for code, turns in status_apply.items():
                target_status[code] = max(target_status.get(code, 0), turns)
            if ability_text:
                log.append(ability_text)
            log.append(f"⚔️ Урон: {dmg}. Осталось HP цели: {max(0, target['hp_cur'])}")
            if target["hp_cur"] <= 0:
                break
        if a["hp_cur"] <= 0 or d["hp_cur"] <= 0:
            break
    if a["hp_cur"] == d["hp_cur"]:
        winner = a if atk_stats["speed"] + atk_stats["luck"] >= def_stats["speed"] + def_stats["luck"] else d
    else:
        winner = a if a["hp_cur"] > d["hp_cur"] else d
    loser = d if winner is a else a
    return {
        "winner_id": int(winner["user_id"]),
        "loser_id": int(loser["user_id"]),
        "log": log,
        "ranked": ranked,
        "stake_gold": stake_gold,
        "a_hp": max(0, a["hp_cur"]),
        "d_hp": max(0, d["hp_cur"]),
    }


# -----------------------------
# Банк и лагерь
# -----------------------------

def loan_offer(profile: dict[str, Any]) -> dict[str, int]:
    level = int(profile.get("level", 1))
    rep = int(profile.get("reputation", 0))
    amount = max(100, 80 + level * 26 + rep * 2)
    debt = int(amount * (1 + LOAN_INTEREST_RATE))
    return {"amount": amount, "debt": debt}


def camp_rewards(profile: dict[str, Any], hours: int) -> dict[str, Any]:
    rnd = random.Random(int(profile["user_id"]) + hours * 77 + now_day())
    gold = 12 * hours + int(profile.get("level", 1)) * 2
    xp = 18 * hours + int(profile.get("level", 1)) * 3
    loot = []
    for _ in range(min(4, max(1, hours // 2))):
        loot.append((random_loot_by_rarity(rnd, rnd.choice(["food", "material", "elixir"]), 1, 4), 1))
    return {"gold": gold, "xp": xp, "loot": loot}


# -----------------------------
# Мировой босс
# -----------------------------

def world_boss_today() -> dict[str, Any]:
    rnd = random.Random(now_day() * 141)
    tpl = rnd.choice(WORLD_BOSS_TEMPLATES)
    hp = tpl["hp"] + rnd.randint(-1200, 1800)
    return {**tpl, "max_hp": hp, "daily_key": now_day()}


def world_boss_attack(profile: dict[str, Any], stats: dict[str, Any], already_attacks: int) -> dict[str, Any]:
    boss = world_boss_today()
    rnd = random.Random(int(profile["user_id"]) + int(time.time()))
    remaining = max(0, WORLD_BOSS_MAX_ATTACKS_PER_DAY - already_attacks)
    if remaining <= 0:
        return {"ok": False, "text": "Лимит атак на босса за сегодня исчерпан."}
    damage = int((stats["attack"] * 0.8 + stats["speed"] * 0.35 + stats["luck"] * 0.2 + rnd.randint(8, 32)) * (1 + stats.get("boss_damage_pct", 0) / 100))
    crit = rnd.random() < min(0.28, stats["luck"] / 220)
    if crit:
        damage = int(damage * 1.55)
    return {
        "ok": True,
        "boss": boss,
        "damage": damage,
        "crit": crit,
        "reward_gold": int((22 + damage // 10) * (1 + stats.get("gold_gain_pct", 0) / 100)),
        "reward_xp": int((28 + damage // 8) * (1 + stats.get("xp_gain_pct", 0) / 100)),
    }


# -----------------------------
# Контракты и фракции
# -----------------------------

def daily_contract_board(day_key: int | None = None) -> list[dict[str, Any]]:
    day_key = now_day() if day_key is None else day_key
    rnd = random.Random(day_key * 997)
    board = CONTRACT_TEMPLATES[:]
    rnd.shuffle(board)
    return board[:CONTRACTS_PER_DAY]


def contract_by_code(code: str) -> dict[str, Any] | None:
    for row in CONTRACT_TEMPLATES:
        if row["code"] == code:
            return row
    return None


def run_contract(profile: dict[str, Any], equipment: dict[str, Any], buffs: list[dict[str, Any]], contract_code: str, extras: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract_by_code(contract_code)
    if not contract:
        return {"ok": False, "text": "Контракт не найден."}
    stats = effective_profile(profile, equipment, buffs, extras)
    rnd = random.Random(int(profile["user_id"]) * 13 + now_day() * 17 + hash(contract_code) % 997)
    lvl = int(profile.get("level", 1))
    chance = contract["base_chance"] + min(0.24, lvl / (MAX_LEVEL * 1.8)) + min(0.12, (stats["attack"] + stats["defense"] + stats["speed"]) / 12000)
    if extras and extras.get("faction_key") == "forest" and contract["loot_category"] in {"food", "recipe"}:
        chance += 0.04
    if extras and extras.get("faction_key") == "mountain" and contract["loot_category"] in {"material", "equipment"}:
        chance += 0.05
    if extras and extras.get("faction_key") == "swamp" and contract["loot_category"] in {"elixir", "scroll"}:
        chance += 0.05
    if extras and extras.get("faction_key") == "storm" and contract["loot_category"] in {"equipment", "recipe"}:
        chance += 0.04
    chance = max(0.18, min(0.9, chance))
    success = rnd.random() <= chance
    loot = []
    if success:
        loot.append((random_loot_by_rarity(rnd, contract["loot_category"], 2, 6), 1))
        if rnd.random() < 0.33:
            loot.append((random_loot_by_rarity(rnd, rnd.choice(["food", "material", "elixir", "scroll"]), 2, 5), 1))
        gold = int(contract["gold"] * (1 + stats.get("gold_gain_pct", 0) / 100) * (1 + lvl / (MAX_LEVEL * 4)))
        xp = int(contract["xp"] * (1 + stats.get("xp_gain_pct", 0) / 100) * (1 + lvl / (MAX_LEVEL * 3.6)))
        text = "Контракт выполнен"
    else:
        gold = max(12, contract["gold"] // 3)
        xp = max(18, contract["xp"] // 2)
        loot.append((random_loot_by_rarity(rnd, "material", 1, 3), 1))
        text = "Контракт сорван"
    return {
        "ok": True,
        "success": success,
        "chance": chance,
        "gold": gold,
        "xp": xp,
        "loot": loot,
        "contract": contract,
        "text": text,
    }


def faction_daily_reward(extras: dict[str, Any]) -> dict[str, Any]:
    faction_key = extras.get("faction_key") or ""
    if faction_key not in FACTIONS:
        return {"gold": 0, "item": None}
    day_key = now_day()
    rnd = random.Random(day_key * 123 + len(faction_key) * 17 + int(extras.get("faction_rep", 0)))
    faction = FACTIONS[faction_key]
    cat = faction["daily_category"]
    rep = int(extras.get("faction_rep", 0))
    gold = 26 + rep // 10
    item_id = random_loot_by_rarity(rnd, cat, 1, min(6, 2 + rep // 40))
    return {"gold": gold, "item": item_id}


# -----------------------------
# Крафт
# -----------------------------

def craft_preview(recipe_id: int, inventory_amounts: dict[int, int]) -> dict[str, Any]:
    recipe = RECIPES[recipe_id]
    missing = []
    for item_id, need in recipe["ingredients"].items():
        have = inventory_amounts.get(item_id, 0)
        if have < need:
            missing.append((item_id, need - have))
    return {"recipe": recipe, "missing": missing, "lines": recipe_lines(recipe)}


# -----------------------------
# Социальные/чаты
# -----------------------------

def maybe_chat_event(chat_id: int) -> dict[str, Any]:
    rnd = random.Random(chat_id + now_day() * 11 + int(time.time() // 600))
    return rnd.choice([
        {"code": "chest", "title": "Найден сундук", "text": "Кто первым откроет сундук, тот получит добычу."},
        {"code": "caravan", "title": "Замечен караван", "text": "Караван просит охрану — награда ждёт самого быстрого."},
        {"code": "beast", "title": "Дикий хищник", "text": "В чат ворвался хищник. Нажми, чтобы прогнать его."},
        {"code": "herbs", "title": "Россыпь трав", "text": "Редкие травы вот-вот исчезнут. Успей собрать первым."},
    ])
