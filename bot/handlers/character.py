# handlers/character.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from models.database import get_connection
from aiogram import F

router = Router()

VIP_CHAR = ["Рысь","Росомаха","Орёл"]

@router.message(Command("сменить_персонажа"))
async def change_character(message: Message):
    # простая демонстрация: простое уведомление
    await message.reply("Чтобы сменить персонажа, используйте свитки смены (пока не реализовано полностью).")

def register_handlers_character(dp):
    dp.include_router(router)