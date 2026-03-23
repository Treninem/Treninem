from telegram import Update
from telegram.ext import ContextTypes
from database import Session, User
from utils.keyboards import get_main_menu

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = Session()
    user = session.query(User).filter_by(telegram_id=user_id).first()

    if not user:
        await update.message.reply_text("Сначала зарегистрируйтесь с помощью /start")
        session.close()
        return

    vip_status = "VIP" if user.is_vip else "Обычный"
    if user.vip_expires:
        vip_status += f" (до {user.vip_expires.strftime('%d.%m.%Y')})"

    profile_text = (
        f"👤 **Профиль {user.nickname}**\n\n"
        f"🐱 Персонаж: {user.character}\n"
        f"⭐ Уровень: {user.level}\n"
        f"✨ Опыт: {user.exp}\n\n"
        f"❤️ HP: {user.hp}/{user.max_hp}\n"
        f"⚡ Энергия: {user.energy}/{user.max_energy}\n"
        f"🍽️ Сытость: {user.satiety}/{user.max_satiety}\n\n"
        f"💰 Монеты: {user.money:.0f}\n"
        f"💎 Кристаллы: {user.crystals:.0f}\n\n"
        f"🏆 Статус: {vip_status}\n"
        f"🌿 Любимый ресурс: {user.favorite_resource}"
    )

    await update.message.reply_text(profile_text, parse_mode='Markdown', reply_markup=get_main_menu())
    session.close()

async def satiety_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = Session()
    user = session.query(User).filter_by(telegram_id=user_id).first()

    if not user:
        await update.message.reply_text("Сначала зарегистрируйтесь с помощью /start")
        session.close()
        return

    satiety_text = f"🍽️ Ваш уровень сытости: {user.satiety}/{user.max_satiety}"

    # Рекомендации по еде в зависимости от персонажа
    food_recommendations = {
        "🐺 Волк": "Рекомендуется: мясо, кости",
        "🦊 Лиса": "Рекомендуется: ягоды, мыши",
        "🐻 Медведь": "Рекомендуется: мёд, рыба",
        "🐿️ Белка": "Рекомендуется: орехи, грибы",
        "🦝 Барсук": "Рекомендуется: черви, коренья",
        "🦉 Сова": "Рекомендуется: мыши, насекомые",
        "🦦 Выдра": "Рекомендуется: рыба, моллюски"
    }

    if user.character in food_recommendations:
        satiety_text += f"\n\n🍴 {food_recommendations[user.character]}"

    await update.message.reply_text(satiety_text, reply_markup=get_main_menu())
    session.close()

async def food_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    food_text = (
        "🍴 **Доступные виды еды:**\n\n"
        "• Ягоды — восстанавливают 5 сытости\n"
        "• Орехи — восстанавливают 3 сытости\n"
        "• Грибы — восстанавливают 4 сытости\n"
        "• Мёд — восстанавливают 8 сытости\n"
        "• Рыба — восстанавливают 6 сытости\n"
        "• Черви — восстанавливают 2 сытости\n"
        "• Кости — восстанавливают 3 сытости\n"
        "• Коренья — восстанавливают 4 сытости"
    )
    await update.message.reply_text(food_text, parse_mode='Markdown', reply_markup=get_main_menu())
