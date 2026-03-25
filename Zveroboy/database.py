import sqlite3
import json

# Подключение к базе данных SQLite
conn = sqlite3.connect('zveroboy.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц при первом запуске
def init_db():
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            level INTEGER DEFAULT 1,
            experience INTEGER DEFAULT 0,
            required_exp INTEGER DEFAULT 100,
            health INTEGER DEFAULT 80,
            max_health INTEGER DEFAULT 80,
            attack INTEGER DEFAULT 15,
            defense INTEGER DEFAULT 8,
            speed INTEGER DEFAULT 12,
            gold INTEGER DEFAULT 100,
            character TEXT,
            inventory TEXT DEFAULT '{}'
        )
    ''')

    conn.commit()

# Проверка регистрации пользователя
def is_user_registered(user_id):
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone() is not None

# Регистрация нового пользователя
def register_user(user_id, username, first_name):
    cursor.execute(
        "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user_id, username, first_name)
    )
    conn.commit()

# Добавление золота пользователю
def add_gold(user_id, amount):
    cursor.execute("UPDATE users SET gold = gold + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

# Удаление золота у пользователя
def remove_gold(user_id, amount):
    cursor.execute("UPDATE users SET gold = gold - ? WHERE user_id = ? AND gold >= ?", (amount, user_id, amount))
    conn.commit()

# Добавление предмета в инвентарь
def add_item_to_inventory(user_id, item_id, quantity):
    user_data = get_user_data(user_id)
    inventory = user_data['inventory']
    if item_id in inventory:
        inventory[item_id] += quantity
    else:
        inventory[item_id] = quantity
    cursor.execute(
        "UPDATE users SET inventory = ? WHERE user_id = ?",
        (json.dumps(inventory), user_id)
    )
    conn.commit()

# Получение количества предмета в инвентаре
def get_item_quantity(user_id, item_id):
    user_data = get_user_data(user_id)
    return user_data['inventory'].get(item_id, 0)

# Удаление предмета из инвентаря
def remove_item_from_inventory(user_id, item_id, quantity):
    user_data = get_user_data(user_id)
    inventory = user_data['inventory']
    if inventory.get(item_id, 0) >= quantity:
        inventory[item_id] -= quantity
        if inventory[item_id] <= 0:
            del inventory[item_id]
        cursor.execute(
            "UPDATE users SET inventory = ? WHERE user_id = ?",
            (json.dumps(inventory), user_id)
        )
        conn.commit()

# Повышение уровня пользователя
def level_up_user(user_id):
    user_data = get_user_data(user_id)
    new_level = user_data['level'] + 1
    new_max_health = int(user_data['max_health'] * 1.05)
    new_attack = int(user_data['attack'] * 1.04)
    new_defense = int(user_data['defense'] * 1.03)
    new_speed = int(user_data['speed'] * 1.02)
    new_required_exp = int(user_data['required_exp'] * 1.2)

    cursor.execute('''
        UPDATE users
        SET level = ?, max_health = ?, health = ?, attack = ?, defense = ?, speed = ?, required_exp = ?
        WHERE user_id = ?
    ''', (new_level, new_max_health, new_max_health, new_attack, new_defense, new_speed, new_required_exp, user_id))
    conn.commit()

# Обновление поля пользователя
def update_user_field(user_id, field, value):
    cursor.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()

# Получение списка забаненных пользователей
def get_banned_users():
    cursor.execute("SELECT user_id FROM users WHERE banned = 1")
    return [row[0] for row in cursor.fetchall()]

# Получение данных пользователя
def get_user_data(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row:
        # Преобразуем строку в словарь с понятными ключами
        return {
            'user_id': row[0],
            'username': row[1],
            'first_name': row[2],
            'level': row[3],
            'experience': row[4],
            'required_exp': row[5],
            'health': row[6],
            'max_health': row[7],
            'attack': row[8],
            'defense': row[9],
            'speed': row[10],
            'gold': row[11],
            'character': row[12],
            'inventory': json.loads(row[13]) if row[13] else {}
        }
    return None

# Инициализация базы данных при импорте модуля
init_db()
