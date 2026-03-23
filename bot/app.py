from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import config
from modules.user_management import register_user, get_user_profile
from modules.game_mechanics import start_expedition, complete_expedition
from modules.economy import list_market_items, process_trade
from modules.admin_panel import check_admin_password, get_stats, give_item
from utils.helpers import format_user_profile
from utils.validators import validate_trade_command, validate_gift_command

# Инициализация бота
application = Application.builder().token(config.BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user_profile(user.id)
    if not user_data:
        await update.message.reply_text(
            "Добро пожаловать! Для регистрации введите:\n"
            "старт <никнейм> <персонаж>\n"
            "Персонажи: лиса, волк, медведь, белка, барсук, сова, выдра"
        )
    else:
        await update.message.reply_text("Вы уже зарегистрированы!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user = update.effective_user

    # Обработка команды регистрации
    if text.startswith("старт "):
        parts = text.split()
        if len(parts) < 3:
            await update.message.reply_text("Использование: старт <никнейм> <персонаж>")
            return
        nickname = parts[1]
        character = parts[2]

        if not validate_nickname(nickname):
            await update.message.reply_text("Никнейм должен быть 3–16 символов, только буквы/цифры/подчёркивание")
            return

        success = register_user(user.id, nickname, character)
        if success:
            await update.message.reply_text(f"Успешная регистрация! Персонаж: {character}")
        else:
            await update.message.reply_text("Ошибка регистрации. Возможно, вы уже зарегистрированы.")

    # Профиль пользователя
    elif text == "/профиль":
        user_data = get_user_profile(user.id)
        if user_data:
            profile_text = format_user_profile(user_data)
            await update.message.reply_text(profile_text)
        else:
            await update.message.reply_text("Сначала зарегистрируйтесь командой 'старт'")

    # Экспедиции
    elif text.startswith("/экспедиция "):
        difficulty = text.split()[1]
        if difficulty not in ["easy", "medium", "hard", "nightmare"]:
            await update.message.reply_text("Неверный уровень. Используйте: easy/medium/hard/nightmare")
            return
        result = start_expedition(user.id, difficulty)
        await update.message.reply_text(result["message"])

    # Рынок
    elif text == "/рынок":
        items = list_market_items()
        if items:
            market_text = "\n".join([f"{item.item_id}: {item.price} монет ({item.quantity} шт.)" for item in items[:10]])
            await update.message.reply_text(f"Актуальные лоты:\n{market_text}")
        else:
            await update.message.reply_text("На рынке пока нет товаров")

    # Обмен
    elif text.startswith("обмен "):
        trade_data = validate_trade_command(text)
        if trade_data:
            # Здесь должна быть логика создания предложения обмена
            await update.message.reply_text(
                f"Предложение обмена отправлено пользователю {trade_data['target_user']}"
            )
        else:
            await update.message.reply_text("Неверный формат команды обмена")

    # Подарок
    elif text.startswith("/подарить "):
        gift_data = validate_gift_command(text)
        if gift_data:
            # Здесь должна быть логика передачи предмета
            await update.message.reply_text(
                f"Подарок отправлен пользователю {gift_data['target_user']}"
            )
        else:
            await update.message.reply_text("Неверный формат команды подарка")

    # Админ‑команды
    elif text.startswith("/admin "):
        password = text.split()[1]
        if check_admin_password(password):
            context.user_data["is_admin"] = True
            await update.message.reply_text("Доступ администратора получен")
        else:
            await update.message.reply_text("Неверный пароль")

    elif text == "/stats" and context.user_data.get("is_admin"):
        stats = get_stats()
        stats_text = (
            f"Статистика:\n"
            f"Всего пользователей: {stats['total_users']}\n"
            f"Активных экспедиций: {stats['active_expeditions']}\n"
            f"Лотов на рынке: {stats['market_listings']}"
        )
        await update.message.reply_text(stats_text)

    else:
        await update.message.reply_text("Неизвестная команда. Используйте /help для списка команд")

# Добавляем обработчики
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Запускаем бота
if __name__ == "__main__":
    application.run_polling()
