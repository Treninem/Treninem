# handlers/registration.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import sqlite3
from models.database import get_connection, init_db

router = Router()

class RegStates(StatesGroup):
    nickname = State()
    character = State()
    favorite_resource = State()

CHARACTERS = ["Лиса","Волк","Медведь","Белка","Барсук","Сова","Выдра"]

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await message.reply("Привет! Введите никнейм (до 16 символов):")
    await state.set_state(RegStates.nickname)

@router.message(RegStates.nickname)
async def set_nickname(message: Message, state: FSMContext):
    nick = message.text.strip()
    if len(nick) > 16:
        await message.reply("Никнейм слишком длинный. Введите до 16 символов.")
        return
    # сохранить ник
    user_id = message.from_user.id
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (id, username, hp, energy, hunger, level, exp, coins, crystals) VALUES (?, ?, 80,5,2,1,0,0,0)", (user_id, nick))
        conn.commit()
    await message.reply(f"Ник установлен: {nick}. Выберите персонажа: {', '.join(CHARACTERS)}")
    await state.set_state(RegStates.character)

@router.message(RegStates.character)
async def set_character(message: Message, state: FSMContext):
    ch = message.text.strip()
    if ch not in CHARACTERS:
        await message.reply("Неправильный выбор персонажа. Выберите из списка: " + ", ".join(CHARACTERS))
        return
    user_id = message.from_user.id
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET character=? WHERE id=?", (ch, user_id))
        conn.commit()
    await message.reply("Выберите любимый ресурс:")
    await state.set_state(RegStates.favorite_resource)

@router.message(RegStates.favorite_resource)
async def set_resource(message: Message, state: FSMContext):
    res = message.text.strip()
    user_id = message.from_user.id
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("UPDATE users SET favorite_resource=? WHERE id=?", (res, user_id))
        conn.commit()
    await message.reply("Регистрация завершена! Введите /профиль чтобы увидеть ваш профиль.")
    await state.clear()

def register_handlers_registration(dp):
    dp.include_router(router)