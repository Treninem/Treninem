# Импортируем необходимые библиотеки
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import database
import game_mechanics
from admin_commands import is_authorized, give_item, ban_user, unban_user, make_admin, remove_admin, take_item, level_up, banned_list



# Настраиваем логирование для отслеживания ошибок и событий
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота (замените на ваш токен от @BotFather)
TOKEN = "8501813124:AAG1VVyqD7EviyYEVtntNJN_aOgG2eo8_HU"

# Функция обработки команды /start — регистрация нового игрока
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id  # Получаем ID пользователя Telegram
    username = update.effective_user.username  # Получаем username пользователя
    first_name = update.effective_user.first_name  # Получаем имя пользователя

    # Проверяем, зарегистрирован ли пользователь
    if not database.is_user_registered(user_id):
        # Если нет — регистрируем с начальными параметрами
        database.register_user(user_id, username, first_name)
        await update.message.reply_text(
            f"Добро пожаловать, {first_name}! Вы успешно зарегистрированы в игре «Зверобой».\n"
            "Используйте /profile для просмотра профиля и выбора персонажа."
        )
    else:
        await update.message.reply_text("Вы уже зарегистрированы!")

# Функция обработки команды /profile — просмотр профиля игрока
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = database.get_user_data(user_id)  # Получаем данные пользователя из БД

    if user_data:
        # Формируем сообщение с данными профиля
        message = (
            f"👤 Профиль {user_data['first_name']}\n"
            f"Уровень: {user_data['level']}\n"
            f"Опыт: {user_data['experience']}/{user_data['required_exp']}\n"
            f"Здоровье: {user_data['health']}/{user_data['max_health']}\n"
            f"Золото: {user_data['gold']}\n"
        )
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("Сначала зарегистрируйтесь с помощью /start")


async def give_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, "admin"):
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return

    try:
        # Аргументы: /give <user_id> <item_id> <quantity>
        user_id = int(context.args[0])
        item_id = int(context.args[1])
        quantity = int(context.args[2])

        result = give_item(user_id, item_id, quantity)
        await update.message.reply_text(result)
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /give <user_id> <item_id> <количество>")

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, "admin"):
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return

    try:
        user_id = int(context.args[0])
        result = ban_user(user_id)
        await update.message.reply_text(result)
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /ban <user_id>")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, "admin"):
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return

    try:
        user_id = int(context.args[0])
        result = unban_user(user_id)
        await update.message.reply_text(result)
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /unban <user_id>")

async def make_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, "owner"):
        await update.message.reply_text("❌ Только владелец может назначать администраторов.")
        return

    try:
        user_id = int(context.args[0])
        result = make_admin(user_id)
        await update.message.reply_text(result)
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /make_admin <user_id>")

async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, "owner"):
        await update.message.reply_text("❌ Только владелец может разжаловать администраторов.")
        return

    try:
        user_id = int(context.args[0])
        result = remove_admin(user_id)
        await update.message.reply_text(result)
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /remove_admin <user_id>")

async def take_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, "admin"):
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return

    try:
        user_id = int(context.args[0])
        item_id = int(context.args[1])
        quantity = int(context.args[2])
        result = take_item(user_id, item_id, quantity)
        await update.message.reply_text(result)
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /take <user_id> <item_id> <количество>")

async def level_up_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, "admin"):
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return

    try:
        user_id = int(context.args[0])
        levels = int(context.args[1])
        result = level_up(user_id, levels)
        await update.message.reply_text(result)
    except (IndexError, ValueError):
        await update.message.reply_text("Использование: /level_up <user_id> <количество_уровней>")

async def banned_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id, "admin"):
        await update.message.reply_text("❌ У вас нет прав для этой команды.")
        return

    result = banned_list()
    await update.message.reply_text(result)

# Основная функция запуска бота
def main():
    # Создаём приложение с токеном бота
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("give", give_command))
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("unban", unban_command))
    application.add_handler(CommandHandler("make_admin", make_admin_command))
    application.add_handler(CommandHandler("remove_admin", remove_admin_command))
    application.add_handler(CommandHandler("take", take_command))
    application.add_handler(CommandHandler("level_up", level_up_command))
    application.add_handler(CommandHandler("banned_list", banned_list_command))

    # Запускаем бота
    application.run_polling()

# Запуск программы
if __name__ == "__main__":
    main()




