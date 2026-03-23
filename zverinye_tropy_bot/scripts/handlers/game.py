import random
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from database import Session, User, Expedition
from utils.keyboards import get_main_menu

# Шансы успеха для разных уровней подземелий
EXPEDITION_SUCCESS_CHANCES = {
    1: 0.9,  # Лёгкое
    2: 0.6,  # Среднее
    3: 0.3,  # Сложное
    4: 0.1   # Кошмарное
}

# Награды для разных уровней
EXPEDITION_REWARDS = {
    1: {"money": (10, 30), "items": [("Ягоды", 2, 5), ("Орехи", 1, 3)]},
    2: {"money": (30, 60), "items": [("Грибы", 1, 2), ("Мёд", 1, 1), ("Чертежи", 1, 1)]},
    3: {"money": (60, 100), "items": [("Свиток смены персонажа", 1, 1)]},
    4: {"money": (100, 200), "items": [("Кристаллы", 5, 15), ("VIP‑свиток", 1, 1)]}
}

async def expedition_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    level_str = ' '.join(context.args) if context.args else ''

    if not level_str.isdigit():
        await update.message.reply_text("Укажите уровень экспедиции: 1–4")
        return

    level = int(level_str)
    if level not in [1, 2, 3, 4]:
        await update.message.reply_text("Уровень экспедиции должен быть от 1 до 4")
        return

    session = Session()
    user = session.query(User).filter_by(telegram_id=user_id).first()

    if not user:
        await update.message.reply_text("Сначала зарегистрируйтесь с помощью /start")
        session.close()
        return

    if user.satiety <= 0:
        await update.message.reply_text("Вы слишком голодны для экспедиции! Восстановите сытость.")
        session.close()
        return
    if user.energy <= 0:
        await update.message.reply_text("У вас недостаточно энергии для экспедиции!")
        session.close()
        return

    # Тратим энергию
    energy_cost = level * 2
    if user.energy < energy_cost:
        await update.message.reply_text(f"Недостаточно энергии! Требуется {energy_cost} ед.")
        session.close()
        return

    user.energy -= energy_cost
    user.satiety -= level


    # Создаём запись экспедиции
    duration = timedelta(hours=level)  # Чем сложнее, тем дольше
    end_time = datetime.utcnow() + duration

    expedition = Expedition(
        user_id=user.id,
        level=level,
        status="в пути",
        end_time=end_time
    )
    session.add(expedition)
    session.commit()

    success_chance = EXPEDITION_SUCCESS_CHANCES[level]
    result_text = (
        f"⛏️ Вы отправились в экспедицию уровня {level}!\n"
        f"⏰ Время возвращения: {end_time.strftime('%H:%M %d.%m')}\n"
        f"🎯 Шанс успеха: {success_chance * 100:.0f}%"
    )
    await update.message.reply_text(result_text, reply_markup=get_main_menu())
    session.close()

async def craft_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Заглушка для крафта — будет доработано позже
    await update.message.reply_text("🛠️ Система крафта в разработке!", reply_markup=get_main_menu())

async def battle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Заглушка для
    # Заглушка для боя — будет доработано позже
    await update.message.reply_text("👊 Система боёв в разработке!", reply_markup=get_main_menu())

async def check_expedition_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = Session()
    user = session.query(User).filter_by(telegram_id=user_id).first()

    if not user:
        await update.message.reply_text("Сначала зарегистрируйтесь с помощью /start")
        session.close()
        return

    # Ищем текущую экспедицию
    expedition = session.query(Expedition).filter_by(user_id=user.id, status="в пути").first()
    if not expedition:
        await update.message.reply_text("У вас нет активных экспедиций!")
        session.close()
        return

    if datetime.utcnow() < expedition.end_time:
        remaining_time = expedition.end_time - datetime.utcnow()
        hours = remaining_time.seconds // 3600
        minutes = (remaining_time.seconds % 3600) // 60
        await update.message.reply_text(
            f"⛏️ Ваша экспедиция ещё в пути!\n"
            f"⏰ Осталось: {hours}ч {minutes}м"
        )
        session.close()
        return

    # Определяем успех экспедиции
    success_chance = EXPEDITION_SUCCESS_CHANCES[expedition.level]
    is_successful = random.random() <= success_chance

    result_text = f"⛏️ **Результаты экспедиции уровня {expedition.level}**\n\n"

    if is_successful:
        # Получаем награды
        rewards = EXPEDITION_REWARDS[expedition.level]
        money_gain = random.randint(rewards["money"][0], rewards["money"][1])
        user.money += money_gain
        result_text += f"✅ Успех! Вы получили {money_gain} монет.\n"

        # Добавляем предметы
        for item_name, min_qty, max_qty in rewards["items"]:
            qty = random.randint(min_qty, max_qty)
            if item_name in user.inventory:
                user.inventory[item_name] += qty
            else:
                user.inventory[item_name] = qty
            result_text += f"🎁 Получено: {item_name} ×{qty}\n"
    else:
        result_text += "❌ Неудача! Экспедиция не принесла результатов."

    # Обновляем статус экспедиции
    expedition.status = "завершена"
    session.commit()
    await update.message.reply_text(result_text, parse_mode='Markdown', reply_markup=get_main_menu())
    session.close()
