from telegram import Update
from telegram.ext import ContextTypes
from utils.keyboards import get_main_menu

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = (
        "📖 **Правила игры «Звериные тропы»**\n\n"
        "1. **Уважение к другим игрокам**\n"
        "   Запрещены оскорбления, спам, мошенничество.\n\n"
        "2. **Торговля**\n"
        "   Обманы в обмене запрещены. Администрация не вмешивается в добровольные сделки.\n\n"
        "3. **Бои**\n"
        "   Используйте только разрешённые механики. Запрещены баги и эксплойты.\n\n"
        "4. **Аккаунт**\n"
        "   Запрещена передача аккаунта третьим лицам.\n\n"
        "5. **Премиум**\n"
        "   Покупка кристаллов через сторонние источники запрещена.\n\n"
        "⚠️ Нарушение правил может привести к блокировке аккаунта.\n\n"
        "При возникновении вопросов обращайтесь к администрации."
    )
    await update.message.reply_text(rules_text, parse_mode='Markdown', reply_markup=get_main_menu())

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /report ID_нарушителя причина\n"
            "Пример: /report 123456789 Оскорбления в чате"
        )
        return

    try:
        offender_id = int(context.args[0])
        reason = ' '.join(context.args[1:])
    except ValueError:
        await update.message.reply_text("Неверный формат ID пользователя!")
        return

    reporter_id = update.effective_user.id
    reporter_name = update.effective_user.first_name

    # Отправляем отчёт администраторам
    admin_report_text = (
        f"🚨 **Новый отчёт о нарушении**\n\n"
        f"👤 Нарушитель: {offender_id}\n"
        f"📝 Причина: {reason}\n"
        f"👥 Отчёт отправил: {reporter_id} ({reporter_name})\n"
        f"⏰ Время: {datetime.utcnow().strftime('%H:%M %d.%m.%Y')}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(admin_id, admin_report_text, parse_mode='Markdown')
        except Exception as e:
            print(f"Не удалось отправить отчёт администратору {admin_id}: {e}")

    await update.message.reply_text(
        "✅ Ваш отчёт отправлен администраторам. Спасибо за помощь в поддержании порядка!",
        reply_markup=get_main_menu()
    )
