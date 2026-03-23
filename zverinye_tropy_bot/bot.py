
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN
from handlers.start import get_start_conversation
from handlers.profile import profile_command, satiety_command, food_list_command
from handlers.game import expedition_command, craft_command, battle_command, check_expedition_results
from handlers.economy import shop_command, buy_command, market_command, sell_command
from handlers.rules import rules_command, report_command
from handlers.admin import admin_command, handle_admin_password, stats_command, give_item_command, add_money_command, ban_command, unban_command
from handlers.russian_commands import handle_russian_commands
from telegram.error import TimedOut, NetworkError


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 **Помощь по боту «Звериные тропы»**\n\n"
        "Вы можете использовать команды двумя способами:\n\n"
        "**1. Через `/` (латинские команды):**\n"
        "/start — Регистрация и начало игры\n"
        "/profile — Ваш профиль и характеристики\n"
        "/satiety — Уровень сытости и рекомендации\n"
        "/food — Список еды и её эффекты\n"
        "/expedition — Отправить персонажа в экспедицию\n"
        "/craft — Создать предметы из ресурсов\n"
        "/battle — Сразиться с другим игроком или монстром\n"
        "/results — Проверить результаты экспедиции\n"
        "/shop — Купить предметы за монеты\n"
        "/market — Торговля с другими игроками\n"
        "/rules — Правила игры\n"
        "/report ID причина — Сообщить о нарушении\n"
        "/help — Эта справка\n\n"
        "**2. Просто текстом (русские команды):**\n"
        "Профиль — Ваш профиль и характеристики\n"
        "Сытость — Уровень сытости и рекомендации\n"
        "Еда — Список еды и её эффекты\n"
        "Экспедиция — Отправить персонажа в экспедицию\n"
        "Крафт — Создать предметы из ресурсов\n"
        "Битва — Сразиться с другим игроком или монстром\n"
        "Результаты — Проверить результаты экспедиции\n"
        "Магазин — Купить предметы за монеты\n"
        "Рынок — Торговля с другими игроками\n"
        "Правила — Правила игры\n"
        "Сообщить о нарушении ID причина — Сообщить о нарушении\n\n"
        "Администраторам:\n"
        "/admin — Панель администратора\n"
        "/stats — Статистика сервера\n"
        "/give_item ID предмет количество — Выдать предмет игроку\n"
        "/add_money ID сумма — Добавить деньги игроку\n"
        "/ban ID — Заблокировать игрока\n"
        "/unban ID — Разблокировать игрока"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

def run_bot():
    """Функция для запуска бота без конфликта с event loop"""
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(get_start_conversation())
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("satiety", satiety_command))
    application.add_handler(CommandHandler("food", food_list_command))
    application.add_handler(CommandHandler("expedition", expedition_command))
    application.add_handler(CommandHandler("craft", craft_command))
    application.add_handler(CommandHandler("battle", battle_command))
    application.add_handler(CommandHandler("results", check_expedition_results))
    application.add_handler(CommandHandler("shop", shop_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("market", market_command))
    application.add_handler(CommandHandler("sell", sell_command))
    application.add_handler(CommandHandler("rules", rules_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("help", help_command))

    # Административные команды
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_password))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("give_item", give_item_command))
    application.add_handler(CommandHandler("add_money", add_money_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))

    # Обработчик русского текста
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_russian_commands
        )
    )

    print("Бот запущен...")

    # Запускаем polling без asyncio.run()
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=None
    )

# Запуск приложения
if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")
    except Exception as e:
        print(f"Критическая ошибка: {e}")