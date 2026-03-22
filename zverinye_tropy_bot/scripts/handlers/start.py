from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import Session, User
from utils.keyboards import get_main_menu, get_character_keyboard, get_resource_keyboard

# Константы для ConversationHandler
NICKNAME, CHARACTER, FAVORITE_RESOURCE = range(3)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = Session()

    # Проверяем, зарегистрирован ли пользователь
    user = session.query(User).filter_by(telegram_id=user_id).first()
    if user:
        await update.message.reply_text(
            f"Добро пожаловать обратно, {user.nickname}!\n"
            "Используйте главное меню для взаимодействия с игрой.",
            reply_markup=get_main_menu()
        )
        session.close()
        return ConversationHandler.END

    await update.message.reply_text(
        "🦊 Добро пожаловать в «Звериные тропы»!\n\n"
        "Для начала введите ваш никнейм (до 16 символов):"
    )
    session.close()
    return NICKNAME

async def receive_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nickname = update.message.text.strip()

    if not nickname:
        await update.message.reply_text("Никнейм не может быть пустым. Введите никнейм:")
        return NICKNAME

    if len(nickname) > 16:
        await update.message.reply_text("Никнейм слишком длинный! Максимум 16 символов. Введите новый:")
        return NICKNAME

    context.user_data['nickname'] = nickname

    await update.message.reply_text(
        f"Отлично, {nickname}! Теперь выберите вашего персонажа:",
        reply_markup=get_character_keyboard()
    )
    return CHARACTER

async def select_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    character = update.message.text
    context.user_data['character'] = character

    await update.message.reply_text(
        "Теперь укажите ваш любимый тип ресурса (это повлияет на шанс его нахождения в экспедициях):",
        reply_markup=get_resource_keyboard()
    )
    return FAVORITE_RESOURCE

async def select_favorite_resource(update: Update, context: ContextTypes.DEFAULT_TYPE):
    favorite_resource = update.message.text
    user_id = update.effective_user.id
    nickname = context.user_data.get('nickname')
    character = context.user_data.get('character')

    # Базовые характеристики персонажей
    character_stats = {
        "🐺 Волк": {"hp": 120, "energy_per_action": 4, "satiety_per_action": 3, "damage": 20},
        "🦊 Лиса": {"hp": 80, "energy_per_action": 5, "satiety_per_action": 2, "damage": 15},
        "🐻 Медведь": {"hp": 180, "energy_per_action": 3, "satiety_per_action": 4, "damage": 25},
        "🐿️ Белка": {"hp": 60, "energy_per_action": 6, "satiety_per_action": 1, "damage": 10},
        "🦝 Барсук": {"hp": 100, "energy_per_action": 4, "satiety_per_action": 2, "damage": 18},
        "🦉 Сова": {"hp": 70, "energy_per_action": 5, "satiety_per_action": 1, "damage": 12},
        "🦦 Выдра": {"hp": 90, "energy_per_action": 5, "satiety_per_action": 2, "damage": 16}
    }

    stats = character_stats.get(character, {"hp": 100, "energy_per_action": 4, "satiety_per_action": 2, "damage": 15})

    session = Session()
    new_user = User(
        telegram_id=user_id,
        username=update.effective_user.username,
        nickname=nickname,
        character=character,
        hp=stats["hp"],
        max_hp=stats["hp"],
        energy=stats["energy_per_action"] * 2,
        max_energy=stats["energy_per_action"] * 2,
        satiety=10,
        max_satiety=10,
        damage=stats["damage"],
        inventory={},
        favorite_resource=favorite_resource
    )
    session.add(new_user)
    session.commit()
    session.close()

    await update.message.reply_text(
        f"Поздравляем, {nickname}! Вы выбрали персонажа: {character}.\n"
        f"Ваш любимый ресурс: {favorite_resource}.\n\n"
        "Используйте /профиль для просмотра характеристик.\n"
        "Удачи в приключениях!",
        reply_markup=get_main_menu()
    )
    # Очищаем временные данные
    context.user_data.clear()
    return ConversationHandler.END

def get_start_conversation():
    from telegram.ext import MessageHandler, filters
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Command("start"), start_command)],
        states={
            NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_nickname)],
            CHARACTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_character)],
            FAVORITE_RESOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_favorite_resource)]
        },
        fallbacks=[]
    )
