import random
import database
import items
import crafts

# Шансы прохождения подземелья в зависимости от уровня
DUNGEON_CHANCES = {
    'easy': {1: 4, 25: 100},      # Лёгкий: 4 % на 1 лвл, 100 % на 25 лвл
    'medium': {1: 2, 50: 100},    # Средний: 2 % на 1 лвл, 100 % на 50 лвл
    'hard': {1: 1, 75: 100}       # Сложный: 1 % на 1 лвл, 100 % на 75 лвл
}

# Награда за экспедицию по уровням сложности
EXPEDITION_REWARDS = {
    'easy': {'gold': (1, 5), 'items': [(10001, 1), (20001, 2)]},
    'normal': {'gold': (5, 15), 'items': [(11002, 1), (21002, 3)]},
    'hard': {'gold': (15, 30), 'items': [(12003, 1), (31001, 1)]},
    'nightmare': {'gold': (30, 50), 'items': [(42002, 1), (52002, 1)]}
}

# Функция расчёта шанса прохождения подземелья
def calculate_dungeon_chance(user_level, difficulty):
    """
    Рассчитывает шанс прохождения подземелья на основе уровня игрока.
    difficulty — 'easy', 'medium' или 'hard'.
    Возвращает шанс в процентах.
    """
    levels = DUNGEON_CHANCES[difficulty]
    min_level, min_chance = min(levels.items())
    max_level, max_chance = max(levels.items())

    if user_level <= min_level:
        return min_chance
    elif user_level >= max_level:
        return max_chance
    else:
        # Линейная интерполяция между минимальным и максимальным шансом
        progress = (user_level - min_level) / (max_level - min_level)
        return min_chance + (max_chance - min_chance) * progress

# Функция экспедиции
def expedition(user_id, difficulty):
    """
    Выполняет экспедицию. Возвращает результат и награду.
    """
    user_data = database.get_user_data(user_id)
    chance = random.randint(1, 100)
    success_threshold = EXPEDITION_REWARDS[difficulty]['gold'][1] * 2  # Упрощённый расчёт шанса

    if chance <= success_threshold:
        gold_reward = random.randint(*EXPEDITION_REWARDS[difficulty]['gold'])
        items_reward = EXPEDITION_REWARDS[difficulty]['items']
        # Обновляем данные пользователя
        database.add_gold(user_id, gold_reward)
        for item_id, count in items_reward:
            database.add_item_to_inventory(user_id, item_id, count)
        return f"✅ Экспедиция успешна! Вы получили {gold_reward} золота и предметы."
    else:
        return "❌ Экспедиция не удалась. Попробуйте снова позже."

# Функция ПВП
def pvp_battle(attacker_id, defender_id):
    """
    Проводит бой между двумя игроками. Возвращает победителя и результат.
    """
    attacker = database.get_user_data(attacker_id)
    defender = database.get_user_data(defender_id)

    # Упрощённая механика боя: сравниваем атаку атакующего и защиту защитника
    attacker_power = attacker['attack'] * (1 + random.uniform(-0.1, 0.1))
    defender_power = defender['defense'] * (1 + random.uniform(-0.1, 0.1))

    if attacker_power > defender_power:
        winner = attacker
        loser = defender
        result = f"Победил {attacker['first_name']}!"
    else:
        winner = defender
        loser = attacker
        result = f"Победил {defender['first_name']}!"

    # Награда победителю: 10 % от золота проигравшего
    reward = loser['gold'] // 10
    database.add_gold(winner['user_id'], reward)
    database.remove_gold(loser['user_id'], reward)

    return result
