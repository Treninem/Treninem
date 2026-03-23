from telegram import Update
from telegram.ext import ContextTypes
from handlers.profile import profile_command, satiety_command, food_list_command
from handlers.game import expedition_command, craft_command, battle_command, check_expedition_results
from handlers.economy import shop_command, buy_command, market_command, sell_command
from handlers.rules import rules_command, report_command
from handlers.admin import admin_command, stats_command, give_item_command, add_money_command, ban_command, unban_command


# Словарь соответствий русского текста и функций-обработчиков
RUSSIAN_COMMANDS = {
    # Профиль и статистика
    "профиль": profile_command,
    "мой профиль": profile_command,
    "персонаж": profile_command,

    # Сытость и еда
    "сытость": satiety_command,
    "уровень сытости": satiety_command,
    "еда": food_list_command,
    "список еды": food_list_command,

    # Игровые действия
    "экспедиция": expedition_command,
    "отправить в экспедицию": expedition_command,
    "крафт": craft_command,
    "создать предмет": craft_command,
    "битва": battle_command,
    "сражение": battle_command,
    "результаты": check_expedition_results,
    "результаты экспедиции": check_expedition_results,

    # Экономика
    "магазин": shop_command,
    "купить": buy_command,
    "рынок": market_command,
    "продать": sell_command,

    # Прочее
    "правила": rules_command,
    "нарушения": report_command,
    "сообщить о нарушении": report_command,

    # Админ
    "админ": admin_command,
    "панель администратора": admin_command,
    "статистика": stats_command,
    "выдать предмет": give_item_command,
    "добавить деньги": add_money_command,
    "забанить": ban_command,
    "разбанить": unban_command,
}

async def handle_russian_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает русский текст как команды"""
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower().strip()

    # Ищем соответствие в словаре
    if text in RUSSIAN_COMMANDS:
        # Вызываем соответствующую функцию
        await RUSSIAN_COMMANDS[text](update, context)
