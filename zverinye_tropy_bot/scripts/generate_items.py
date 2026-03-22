import json

# Список предметов для игры
items_data = [
    {
        "name": "Ягоды",
        "description": "Сладкие лесные ягоды",
        "rarity": "обычный",
        "type": "ресурс",
        "price": 5
    },
    {
        "name": "Орехи",
        "description": "Питательные лесные орехи",
        "rarity": "обычный",
        "type": "ресурс",
        "price": 8
    },
    {
        "name": "Грибы",
        "description": "Целебные грибы леса",
        "rarity": "редкий",
        "type": "ресурс",
        "price": 15
    },
    {
        "name": "Мёд",
        "description": "Сладкий пчелиный мёд",
        "rarity": "редкий",
        "type": "еда",
        "price": 20,
        "heal_amount": 15
    },
    {
        "name": "Рыба",
        "description": "Свежая речная рыба",
        "rarity": "обычный",
        "type": "еда",
        "price": 12,
        "heal_amount": 10
    },
    {
        "name": "Черви",
        "description": "Земляные черви для наживки",
        "rarity": "обычный",
        "type": "ресурс",
        "price": 3
    },
    {
        "name": "Кости",
        "description": "Старые кости животных",
        "rarity": "обычный",
        "type": "ресурс",
        "price": 7
    },
    {
        "name": "Коренья",
        "description": "Полезные лесные коренья",
        "rarity": "редкий",
        "type": "ресурс",
        "price": 18
    },
    {
        "name": "Эликсир энергии",
        "description": "Восстанавливает 5 единиц энергии",
        "rarity": "эпический",
        "type": "зелье",
        "price": 50,
        "energy_boost": 5
    },
    {
        "name": "Свиток смены персонажа",
        "description": "Позволяет сменить текущего персонажа",
        "rarity": "легендарный",
        "type": "свиток",        "price": 200
    },
    {
        "name": "Свиток усиления",
        "description": "Повышает урон на 1 уровень",
        "rarity": "эпический",
        "type": "свиток",
        "price": 150
    }
]

# Сохраняем в JSON-файл
with open('data/items.json', 'w', encoding='utf-8') as f:
    json.dump(items_data, f, ensure_ascii=False, indent=4)

print("Файл items.json успешно создан с", len(items_data), "предметами!")
