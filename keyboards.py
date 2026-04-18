from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from presets import MASK_PRESETS

PRESETS_PER_PAGE = 6
USERS_PER_PAGE = 8
FLAGS_PER_PAGE = 6
VIPS_PER_PAGE = 8
BOTS_PER_PAGE = 7

TEXT_TYPE_BUTTONS = [
    ('poem', '📝 Стих'),
    ('song', '🎶 Песня'),
    ('poema', '📜 Поэма'),
    ('greeting', '🎉 Поздравление'),
    ('quote', '💬 Фразы'),
    ('status', '🔥 Статус'),
    ('toast', '🥂 Тост'),
    ('caption', '📣 Подпись'),
    ('rap', '🎤 Рэп'),
    ('custom', '✨ Свой формат'),
]


def main_menu_keyboard(*, is_root: bool, is_admin: bool) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton('✨ Маски-галерея'), KeyboardButton('🎨 Маска по описанию')],
        [KeyboardButton('🪄 Подобрать стиль'), KeyboardButton('✍️ Тексты / стихи')],
        [KeyboardButton('🖼 Примеры масок'), KeyboardButton('👤 Профиль')],
        [KeyboardButton('⭐ Купить запросы'), KeyboardButton('❓ Помощь')],
    ]
    if is_root:
        keyboard.append([KeyboardButton('🚀 Подключить своего бота'), KeyboardButton('📘 Как это работает')])
    else:
        keyboard.append([KeyboardButton('🚀 Создать такого же бота'), KeyboardButton('📘 Как это работает')])
    if is_admin and is_root:
        keyboard.append([KeyboardButton('🛡 Админ-сеть')])
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder='Выбери действие ниже ⬇️',
    )


def preset_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    total_pages = max(1, (len(MASK_PRESETS) + PRESETS_PER_PAGE - 1) // PRESETS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * PRESETS_PER_PAGE
    chunk = MASK_PRESETS[start : start + PRESETS_PER_PAGE]

    rows: list[list[InlineKeyboardButton]] = []
    for preset in chunk:
        rows.append([InlineKeyboardButton(text=f'{preset.emoji} {preset.title[:42]}', callback_data=f'preset:{preset.key}')])

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton('⬅️', callback_data=f'page:{page - 1}'))
    nav.append(InlineKeyboardButton(f'Стр. {page + 1}/{total_pages}', callback_data='noop'))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton('➡️', callback_data=f'page:{page + 1}'))
    rows.append(nav)
    rows.append([InlineKeyboardButton('🖼 Открыть примеры', callback_data=f'gallery:{page}')])
    rows.append([InlineKeyboardButton('⭐ Пополнить баланс', callback_data='buy:menu')])
    return InlineKeyboardMarkup(rows)


def quick_after_photo_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton('✨ Открыть маски-галерею', callback_data='menu:presets')],
            [InlineKeyboardButton('🎨 Своя маска по описанию', callback_data='menu:custom_mask')],
            [InlineKeyboardButton('🪄 Подобрать стиль', callback_data='menu:suggest')],
        ]
    )


def photo_batch_keyboard(*, can_send: bool, mode: str = "preset") -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if can_send:
        if mode == 'custom':
            rows.append([InlineKeyboardButton('✍️ Написать описание маски', callback_data='media:custom_prompt')])
        else:
            rows.append([InlineKeyboardButton('✅ Отправить в шаблон', callback_data='media:send')])
    rows.append([
        InlineKeyboardButton('🗑 Очистить фото', callback_data='media:clear'),
        InlineKeyboardButton('❌ Отмена', callback_data='media:cancel'),
    ])
    return InlineKeyboardMarkup(rows)


def premium_keyboard(root_username: str, seller_bot_id: int) -> InlineKeyboardMarkup:
    base = f'https://t.me/{root_username}?start=pay_{seller_bot_id}_'
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton('⭐ Старт-пак', url=base + 'pack_small')],
            [InlineKeyboardButton('🚀 Большой пак', url=base + 'pack_big')],
            [InlineKeyboardButton('👑 MAX-пак', url=base + 'pro_30')],
        ]
    )


def root_buy_keyboard(seller_bot_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton('⭐ Старт-пак', callback_data=f'pay:pack_small:{seller_bot_id}')],
            [InlineKeyboardButton('🚀 Большой пак', callback_data=f'pay:pack_big:{seller_bot_id}')],
            [InlineKeyboardButton('👑 MAX-пак', callback_data=f'pay:pro_30:{seller_bot_id}')],
        ]
    )


def text_types_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for i in range(0, len(TEXT_TYPE_BUTTONS), 2):
        row = [InlineKeyboardButton(title, callback_data=f'texttype:{key}') for key, title in TEXT_TYPE_BUTTONS[i : i + 2]]
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def result_keyboard(last_kind: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton('⚡ Усилить эффект', callback_data='rerun:strong')]]
    if last_kind == 'image':
        rows.append([InlineKeyboardButton('✨ Другие маски', callback_data='menu:presets')])
    rows.append([InlineKeyboardButton('⭐ Пополнить', callback_data='buy:menu')])
    return InlineKeyboardMarkup(rows)




def cancel_flow_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton('❌ Отмена')]],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder='Можно отменить текущее действие',
    )

def create_bot_keyboard(parent_bot_id: int | None = None) -> InlineKeyboardMarkup:
    cb = 'createbot:start' if parent_bot_id is None else f'createbot:start:{parent_bot_id}'
    return InlineKeyboardMarkup([[InlineKeyboardButton('🚀 Подключить моего бота', callback_data=cb)]])


def owner_help_keyboard(root_username: str, parent_bot_id: int | None = None) -> InlineKeyboardMarkup:
    deep_link = f'https://t.me/{root_username}'
    if parent_bot_id is not None:
        deep_link += f'?start=ref_{parent_bot_id}'
    return InlineKeyboardMarkup([[InlineKeyboardButton('🚀 Открыть мастер подключения', url=deep_link)]])


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton('📊 Сеть: общая статистика', callback_data='admin:stats')],
            [InlineKeyboardButton('🌳 Дерево ботов', callback_data='admin:tree')],
            [InlineKeyboardButton('🤖 Дочерние боты', callback_data='admin:bots:0')],
            [InlineKeyboardButton('👥 Пользователи', callback_data='admin:users:0')],
            [InlineKeyboardButton('🔥 Топ пользователей', callback_data='admin:topusers')],
            [InlineKeyboardButton('🎭 Топ масок', callback_data='admin:masks')],
            [InlineKeyboardButton('🔎 Топ запросов', callback_data='admin:prompts')],
            [InlineKeyboardButton('💸 Комиссии', callback_data='admin:commissions')],
            [InlineKeyboardButton('👤 Контакты поддержки', callback_data='admin:support')],
            [InlineKeyboardButton('🚨 Подозрительные', callback_data='admin:flags:0')],
        ]
    )


def admin_user_actions_keyboard(user_id: int, is_banned: bool, is_vip: bool, back_page: int = 0, is_owner: bool = False) -> InlineKeyboardMarkup:
    ban_label = '✅ Разбан' if is_banned else '🚫 Бан'
    ban_action = 'admin:unban' if is_banned else 'admin:ban'
    vip_label = '🛡 Корневой владелец' if is_owner else ('❌ Убрать VIP' if is_vip else '👑 Выдать VIP')
    vip_callback = 'noop' if is_owner else f"admin:vip:{user_id}:{'0' if is_vip else '1'}:{back_page}"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(ban_label, callback_data=f'{ban_action}:{user_id}:{back_page}'),
                InlineKeyboardButton(vip_label, callback_data=vip_callback),
            ],
            [
                InlineKeyboardButton('➕ +5', callback_data=f'admin:cred:{user_id}:5:{back_page}'),
                InlineKeyboardButton('➕ +10', callback_data=f'admin:cred:{user_id}:10:{back_page}'),
                InlineKeyboardButton('➕ +25', callback_data=f'admin:cred:{user_id}:25:{back_page}'),
            ],
            [
                InlineKeyboardButton('➕ +50', callback_data=f'admin:cred:{user_id}:50:{back_page}'),
                InlineKeyboardButton('✍️ Выдать вручную', callback_data=f'admin:grantprompt:{user_id}:{back_page}'),
            ],
            [InlineKeyboardButton('🔙 К списку', callback_data=f'admin:users:{back_page}')],
        ]
    )


def suspicious_flag_actions_keyboard(flag_id: int, user_id: int, is_banned: bool, back_page: int = 0) -> InlineKeyboardMarkup:
    primary_label = '✅ Разбан' if is_banned else '🚫 Бан'
    primary_action = 'admin:unban' if is_banned else 'admin:ban'
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton('👤 Профиль', callback_data=f'admin:user:{user_id}:{back_page}')],
            [
                InlineKeyboardButton(primary_label, callback_data=f'{primary_action}:{user_id}:{back_page}'),
                InlineKeyboardButton('✔️ Проверено', callback_data=f'admin:flagreview:{flag_id}:{back_page}'),
            ],
            [InlineKeyboardButton('🚨 К подозрительным', callback_data=f'admin:flags:{back_page}')],
        ]
    )


def admin_bot_actions_keyboard(bot_id: int, back_page: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton('🔄 Обновить карточку', callback_data=f'admin:bot:{bot_id}:{back_page}')],
            [InlineKeyboardButton('🔙 К ботам', callback_data=f'admin:bots:{back_page}')],
        ]
    )
