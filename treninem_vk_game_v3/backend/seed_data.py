from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List

RARITIES = [
    ('trash', 'мусор'),
    ('common', 'обычный'),
    ('rare', 'редкий'),
    ('epic', 'эпический'),
    ('legendary', 'легендарный'),
    ('mythic', 'мифический'),
]

CATEGORIES = {
    'food': 'еда',
    'material': 'материалы',
    'equipment': 'экипировка',
    'elixir': 'эликсиры',
    'scroll': 'свитки',
}

CHARACTERS = {
    'wolf': {
        'label': 'Волк',
        'stats': {'hp': 125, 'energy': 90, 'attack': 18, 'defense': 12, 'speed': 17},
        'abilities': ['Рывок стаи', 'Кровавый след'],
    },
    'lion': {
        'label': 'Лев',
        'stats': {'hp': 145, 'energy': 85, 'attack': 20, 'defense': 14, 'speed': 13},
        'abilities': ['Царский рык', 'Солнечная грива'],
    },
    'fox': {
        'label': 'Лиса',
        'stats': {'hp': 110, 'energy': 110, 'attack': 15, 'defense': 10, 'speed': 21},
        'abilities': ['Теневой хвост', 'Хитрая подмена'],
    },
    'bear': {
        'label': 'Медведь',
        'stats': {'hp': 170, 'energy': 75, 'attack': 17, 'defense': 18, 'speed': 9},
        'abilities': ['Каменная шкура', 'Гнев берлоги'],
    },
    'eagle': {
        'label': 'Орёл',
        'stats': {'hp': 105, 'energy': 120, 'attack': 16, 'defense': 10, 'speed': 23},
        'abilities': ['Высотный удар', 'Око бури'],
    },
    'crocodile': {
        'label': 'Крокодил',
        'stats': {'hp': 155, 'energy': 80, 'attack': 19, 'defense': 16, 'speed': 10},
        'abilities': ['Челюсти трясины', 'Болотный щит'],
    },
    'rhino': {
        'label': 'Носорог',
        'stats': {'hp': 160, 'energy': 80, 'attack': 18, 'defense': 17, 'speed': 11},
        'abilities': ['Лобовая ярость', 'Панцирный напор'],
    },
}

EFFECT_KINDS = [
    'restore_hp', 'restore_energy', 'add_gold', 'add_exp', 'add_slots',
    'add_weight_limit', 'buff_attack', 'buff_defense', 'buff_speed',
    'buff_hp', 'buff_energy', 'equip_bonus', 'none'
]

EQUIP_SLOTS = ['weapon', 'helmet', 'armor', 'boots', 'amulet']

@dataclass
class Item:
    item_code: str
    name: str
    category: str
    rarity: str
    description: str
    weight: float
    price: int
    effect_kind: str
    effect_stat: str
    effect_value: int
    effect_duration: int
    equip_slot: str
    is_consumable: int
    is_stackable: int
    icon: str


def _rarity_by_index(i: int) -> str:
    thresholds = [(10, 'trash'), (40, 'common'), (70, 'rare'), (90, 'epic'), (98, 'legendary'), (10**9, 'mythic')]
    for cap, rarity in thresholds:
        if i <= cap:
            return rarity
    return 'common'


def _category_prefix(category: str) -> str:
    return {
        'food': '10',
        'equipment': '20',
        'material': '30',
        'elixir': '40',
        'scroll': '50',
        'currency': '60',
    }[category]


def _rarity_digit(rarity: str) -> str:
    return {
        'trash': '1',
        'common': '2',
        'rare': '3',
        'epic': '4',
        'legendary': '5',
        'mythic': '6',
    }[rarity]


def make_item_code(category: str, rarity: str, index: int) -> str:
    return f"ID{_category_prefix(category)}{_rarity_digit(rarity)}{index:03d}"


def generate_items() -> List[Dict]:
    items: List[Dict] = []
    food_prefixes = ['Сушёная', 'Лесная', 'Дикая', 'Медовая', 'Травяная', 'Огненная', 'Лунная', 'Снежная', 'Ягодная', 'Солнечная']
    food_bases = ['рыба', 'малина', 'оленина', 'ягода', 'лепёшка', 'вода', 'мёд', 'похлёбка', 'сыр', 'груша']
    material_prefixes = ['Грубый', 'Крепкий', 'Туманный', 'Древний', 'Костяной', 'Скалистый', 'Плотный', 'Сияющий', 'Болотный', 'Стальной']
    material_bases = ['камень', 'корень', 'слиток', 'клык', 'паутина', 'уголь', 'верёвка', 'кость', 'лист', 'руда']
    equip_prefixes = ['Охотничий', 'Стражевой', 'Кровавый', 'Лесной', 'Грозовой', 'Латный', 'Звериный', 'Мифический', 'Сумеречный', 'Солнечный']
    equip_bases = ['клинок', 'шлем', 'доспех', 'сапоги', 'амулет', 'коготь', 'щит', 'плащ', 'браслет', 'копьё']
    elixir_prefixes = ['Малый', 'Средний', 'Большой', 'Чистый', 'Сердечный', 'Бодрящий', 'Алый', 'Ледяной', 'Яростный', 'Звёздный']
    elixir_bases = ['эликсир жизни', 'эликсир энергии', 'настой силы', 'настой защиты', 'настой скорости', 'сироп воли', 'зелье охоты', 'зелье духа', 'капля грома', 'сок зверя']
    scroll_prefixes = ['Свиток', 'Древний свиток', 'Рунический свиток', 'Пыльный свиток', 'Золотой свиток', 'Тёмный свиток', 'Священный свиток', 'Тайный свиток', 'Старший свиток', 'Легендарный свиток']
    scroll_bases = ['расширения', 'силы', 'защиты', 'скорости', 'энергии', 'охоты', 'трофеев', 'наград', 'облегчения', 'опыта']

    # Food 120
    for i in range(1, 121):
        rarity = _rarity_by_index(i)
        name = f"{food_prefixes[(i-1)%10]} {food_bases[(i-1)//10 % 10]} #{i}"
        effect_kind = 'restore_hp' if i % 2 else 'restore_energy'
        value = 8 + i
        items.append(asdict(Item(
            make_item_code('food', rarity, i), name, 'food', rarity,
            f'Еда для походов. Восстанавливает часть ресурса.',
            round(0.1 + (i % 5) * 0.1, 2), 5 + i * 2,
            effect_kind, 'hp' if effect_kind == 'restore_hp' else 'energy', value, 0,
            '', 1, 1, '🍖'
        )))

    # Materials 120
    for i in range(1, 121):
        rarity = _rarity_by_index(i)
        name = f"{material_prefixes[(i-1)%10]} {material_bases[(i-1)//10 % 10]} #{i}"
        items.append(asdict(Item(
            make_item_code('material', rarity, i), name, 'material', rarity,
            'Материал для крафта, обмена и редких рецептов.',
            round(0.3 + (i % 7) * 0.15, 2), 8 + i * 3,
            'none', '', 0, 0, '', 0, 1, '🪨'
        )))

    # Equipment 120
    for i in range(1, 121):
        rarity = _rarity_by_index(i)
        base = equip_bases[(i-1)//12 % 10]
        slot = 'weapon' if base in ('клинок', 'коготь', 'копьё') else 'helmet' if base == 'шлем' else 'armor' if base in ('доспех', 'щит', 'плащ') else 'boots' if base == 'сапоги' else 'amulet'
        stat = ['attack', 'defense', 'speed', 'hp', 'energy'][i % 5]
        val = 3 + i // 6
        items.append(asdict(Item(
            make_item_code('equipment', rarity, i), f"{equip_prefixes[(i-1)%10]} {base} #{i}", 'equipment', rarity,
            'Экипировка усиливает характеристики и занимает слот.',
            round(0.8 + (i % 8) * 0.25, 2), 40 + i * 9,
            'equip_bonus', stat, val, 0, slot, 0, 0, '🛡️'
        )))

    # Elixirs 120
    for i in range(1, 121):
        rarity = _rarity_by_index(i)
        name = f"{elixir_prefixes[(i-1)%10]} {elixir_bases[(i-1)//10 % 10]} #{i}"
        kinds = ['restore_hp', 'restore_energy', 'buff_attack', 'buff_defense', 'buff_speed', 'add_exp']
        effect_kind = kinds[i % len(kinds)]
        stat = {
            'restore_hp': 'hp', 'restore_energy': 'energy', 'buff_attack': 'attack',
            'buff_defense': 'defense', 'buff_speed': 'speed', 'add_exp': 'exp'
        }[effect_kind]
        value = 12 + i
        items.append(asdict(Item(
            make_item_code('elixir', rarity, i), name, 'elixir', rarity,
            'Эликсир одноразового применения.',
            round(0.2 + (i % 4) * 0.1, 2), 20 + i * 5,
            effect_kind, stat, value, 0, '', 1, 1, '🧪'
        )))

    # Scrolls 120
    for i in range(1, 121):
        rarity = _rarity_by_index(i)
        name = f"{scroll_prefixes[(i-1)%10]} {scroll_bases[(i-1)//10 % 10]} #{i}"
        cycle = ['add_slots', 'add_weight_limit', 'buff_attack', 'buff_defense', 'buff_speed', 'buff_hp', 'buff_energy', 'add_gold', 'add_exp']
        effect_kind = cycle[(i - 1) % len(cycle)]
        stat = {
            'add_slots': 'slots', 'add_weight_limit': 'weight_limit', 'buff_attack': 'attack', 'buff_defense': 'defense',
            'buff_speed': 'speed', 'buff_hp': 'hp', 'buff_energy': 'energy', 'add_gold': 'gold', 'add_exp': 'exp'
        }[effect_kind]
        value = 1 + i // 20 if effect_kind == 'add_slots' else 3 + i // 8 if effect_kind == 'add_weight_limit' else 25 + i * 2
        items.append(asdict(Item(
            make_item_code('scroll', rarity, i), name, 'scroll', rarity,
            'Свиток одноразового действия.',
            round(0.05 + (i % 3) * 0.05, 2), 25 + i * 6,
            effect_kind, stat, value, 0, '', 1, 1, '📜'
        )))

    # Currency definition (not stored in inventory as regular item)
    items.append(asdict(Item(
        'ID601001', 'Золото', 'currency', 'common', 'Основная валюта игры.',
        0.0, 1, 'add_gold', 'gold', 1, 0, '', 0, 1, '🪙'
    )))
    return items


def generate_recipes(items: List[Dict]) -> List[Dict]:
    by_cat = {'food': [], 'material': [], 'equipment': [], 'elixir': [], 'scroll': []}
    for item in items:
        if item['category'] in by_cat:
            by_cat[item['category']].append(item)
    recipes = []
    for i in range(1, 121):
        mat1 = by_cat['material'][(i * 2) % len(by_cat['material'])]
        mat2 = by_cat['material'][(i * 3 + 7) % len(by_cat['material'])]
        result = by_cat['food'][i % len(by_cat['food'])] if i <= 40 else by_cat['elixir'][i % len(by_cat['elixir'])] if i <= 80 else by_cat['equipment'][i % len(by_cat['equipment'])]
        recipes.append({
            'recipe_code': f'R{i:03d}',
            'name': f'Рецепт #{i}: {result["name"]}',
            'ingredients': [
                {'item_code': mat1['item_code'], 'qty': 2 + (i % 3)},
                {'item_code': mat2['item_code'], 'qty': 1 + (i % 4)},
            ],
            'result_item_code': result['item_code'],
            'result_qty': 1,
            'difficulty': ['лёгкая', 'средняя', 'сложная'][i % 3],
        })
    return recipes


ITEMS = generate_items()
RECIPES = generate_recipes(ITEMS)
