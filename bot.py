from __future__ import annotations

import asyncio
import html
import logging
import mimetypes
import re
import signal
import uuid
from math import ceil
from pathlib import Path
from typing import Any

from telegram import (
    Bot,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    LabeledPrice,
    Message,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ChatAction, ParseMode
from telegram.error import BadRequest, Forbidden, InvalidToken, TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from app.config import get_commission_plan, load_settings
from app.db import BotInstance, Database
from app.keyboards import (
    BOTS_PER_PAGE,
    FLAGS_PER_PAGE,
    USERS_PER_PAGE,
    admin_bot_actions_keyboard,
    admin_menu_keyboard,
    admin_user_actions_keyboard,
    create_bot_keyboard,
    main_menu_keyboard,
    owner_help_keyboard,
    preset_keyboard,
    premium_keyboard,
    quick_after_photo_keyboard,
    result_keyboard,
    root_buy_keyboard,
    suspicious_flag_actions_keyboard,
    text_types_keyboard,
)
from app.previews import preview_page_caption, preview_page_count, preview_page_path
from app.presets import PRESET_BY_KEY
from app.prompts import custom_edit_prompt, preset_edit_prompt
from app.services.openai_service import OpenAIService

logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger('mask-platform')

settings = load_settings()
db = Database(settings.db_path, settings.free_trial_credits, settings.child_owner_daily_free)
openai_service = OpenAIService(settings)
commission_plan = get_commission_plan(settings)

PRODUCTS: dict[str, dict[str, Any]] = {
    'pack_small': {
        'title': 'Старт-пак',
        'description': f'{settings.small_pack_credits} запросов для масок, подбора стиля и текстов.',
        'price': settings.small_pack_price,
        'credits': settings.small_pack_credits,
    },
    'pack_big': {
        'title': 'Большой пак',
        'description': f'{settings.big_pack_credits} запросов по более выгодной цене.',
        'price': settings.big_pack_price,
        'credits': settings.big_pack_credits,
    },
    'pro_30': {
        'title': 'PRO 30 дней',
        'description': 'Безлимитные запросы на 30 дней, приоритетное использование и доступ ко всем режимам.',
        'price': settings.pro_30_price,
        'premium_days': settings.pro_30_days,
    },
}

SUSPICIOUS_KEYWORDS = (
    'carding', 'scam', 'spam', 'phishing', 'fraud', 'adult', 'nude', 'nsfw', 'drugs',
    'кардинг', 'скам', 'спам', 'фишинг', 'мошенн', 'наркот', 'обнажен', '18+',
)


class PlatformRuntime:
    def __init__(self) -> None:
        self.apps: dict[int, Application] = {}
        self.root_bot_id: int | None = None
        self.root_username: str = ''
        self._stop_event = asyncio.Event()

    async def validate_child_token(self, token: str) -> tuple[int, str | None, str]:
        bot = Bot(token=token)
        try:
            me = await bot.get_me()
        except InvalidToken as exc:
            raise ValueError('Токен не прошёл проверку. Проверь, что ты вставил токен именно от BotFather.') from exc
        except TelegramError as exc:
            raise ValueError(f'Не удалось проверить токен: {exc}') from exc
        title = me.full_name or me.first_name or (me.username or f'Bot {me.id}')
        return me.id, me.username, title

    async def ensure_root(self) -> BotInstance:
        root_bot = Bot(token=settings.telegram_bot_token)
        me = await root_bot.get_me()
        bot_id = db.ensure_root_bot(
            token=settings.telegram_bot_token,
            telegram_bot_id=me.id,
            username=me.username,
            title=me.full_name or me.first_name or (me.username or f'Bot {me.id}'),
        )
        self.root_bot_id = bot_id
        self.root_username = me.username or ''
        instance = db.get_bot(bot_id)
        if not instance:
            raise RuntimeError('Не удалось инициализировать root bot instance.')
        return instance

    async def start_bot_instance(self, instance: BotInstance) -> None:
        if instance.id in self.apps:
            return
        app = build_application(instance, self)
        self.apps[instance.id] = app
        await app.initialize()
        await app.start()
        if app.updater is None:
            raise RuntimeError('Updater is not available for polling mode.')
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await set_commands_for_application(app, instance.kind == 'root')
        logger.info('Started bot instance %s (@%s)', instance.id, instance.username)

    async def stop_bot_instance(self, bot_id: int) -> None:
        app = self.apps.pop(bot_id, None)
        if not app:
            return
        try:
            if app.updater is not None:
                await app.updater.stop()
            await app.stop()
            await app.shutdown()
        finally:
            logger.info('Stopped bot instance %s', bot_id)

    async def start_all(self) -> None:
        db.init()
        root_instance = await self.ensure_root()
        active_bots = db.list_active_bots()
        ordered = sorted(active_bots, key=lambda x: 0 if x.kind == 'root' else 1)
        if root_instance.id not in {item.id for item in ordered}:
            ordered.insert(0, root_instance)
        for instance in ordered:
            await self.start_bot_instance(instance)

    async def stop_all(self) -> None:
        for bot_id in list(self.apps.keys())[::-1]:
            await self.stop_bot_instance(bot_id)

    async def register_child_bot(
        self,
        token: str,
        owner_user_id: int,
        parent_bot_id: int | None,
        desired_title: str | None,
    ) -> BotInstance:
        telegram_bot_id, username, inferred_title = await self.validate_child_token(token)
        title = (desired_title or inferred_title).strip()[:80]
        bot_id = db.create_child_bot(
            token=token,
            telegram_bot_id=telegram_bot_id,
            username=username,
            title=title,
            owner_user_id=owner_user_id,
            parent_bot_id=parent_bot_id,
        )
        instance = db.get_bot(bot_id)
        if not instance:
            raise RuntimeError('Не удалось создать запись дочернего бота.')
        await self.start_bot_instance(instance)
        return instance

    async def send_root_message(self, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
        if self.root_bot_id is None:
            return
        app = self.apps.get(self.root_bot_id)
        if not app:
            return
        await app.bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML, reply_markup=reply_markup, disable_web_page_preview=True)


runtime = PlatformRuntime()


def split_text(text: str, chunk_size: int = 3500) -> list[str]:
    text = text.strip()
    if len(text) <= chunk_size:
        return [text]
    chunks: list[str] = []
    current = ''
    for line in text.splitlines(True):
        if len(current) + len(line) > chunk_size:
            if current:
                chunks.append(current)
                current = ''
            while len(line) > chunk_size:
                chunks.append(line[:chunk_size])
                line = line[chunk_size:]
        current += line
    if current:
        chunks.append(current)
    return chunks


def is_admin_user(user_id: int | None) -> bool:
    return bool(user_id and user_id in settings.admin_user_ids)


def mention_html(user_id: int, first_name: str | None, username: str | None = None) -> str:
    if username:
        label = '@' + username
    else:
        label = first_name or f'User {user_id}'
    return f'<a href="tg://user?id={user_id}">{html.escape(label)}</a>'


def get_current_bot_id(context: ContextTypes.DEFAULT_TYPE) -> int:
    return int(context.application.bot_data['bot_id'])


def get_current_bot_kind(context: ContextTypes.DEFAULT_TYPE) -> str:
    return str(context.application.bot_data['bot_kind'])


def get_current_bot(context: ContextTypes.DEFAULT_TYPE) -> BotInstance:
    bot_id = get_current_bot_id(context)
    instance = db.get_bot(bot_id)
    if not instance:
        raise RuntimeError(f'Unknown bot instance {bot_id}')
    return instance


def reply_menu(context: ContextTypes.DEFAULT_TYPE, user_id: int | None) -> ReplyKeyboardMarkup:
    return main_menu_keyboard(is_root=get_current_bot_kind(context) == 'root', is_admin=is_admin_user(user_id) and get_current_bot_kind(context) == 'root')


def current_root_username() -> str:
    return runtime.root_username


def access_mode_label(user_id: int, balance) -> str:
    if is_admin_user(user_id):
        return 'корневой владелец / безлимит'
    if balance and getattr(balance, 'is_platform_vip', 0):
        return 'VIP платформы / безлимит'
    if balance and balance.premium_active:
        return 'PRO / безлимит'
    if balance and getattr(balance, 'is_bot_owner', 0):
        return 'владелец дочернего бота'
    return 'обычный режим'


async def set_commands_for_application(app: Application, is_root: bool) -> None:
    commands = [
        BotCommand('start', 'Запуск и меню'),
        BotCommand('menu', 'Открыть меню'),
        BotCommand('buy', 'Купить запросы'),
        BotCommand('profile', 'Профиль и баланс'),
        BotCommand('help', 'Помощь'),
    ]
    if is_root:
        commands.append(BotCommand('admin', 'Админ-сеть'))
    await app.bot.set_my_commands(commands)


async def ensure_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    db.upsert_user(
        user_id=update.effective_user.id,
        username=update.effective_user.username,
        first_name=update.effective_user.first_name,
    )
    db.touch_user(update.effective_user.id)
    db.ensure_bot_user_state(get_current_bot_id(context), update.effective_user.id)
    db.touch_bot_user(get_current_bot_id(context), update.effective_user.id)


async def blocked_if_banned(update: Update) -> bool:
    user = update.effective_user
    if not user:
        return False
    if is_admin_user(user.id):
        return False
    if not db.is_banned_global(user.id):
        return False

    text = 'Твой доступ ко всей сети ботов ограничен администратором.'
    try:
        if update.callback_query:
            await update.callback_query.answer('Доступ ограничен', show_alert=True)
            if update.callback_query.message:
                await update.callback_query.message.reply_text(text)
        elif update.effective_message:
            await update.effective_message.reply_text(text)
    except Exception:
        logger.exception('Failed to notify banned user %s', user.id)
    return True


async def send_create_bot_intro(message: Message, parent_bot_id: int | None = None) -> None:
    text = (
        '🚀 <b>Подключение своего бота</b>\n\n'
        'Как это работает:\n'
        '1) Создаёшь бота у <b>@BotFather</b>.\n'
        '2) Отправляешь токен в этот мастер подключения.\n'
        '3) Платформа автоматически запускает копию движка на твоём токене.\n\n'
        'В твоём боте:\n'
        '• остаются все AI-функции платформы;\n'
        f'• тебе доступно <b>{settings.child_owner_daily_free} бесплатных запросов в день</b> как владельцу;\n'
        '• покупка премиума проходит безопасно через корневого бота платформы;\n'
        '• внутренняя многоуровневая комиссия считается автоматически в базе.\n\n'
        'Нажми кнопку ниже, чтобы начать мастер подключения.'
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=create_bot_keyboard(parent_bot_id))


async def explain_how_it_works(message: Message, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_instance = get_current_bot(context)
    is_root = bot_instance.kind == 'root'
    text = (
        '📘 <b>Как работает бот</b>\n\n'
        '• Отправь фото и выбери одну из 30 масок или опиши свою.\n'
        '• Можно сгенерировать стих, песню, поздравление, подпись и другие тексты.\n'
        '• Просмотр примеров масок бесплатный.\n'
        f'• Первые <b>{settings.free_trial_credits}</b> запросов на каждом боте бесплатные.\n'
        '• После этого можно купить запросы или PRO.\n\n'
    )
    if is_root:
        text += (
            'Этот бот также умеет подключать дочерние боты на токенах владельцев.\n'
            'Для старта открой «Подключить своего бота».\n'
        )
    else:
        text += (
            'Этот бот подключён к платформе.\n'
            'Если хочешь такой же бот для себя, нажми «Создать такого же бота».\n'
        )
    await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_menu(context, message.from_user.id if message.from_user else None))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update, context)
    if await blocked_if_banned(update):
        return
    message = update.effective_message
    if not message:
        return
    bot_instance = get_current_bot(context)
    arg = context.args[0] if context.args else ''

    if arg.startswith('ref_') and bot_instance.kind == 'root':
        parent_bot_id = int(arg.split('_', 1)[1]) if arg.split('_', 1)[1].isdigit() else None
        await send_create_bot_intro(message, parent_bot_id)
        return

    if arg.startswith('pay_') and bot_instance.kind == 'root':
        parts = arg.split('_')
        if len(parts) >= 3 and parts[1].isdigit():
            seller_bot_id = int(parts[1])
            product_key = '_'.join(parts[2:])
            await show_premium(message, context, seller_bot_id=seller_bot_id, preselect=product_key if product_key in PRODUCTS else None)
            return

    if bot_instance.kind == 'root':
        text = (
            '✨ <b>Добро пожаловать в AI Mask Platform</b>\n\n'
            'Что умеет корневой бот:\n'
            '• 30 трендовых масок и стилизаций для фото;\n'
            '• маска по твоему тексту;\n'
            '• подбор лучших пресетов под конкретное фото;\n'
            '• стихи, песни, поэмы, поздравления, тосты, подписи и статусы;\n'
            '• безопасная оплата пакетов и PRO через Telegram Stars;\n'
            '• мастер подключения дочерних ботов.\n\n'
            f'🎁 На старте у тебя есть <b>{settings.free_trial_credits} бесплатных запросов</b> на этом боте.\n'
            'Отправь фото или выбери действие в меню ниже.'
        )
    else:
        invite_hint = f'https://t.me/{current_root_username()}?start=ref_{bot_instance.id}' if current_root_username() else ''
        extra = f'\n\n🚀 Для запуска такого же бота: {invite_hint}' if invite_hint else ''
        text = (
            f'✨ <b>{html.escape(bot_instance.title)}</b>\n\n'
            'Это дочерний AI-бот платформы. Здесь ты можешь:\n'
            '• накладывать стильные маски на фото;\n'
            '• придумывать свою маску по тексту;\n'
            '• создавать стихи, песни, поздравления и подписи;\n'
            '• покупать запросы и PRO через защищённую платформу.\n\n'
            f'🎁 На этом боте у тебя есть <b>{settings.free_trial_credits} бесплатных запросов</b>.{extra}'
        )
    await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_menu(context, update.effective_user.id))


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update, context)
    if await blocked_if_banned(update):
        return
    await update.effective_message.reply_text('Меню открыто. Выбирай нужный режим ниже ⬇️', reply_markup=reply_menu(context, update.effective_user.id))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update, context)
    if await blocked_if_banned(update):
        return
    await explain_how_it_works(update.effective_message, context)


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update, context)
    if await blocked_if_banned(update):
        return
    user_id = update.effective_user.id
    bot_id = get_current_bot_id(context)
    balance = db.get_user_balance(bot_id, user_id)
    if not balance:
        await update.effective_message.reply_text('Не удалось загрузить профиль.', reply_markup=reply_menu(context, user_id))
        return

    premium_until = balance.premium_until or 'не активен'
    status = 'заблокирован' if balance.is_banned_global else 'активен'
    available_now = '∞' if is_admin_user(user_id) or balance.total_renders_left == '∞' else balance.total_renders_left
    mode = access_mode_label(user_id, balance)
    owner_note = ''
    if balance.is_bot_owner:
        owner_note = f'\n• Ежедневный лимит владельца: <b>{balance.owner_daily_left}/{balance.owner_daily_limit}</b>'
    text = (
        '👤 <b>Твой профиль</b>\n\n'
        f'• Бесплатных запросов на этом боте: <b>{balance.free_trial_left}</b>\n'
        f'• Платных запросов на этом боте: <b>{balance.paid_credits}</b>\n'
        f'• Бонусов по сети: <b>{balance.global_bonus_credits}</b>\n'
        f'• PRO на этом боте до: <b>{html.escape(str(premium_until))}</b>{owner_note}\n'
        f'• Доступно сейчас: <b>{available_now}</b>\n'
        f'• Режим доступа: <b>{mode}</b>\n'
        f'• Статус: <b>{status}</b>'
    )
    if is_admin_user(user_id):
        text += '\n\n✨ <i>Твои запросы нигде не списываются.</i>'
    await update.effective_message.reply_text(text, reply_markup=reply_menu(context, user_id), parse_mode=ParseMode.HTML)


async def show_premium(
    message: Message,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    seller_bot_id: int | None = None,
    preselect: str | None = None,
) -> None:
    current_bot = get_current_bot(context)
    seller_bot_id = seller_bot_id or current_bot.id
    seller_bot = db.get_bot(seller_bot_id)
    seller_name = seller_bot.title if seller_bot else 'этот бот'
    text = (
        '⭐ <b>Платные пакеты</b>\n\n'
        f'• Старт-пак — <b>{settings.small_pack_credits}</b> запросов за <b>{settings.small_pack_price}⭐</b>\n'
        f'• Большой пак — <b>{settings.big_pack_credits}</b> запросов за <b>{settings.big_pack_price}⭐</b>\n'
        f'• PRO 30 дней — безлимит за <b>{settings.pro_30_price}⭐</b>\n\n'
        f'Покупка будет привязана к боту: <b>{html.escape(seller_name)}</b>.\n'
        'Запросами считаются генерация масок, тексты и подбор стиля. Просмотр примеров масок бесплатный.'
    )
    if current_bot.kind == 'root':
        await message.reply_text(text, reply_markup=root_buy_keyboard(seller_bot_id), parse_mode=ParseMode.HTML)
        if preselect in PRODUCTS:
            await send_product_invoice(message, message.from_user.id, seller_bot_id, preselect)
        return
    root_username = current_root_username()
    if not root_username:
        await message.reply_text('Платёжный центр платформы пока не готов. Попробуй позже.')
        return
    await message.reply_text(text, reply_markup=premium_keyboard(root_username, seller_bot_id), parse_mode=ParseMode.HTML)


async def premium_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update, context)
    if await blocked_if_banned(update):
        return
    await show_premium(update.effective_message, context)


async def send_product_invoice(message: Message, buyer_user_id: int, seller_bot_id: int, product_key: str) -> None:
    product = PRODUCTS[product_key]
    payload = f'{product_key}:{buyer_user_id}:{seller_bot_id}:{uuid.uuid4().hex[:12]}'
    await message.reply_invoice(
        title=product['title'],
        description=product['description'],
        payload=payload,
        provider_token='',
        currency='XTR',
        prices=[LabeledPrice(label=product['title'], amount=product['price'])],
    )


async def send_gallery_page(message: Message, page: int) -> None:
    page = max(0, min(page, preview_page_count() - 1))
    preview_path = preview_page_path(page)
    caption = preview_page_caption(page)
    if preview_path.exists():
        with preview_path.open('rb') as photo_file:
            await message.reply_photo(photo=photo_file, caption=caption, reply_markup=preset_keyboard(page))
    else:
        await message.reply_text(caption, reply_markup=preset_keyboard(page))


async def edit_gallery_page(query, page: int) -> None:
    page = max(0, min(page, preview_page_count() - 1))
    preview_path = preview_page_path(page)
    caption = preview_page_caption(page)
    if not query.message:
        return
    if preview_path.exists() and query.message.photo:
        with preview_path.open('rb') as photo_file:
            media = InputMediaPhoto(media=photo_file, caption=caption)
            await query.message.edit_media(media=media, reply_markup=preset_keyboard(page))
    elif preview_path.exists():
        with preview_path.open('rb') as photo_file:
            await query.message.reply_photo(photo=photo_file, caption=caption, reply_markup=preset_keyboard(page))
    else:
        try:
            await query.message.edit_text(caption, reply_markup=preset_keyboard(page))
        except BadRequest:
            await query.message.reply_text(caption, reply_markup=preset_keyboard(page))


async def notify_admins_about_flag(flag_id: int, bot_id: int, user_id: int, reason: str, details: str | None) -> None:
    if not settings.admin_user_ids:
        return
    detail = db.get_user_detail(user_id)
    bot_detail = db.get_bot_detail(bot_id)
    if not detail or not bot_detail:
        return

    text = (
        '🚨 <b>Подозрительный пользователь</b>\n\n'
        f'Бот: <b>{html.escape(bot_detail["title"])}</b>\n'
        f'Пользователь: {mention_html(user_id, detail["first_name"], detail["username"])}\n'
        f'ID: <code>{user_id}</code>\n'
        f'Причина: <b>{html.escape(reason)}</b>\n'
        f'Детали: {html.escape(details or "—")}\n'
        f'Запросов за 24ч: <b>{detail["jobs_24h"]}</b>\n'
        f'Всего запросов: <b>{detail["total_jobs"]}</b>'
    )
    for admin_id in settings.admin_user_ids:
        try:
            await runtime.send_root_message(
                admin_id,
                text,
                reply_markup=suspicious_flag_actions_keyboard(flag_id=flag_id, user_id=user_id, is_banned=bool(detail['is_banned_global']), back_page=0),
            )
        except Forbidden:
            logger.warning('Admin %s did not start the root bot yet.', admin_id)
        except Exception:
            logger.exception('Failed to notify admin %s', admin_id)


async def maybe_report_suspicious(bot_id: int, user_id: int, action_type: str, prompt_text: str | None = None) -> None:
    if is_admin_user(user_id):
        return
    balance = db.get_user_balance(bot_id, user_id)
    if balance and balance.is_platform_vip:
        return

    reasons: list[tuple[str, str]] = []
    recent_total = db.get_recent_event_count(
        bot_id,
        user_id,
        event_types=('image_preset', 'image_custom', 'text', 'suggest'),
        minutes=settings.suspicious_burst_window_minutes,
        status='done',
    )
    if recent_total >= settings.suspicious_burst_limit:
        reasons.append(('Слишком высокая активность', f'{recent_total} успешных AI-запросов за {settings.suspicious_burst_window_minutes} минут.'))

    if balance and not balance.username and recent_total >= 4:
        reasons.append(('Высокая активность без username', f'Пользователь без username сделал {recent_total} запросов за короткое время.'))

    if prompt_text:
        lowered = prompt_text.lower()
        for keyword in SUSPICIOUS_KEYWORDS:
            if keyword in lowered:
                reasons.append(('Подозрительный текст запроса', f'Тип: {action_type}. Ключевое слово: {keyword}. Запрос: {prompt_text[:300]}'))
                break

    for reason, details in reasons:
        flag_id = db.create_suspicious_flag(bot_id, user_id, reason, details)
        if flag_id:
            await notify_admins_about_flag(flag_id, bot_id, user_id, reason, details)


async def consume_quota_or_offer(message: Message, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> tuple[bool, str]:
    bot_id = get_current_bot_id(context)
    allowed, reason = db.consume_request(bot_id, user_id, is_admin=is_admin_user(user_id))
    if allowed:
        return True, reason
    if reason == 'banned':
        await message.reply_text('Твой доступ к сети ботов ограничен администратором.')
        return False, reason
    await show_premium(message, context)
    return False, reason


async def suggest_masks_for_last_photo(message: Message, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo_path = context.user_data.get('last_photo_path')
    if not photo_path or not Path(photo_path).exists():
        await message.reply_text('Сначала пришли фото, чтобы я подобрал маски именно под него.')
        return

    allowed, reason = await consume_quota_or_offer(message, context, user_id)
    bot_id = get_current_bot_id(context)
    if not allowed:
        db.save_job(bot_id, user_id, 'suggest', str(photo_path), None, None, 'Подбор стиля', 'denied', 'empty quota')
        return

    wait_message = await message.reply_text('Смотрю на фото и подбираю лучшие маски...')
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    try:
        keys = await asyncio.to_thread(openai_service.suggest_presets_for_photo, Path(photo_path))
    except Exception as exc:  # noqa: BLE001
        logger.exception('Mask suggestion failed: %s', exc)
        db.restore_request(bot_id, user_id, reason)
        db.save_job(bot_id, user_id, 'suggest', str(photo_path), None, None, 'Подбор стиля', 'failed', str(exc))
        await wait_message.edit_text('Не удалось подобрать маски. Списание автоматически отменено, попробуй ещё раз позже.')
        return

    buttons = []
    for key in keys:
        preset = PRESET_BY_KEY[key]
        buttons.append([InlineKeyboardButton(f'{preset.emoji} {preset.title}', callback_data=f'preset:{preset.key}')])
    reply_markup = InlineKeyboardMarkup(buttons + [[InlineKeyboardButton('✨ Открыть всю галерею', callback_data='menu:presets')]])
    lines = ['🪄 Под твоё фото я бы начал с этих вариантов:']
    for idx, key in enumerate(keys, start=1):
        preset = PRESET_BY_KEY[key]
        lines.append(f'{idx}. {preset.emoji} {preset.title} — {preset.short_note}')
    await wait_message.edit_text('\n'.join(lines), reply_markup=reply_markup)
    db.save_job(bot_id, user_id, 'suggest', str(photo_path), None, ','.join(keys), 'Подбор стиля', 'done')
    await maybe_report_suspicious(bot_id, user_id, 'suggest')


async def generate_creative_text(message: Message, user_id: int, context: ContextTypes.DEFAULT_TYPE, kind: str, brief: str) -> None:
    bot_id = get_current_bot_id(context)
    allowed, reason = await consume_quota_or_offer(message, context, user_id)
    if not allowed:
        db.save_job(bot_id, user_id, 'text', None, None, None, brief, 'denied', 'empty quota')
        return

    wait_message = await message.reply_text('Генерирую текст...')
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    try:
        result = await asyncio.to_thread(openai_service.generate_text, kind, brief)
    except Exception as exc:  # noqa: BLE001
        logger.exception('Text generation failed: %s', exc)
        db.restore_request(bot_id, user_id, reason)
        db.save_job(bot_id, user_id, 'text', None, None, None, brief, 'failed', str(exc))
        await wait_message.edit_text('Не удалось сгенерировать текст. Списание автоматически отменено, попробуй ещё раз.')
        return

    chunks = split_text(result)
    await wait_message.edit_text(chunks[0], reply_markup=result_keyboard('text'))
    for extra in chunks[1:]:
        await message.reply_text(extra)
    db.save_job(bot_id, user_id, 'text', None, None, None, brief, 'done')
    context.user_data['last_edit'] = {'type': 'text', 'kind': kind, 'brief': brief}
    await maybe_report_suspicious(bot_id, user_id, 'text', brief)


async def render_with_preset(message: Message, user_id: int, context: ContextTypes.DEFAULT_TYPE, preset_key: str, stronger: bool) -> None:
    photo_path = context.user_data.get('last_photo_path')
    if not photo_path or not Path(photo_path).exists():
        await message.reply_text('Сначала пришли фото.')
        return
    preset = PRESET_BY_KEY[preset_key]
    prompt = preset_edit_prompt(preset, stronger=stronger)
    await execute_image_render(
        message=message,
        user_id=user_id,
        context=context,
        prompt=prompt,
        source_path=Path(photo_path),
        job_type='image_preset',
        preset_key=preset_key,
        stronger=stronger,
        original_user_prompt=preset.title,
    )


async def render_custom_mask(message: Message, user_id: int, context: ContextTypes.DEFAULT_TYPE, user_prompt: str, stronger: bool) -> None:
    photo_path = context.user_data.get('last_photo_path')
    if not photo_path or not Path(photo_path).exists():
        await message.reply_text('Сначала пришли фото.')
        return
    prompt = custom_edit_prompt(user_prompt, stronger=stronger)
    await execute_image_render(
        message=message,
        user_id=user_id,
        context=context,
        prompt=prompt,
        source_path=Path(photo_path),
        job_type='image_custom',
        preset_key='custom',
        stronger=stronger,
        original_user_prompt=user_prompt,
    )


async def execute_image_render(
    message: Message,
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    prompt: str,
    source_path: Path,
    job_type: str,
    preset_key: str,
    stronger: bool,
    original_user_prompt: str | None,
) -> None:
    bot_id = get_current_bot_id(context)
    allowed, reason = await consume_quota_or_offer(message, context, user_id)
    if not allowed:
        db.save_job(bot_id, user_id, job_type, str(source_path), None, preset_key, original_user_prompt, 'denied', 'empty quota')
        return

    wait_message = await message.reply_text('Генерирую маску, это может занять немного времени...')
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.UPLOAD_PHOTO)
    try:
        result_bytes = await asyncio.to_thread(openai_service.edit_image, source_path, prompt)
    except Exception as exc:  # noqa: BLE001
        logger.exception('Image render failed: %s', exc)
        db.restore_request(bot_id, user_id, reason)
        db.save_job(bot_id, user_id, job_type, str(source_path), None, preset_key, original_user_prompt, 'failed', str(exc))
        await wait_message.edit_text('Не удалось сгенерировать изображение. Списание автоматически отменено, попробуй ещё раз.')
        return

    output_path = settings.result_dir / f'{bot_id}_{user_id}_{uuid.uuid4().hex}.png'
    output_path.write_bytes(result_bytes)
    db.save_job(bot_id, user_id, job_type, str(source_path), str(output_path), preset_key, original_user_prompt, 'done')

    balance = db.get_user_balance(bot_id, user_id)
    remaining = balance.total_renders_left if balance else '—'
    caption = f'Готово. Маска: {preset_key}.\nОстаток запросов: {remaining}\nТип списания: {reason}'
    await wait_message.delete()
    with output_path.open('rb') as photo_file:
        await message.reply_photo(photo=photo_file, caption=caption, reply_markup=result_keyboard('image'))

    context.user_data['last_edit'] = {
        'type': 'image',
        'preset_key': preset_key,
        'stronger': stronger,
        'custom_prompt': original_user_prompt,
    }
    await maybe_report_suspicious(bot_id, user_id, job_type, original_user_prompt)


async def rerun_last_action_stronger(message: Message, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    last_edit = context.user_data.get('last_edit')
    if not last_edit:
        await message.reply_text('Пока нечего усиливать. Сначала сделай маску или текст.')
        return

    if last_edit['type'] == 'image':
        preset_key = last_edit.get('preset_key')
        if preset_key == 'custom':
            custom_prompt = last_edit.get('custom_prompt')
            if not custom_prompt:
                await message.reply_text('Не удалось восстановить прошлый custom prompt.')
                return
            await render_custom_mask(message, user_id, context, custom_prompt, stronger=True)
            return
        await render_with_preset(message, user_id, context, preset_key, stronger=True)
        return

    if last_edit['type'] == 'text':
        brief = last_edit.get('brief', '')
        kind = last_edit.get('kind', 'custom')
        intensified = brief + '\n\nСделай вариант смелее, ярче и эмоциональнее.'
        await generate_creative_text(message, user_id, context, kind, intensified)
        return


async def save_incoming_image(message: Message) -> Path:
    if message.photo:
        telegram_file = await message.photo[-1].get_file()
        suffix = '.jpg'
    elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):
        telegram_file = await message.document.get_file()
        suffix = mimetypes.guess_extension(message.document.mime_type) or '.jpg'
    else:
        raise RuntimeError('Сообщение не содержит изображения.')

    file_path = settings.temp_dir / f'{message.from_user.id}_{uuid.uuid4().hex}{suffix}'
    await telegram_file.download_to_drive(custom_path=str(file_path))
    return file_path


def maybe_remove_file(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        logger.warning('Could not remove file: %s', path)


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update, context)
    if await blocked_if_banned(update):
        return
    message = update.effective_message
    if not message:
        return
    path = await save_incoming_image(message)
    old_path = context.user_data.get('last_photo_path')
    if old_path and old_path != str(path):
        maybe_remove_file(Path(old_path))
    context.user_data['last_photo_path'] = str(path)
    context.user_data['last_edit'] = None
    text = (
        '📸 Фото сохранено.\n\n'
        'Теперь можно:\n'
        '• открыть галерею из 30 масок;\n'
        '• придумать свою маску по описанию;\n'
        '• попросить меня подобрать лучшие стили именно под этот снимок.'
    )
    await message.reply_text(text, reply_markup=quick_after_photo_keyboard())


def _root_owner_id() -> int | None:
    return settings.root_owner_user_id


def _payout_amount(total_amount: int, permille: int) -> int:
    return max(0, int(total_amount) * int(permille) // 1000)


def _format_bot_link(bot_row: Any) -> str:
    if bot_row and bot_row.get('bot_username'):
        return '@' + str(bot_row['bot_username'])
    if bot_row and bot_row.get('username'):
        return '@' + str(bot_row['username'])
    return '—'


async def distribute_commissions(payment_id: int, seller_bot_id: int, amount: int) -> None:
    chain = db.get_bot_owner_chain(seller_bot_id, max_depth=3)
    awarded_users: set[int] = set()
    direct_notes = ['прямая продажа', 'родительская линия', 'уровень 3']
    permilles = [commission_plan.direct_permille, commission_plan.parent_permille, commission_plan.grandparent_permille]
    for idx, row in enumerate(chain):
        owner_user_id = row['owner_user_id']
        if owner_user_id is None:
            continue
        owner_id = int(owner_user_id)
        permille = permilles[idx]
        if permille <= 0:
            continue
        db.record_commission(payment_id, owner_id, seller_bot_id, _payout_amount(amount, permille), idx + 1, direct_notes[idx])
        awarded_users.add(owner_id)
    root_owner_id = _root_owner_id()
    if root_owner_id and root_owner_id not in awarded_users:
        db.record_commission(payment_id, root_owner_id, seller_bot_id, _payout_amount(amount, commission_plan.platform_permille), 99, 'платформа')


async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if not query:
        return
    payload = query.invoice_payload or ''
    parts = payload.split(':')
    ok = len(parts) >= 4 and parts[0] in PRODUCTS and query.currency == 'XTR'
    if ok and parts[1].isdigit() and int(parts[1]) != query.from_user.id:
        ok = False
    await query.answer(ok=ok, error_message='Платёж не прошёл проверку, попробуй ещё раз.' if not ok else None)


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update, context)
    payment = update.effective_message.successful_payment
    if not payment:
        return
    payload = payment.invoice_payload
    parts = payload.split(':')
    if len(parts) < 4:
        await update.effective_message.reply_text('Платёж получен, но данные покупки не распознаны.')
        return

    product_key, buyer_user_id_raw, seller_bot_id_raw = parts[0], parts[1], parts[2]
    if not (buyer_user_id_raw.isdigit() and seller_bot_id_raw.isdigit() and product_key in PRODUCTS):
        await update.effective_message.reply_text('Платёж получен, но товар не распознан. Проверь лог.')
        return
    buyer_user_id = int(buyer_user_id_raw)
    seller_bot_id = int(seller_bot_id_raw)
    if update.effective_user.id != buyer_user_id:
        await update.effective_message.reply_text('Эта покупка предназначалась для другого пользователя.')
        return

    product = PRODUCTS[product_key]
    payment_id = db.save_payment(
        buyer_user_id=buyer_user_id,
        seller_bot_id=seller_bot_id,
        invoice_payload=payload,
        product_key=product_key,
        amount=payment.total_amount,
        currency=payment.currency,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        provider_payment_charge_id=payment.provider_payment_charge_id,
    )

    if 'credits' in product:
        db.add_bot_paid_credits(seller_bot_id, buyer_user_id, int(product['credits']))
        grant_text = f'На баланс выбранного бота зачислено {product["credits"]} запросов.'
    else:
        db.add_bot_premium_days(seller_bot_id, buyer_user_id, int(product['premium_days']))
        grant_text = f'PRO на выбранном боте активирован на {product["premium_days"]} дней.'

    await distribute_commissions(payment_id, seller_bot_id, payment.total_amount)
    seller_bot = db.get_bot(seller_bot_id)
    seller_name = seller_bot.title if seller_bot else 'бот'
    await update.effective_message.reply_text(
        f'Оплата прошла успешно. {grant_text}\nБот назначения: <b>{html.escape(seller_name)}</b>.',
        reply_markup=reply_menu(context, update.effective_user.id),
        parse_mode=ParseMode.HTML,
    )


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update, context)
    if await blocked_if_banned(update):
        return
    query = update.callback_query
    if not query:
        return

    data = query.data or ''
    if data == 'noop':
        await query.answer()
        return

    if data.startswith('admin:'):
        if get_current_bot_kind(context) != 'root' or not is_admin_user(query.from_user.id):
            await query.answer('Недостаточно прав.', show_alert=True)
            return
        await query.answer()
        await handle_admin_callback(query, context, data)
        return

    if data.startswith('pay:') and get_current_bot_kind(context) == 'root':
        _, product_key, seller_bot_id = data.split(':')
        await query.answer()
        if product_key in PRODUCTS and seller_bot_id.isdigit() and query.message:
            await send_product_invoice(query.message, query.from_user.id, int(seller_bot_id), product_key)
        return

    if data.startswith('createbot:start'):
        parent_bot_id = None
        parts = data.split(':')
        if len(parts) > 2 and parts[2].isdigit():
            parent_bot_id = int(parts[2])
        context.user_data['create_bot_flow'] = {'step': 'awaiting_token', 'parent_bot_id': parent_bot_id}
        await query.answer()
        await query.message.reply_text(
            'Отправь токен твоего бота от @BotFather одним сообщением.\n\n'
            'Для отмены напиши: <b>отмена</b>.',
            parse_mode=ParseMode.HTML,
        )
        return

    if data.startswith('page:'):
        page = int(data.split(':', 1)[1])
        await query.answer()
        await edit_gallery_page(query, page)
        return

    if data.startswith('gallery:'):
        page = int(data.split(':', 1)[1])
        await query.answer()
        await edit_gallery_page(query, page)
        return

    if data == 'menu:presets':
        await query.answer()
        await send_gallery_page(query.message, 0)
        return

    if data == 'menu:custom_mask':
        await query.answer()
        context.user_data['awaiting_custom_prompt'] = True
        await query.message.reply_text('Напиши, какую маску или эффект ты хочешь наложить на последнее фото.')
        return

    if data == 'menu:suggest':
        await query.answer()
        await suggest_masks_for_last_photo(query.message, query.from_user.id, context)
        return

    if data.startswith('texttype:'):
        text_kind = data.split(':', 1)[1]
        context.user_data['awaiting_text_kind'] = text_kind
        await query.answer()
        await query.message.reply_text('Напиши слова, тему, настроение и любые детали для генерации текста.')
        return

    if data == 'buy:menu':
        await query.answer()
        await show_premium(query.message, context)
        return

    if data.startswith('preset:'):
        preset_key = data.split(':', 1)[1]
        preset = PRESET_BY_KEY.get(preset_key)
        if not preset:
            await query.answer('Не удалось найти этот пресет.', show_alert=True)
            return
        await query.answer('Запускаю рендер...')
        await render_with_preset(query.message, query.from_user.id, context, preset_key, stronger=False)
        return

    if data == 'rerun:strong':
        await query.answer('Усиливаю эффект...')
        await rerun_last_action_stronger(query.message, query.from_user.id, context)
        return


async def handle_admin_callback(query, context: ContextTypes.DEFAULT_TYPE, data: str) -> None:
    if data == 'admin:menu':
        await send_admin_menu(query.message)
        return
    if data == 'admin:stats':
        await send_admin_stats(query.message)
        return
    if data == 'admin:tree':
        await send_admin_tree(query.message)
        return
    if data == 'admin:topusers':
        await send_admin_top_users(query.message)
        return
    if data == 'admin:masks':
        await send_admin_masks(query.message)
        return
    if data == 'admin:prompts':
        await send_admin_prompts(query.message)
        return
    if data == 'admin:commissions':
        await send_admin_commissions(query.message)
        return
    if data.startswith('admin:users:'):
        await send_admin_users_page(query.message, int(data.split(':')[-1]))
        return
    if data.startswith('admin:bots:'):
        await send_admin_bots_page(query.message, int(data.split(':')[-1]))
        return
    if data.startswith('admin:bot:'):
        _, _, bot_id, back_page = data.split(':')
        await send_admin_bot_detail(query.message, int(bot_id), int(back_page))
        return
    if data.startswith('admin:user:'):
        _, _, user_id, back_page = data.split(':')
        await send_admin_user_detail(query.message, int(user_id), int(back_page))
        return
    if data.startswith('admin:ban:'):
        _, _, user_id, back_page = data.split(':')
        db.ban_global_user(int(user_id), 'Заблокирован из панели сети')
        try:
            await runtime.send_root_message(int(user_id), '⛔ Твой доступ ко всей сети ботов ограничен администратором.')
        except Exception:
            pass
        await query.message.reply_text(f'Пользователь {user_id} заблокирован во всей сети.')
        await send_admin_user_detail(query.message, int(user_id), int(back_page))
        return
    if data.startswith('admin:unban:'):
        _, _, user_id, back_page = data.split(':')
        db.unban_global_user(int(user_id))
        try:
            await runtime.send_root_message(int(user_id), '✅ Ограничение снято. Ты снова можешь пользоваться сетью ботов.')
        except Exception:
            pass
        await query.message.reply_text(f'Пользователь {user_id} разблокирован во всей сети.')
        await send_admin_user_detail(query.message, int(user_id), int(back_page))
        return
    if data.startswith('admin:vip:'):
        _, _, user_id, enabled, back_page = data.split(':')
        enabled_flag = enabled == '1'
        if int(user_id) not in settings.admin_user_ids:
            db.set_platform_vip(int(user_id), enabled_flag, note=f'admin:{query.from_user.id}')
        try:
            text = '👑 Тебе выдан VIP-платформы: запросы временно не списываются.' if enabled_flag else 'ℹ️ VIP-платформы отключён. Снова действует обычный баланс.'
            await runtime.send_root_message(int(user_id), text)
        except Exception:
            pass
        await query.message.reply_text('VIP-статус обновлён.')
        await send_admin_user_detail(query.message, int(user_id), int(back_page))
        return
    if data.startswith('admin:cred:'):
        _, _, user_id, delta, back_page = data.split(':')
        new_value = db.adjust_global_bonus_credits(int(user_id), int(delta), details=f'admin:{query.from_user.id}')
        try:
            await runtime.send_root_message(int(user_id), f'🎁 Администратор изменил твой общий бонус-баланс на {int(delta)}. Теперь доступно: {new_value}.')
        except Exception:
            pass
        await query.message.reply_text(f'Глобальный бонус-баланс пользователя {user_id} обновлён: {new_value}.')
        await send_admin_user_detail(query.message, int(user_id), int(back_page))
        return
    if data.startswith('admin:grantprompt:'):
        _, _, user_id, back_page = data.split(':')
        context.user_data['admin_pending_grant'] = {'user_id': int(user_id), 'back_page': int(back_page)}
        await query.message.reply_text(
            f'Напиши одним сообщением, сколько общих бонус-запросов изменить пользователю <code>{user_id}</code>.\n'
            'Примеры: <code>25</code>, <code>7</code>, <code>-3</code>.\n'
            'Для отмены напиши: <b>отмена</b>.',
            parse_mode=ParseMode.HTML,
        )
        return
    if data.startswith('admin:flags:'):
        await send_admin_flags_page(query.message, int(data.split(':')[-1]))
        return
    if data.startswith('admin:flagreview:'):
        _, _, flag_id, back_page = data.split(':')
        db.mark_flag_reviewed(int(flag_id))
        await query.message.reply_text('Флаг помечен как проверенный.')
        await send_admin_flags_page(query.message, int(back_page))
        return


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update, context)
    if get_current_bot_kind(context) != 'root' or not is_admin_user(update.effective_user.id):
        await update.effective_message.reply_text('У тебя нет доступа к панели сети.')
        return
    await send_admin_menu(update.effective_message)


async def send_admin_menu(message: Message) -> None:
    text = (
        '🛡 <b>Панель сети</b>\n\n'
        'Здесь ты видишь всю иерархию дочерних ботов, пользователей, продажи, комиссии и подозрительные аккаунты.'
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=admin_menu_keyboard())


async def send_admin_stats(message: Message) -> None:
    row = db.dashboard_stats()
    platform_margin = int(row['stars_revenue']) - int(row['commissions_total'])
    text = (
        '📊 <b>Общая статистика сети</b>\n\n'
        f'• Пользователей всего: <b>{row["total_users"]}</b>\n'
        f'• Активных за 24ч: <b>{row["active_users_24h"]}</b>\n'
        f'• Ботов активных: <b>{row["active_bots"]}</b>\n'
        f'• Дочерних ботов: <b>{row["child_bots"]}</b>\n'
        f'• Всего AI-запросов: <b>{row["total_jobs"]}</b>\n'
        f'• AI-запросов за 24ч: <b>{row["jobs_24h"]}</b>\n'
        f'• Платящих пользователей: <b>{row["paid_users"]}</b>\n'
        f'• VIP платформы: <b>{row["vip_users"]}</b>\n'
        f'• Звёзд получено: <b>{row["stars_revenue"]}</b>⭐\n'
        f'• Начислено комиссий: <b>{row["commissions_total"]}</b>⭐\n'
        f'• Остаток платформы: <b>{platform_margin}</b>⭐\n'
        f'• Заблокированных: <b>{row["banned_users"]}</b>\n'
        f'• Открытых подозрительных флагов: <b>{row["open_flags"]}</b>'
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=admin_menu_keyboard())


async def send_admin_tree(message: Message) -> None:
    rows = db.get_bot_tree()
    lines = ['🌳 <b>Дерево сети</b>', '']
    for row in rows:
        prefix = '└─ ' if int(row['depth']) > 0 else '● '
        indent = '   ' * int(row['depth'])
        owner = mention_html(row['owner_user_id'], row['owner_first_name'], row['owner_username']) if row['owner_user_id'] else 'корневой бот'
        username = '@' + row['username'] if row['username'] else 'без username'
        lines.append(f'{indent}{prefix}<b>{html.escape(row["title"])}</b> ({html.escape(username)}) — {owner}')
    await message.reply_text('\n'.join(lines), parse_mode=ParseMode.HTML, reply_markup=admin_menu_keyboard(), disable_web_page_preview=True)


async def send_admin_top_users(message: Message) -> None:
    rows = db.top_users_by_usage(12)
    lines = ['🔥 <b>Топ пользователей по активности</b>', '']
    if not rows:
        lines.append('Пока данных нет.')
    else:
        for idx, row in enumerate(rows, start=1):
            badges = []
            if row['is_platform_vip']:
                badges.append('👑VIP')
            if row['is_banned_global']:
                badges.append('⛔')
            badge = (' ' + ' '.join(badges)) if badges else ''
            lines.append(f'{idx}. {mention_html(row["user_id"], row["first_name"], row["username"])}{badge} — <b>{row["cnt"]}</b> запросов')
    await message.reply_text('\n'.join(lines), parse_mode=ParseMode.HTML, reply_markup=admin_menu_keyboard(), disable_web_page_preview=True)


async def send_admin_masks(message: Message) -> None:
    rows = db.popular_masks(10)
    lines = ['🎭 <b>Самые популярные маски</b>', '']
    if not rows:
        lines.append('Пока данных нет.')
    else:
        for idx, row in enumerate(rows, start=1):
            preset = PRESET_BY_KEY.get(row['preset_key'])
            title = preset.title if preset else row['preset_key']
            emoji = preset.emoji if preset else '🎭'
            lines.append(f'{idx}. {emoji} <b>{html.escape(title)}</b> — {row["cnt"]}')
    await message.reply_text('\n'.join(lines), parse_mode=ParseMode.HTML, reply_markup=admin_menu_keyboard())


async def send_admin_prompts(message: Message) -> None:
    rows = db.popular_prompts(10)
    lines = ['🔎 <b>Самые популярные запросы</b>', '']
    if not rows:
        lines.append('Пока данных нет.')
    else:
        for idx, row in enumerate(rows, start=1):
            kind = 'Текст' if row['job_type'] == 'text' else 'Своя маска'
            prompt_preview = html.escape((row['prompt'] or '').strip().replace('\n', ' ')[:150])
            lines.append(f'{idx}. <b>{kind}</b> — {row["cnt"]} раз\n<code>{prompt_preview or "—"}</code>')
    await message.reply_text('\n'.join(lines), parse_mode=ParseMode.HTML, reply_markup=admin_menu_keyboard())


async def send_admin_commissions(message: Message) -> None:
    rows = db.commission_summary(15)
    lines = ['💸 <b>Кому начислено комиссий</b>', '']
    if not rows:
        lines.append('Пока начислений нет.')
    else:
        for idx, row in enumerate(rows, start=1):
            lines.append(f'{idx}. {mention_html(row["beneficiary_user_id"], row["first_name"], row["username"])} — <b>{row["total_amount"]}⭐</b> ({row["cnt"]} начисл.)')
    await message.reply_text('\n'.join(lines), parse_mode=ParseMode.HTML, reply_markup=admin_menu_keyboard(), disable_web_page_preview=True)


async def send_admin_users_page(message: Message, page: int) -> None:
    rows, total = db.list_users(page, USERS_PER_PAGE)
    total_pages = max(1, ceil(total / USERS_PER_PAGE))
    lines = [f'👥 <b>Пользователи сети</b> — страница {page + 1}/{total_pages}', '']
    buttons: list[list[InlineKeyboardButton]] = []
    if not rows:
        lines.append('Пользователей пока нет.')
    else:
        for idx, row in enumerate(rows, start=page * USERS_PER_PAGE + 1):
            badges = []
            badges.append('⛔' if row['is_banned_global'] else '✅')
            if row['is_platform_vip']:
                badges.append('👑')
            if row['user_id'] in settings.admin_user_ids:
                badges.append('🛡')
            badge = ' '.join(badges)
            user_link = mention_html(row['user_id'], row['first_name'], row['username'])
            lines.append(
                f'{idx}. {badge} {user_link} — ID <code>{row["user_id"]}</code>\n'
                f'   запросов: <b>{row["jobs_count"]}</b>, платежей: <b>{row["payments_count"]}</b>, ботов: <b>{row["bots_count"]}</b>, бонусы: <b>{row["global_bonus_credits"]}</b>'
            )
            buttons.append([InlineKeyboardButton('👤 Открыть карточку', callback_data=f'admin:user:{row["user_id"]}:{page}')])
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton('⬅️', callback_data=f'admin:users:{page - 1}'))
    nav.append(InlineKeyboardButton(f'{page + 1}/{total_pages}', callback_data='noop'))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton('➡️', callback_data=f'admin:users:{page + 1}'))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton('🛡 В меню сети', callback_data='admin:menu')])
    await message.reply_text('\n\n'.join(lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)


async def send_admin_user_detail(message: Message, user_id: int, back_page: int) -> None:
    row = db.get_user_detail(user_id)
    if not row:
        await message.reply_text('Пользователь не найден.', reply_markup=admin_menu_keyboard())
        return
    memberships = db.get_user_memberships(user_id)
    premium_lines = []
    for membership in memberships[:8]:
        prem = membership['premium_until'] or '—'
        owner_badge = ' 👑владелец' if membership['is_owner'] else ''
        username = '@' + membership['bot_username'] if membership['bot_username'] else 'без username'
        premium_lines.append(
            f'• <b>{html.escape(membership["bot_title"])}</b> ({html.escape(username)}){owner_badge}: '
            f'free <b>{membership["free_trial_left"]}</b>, paid <b>{membership["paid_credits"]}</b>, owner/day <b>{membership["owner_daily_left"]}</b>, PRO <b>{html.escape(str(prem))}</b>'
        )
    if not premium_lines:
        premium_lines.append('• У пользователя пока нет активностей по ботам.')
    text = (
        '👤 <b>Карточка пользователя</b>\n\n'
        f'Ссылка: {mention_html(row["user_id"], row["first_name"], row["username"])}\n'
        f'ID: <code>{row["user_id"]}</code>\n'
        f'Имя: <b>{html.escape(row["first_name"] or "—")}</b>\n'
        f'Username: <b>{html.escape("@" + row["username"] if row["username"] else "—")}</b>\n'
        f'Глобальные бонусы: <b>{row["global_bonus_credits"]}</b>\n'
        f'Всего запросов: <b>{row["total_jobs"]}</b>\n'
        f'За 24ч: <b>{row["jobs_24h"]}</b>\n'
        f'Покупок: <b>{row["total_payments"]}</b>\n'
        f'Потрачено: <b>{row["total_spent"]}</b>⭐\n'
        f'Открытых флагов: <b>{row["open_flags"]}</b>\n'
        f'Создано дочерних ботов: <b>{row["owned_bots"]}</b>\n'
        f'Начислено комиссий: <b>{row["earned_commissions"]}</b>⭐\n'
        f'VIP платформы: <b>{"да" if row["is_platform_vip"] or user_id in settings.admin_user_ids else "нет"}</b>\n'
        f'Статус: <b>{"забанен" if row["is_banned_global"] else "активен"}</b>\n'
        f'Причина бана: <b>{html.escape(row["ban_reason"] or "—")}</b>\n\n'
        '<b>Состояния по ботам:</b>\n' + '\n'.join(premium_lines)
    )
    await message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        reply_markup=admin_user_actions_keyboard(
            user_id=user_id,
            is_banned=bool(row['is_banned_global']),
            is_vip=bool(row['is_platform_vip']),
            back_page=back_page,
            is_owner=user_id in settings.admin_user_ids,
        ),
        disable_web_page_preview=True,
    )


async def send_admin_bots_page(message: Message, page: int) -> None:
    rows, total = db.list_bots(page, BOTS_PER_PAGE)
    total_pages = max(1, ceil(total / BOTS_PER_PAGE))
    lines = [f'🤖 <b>Дочерние боты</b> — страница {page + 1}/{total_pages}', '']
    buttons: list[list[InlineKeyboardButton]] = []
    if not rows:
        lines.append('Дочерних ботов пока нет.')
    else:
        for idx, row in enumerate(rows, start=page * BOTS_PER_PAGE + 1):
            owner = mention_html(row['owner_user_id'], row['owner_first_name'], row['owner_username']) if row['owner_user_id'] else '—'
            username = '@' + row['username'] if row['username'] else 'без username'
            parent_title = html.escape(row['parent_title'] or 'root')
            lines.append(
                f'{idx}. <b>{html.escape(row["title"])}</b> ({html.escape(username)})\n'
                f'   владелец: {owner}; parent: <b>{parent_title}</b>\n'
                f'   участники: <b>{row["members_count"]}</b>, запросы: <b>{row["jobs_count"]}</b>, продажи: <b>{row["sales_count"]}</b>, доход: <b>{row["stars_revenue"]}</b>⭐'
            )
            buttons.append([InlineKeyboardButton('🤖 Открыть карточку', callback_data=f'admin:bot:{row["id"]}:{page}')])
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton('⬅️', callback_data=f'admin:bots:{page - 1}'))
    nav.append(InlineKeyboardButton(f'{page + 1}/{total_pages}', callback_data='noop'))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton('➡️', callback_data=f'admin:bots:{page + 1}'))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton('🛡 В меню сети', callback_data='admin:menu')])
    await message.reply_text('\n\n'.join(lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)


async def send_admin_bot_detail(message: Message, bot_id: int, back_page: int) -> None:
    row = db.get_bot_detail(bot_id)
    if not row:
        await message.reply_text('Бот не найден.', reply_markup=admin_menu_keyboard())
        return
    owner = mention_html(row['owner_user_id'], row['owner_first_name'], row['owner_username']) if row['owner_user_id'] else '—'
    username = '@' + row['username'] if row['username'] else 'без username'
    parent = row['parent_title'] or 'root'
    text = (
        '🤖 <b>Карточка дочернего бота</b>\n\n'
        f'Название: <b>{html.escape(row["title"])}</b>\n'
        f'Username: <b>{html.escape(username)}</b>\n'
        f'ID в сети: <code>{row["id"]}</code>\n'
        f'Владелец: {owner}\n'
        f'Родитель: <b>{html.escape(parent)}</b>\n'
        f'Статус: <b>{html.escape(row["status"])}</b>\n'
        f'Бесплатно для юзера: <b>{row["user_free_trial"]}</b>\n'
        f'Владелец / день: <b>{row["owner_daily_free"]}</b>\n'
        f'Участников: <b>{row["members_count"]}</b>\n'
        f'AI-запросов: <b>{row["jobs_count"]}</b>\n'
        f'Продаж: <b>{row["sales_count"]}</b>\n'
        f'Доход привязанных продаж: <b>{row["stars_revenue"]}</b>⭐\n'
        f'Создан: <b>{html.escape(str(row["created_at"]))}</b>\n'
        f'Запущен: <b>{html.escape(str(row["launched_at"] or "—"))}</b>'
    )
    await message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=admin_bot_actions_keyboard(bot_id, back_page), disable_web_page_preview=True)


async def send_admin_flags_page(message: Message, page: int) -> None:
    rows, total = db.list_suspicious_flags(page, FLAGS_PER_PAGE)
    total_pages = max(1, ceil(total / FLAGS_PER_PAGE))
    lines = [f'🚨 <b>Подозрительные пользователи</b> — страница {page + 1}/{total_pages}', '']
    buttons: list[list[InlineKeyboardButton]] = []
    if not rows:
        lines.append('Открытых флагов нет.')
    else:
        for idx, row in enumerate(rows, start=page * FLAGS_PER_PAGE + 1):
            user_link = mention_html(row['user_id'], row['first_name'], row['username'])
            badge = ' 👑VIP' if row['is_platform_vip'] else ''
            bot_title = html.escape(row['bot_title'] or '—')
            lines.append(f'{idx}. {user_link}{badge} — <b>{html.escape(row["reason"])}</b>\n   бот: <b>{bot_title}</b>\n   {html.escape((row["details"] or "—")[:220])}')
            buttons.append([
                InlineKeyboardButton('👤 Профиль', callback_data=f'admin:user:{row["user_id"]}:{page}'),
                InlineKeyboardButton('✔️ Проверено', callback_data=f'admin:flagreview:{row["id"]}:{page}'),
                InlineKeyboardButton('✅ Разбан' if row['is_banned_global'] else '🚫 Бан', callback_data=f'admin:{"unban" if row["is_banned_global"] else "ban"}:{row["user_id"]}:{page}'),
            ])
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton('⬅️', callback_data=f'admin:flags:{page - 1}'))
    nav.append(InlineKeyboardButton(f'{page + 1}/{total_pages}', callback_data='noop'))
    if page + 1 < total_pages:
        nav.append(InlineKeyboardButton('➡️', callback_data=f'admin:flags:{page + 1}'))
    buttons.append(nav)
    buttons.append([InlineKeyboardButton('🛡 В меню сети', callback_data='admin:menu')])
    await message.reply_text('\n\n'.join(lines), parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons), disable_web_page_preview=True)


TOKEN_REGEX = re.compile(r'^\d{6,12}:[A-Za-z0-9_-]{20,}$')


async def handle_create_bot_flow(message: Message, context: ContextTypes.DEFAULT_TYPE, text: str) -> bool:
    flow = context.user_data.get('create_bot_flow')
    if not flow:
        return False
    lower = text.lower().strip()
    if lower in {'отмена', 'cancel', 'стоп'}:
        context.user_data.pop('create_bot_flow', None)
        await message.reply_text('Подключение бота отменено.', reply_markup=reply_menu(context, message.from_user.id if message.from_user else None))
        return True

    if flow.get('step') == 'awaiting_token':
        token = text.strip()
        if not TOKEN_REGEX.fullmatch(token):
            await message.reply_text('Похоже, это не токен. Вставь токен целиком из сообщения BotFather. Для отмены напиши «отмена».')
            return True
        try:
            telegram_bot_id, username, inferred_title = await runtime.validate_child_token(token)
        except ValueError as exc:
            await message.reply_text(str(exc))
            return True
        flow.update({'step': 'awaiting_title', 'token': token, 'telegram_bot_id': telegram_bot_id, 'username': username, 'inferred_title': inferred_title})
        context.user_data['create_bot_flow'] = flow
        await message.reply_text(
            f'Токен принят. Бот найден: <b>{html.escape(inferred_title)}</b> ({html.escape("@" + username if username else "без username")}).\n\n'
            'Теперь пришли красивое название для карточки в сети.\n'
            'Можно просто отправить одно сообщение, например: <code>Magic Mask by Alex</code>.',
            parse_mode=ParseMode.HTML,
        )
        return True

    if flow.get('step') == 'awaiting_title':
        desired_title = text.strip()[:80]
        if len(desired_title) < 2:
            await message.reply_text('Название слишком короткое. Пришли более осмысленное название или «отмена».')
            return True
        try:
            instance = await runtime.register_child_bot(
                token=flow['token'],
                owner_user_id=message.from_user.id,
                parent_bot_id=flow.get('parent_bot_id'),
                desired_title=desired_title,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception('Child bot registration failed: %s', exc)
            await message.reply_text(f'Не удалось подключить бота: {exc}')
            return True
        context.user_data.pop('create_bot_flow', None)
        username = '@' + instance.username if instance.username else 'без username'
        root_name = '@' + current_root_username() if current_root_username() else 'корневой бот'
        text_reply = (
            '✅ <b>Бот подключён к платформе</b>\n\n'
            f'Название: <b>{html.escape(instance.title)}</b>\n'
            f'Username: <b>{html.escape(username)}</b>\n'
            f'ID в сети: <code>{instance.id}</code>\n\n'
            f'Что дальше:\n'
            f'1) Открой своего бота и нажми <code>/start</code>.\n'
            f'2) При желании настрой имя и аватар у BotFather.\n'
            f'3) Премиум для твоих пользователей будет продаваться через {html.escape(root_name)}.\n'
            f'4) Тебе как владельцу доступно <b>{settings.child_owner_daily_free} бесплатных запросов в день</b>.\n\n'
            'Подключение завершено.'
        )
        await message.reply_text(text_reply, parse_mode=ParseMode.HTML, reply_markup=reply_menu(context, message.from_user.id if message.from_user else None))
        return True

    return False


async def text_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update, context)
    if await blocked_if_banned(update):
        return
    message = update.effective_message
    if not message or not message.text:
        return
    text = message.text.strip()
    bot_instance = get_current_bot(context)

    if bot_instance.kind == 'root' and is_admin_user(update.effective_user.id) and context.user_data.get('admin_pending_grant'):
        pending = context.user_data['admin_pending_grant']
        if text.lower() in {'отмена', 'cancel', 'стоп'}:
            context.user_data.pop('admin_pending_grant', None)
            await message.reply_text('Выдача бонусов отменена.', reply_markup=reply_menu(context, update.effective_user.id))
            return
        if not re.fullmatch(r'[+-]?\d+', text):
            await message.reply_text('Пришли целое число. Например: <code>25</code> или <code>-5</code>. Для отмены напиши «отмена».', parse_mode=ParseMode.HTML)
            return
        delta = int(text)
        target_user_id = int(pending['user_id'])
        back_page = int(pending.get('back_page', 0))
        new_value = db.adjust_global_bonus_credits(target_user_id, delta, details=f'admin:{update.effective_user.id}')
        context.user_data.pop('admin_pending_grant', None)
        action_word = 'выдано' if delta >= 0 else 'списано'
        await message.reply_text(
            f'Готово: пользователю <code>{target_user_id}</code> {action_word} <b>{abs(delta)}</b> бонусов. Теперь общий бонус-баланс: <b>{new_value}</b>.',
            parse_mode=ParseMode.HTML,
        )
        try:
            if delta != 0:
                verb = 'начислено' if delta > 0 else 'списано'
                await runtime.send_root_message(target_user_id, f'ℹ️ Администратор изменил твой общий бонус-баланс: {verb} {abs(delta)} запросов.')
        except Exception:
            pass
        await send_admin_user_detail(message, target_user_id, back_page)
        return

    if await handle_create_bot_flow(message, context, text):
        return

    if text in {'✨ Маски', '✨ Маски-галерея', '🖼 Примеры масок'}:
        await send_gallery_page(message, 0)
        return
    if text in {'✨ Маска по тексту', '🎨 Маска по описанию'}:
        if not context.user_data.get('last_photo_path'):
            await message.reply_text('Сначала пришли фото, затем опиши свою маску.', reply_markup=reply_menu(context, update.effective_user.id))
            return
        context.user_data['awaiting_custom_prompt'] = True
        await message.reply_text('Напиши, какую маску или эффект ты хочешь наложить на фото.')
        return
    if text in {'🖼 Подсказать маски', '🪄 Подобрать стиль'}:
        await suggest_masks_for_last_photo(message, update.effective_user.id, context)
        return
    if text in {'✍️ Тексты', '✍️ Тексты / стихи'}:
        await message.reply_text('Выбери, какой именно текст создать:', reply_markup=text_types_keyboard())
        return
    if text in {'⭐ Премиум', '⭐ Купить запросы'}:
        await show_premium(message, context)
        return
    if text == '👤 Профиль':
        await profile(update, context)
        return
    if text in {'❓ Помощь', '📘 Как это работает'}:
        await explain_how_it_works(message, context)
        return
    if text == '🛡 Админ-сеть':
        await admin_command(update, context)
        return
    if text in {'🚀 Подключить своего бота'} and bot_instance.kind == 'root':
        await send_create_bot_intro(message, None)
        return
    if text in {'🚀 Создать такого же бота'} and bot_instance.kind != 'root':
        if current_root_username():
            await message.reply_text(
                'Открой мастер подключения у корневого бота платформы:',
                reply_markup=owner_help_keyboard(current_root_username(), bot_instance.id),
            )
        else:
            await message.reply_text('Корневой бот платформы пока не определён.')
        return

    if context.user_data.get('awaiting_custom_prompt'):
        context.user_data['awaiting_custom_prompt'] = False
        await render_custom_mask(message, update.effective_user.id, context, text, stronger=False)
        return

    text_kind = context.user_data.get('awaiting_text_kind')
    if text_kind:
        context.user_data['awaiting_text_kind'] = None
        await generate_creative_text(message, update.effective_user.id, context, text_kind, text)
        return

    await message.reply_text('Не понял команду. Можно прислать фото или открыть меню ниже.', reply_markup=reply_menu(context, update.effective_user.id))


async def answer_noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await ensure_user(update, context)
    if await blocked_if_banned(update):
        return
    await show_premium(update.effective_message, context)


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await profile(update, context)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception('Unhandled exception: %s', context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text('Произошла ошибка. Попробуй ещё раз.')


def build_application(bot_instance: BotInstance, runtime_obj: PlatformRuntime) -> Application:
    application = Application.builder().token(bot_instance.token).build()
    application.bot_data['bot_id'] = bot_instance.id
    application.bot_data['bot_kind'] = bot_instance.kind
    application.bot_data['runtime'] = runtime_obj

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('menu', menu))
    application.add_handler(CommandHandler('buy', buy_command))
    application.add_handler(CommandHandler('profile', profile_command))
    application.add_handler(CommandHandler('admin', admin_command))
    application.add_handler(CommandHandler('help', help_command))

    application.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    application.add_handler(CallbackQueryHandler(answer_noop, pattern='^noop$'))
    application.add_handler(CallbackQueryHandler(callback_router))

    image_filter = filters.PHOTO | filters.Document.IMAGE
    application.add_handler(MessageHandler(image_filter, photo_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_router))

    application.add_error_handler(error_handler)
    return application


def _is_placeholder_secret(value: str) -> bool:
    stripped = (value or '').strip()
    if not stripped:
        return True
    upper = stripped.upper()
    return upper.startswith('PASTE_') or 'YOUR_' in upper or upper.endswith('_HERE')


async def amain() -> None:
    if _is_placeholder_secret(settings.telegram_bot_token):
        raise RuntimeError('TELEGRAM_BOT_TOKEN is empty or still contains a placeholder. Fill .env first.')
    if _is_placeholder_secret(settings.openai_api_key):
        raise RuntimeError('OPENAI_API_KEY is empty or still contains a placeholder. Fill .env first.')
    if not settings.admin_user_ids:
        logger.warning('ADMIN_USER_IDS is empty. Admin panel will be unavailable until you set it.')

    await runtime.start_all()
    logger.info('Platform started')

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, runtime._stop_event.set)
        except NotImplementedError:
            pass
    await runtime._stop_event.wait()
    await runtime.stop_all()


def main() -> None:
    asyncio.run(amain())


if __name__ == '__main__':
    main()
