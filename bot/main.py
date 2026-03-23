# main.py
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

from handlers.registration import register_handlers_registration
from handlers.character import register_handlers_character
from handlers.economy import register_handlers_economy
from handlers.admin import register_handlers_admin

load_dotenv()

API_TOKEN = os.getenv("BOT_TOKEN")
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=storage)

# Регистрация модулей
register_handlers_registration(dp)
register_handlers_character(dp)
register_handlers_economy(dp)
register_handlers_admin(dp)

async def on_startup():
    print("Бот запущен")

if __name__ == "__main__":
    import asyncio
    from aiogram import executor
    asyncio.run(on_startup())
    executor.start_polling(dp, skip_updates=True)