import os
from cryptography.fernet import Fernet

# Токен бота от @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# URL базы данных (SQLite по умолчанию)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")

# Секретный ключ для хеширования паролей
SECRET_KEY = os.getenv("SECRET_KEY", Fernet.generate_key().decode())

# Настройки премиум‑подписки
PREMIUM_BONUSES = {
    "7_days": {"resource_chance": 0.2, "inventory_slots": 10},
    "30_days": {"resource_chance": 0.25, "inventory_slots": 20},
    "90_days": {"resource_chance": 0.3, "inventory_slots": 30}
}

# Настройки VIP‑статуса
VIP_BONUSES = {
    "discount": 0.15,
    "craft_speed": 0.5
}
