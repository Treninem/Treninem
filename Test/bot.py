import logging
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота (не публикуйте его в открытом доступе!)
BOT_TOKEN = "8501813124:AAG1VVyqD7EviyYEVtntNJN_aOgG2eo8_HU"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Привет, {user.mention_html()}! Бот работает. Связь проверена."
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Расширенная проверка связи и пинга."""
    start_time = asyncio.get_event_loop().time()

    try:
        # Отправляем временное сообщение для измерения задержки
        temp_msg = await update.message.reply_text("🔄 Измеряем задержку...")
        end_time = asyncio.get_event_loop().time()

        # Рассчитываем пинг в миллисекундах
        ping_time = int((end_time - start_time) * 1000)

        # Редактируем сообщение с результатом
        await temp_msg.edit_text(
            f"🏓 Pong! Задержка: {ping_time} мс\n"
            f"✅ Связь стабильная"
        )
    except Exception as e:
        logger.error(f"Ошибка при проверке пинга: {e}")
        await update.message.reply_text("❌ Ошибка при измерении задержки.")

async def check_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Комплексная проверка токена Telegram."""
    results = []

    # 1. Базовая проверка — есть ли токен и корректная ли у него длина
    if not BOT_TOKEN:
        results.append("❌ Токен не установлен")
    elif len(BOT_TOKEN) < 45:
        results.append("❌ Токен слишком короткий (подозрительно)")
    else:
        results.append("✅ Токен установлен и имеет корректную длину")

    # 2. Проверка формата токена (должен содержать цифру:букву)
    if BOT_TOKEN and ':' not in BOT_TOKEN:
        results.append("❌ Токен имеет неверный формат (отсутствует разделитель :)")
    elif BOT_TOKEN:
        parts = BOT_TOKEN.split(':')
        if len(parts) == 2 and parts[0].isdigit():
            results.append("✅ Формат токена корректен")
        else:
            results.append("❌ Некорректный формат токена")

    # 3. Проверка через API Telegram
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe") as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('ok'):
                        bot_info = data['result']
                        results.append(
                            f"✅ Токен валиден. Бот: @{bot_info.get('username', 'N/A')} "
                            f"({bot_info.get('first_name', 'N/A')})"
                        )
                    else:
                        results.append("❌ API Telegram вернул ошибку для токена")
                else:
                    results.append(f"❌ Ошибка API: HTTP {response.status}")
        except Exception as e:
            results.append(f"❌ Ошибка подключения к API Telegram: {e}")

    # Формируем итоговый отчёт
    report = "🔎 Результаты проверки токена:\n" + "\n".join(results)
    await update.message.reply_text(report)

async def check_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверка общей связи с Telegram API."""
    try:
        # Пробуем получить информацию о боте через API
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1&limit=1"
            ) as response:
                if response.status == 200:
                    await update.message.reply_text(
                "✅ Связь с Telegram API установлена успешно\n"
                "🌐 Сервер отвечает корректно"
            )
                else:
                    await update.message.reply_text(
                        f"❌ Проблемы с соединением. HTTP статус: {response.status}"
                    )
    except Exception as e:
        logger.error(f"Ошибка соединения: {e}")
        await update.message.reply_text(
            "❌ Нет связи с Telegram API\n"
            "Проверьте интернет‑соединение или статус Telegram"
        )

def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("check_token", check_token))
    application.add_handler(CommandHandler("check_connection", check_connection))

    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()
