import json
from telegram import Update
from telegram.ext import ContextTypes
from database import Session, User, MarketLot
from utils.keyboards import get_main_menu

# Загружаем данные предметов
with open('data/items.json', 'r', encoding='utf-8') as f:
    ITEMS_DATA = json.load(f)

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    shop_text = "🛒 **Магазин** (обновляется ежедневно)\n\n"
    for item in ITEMS_DATA[:5]:  # Показываем первые 5 предметов
        shop_text += f"• {item['name']} — {item['price']} монет\n"
        if 'heal_amount' in item and item['heal_amount'] > 0:
            shop_text += f"  Восстанавливает {item['heal_amount']} сытости\n"
        shop_text += f"  {item['description']}\n\n"
    shop_text += "Используйте /купить ID_предмета количество для покупки"
    await update.message.reply_text(shop_text, parse_mode='Markdown', reply_markup=get_main_menu())

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /купить ID_предмета количество")
        return

    try:
        item_id = int(context.args[0]) - 1
        quantity = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Неверный формат. Используйте: /купить ID_предмета количество")
        return

    if item_id < 0 or item_id >= len(ITEMS_DATA):
        await update.message.reply_text("Предмет с таким ID не найден!")
        return

    item = ITEMS_DATA[item_id]
    total_cost = item['price'] * quantity

    user_id = update.effective_user.id
    session = Session()
    user = session.query(User).filter_by(telegram_id=user_id).first()

    if not user:
        await update.message.reply_text("Сначала зарегистрируйтесь с помощью /start")
        session.close()
        return

    if user.money < total_cost:
        await update.message.reply_text(f"Недостаточно монет! Требуется {total_cost}, у вас {user.money:.0f}")
        session.close()
        return

    # Покупаем предмет
    user.money -= total_cost
    item_name = item['name']
    if item_name in user.inventory:
        user.inventory[item_name] += quantity
    else:
        user.inventory[item_name] = quantity

    session.commit()
    await update.message.reply_text(
        f"✅ Вы купили {item_name} ×{quantity} за {total_cost} монет!",
        reply_markup=get_main_menu()
    )
    session.close()

async def market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    lots = session.query(MarketLot).limit(10).all()

    if not lots:
        await update.message.reply_text("На рынке пока нет лотов!")
        session.close()
        return

    market_text = "⛒ **Рынок игроков** (первые 10 лотов)\n\n"
    for lot in lots:
        market_text += f"ID: {lot.id}\n"
        market_text += f"Продавец: {lot.seller_id}\n"
        market_text += f"Предмет: {lot.item_id}\n"
        market_text += f"Цена: {lot.price} монет\n"
        market_text += f"Количество: {lot.quantity}\n"
        market_text += "─────────────\n"

    market_text += "\nИспользуйте /выставить ID_предмета цена количество для продажи"
    await update.message.reply_text(market_text, parse_mode='Markdown', reply_markup=get_main_menu())
    session.close()

async def sell_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Заглушка для выставления на рынок — будет доработано позже
    await update.message.reply_text("Система рынка в разработке!", reply_markup=get_main_menu())
