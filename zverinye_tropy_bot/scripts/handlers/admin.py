from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from database import Session, User
from config import ADMIN_IDS, ADMIN_PASSWORD
from datetime import datetime, timedelta
from sqlalchemy import func

from utils.keyboards import get_main_menu


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ У вас нет прав администратора!")
        return

    # Запрашиваем пароль
    await update.message.reply_text(
        "🔒 Введите пароль администратора:"
    )
    context.user_data['awaiting_admin_password'] = True

async def handle_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text

    if not context.user_data.get('awaiting_admin_password'):
        return

    if password != ADMIN_PASSWORD:
        await update.message.reply_text("❌ Неверный пароль!")
        context.user_data['awaiting_admin_password'] = False
        return

    context.user_data['awaiting_admin_password'] = False
    admin_menu = (
        "🛠️ **Панель администратора**\n\n"
        "Команды:\n"
        "/stats — Статистика сервера\n"
        "/give_item ID_пользователя название_предмета количество — Выдать предмет\n"
        "/add_money ID_пользователя сумма — Добавить монеты\n"
        "/ban ID_пользователя — Заблокировать пользователя\n"
        "/unban ID_пользователя — Разблокировать пользователя"
    )
    await update.message.reply_text(admin_menu, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    session = Session()
    total_users = session.query(User).count()
    active_users = session.query(User).filter(User.last_activity > datetime.utcnow() - timedelta(days=7)).count()
    total_money = session.query(func.sum(User.money)).scalar() or 0
    total_crystals = session.query(func.sum(User.crystals)).scalar() or 0

    stats_text = (
        f"📊 **Статистика сервера**\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🟢 Активных за неделю: {active_users}\n"
        f"💰 Общая сумма монет: {total_money:.0f}\n"
        f"💎 Общее количество кристаллов: {total_crystals:.0f}"
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown')
    session.close()

async def give_item_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    if len(context.args) != 3:
        await update.message.reply_text("Использование: /give_item ID_пользователя название_предмета количество")
        return

    try:
        user_id = int(context.args[0])
        item_name = context.args[1]
        quantity = int(context.args[2])
    except ValueError:
        await update.message.reply_text("Неверный формат аргументов!")
        return

    session = Session()
    user = session.query(User).filter_by(telegram_id=user_id).first()

    if not user:
        await update.message.reply_text("Пользователь не найден!")
        session.close()
        return

    if item_name in user.inventory:
        user.inventory[item_name] += quantity
    else:
        user.inventory[item_name] = quantity

    session.commit()
    await update.message.reply_text(f"✅ Предмет '{item_name}' ×{quantity} выдан пользователю {user_id}")
    session.close()

async def add_money_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    if len(context.args) != 2:
        await update.message.reply_text("Использование: /add_money ID_пользователя сумма")
        return

    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("Неверный формат аргументов!")
        return

    session = Session()
    user = session.query(User).filter_by(telegram_id=user_id).first()

    if not user:
        await update.message.reply_text("Пользователь не найден!")
        session.close()
        return

    user.money += amount
    session.commit()
    await update.message.reply_text(f"✅ {amount:.0f} монет добавлено пользователю {user_id}")
    session.close()

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /ban ID_пользователя")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Неверный ID пользователя!")
        return

    session = Session()
    user = session.query(User).filter_by(telegram_id=user_id).first()

    if not user:
        await update.message.reply_text("Пользователь не найден!")
        session.close()
        return

    user.is_banned = True
    session.commit()
    await update.message.reply_text(f"✅ Пользователь {user_id} заблокирован!")
    session.close()

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if len(context.args) != 1:
        await update.message.reply_text("Использование: /unban ID_пользователя")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Неверный ID пользователя!")
        return


    session = Session()
    user = session.query(User).filter_by(telegram_id=user_id).first()

    if not user:
        await update.message.reply_text("Пользователь не найден!")
        session.close()
        return

    user.is_banned = False
    session.commit()
    await update.message.reply_text(f"✅ Пользователь {user_id} разблокирован!")
    session.close()
