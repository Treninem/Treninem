# handlers/economy.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from models.database import get_connection

router = Router()

@router.message(Command("профиль"))
async def profile(message: Message):
    user_id = message.from_user.id
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT username, character, hp, energy, hunger, coins, crystals FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        if not row:
            await message.reply("Профиль не найден. Пройдите регистрацию командой /start.")
            return
        reply = f"Ник: {row['username']}\nПерсонаж: {row['character']}\nHP: {row['hp']}\nЭнергия: {row['energy']}\nСытость: {row['hunger']}\nМонеты: {row['coins']}\nКристаллы: {row['crystals']}"
        await message.reply(reply)

def register_handlers_economy(dp):
    dp.include_router(router)