# Словарь всех предметов в игре с их характеристиками
ITEMS = {
    # Еда (ID начинается с 1)
    10001: {'name': 'Хлеб', 'type': 'food', 'rarity': 'common', 'heal': 10},
    11002: {'name': 'Яблоко', 'type': 'food', 'rarity': 'common', 'heal': 5},
    12003: {'name': 'Жареное мясо', 'type': 'food', 'rarity': 'rare', 'heal': 25},
    13004: {'name': 'Грибной бульон', 'type': 'food', 'rarity': 'uncommon', 'heal': 16, 'weight': 0.5},
    14005: {'name': 'Вяленая рыба', 'type': 'food', 'rarity': 'common', 'heal': 10, 'weight': 0.3},
    15006: {'name': 'Медвежий жир', 'type': 'food', 'rarity': 'epic', 'heal': 45, 'weight': 0.7},
    16007: {'name': 'Ореховая смесь', 'type': 'food', 'rarity': 'common', 'heal': 8, 'weight': 0.2},
    17008: {'name': 'Тушёная крольчатина', 'type': 'food', 'rarity': 'uncommon', 'heal': 20, 'weight': 0.6},
    18009: {'name': 'Печёный корень сельдерея', 'type': 'food', 'rarity': 'common', 'heal': 7, 'weight': 0.3},
    19010: {'name': 'Вяленое мясо кабана', 'type': 'food', 'rarity': 'rare', 'heal': 32, 'weight': 0.8},
    10111: {'name': 'Мёд диких пчёл', 'type': 'food', 'rarity': 'uncommon', 'heal': 25, 'weight': 0.4},
    11112: {'name': 'Шиповниковый чай', 'type': 'food', 'rarity': 'common', 'heal': 9, 'weight': 0.2},
    12113: {'name': 'Охотничьи сухари', 'type': 'food', 'rarity': 'common', 'heal': 11, 'weight': 0.3},
    13114: {'name': 'Запечённая репа', 'type': 'food', 'rarity': 'common', 'heal': 5, 'weight': 0.4},
    14115: {'name': 'Лосиная печень', 'type': 'food', 'rarity': 'legendary', 'heal': 60, 'weight': 1.0},

    # Материалы (ID начинается с 2)
    20001: {'name': 'Дерево', 'type': 'material', 'rarity': 'common'},
    21002: {'name': 'Камень', 'type': 'material', 'rarity': 'common'},
    22003: {'name': 'Железная руда', 'type': 'material', 'rarity': 'rare'},
    23004: {'name': 'Клык волка', 'type': 'material', 'rarity': 'uncommon', 'weight': 0.1},
    24005: {'name': 'Коготь орла', 'type': 'material', 'rarity': 'rare', 'weight': 0.05},
    25006: {'name': 'Шкура медведя', 'type': 'material', 'rarity': 'epic', 'weight': 5.0},
    26007: {'name': 'Рог лося', 'type': 'material', 'rarity': 'rare', 'weight': 1.5},
    27008: {'name': 'Перья ястреба', 'type': 'material', 'rarity': 'uncommon', 'weight': 0.03},
    28009: {'name': 'Кости кабана', 'type': 'material', 'rarity': 'common', 'weight': 2.0},
    29010: {'name': 'Шерсть волка', 'type': 'material', 'rarity': 'uncommon', 'weight': 0.8},
    20111: {'name': 'Чешуя щуки', 'type': 'material', 'rarity': 'common', 'weight': 0.2},
    21112: {'name': 'Клюв глухаря', 'type': 'material', 'rarity': 'uncommon', 'weight': 0.04},
    22113: {'name': 'Хвост лисы', 'type': 'material', 'rarity': 'rare', 'weight': 0.3},
    23114: {'name': 'Медвежья желчь', 'type': 'material', 'rarity': 'epic', 'weight': 0.5},
    24115: {'name': 'Волчья слюна', 'type': 'material', 'rarity': 'mythic', 'weight': 0.01},


    # Экипировка (ID начинается с 3)
    31001: {'name': 'Кожаная куртка', 'type': 'equipment', 'rarity': 'common', 'defense_bonus': 5},
    32002: {'name': 'Стальной меч', 'type': 'equipment', 'rarity': 'rare', 'attack_bonus': 10},
    33003: {'name': 'Щит из лосиных рогов', 'type': 'equipment', 'rarity': 'uncommon', 'defense_bonus': 9, 'slot': 'offhand', 'weight': 4.5},
    34004: {'name': 'Шапка из волчьего меха', 'type': 'equipment', 'rarity': 'rare', 'defense_bonus': 4, 'slot': 'head', 'weight': 1.2},
    35005: {'name': 'Сапоги следопыта', 'type': 'equipment', 'rarity': 'epic', 'speed_bonus': 4, 'slot': 'feet', 'weight': 2.0},
    36006: {'name': 'Амулет из клыка', 'type': 'equipment', 'rarity': 'legendary', 'attack_bonus': 18, 'slot': 'accessory', 'weight': 0.4},
    37007: {'name': 'Перчатки из шкуры', 'type': 'equipment', 'rarity': 'uncommon', 'defense_bonus': 3, 'slot': 'hands', 'weight': 1.0},
    38008: {'name': 'Пояс охотника', 'type': 'equipment', 'rarity': 'common', 'inventory_bonus': 5, 'slot': 'waist', 'weight': 0.8},
    39009: {'name': 'Наплечники из кости', 'type': 'equipment', 'rarity': 'rare', 'defense_bonus': 7, 'slot': 'shoulders', 'weight': 2.5},
    30110: {'name': 'Капкан', 'type': 'equipment', 'rarity': 'uncommon', 'trap_damage': 15, 'slot': 'trap', 'weight': 3.0},
    31111: {'name': 'Лук из тиса', 'type': 'equipment', 'rarity': 'rare', 'attack_bonus': 14, 'slot': 'ranged', 'weight': 2.2},
    32112: {'name': 'Стрелы с каменным наконечником', 'type': 'equipment', 'rarity': 'common', 'attack_bonus': 5, 'quantity':
   
    # Зелья (ID начинается с 4)
    41001: {'name': 'Зелье здоровья', 'type': 'potion', 'rarity': 'common', 'heal': 30},
    42002: {'name': 'Зелье скорости', 'type': 'potion', 'rarity': 'rare', 'speed_bonus': 5, 'duration': 300},
    42003: {'name': 'Зелье звериного чутья', 'type': 'potion', 'rarity': 'rare', 'perception_bonus': 10, 'duration': 400, 'weight': 0.1},
    43004: {'name': 'Настойка медвежьей силы', 'type': 'potion', 'rarity': 'epic', 'attack_bonus': 12, 'duration': 600, 'weight': 0.2},
    44005: {'name': 'Эликсир охотничьей удачи', 'type': 'potion', 'rarity': 'legendary', 'luck_bonus': 25, 'duration': 900, 'weight': 0.15},
    45006: {'name': 'Отвар из мухоморов', 'type': 'potion', 'rarity': 'common', 'heal': 8, 'duration': 0, 'weight': 0.1},
    46007: {'name': 'Бальзам целителя', 'type': 'potion', 'rarity': 'uncommon', 'heal': 18, 'weight': 0.12},
    47008: {'name': 'Зелье ночного зрения', 'type': 'potion', 'rarity': 'rare', 'night_vision': True, 'duration': 600, 'weight': 0.1},
    48009: {'name': 'Настой из женьшеня', 'type': 'potion', 'rarity': 'uncommon', 'speed_bonus': 3, 'duration': 180, 'weight': 0.11},
    49010: {'name': 'Зелье стойкости', 'type': 'potion', 'rarity': 'rare', 'defense_bonus': 6, 'duration': 360, 'weight': 0.13},
    40111: {'name': 'Эликсир следопыта', 'type': 'potion', 'rarity': 'epic', 'tracking_bonus': 15, 'duration': 720, 'weight': 0.14},
    41112: {'name': 'Зелье скрытности', 'type': 'potion', 'rarity': 'rare', 'stealth_bonus': 20, 'duration': 480, 'weight': 0.1},
    42113: {'name': 'Отвар бодрости', 'type': 'potion', 'rarity': 'common', 'stamina_regen': 2, 'duration': 300, 'weight': 0.1},
    # Свитки (ID начинается с 5)
    51001: {'name': 'Свиток ускорения', 'type': 'scroll', 'rarity': 'epic', 'effect': 'speed_up', 'duration': 600},
    52002: {'name': 'Свиток защиты', 'type': 'scroll', 'rarity': 'epic', 'effect': 'defense_up', 'duration': 600},

    # Валюта (ID 70001)
    70001: {'name': 'Золото', 'type': 'currency', 'rarity': 'common'}
}

# Функция для получения предмета по ID
def get_item(item_id):
    return ITEMS.get(item_id)

# Функция для получения списка всех предметов
def get_all_items():
    return ITEMS
