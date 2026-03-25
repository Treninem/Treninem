import database
import items

# Список администраторов (изначально пуст, заполняется владельцем)
ADMINS = set()

# ID владельца бота (замените на ваш ID Telegram)
OWNER_ID = 2097006037  # Замените на реальный ID

# Команда выдачи предмета
def give_item(user_id, item_id, quantity):
    """
    Выдаёт предмет пользователю. Используется владельцами/админами.
    """
    if item_id in items.ITEMS:
        database.add_item_to_inventory(user_id, item_id, quantity)
        return f"Предмет {items.ITEMS[item_id]['name']} (ID: {item_id}) выдан пользователю {user_id} в количестве {quantity} шт."
    else:
        return "Ошибка: предмет не найден."

# Команда блокировки пользователя
def ban_user(user_id):
    """
    Блокирует пользователя. Владелец может использовать на любом.
    Админ не может банить владельца и других админов.
    """
    if user_id == OWNER_ID:
        return "Нельзя заблокировать владельца бота."
    if user_id in ADMINS:
        return "Нельзя заблокировать администратора."
    database.update_user_field(user_id, 'banned', True)
    return f"Пользователь {user_id} заблокирован."

# Команда разблокировки пользователя
def unban_user(user_id):
    """
    Разблокирует пользователя.
    """
    database.update_user_field(user_id, 'banned', False)
    return f"Пользователь {user_id} разблокирован."

# Команда назначения админа
def make_admin(user_id):
    """
    Назначает пользователя администратором. Только для владельца.
    """
    if user_id != OWNER_ID:
        ADMINS.add(user_id)
        return f"Пользователь {user_id} назначен администратором."
    else:
        return "Владелец не может назначить себя администратором повторно."

# Команда разжалования админа
def remove_admin(user_id):
    """
    Разжаловывает администратора. Только для владельца.
    """
    if user_id in ADMINS:
        ADMINS.remove(user_id)
        return f"Пользователь {user_id} разжалован из администраторов."
    else:
        return "Пользователь не является администратором."

# Команда забрать предмет
def take_item(user_id, item_id, quantity):
    """
    Забирает предмет у пользователя. Используется владельцами/админами.
    """
    current_quantity = database.get_item_quantity(user_id, item_id)
    if current_quantity >= quantity:
        database.remove_item_from_inventory(user_id, item_id, quantity)
        return f"У пользователя {user_id} забрано {quantity} шт. предмета {items.ITEMS[item_id]['name']}."
    else:
        return f"Недостаточно предметов в инвентаре. Доступно: {current_quantity} шт."

# Команда повышения уровня
def level_up(user_id, levels):
    """
    Повышает уровень персонажа на указанное количество уровней.
    """
    for _ in range(levels):
        database.level_up_user(user_id)
    return f"Уровень пользователя {user_id} повышен на {levels} уровней."

# Команда просмотра списка забаненных
def banned_list():
    """
    Возвращает список забаненных пользователей.
    """
    banned_users = database.get_banned_users()
    if banned_users:
        return "Забаненные пользователи:\n" + "\n".join([str(uid) for uid in banned_users])
    else:
        return "Список забаненных пуст."

# Проверка прав доступа
def is_authorized(user_id, command_level="admin"):
    """
    Проверяет, имеет ли пользователь право на выполнение команды.
    command_level: "owner" или "admin".
    """
    if command_level == "owner":
        return user_id == OWNER_ID
    elif command_level == "admin":
        return user_id == OWNER_ID or user_id in ADMINS
    return False
