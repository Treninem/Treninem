# handlers/admin.py
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from bot_config import ADMIN_IDS, ADMIN_PASSWORD_HASH

router = Router()

@router.message(Command("admin"))
async def admin_login(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("Нет прав доступа.")
        return
    await message.reply("Введите пароль администратора:")

@router.message(lambda m: m.text and m.from_user.id in ADMIN_IDS)
async def admin_password_check(message: Message):
    # Демо: простая проверка пароля (жёстко проверять не стоит в продакшн)
    if str(hash(message.text)) == str(ADMIN_PASSWORD_HASH):
        await message.reply("Доступ разрешён. Команды администратора активированы.")
    else:
        await message.reply("Неверный пароль.")

def register_handlers_admin(dp):
    dp.include_router(router)