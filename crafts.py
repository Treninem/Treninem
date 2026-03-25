# Словарь рецептов крафта
CRAFTS = [
    {
        'result': 41001,  # Зелье здоровья (ID)
        'ingredients': {10001: 2, 11002: 1},  # Хлеб (2 шт.) + Яблоко (1 шт.)
        'name': 'Рецепт: Зелье здоровья'
    },
    {
        'result': 32002,  # Стальной меч (ID)
        'ingredients': {22003: 3, 20001: 5},  # Железная руда (3 шт.) + Дерево (5 шт.)
        'name': 'Рецепт: Стальной меч'
    },
        {
        'result': {'id': 32002, 'quantity': 1},  # Охотничий нож
        'materials': [
            {'id': 22003, 'quantity': 1},  # Железная руда
            {'id': 26007, 'quantity': 1}   # Рог лося (для рукояти)
        ],
        'station': 'forge'
    },
    {
        'result': {'id': 31111, 'quantity': 1},  # Лук из тиса
        'materials': [
            {'id': 20001, 'quantity': 2},  # Древесина дуба
            {'id': 27008, 'quantity': 3}   # Перья ястреба (для стрел, но можно использовать для тетивы)
        ],
        'station': 'workbench'
    },
    {
        'result': {'id': 30110, 'quantity': 1},  # Капкан
        'materials': [
            {'id': 22003, 'quantity': 3},  # Железная руда
            {'id': 21002, 'quantity': 5}   # Речной камень (для утяжеления)
        ],
        'station': 'forge'
    },

    # Экипировка
    {
        'result': {'id': 31001, 'quantity': 1},  # Кожаный доспех охотника
        'materials': [
            {'id': 25006, 'quantity': 4},  # Шкура медведя
            {'id': 29010, 'quantity': 2}   # Шерсть волка (для подкладки)
        ],
        'station': 'tannery'  # Дубильня
    },
    {
        'result': {'id': 34004, 'quantity': 1},  # Шапка из волчьего меха
        'materials': [
            {'id': 29010, 'quantity': 3},  # Шерсть волка
            {'id': 23004, 'quantity': 1}   # Клык волка (украшение/амулет)
        ],
        'station': 'sewing_table'  # Швейный стол
    },
    {
        'result': {'id': 37007, 'quantity': 1},  # Перчатки из шкуры
        'materials': [
            {'id': 25006, 'quantity': 2},  # Шкура медведя
            {'id': 28009, 'quantity': 1}   # Кости кабана (для защиты костяшек)
        ],
        'station': 'sewing_table'
    },
    {
        'result': 12003,  # Жареное мясо (ID)
        'ingredients': {10001: 1, 21002: 1},  # Хлеб (1 шт.) + Камень (1 шт., для готовки)
        'name': 'Рецепт: Жареное мясо'
    }

]

# Функция проверки возможности крафта
def can_craft(user_inventory, recipe):
    """
    Проверяет, достаточно ли материалов в инвентаре для крафта.
    user_inventory — словарь инвентаря пользователя.
    recipe — словарь рецепта из CRAFTS.
    Возвращает True, если можно скрафтить, иначе False.
    """
    for item_id, required_count in recipe['ingredients'].items():
        if user_inventory.get(item_id, 0) < required_count:
            return False
    return True

# Функция выполнения крафта
def perform_craft(user_inventory, recipe):
    """
    Выполняет крафт: удаляет ингредиенты из инвентаря и добавляет результат.
    Возвращает обновлённый инвентарь.
    """
    # Удаляем ингредиенты
    for item_id, count in recipe['ingredients'].items():
        user_inventory[item_id] -= count
        # Удаляем запись, если количество стало 0
        if user_inventory[item_id] <= 0:
            del user_inventory[item_id]
    # Добавляем результат
    result_id = recipe['result']
    if result_id in user_inventory:
        user_inventory[result_id] += 1
    else:
        user_inventory[result_id] = 1
    return user_inventory

# Функция получения всех рецептов
def get_all_crafts():
    return CRAFTS
