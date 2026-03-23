from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu():
    keyboard = [
        ["👤 Профиль", "🍽️ Сытость"],
        ["⛏️ Экспедиция", "🛠️ Крафт"],
        ["🛒 Магазин", "⛒ Рынок"],
        ["📖 Правила", "ℹ️ Помощь"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_character_keyboard():
    keyboard = [
        ["🐺 Волк", "🦊 Лиса"],
        ["🐻 Медведь", "🐿️ Белка"],
        ["🦝 Барсук", "🦉 Сова"],
        ["🦦 Выдра"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_resource_keyboard():
    keyboard = [
        ["Ягоды", "Орехи"],
        ["Грибы", "Мёд"],
        ["Рыба", "Черви"],
        ["Кости", "Коренья"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_expedition_keyboard():
    keyboard = [
        ["1️⃣ Лёгкая", "2️⃣ Средняя"],
        ["3️⃣ Сложная", "4️⃣ Кошмарная"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_craft_keyboard():
    keyboard = [
        ["🍖 Мясо + 🦴 Кости → 🍗 Бульон"],
        ["🌿 Травы + 💧 Вода → 🧪 Эликсир"],
        ["🪵 Дерево + 🪨 Камень → ⛏️ Кирка"],
        ["🔙 Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
