"""Главный файл Telegram-бота «Зверобой» 2.0.

В этой версии есть:
- регистрация с правилами и выбором зверя;
- inline-меню;
- инвентарь, экипировка, крафт, магазин, чёрный рынок;
- рынок, аукцион, заказы на покупку, подарки, сделки, просьбы;
- PvP, подземелья, экспедиции, задания, мировой босс;
- стаи, почта, питомцы, лагерь офлайн, рефералка;
- owner-only админ-панель с заготовкой под монетизацию и анти-мультиаккаунт оповещения.
"""

from __future__ import annotations

import json
import random
import re
import threading
import time
from typing import Any

import telebot
from telebot.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeDefault,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    LabeledPrice,
)

from config import (
    ADMIN_PASSWORD,
    BOT_TOKEN,
    CHAT_EVENT_GOLD,
    CHAT_EVENT_XP,
    CLAN_CREATE_PRICE,
    COOLDOWN_BANK,
    COOLDOWN_CAMP_START,
    COOLDOWN_CHAT_EVENT,
    COOLDOWN_DEATH,
    COOLDOWN_DUNGEON,
    COOLDOWN_EXPEDITION,
    COOLDOWN_GIFT,
    COOLDOWN_MARKET,
    COOLDOWN_PVP,
    COOLDOWN_WORLD_BOSS,
    GAME_TITLE,
    HELP_COMMANDS,
    COMMAND_RU_SYNONYMS,
    MAX_LEVEL,
    PVP_BET_COMMISSION_RATE,
    PVP_WINNER_BET_SHARE_RATE,
    INFO_TEXT,
    LORE_TEXT,
    MAP_TEXT,
    OWNER_ID,
    RULES_TEXT,
    TOP_PAGE,
    VERSION,
    WORLD_BOSS_KILL_BONUS,
    WORLD_BOSS_PARTICIPATION_XP,
)
from data_crafts import RECIPES, add_recipe as register_recipe
from data_items import (
    CATEGORY_CODES,
    CATEGORY_NAMES,
    CHARACTERS,
    CONTRACT_TEMPLATES,
    CURRENCY_ID,
    DAILY_TASK_POOL,
    DEFAULT_MONETIZATION_PACKS,
    FACTIONS,
    ITEMS,
    PET_SPECIES,
    PET_TOKEN_ID,
    PREMIUM_ID,
    REFERRAL_GIFT_ITEM,
    SLOT_ORDER,
    SLOT_TITLES,
    SPECIALIZATIONS,
    TALENTS,
    WEEKLY_TASK_POOL,
    add_item as add_catalog_item,
    get_item,
    is_consumable,
    is_elixir,
    is_equipment,
    is_food,
    is_scroll,
)
from game_logic import (
    camp_rewards,
    choose_task_defs,
    craft_preview,
    daily_contract_board,
    economy_snapshot,
    effective_profile,
    faction_daily_reward,
    format_item_line,
    format_seconds,
    generate_black_market_stock,
    generate_shop_stock,
    item_effect_text,
    format_bonus_dict,
    loan_offer,
    maybe_chat_event,
    profile_progress,
    resolve_pvp,
    run_contract,
    run_dungeon,
    run_expedition,
    dungeon_entry_requirements,
    season_info,
    league_name,
    sync_level,
    world_boss_attack,
    world_boss_today,
)
from user_data import (
    add_admin,
    add_buff,
    add_faction_rep,
    add_friend,
    add_gold,
    add_item,
    add_log,
    add_premium,
    add_suspicion,
    add_talent_points,
    add_win,
    add_loss,
    adjust_player_limits,
    apply_overdue_loans,
    buy_market_listing,
    change_reputation,
    can_prestige,
    can_run_contract,
    claim_faction_daily,
    claim_task,
    clear_camp,
    clear_user_state,
    close_due_auctions,
    close_expired_buy_orders,
    close_expired_market,
    complete_deal,
    contribute_request,
    create_auction,
    create_buy_order,
    create_clan,
    create_deal,
    create_item_request,
    create_loan,
    create_market_listing,
    create_player,
    create_pvp_request,
    create_promo,
    damage_equipment,
    donate_clan_treasury,
    ensure_default_packs,
    ensure_tasks,
    equip_item,
    fulfill_buy_order,
    get_auction,
    get_buffs,
    get_clan,
    get_clan_members,
    get_cooldown_remaining,
    get_codex_count,
    get_deal,
    get_death_remaining,
    get_display_name,
    get_equipment,
    get_gold,
    get_inventory,
    get_item_amount,
    get_item_request,
    get_listing,
    get_market_listings,
    get_open_item_requests,
    get_player,
    get_player_extras,
    get_player_by_username,
    get_pvp_request,
    get_latest_chat_pvp,
    get_pvp_request_by_message,
    get_pvp_bets,
    get_referrals,
    get_user_state,
    get_world_state,
    grant_pack_to_user,
    create_pvp_bet,
    update_pvp_request_message,
    take_pvp_tribute,
    settle_pvp_bets,
    init_db,
    load_custom_items,
    load_custom_recipes,
    inventory_stats,
    is_owner,
    join_clan,
    leave_clan,
    list_admins,
    donation_enabled,
    toggle_donation_enabled,
    toggle_pack_stars,
    set_pack_stars_price,
    set_bank_debt_admin,
    reduce_bank_debt_admin,
    list_auctions,
    list_buy_orders,
    list_clans,
    list_logs,
    list_mail,
    list_packs,
    list_promos,
    list_suspicions,
    list_tasks,
    list_codex,
    mark_mail_read,
    mark_suspicion_sent,
    now_ts,
    place_bid,
    player_exists,
    perform_prestige,
    read_mail,
    redeem_promo,
    register_character,
    remove_admin,
    remove_item,
    repair_all,
    repay_loan,
    reset_talents,
    reset_character_for_reroll,
    send_mail,
    set_blocked,
    set_cooldown,
    set_dead_until,
    set_hp_energy,
    set_faction,
    set_pet,
    set_referral_reward_choice,
    set_rules_accepted,
    set_specialization,
    set_title,
    set_user_state,
    set_world_state,
    save_custom_item,
    save_custom_recipe,
    spend_gold,
    suspicious_referral_count,
    top_by_level,
    top_by_rep,
    top_by_rich,
    top_by_wins,
    touch_identity,
    train_pet,
    toggle_pack,
    transfer_item,
    unequip_slot,
    award_talent_points_for_levels,
    learn_talent,
    mark_contract_done,
)

if not BOT_TOKEN:
    raise RuntimeError("В .env не найден BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

BATTLE_TURN_SEC = 90
BATTLE_MAX_SEC = 12 * 60
BATTLE_ITEM_LIMIT = 2
EXPEDITION_DURATIONS = {'easy': 30 * 60, 'normal': 60 * 60, 'hard': 2 * 60 * 60, 'nightmare': 4 * 60 * 60}
DUNGEON_MAX_SEC = 15 * 60
DUNGEON_ITEM_LIMIT = 2
EXPEDITION_DURATION = {"easy": 30 * 60, "normal": 60 * 60, "hard": 2 * 3600, "nightmare": 4 * 3600}


def register_telegram_commands() -> None:
    """Обновляет список команд в меню Telegram, чтобы не оставались старые команды от прошлых версий бота."""
    private_commands = [
        BotCommand('start', 'запуск и регистрация'),
        BotCommand('menu', 'главное меню'),
        BotCommand('p', 'профиль'),
        BotCommand('inv', 'инвентарь'),
        BotCommand('pvp', 'арена и дуэли'),
        BotCommand('x', 'экспедиция'),
        BotCommand('d', 'подземелье'),
        BotCommand('s', 'магазин'),
        BotCommand('bm', 'чёрный рынок'),
        BotCommand('mk', 'рынок и аукцион'),
        BotCommand('c', 'крафт'),
        BotCommand('b', 'банк'),
        BotCommand('task', 'задания'),
        BotCommand('boss', 'мировой босс'),
        BotCommand('pet', 'питомец'),
        BotCommand('camp', 'лагерь'),
        BotCommand('clan', 'стая'),
        BotCommand('mail', 'почта'),
        BotCommand('top', 'рейтинги'),
        BotCommand('ref', 'рефералка'),
        BotCommand('tal', 'таланты'),
        BotCommand('fac', 'фракция'),
        BotCommand('ct', 'контракты'),
        BotCommand('info', 'правила и помощь'),
        BotCommand('donate', 'поддержка и звёзды'),
    ]
    group_commands = [
        BotCommand('menu', 'главное меню'),
        BotCommand('p', 'профиль'),
        BotCommand('inv', 'инвентарь'),
        BotCommand('pvp', 'дуэли и ставки'),
        BotCommand('mk', 'рынок и обмен'),
        BotCommand('top', 'рейтинги'),
        BotCommand('info', 'правила и помощь'),
        BotCommand('donate', 'поддержка и звёзды'),
    ]
    try:
        bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
        bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
        bot.set_my_commands(private_commands, scope=BotCommandScopeDefault())
    except Exception:
        # Если Telegram временно не принял обновление меню, сам бот всё равно должен запускаться.
        pass

init_db()
ensure_default_packs(DEFAULT_MONETIZATION_PACKS)
OWNER_AUTHED: set[int] = set()
CATEGORY_BY_CODE = {value: key for key, value in CATEGORY_CODES.items()}

ITEM_TEMPLATE_PRESETS: dict[str, dict[str, dict[str, Any]]] = {
    "food": {
        "food_hp": {"title": "🍖 Еда: здоровье", "emoji": "🍖", "price": 18, "weight": 1, "hp_restore": 40, "energy_restore": 0, "description": "Восстанавливает здоровье."},
        "food_energy": {"title": "🥤 Еда: энергия", "emoji": "🥤", "price": 18, "weight": 1, "hp_restore": 0, "energy_restore": 40, "description": "Восстанавливает энергию."},
        "food_mix": {"title": "🍲 Еда: смешанная", "emoji": "🍲", "price": 24, "weight": 1, "hp_restore": 28, "energy_restore": 28, "description": "Восстанавливает здоровье и энергию."},
    },
    "material": {
        "mat_light": {"title": "🪵 Материал: лёгкий", "emoji": "🪵", "price": 12, "weight": 1, "description": "Расходник для крафта."},
        "mat_heavy": {"title": "🪨 Материал: тяжёлый", "emoji": "🪨", "price": 18, "weight": 3, "description": "Тяжёлый ресурс для кузни."},
        "mat_rare": {"title": "💠 Материал: редкий", "emoji": "💠", "price": 26, "weight": 1, "description": "Редкий ресурс для продвинутого ремесла."},
    },
    "equipment": {
        "equip_head": {"title": "⛑ Голова: защита", "emoji": "⛑", "price": 85, "weight": 3, "slot": "head", "stats": {"defense": 6, "hp": 10}, "max_durability": 100, "description": "Шлем, усиливающий защиту."},
        "equip_body": {"title": "🦺 Тело: броня", "emoji": "🦺", "price": 100, "weight": 4, "slot": "body", "stats": {"defense": 8, "hp": 14}, "max_durability": 120, "description": "Броня для корпуса."},
        "equip_paws": {"title": "🧤 Лапы: атака", "emoji": "🧤", "price": 90, "weight": 2, "slot": "paws", "stats": {"attack": 7, "speed": 2}, "max_durability": 90, "description": "Боевые перчатки/накладки."},
        "equip_legs": {"title": "🥾 Ноги: скорость", "emoji": "🥾", "price": 90, "weight": 2, "slot": "legs", "stats": {"speed": 6, "hp": 8}, "max_durability": 90, "description": "Ускоряющее снаряжение."},
        "equip_accessory": {"title": "📿 Аксессуар: удача", "emoji": "📿", "price": 95, "weight": 1, "slot": "accessory", "stats": {"luck": 6, "energy": 8}, "max_durability": 80, "description": "Редкий аксессуар с бонусом удачи."},
    },
    "elixir": {
        "elixir_heal": {"title": "🧪 Эликсир лечения", "emoji": "🧪", "price": 34, "weight": 1, "hp_restore": 65, "description": "Мгновенно восстанавливает здоровье."},
        "elixir_energy": {"title": "⚗️ Эликсир энергии", "emoji": "⚗️", "price": 34, "weight": 1, "energy_restore": 65, "description": "Мгновенно восстанавливает энергию."},
        "elixir_rage": {"title": "🔥 Эликсир ярости", "emoji": "🔥", "price": 42, "weight": 1, "buffs": {"attack_pct": 10}, "description": "Даёт временный боевой бафф."},
    },
    "scroll": {
        "scroll_slots": {"title": "📜 Свиток сумки", "emoji": "📜", "price": 70, "weight": 1, "buffs": {"inventory_slots": 12}, "description": "Увеличивает вместимость инвентаря."},
        "scroll_weight": {"title": "🪶 Свиток веса", "emoji": "🪶", "price": 70, "weight": 1, "buffs": {"max_weight": 500}, "description": "Увеличивает лимит веса."},
        "scroll_gold": {"title": "✨ Свиток дохода", "emoji": "✨", "price": 78, "weight": 1, "buffs": {"gold_gain_pct": 8}, "description": "Повышает доход от активностей."},
    },
    "currency": {
        "currency_basic": {"title": "💰 Валюта", "emoji": "💰", "price": 1, "weight": 0, "description": "Пользовательская валюта/жетон."},
        "currency_token": {"title": "🎟 Токен", "emoji": "🎟", "price": 12, "weight": 0, "description": "Редкий жетон для ивентов."},
    },
    "recipe": {
        "recipe_book": {"title": "📘 Рецепт", "emoji": "📘", "price": 24, "weight": 1, "description": "Книга рецепта для ремесла."},
        "recipe_scroll": {"title": "🗒 Схема", "emoji": "🗒", "price": 28, "weight": 1, "description": "Схема для крафтовой станции."},
    },
}

CRAFT_STATIONS = {
    "craft": "Общий верстак",
    "kitchen": "Кухня",
    "forge": "Кузня",
    "alchemy": "Алхимия",
    "scribe": "Рунописец",
}


ITEM_EDITOR_FIELDS: dict[str, dict[str, Any]] = {
    'emoji': {'label': 'Смайлик', 'type': 'text'},
    'price': {'label': 'Цена', 'type': 'int'},
    'weight': {'label': 'Вес', 'type': 'int'},
    'slot': {'label': 'Слот экипировки', 'type': 'slot'},
    'hp_restore': {'label': 'Восстановление здоровья', 'type': 'int'},
    'energy_restore': {'label': 'Восстановление энергии', 'type': 'int'},
    'max_durability': {'label': 'Прочность', 'type': 'int'},
    'description': {'label': 'Описание', 'type': 'text'},
    'stats.hp': {'label': 'Статы: здоровье', 'type': 'int'},
    'stats.energy': {'label': 'Статы: энергия', 'type': 'int'},
    'stats.attack': {'label': 'Статы: атака', 'type': 'int'},
    'stats.defense': {'label': 'Статы: защита', 'type': 'int'},
    'stats.speed': {'label': 'Статы: скорость', 'type': 'int'},
    'stats.luck': {'label': 'Статы: удача', 'type': 'int'},
    'buffs.hp_pct': {'label': 'Эффекты: здоровье %', 'type': 'int'},
    'buffs.energy_pct': {'label': 'Эффекты: энергия %', 'type': 'int'},
    'buffs.attack_pct': {'label': 'Эффекты: атака %', 'type': 'int'},
    'buffs.defense_pct': {'label': 'Эффекты: защита %', 'type': 'int'},
    'buffs.speed_pct': {'label': 'Эффекты: скорость %', 'type': 'int'},
    'buffs.luck_pct': {'label': 'Эффекты: удача %', 'type': 'int'},
    'buffs.xp_pct': {'label': 'Эффекты: опыт %', 'type': 'int'},
    'buffs.gold_gain_pct': {'label': 'Эффекты: золото %', 'type': 'int'},
    'buffs.material_drop_pct': {'label': 'Эффекты: добыча материалов %', 'type': 'int'},
    'buffs.status_pct': {'label': 'Эффекты: сила состояний %', 'type': 'int'},
    'buffs.expedition_pct': {'label': 'Эффекты: экспедиции %', 'type': 'int'},
    'buffs.dungeon_pct': {'label': 'Эффекты: подземелья %', 'type': 'int'},
    'buffs.boss_damage_pct': {'label': 'Эффекты: урон по боссу %', 'type': 'int'},
    'buffs.inventory_slots': {'label': 'Эффекты: слоты инвентаря', 'type': 'int'},
    'buffs.max_weight': {'label': 'Эффекты: лимит веса', 'type': 'int'},
    'buffs.slots_plus': {'label': 'Эффекты: слоты сумки', 'type': 'int'},
    'buffs.weight_plus': {'label': 'Эффекты: переносимый вес', 'type': 'int'},
    'buffs.duration_min': {'label': 'Эффекты: длительность (мин)', 'type': 'int'},
    'buffs.steal': {'label': 'Эффекты: воровство', 'type': 'int'},
    'buffs.spy': {'label': 'Эффекты: шпионаж', 'type': 'int'},
    'buffs.gift_bonus': {'label': 'Эффекты: щедрый подарок', 'type': 'int'},
    'buffs.reroll': {'label': 'Эффекты: смена зверя', 'type': 'int'},
    'buffs.pet_token': {'label': 'Эффекты: жетон питомца', 'type': 'int'},
}

ITEM_EDITOR_ORDER = [
    'emoji', 'price', 'weight', 'slot', 'hp_restore', 'energy_restore', 'max_durability', 'description',
    'stats.hp', 'stats.energy', 'stats.attack', 'stats.defense', 'stats.speed', 'stats.luck',
    'buffs.hp_pct', 'buffs.energy_pct', 'buffs.attack_pct', 'buffs.defense_pct', 'buffs.speed_pct', 'buffs.luck_pct',
    'buffs.xp_pct', 'buffs.gold_gain_pct', 'buffs.material_drop_pct', 'buffs.status_pct', 'buffs.expedition_pct',
    'buffs.dungeon_pct', 'buffs.boss_damage_pct', 'buffs.inventory_slots', 'buffs.max_weight', 'buffs.slots_plus',
    'buffs.weight_plus', 'buffs.duration_min', 'buffs.steal', 'buffs.spy', 'buffs.gift_bonus', 'buffs.reroll', 'buffs.pet_token',
]


def parse_item_identity(item_id: int) -> tuple[str, int, int]:
    code = item_id // 10_000
    rarity = (item_id % 10_000) // 1_000
    seq = item_id % 1_000
    if code not in CATEGORY_BY_CODE:
        raise ValueError("Неизвестная принадлежность ID")
    if rarity not in range(1, 7):
        raise ValueError("Редкость в ID должна быть от 1 до 6")
    if seq <= 0:
        raise ValueError("Порядковый номер в ID должен быть больше 0")
    return CATEGORY_BY_CODE[code], rarity, seq


def scaled_template_data(template: dict[str, Any], rarity: int) -> dict[str, Any]:
    factor = 1 + (rarity - 1) * 0.35
    stats = {k: max(1, int(round(v * factor))) for k, v in (template.get("stats") or {}).items()}
    buffs = {k: max(1, int(round(v * factor))) for k, v in (template.get("buffs") or {}).items()}
    return {
        **template,
        "price": max(1, int(round(int(template.get("price", 1)) * (1 + (rarity - 1) * 0.55)))),
        "weight": int(template.get("weight", 1)),
        "stats": stats,
        "buffs": buffs,
        "hp_restore": max(0, int(round(int(template.get("hp_restore", 0)) * factor))),
        "energy_restore": max(0, int(round(int(template.get("energy_restore", 0)) * factor))),
        "max_durability": max(0, int(round(int(template.get("max_durability", 0)) * factor))),
    }


def register_runtime_item(item_data: dict[str, Any]) -> None:
    add_catalog_item(
        item_data["category"],
        int(item_data["rarity"]),
        int(item_data.get("seq", int(item_data["id"]) % 1000)),
        item_data["name"],
        emoji=item_data.get("emoji", "📦"),
        price=int(item_data.get("price", 1)),
        weight=int(item_data.get("weight", 1)),
        slot=item_data.get("slot"),
        stats=item_data.get("stats", {}),
        buffs=item_data.get("buffs", {}),
        hp_restore=int(item_data.get("hp_restore", 0)),
        energy_restore=int(item_data.get("energy_restore", 0)),
        max_durability=int(item_data.get("max_durability", 0)),
        description=item_data.get("description", ""),
        tags=item_data.get("tags", []),
    )


def register_runtime_recipe(recipe_data: dict[str, Any]) -> None:
    register_recipe(
        int(recipe_data["id"]),
        recipe_data["name"],
        int(recipe_data["result"]),
        int(recipe_data.get("result_amount", 1)),
        {int(k): int(v) for k, v in recipe_data.get("ingredients", {}).items()},
        station=recipe_data.get("station", "craft"),
        required_level=int(recipe_data.get("required_level", 1)),
    )


def load_runtime_custom_content() -> None:
    for item in load_custom_items():
        register_runtime_item(item)
    for recipe in load_custom_recipes():
        register_runtime_recipe(recipe)


load_runtime_custom_content()

# -----------------------------
# Общие утилиты
# -----------------------------

LAST_UI_MESSAGE: dict[tuple[int, int], int] = {}
LAST_PRIVATE_REPLY_KB: dict[int, float] = {}


def private_reply_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    kb.row(KeyboardButton('🏠 Меню'), KeyboardButton('👤 Профиль'), KeyboardButton('🎒 Инвентарь'))
    kb.row(KeyboardButton('⚔️ Арена'), KeyboardButton('🧭 Экспедиция'), KeyboardButton('🏰 Подземелье'))
    kb.row(KeyboardButton('🛒 Магазин'), KeyboardButton('📦 Рынок'), KeyboardButton('⚒ Крафт'))
    kb.row(KeyboardButton('🏦 Банк'), KeyboardButton('🎯 Задания'), KeyboardButton('🌍 Босс'))
    kb.row(KeyboardButton('🐾 Питомец'), KeyboardButton('⛺ Лагерь'), KeyboardButton('🐺 Стая'))
    kb.row(KeyboardButton('🏛 Фракция'), KeyboardButton('🧬 Таланты'), KeyboardButton('🧾 Контракты'))
    kb.row(KeyboardButton('✉️ Почта'), KeyboardButton('🏆 Топы'), KeyboardButton('🎁 Рефералка'))
    kb.row(KeyboardButton('📘 Инфо'))
    if OWNER_ID:
        kb.row(KeyboardButton('🔐 Админ'))
    return kb


def ensure_private_reply_keyboard(target, force: bool = False) -> None:
    try:
        if hasattr(target, 'message'):
            chat = target.message.chat
            user_id = target.from_user.id
        elif hasattr(target, 'chat') and hasattr(target, 'from_user'):
            chat = target.chat
            user_id = target.from_user.id
        else:
            return
        if chat.type != 'private':
            return
        now = time.time()
        if not force and now - LAST_PRIVATE_REPLY_KB.get(chat.id, 0) < 300:
            return
        msg = bot.send_message(chat.id, 'ㅤ', reply_markup=private_reply_keyboard())
        LAST_PRIVATE_REPLY_KB[chat.id] = now
        safe_delete(chat.id, msg.message_id, 1)
    except Exception:
        pass


def ui_key_for_target(target) -> tuple[int, int] | None:
    if hasattr(target, "message") and hasattr(target, "from_user"):
        return target.message.chat.id, target.from_user.id
    if hasattr(target, "chat") and hasattr(target, "from_user"):
        return target.chat.id, target.from_user.id
    return None


def remember_ui_message(chat_id: int, user_id: int, message_id: int) -> None:
    LAST_UI_MESSAGE[(chat_id, user_id)] = message_id


def normalize_lookup(text: str) -> str:
    text = (text or '').lower().replace('ё', 'е')
    text = re.sub(r'[^a-zа-я0-9_\s-]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def strip_target_tokens(text: str, remove_numeric_ids: bool = False) -> str:
    text = re.sub(r'@[A-Za-z0-9_]{4,}', ' ', text)
    if remove_numeric_ids:
        text = re.sub(r'\b\d{6,12}\b', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def resolve_item_query(query: str, categories: list[str] | None = None) -> tuple[dict[str, Any] | None, str | None]:
    query = (query or '').strip()
    if not query:
        return None, 'Не указано название предмета.'
    if query.isdigit() and int(query) in ITEMS:
        item = get_item(int(query))
        if categories and item['category'] not in categories:
            return None, 'Этот предмет не подходит для выбранного действия.'
        return item, None
    nq = normalize_lookup(query)
    alias_map = {
        'монета': CURRENCY_ID, 'монеты': CURRENCY_ID, 'монета стаи': CURRENCY_ID, 'валюта': CURRENCY_ID, 'золото': CURRENCY_ID,
        'материал': None, 'материалы': None, 'ресурс': None, 'ресурсы': None,
    }
    if nq in alias_map and alias_map[nq]:
        item = get_item(alias_map[nq])
        if categories and item['category'] not in categories:
            return None, 'Этот предмет не подходит для выбранного действия.'
        return item, None
    pool = [item for item in ITEMS.values() if not categories or item['category'] in categories]
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in pool:
        hay = normalize_lookup(item['name'] + ' ' + item.get('category_name', '') + ' ' + ' '.join(item.get('tags', [])))
        if nq == normalize_lookup(item['name']):
            scored.append((0, item))
        elif hay.startswith(nq):
            scored.append((1, item))
        elif nq in hay:
            scored.append((2, item))
        else:
            words = [w for w in nq.split() if w]
            if words and all(w in hay for w in words):
                scored.append((3, item))
    scored.sort(key=lambda row: (row[0], row[1]['category'], row[1]['rarity'], row[1]['name']))
    if not scored:
        return None, 'Предмет не найден.'
    best_score = scored[0][0]
    best = [item for score, item in scored if score == best_score]
    if len(best) == 1 or best_score == 0:
        return best[0], None
    variants = '\n'.join([f"• {item['emoji']} {item['name']} [{item['id']}]" for item in best[:6]])
    return None, 'Найдено несколько предметов. Уточни название:\n' + variants


def resolve_pack_query(query: str) -> tuple[dict[str, Any] | None, str | None]:
    query = (query or '').strip()
    if not query:
        return None, 'Не указано название пака.'
    rows = list_packs()
    nq = normalize_lookup(query)
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in rows:
        code = normalize_lookup(str(row['code']))
        name = normalize_lookup(str(row['name']))
        full = f"{code} {name}"
        if nq == code or nq == name:
            scored.append((0, row))
        elif full.startswith(nq):
            scored.append((1, row))
        elif nq in full:
            scored.append((2, row))
    scored.sort(key=lambda row: (row[0], row[1].get('price_stars', 0), row[1]['name']))
    if not scored:
        return None, 'Пак не найден.'
    best_score = scored[0][0]
    best = [row for score, row in scored if score == best_score]
    if len(best) == 1 or best_score == 0:
        return best[0], None
    variants = '\n'.join([f"• {row['name']} ({row['code']})" for row in best[:6]])
    return None, 'Найдено несколько паков. Уточни название:\n' + variants


def parse_amount_and_item_query(raw_text: str, verbs: list[str] | None = None, categories: list[str] | None = None) -> tuple[dict[str, Any] | None, int | None, str | None]:
    text = strip_target_tokens(raw_text)
    lower = text.lower()
    for verb in verbs or []:
        lower = re.sub(rf'\b{re.escape(verb)}\b', ' ', lower)
    lower = re.sub(r'\s+', ' ', lower).strip(' ,.-')
    nums = [int(n) for n in re.findall(r'\b\d+\b', lower)]
    explicit_item = next((n for n in nums if n in ITEMS and (not categories or get_item(n)['category'] in categories)), None)
    if explicit_item:
        amount = next((n for n in nums if n != explicit_item), 1)
        return get_item(explicit_item), amount, None
    m = re.search(r'\b(\d+)\b', lower)
    amount = 1
    if m:
        amount = int(m.group(1))
        lower = (lower[:m.start()] + ' ' + lower[m.end():]).strip()
    query = lower.strip(' ,.-')
    item, err = resolve_item_query(query, categories)
    if err:
        return None, None, err
    return item, amount, None


def parse_target_and_amount(message: Message, text: str, default_amount: int = 1) -> tuple[dict[str, Any] | None, int]:
    target = resolve_target_from_message(message, text)
    cleaned = strip_target_tokens(text, remove_numeric_ids=True)
    nums = [int(n) for n in re.findall(r'\b\d+\b', cleaned)]
    amount = nums[0] if nums else default_amount
    return target, amount


def parse_target_amount_and_item(message: Message, text: str, default_amount: int = 1, verbs: list[str] | None = None, categories: list[str] | None = None) -> tuple[dict[str, Any] | None, dict[str, Any] | None, int | None, str | None]:
    target = resolve_target_from_message(message, text)
    item, amount, err = parse_amount_and_item_query(text, verbs=verbs, categories=categories)
    if err:
        return target, None, None, err
    return target, item, (amount or default_amount), None


def target_label(player: dict[str, Any] | None) -> str:
    if not player:
        return '—'
    return get_display_name(int(player['user_id']))


def full_name_from_user(user) -> str:
    parts = [user.first_name or "", user.last_name or ""]
    return " ".join([p for p in parts if p]).strip() or f"id{user.id}"


LAST_REPLY_KEYBOARD_CLEAR: dict[tuple[int, int], float] = {}


def clear_stale_reply_keyboard(target, force: bool = False) -> None:
    """Удаляет старую reply-клавиатуру, если она осталась от прошлых версий бота.

    Telegram хранит reply-клавиатуру на стороне клиента, поэтому одной смены кода мало.
    Нужно один раз отправить сообщение с ReplyKeyboardRemove, после чего клавиатура исчезнет.
    Сообщение сразу удаляется, чтобы не засорять чат.
    """
    try:
        if hasattr(target, 'message'):
            chat_id = target.message.chat.id
            user_id = target.from_user.id
        elif hasattr(target, 'chat') and hasattr(target, 'from_user'):
            chat_id = target.chat.id
            user_id = target.from_user.id
        else:
            return
        key = (chat_id, user_id)
        now = time.time()
        if not force and now - LAST_REPLY_KEYBOARD_CLEAR.get(key, 0) < 300:
            return
        msg = bot.send_message(chat_id, 'ㅤ', reply_markup=ReplyKeyboardRemove())
        LAST_REPLY_KEYBOARD_CLEAR[key] = now
        safe_delete(chat_id, msg.message_id, 1)
    except Exception:
        pass


def safe_delete(chat_id: int, message_id: int, delay: int = 0) -> None:
    def _work() -> None:
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass
    if delay <= 0:
        _work()
    else:
        threading.Timer(delay, _work).start()


def send_temp(chat_id: int, text: str, ttl: int = 40, reply_to_message_id: int | None = None, markup=None):
    msg = bot.send_message(chat_id, text, reply_to_message_id=reply_to_message_id, reply_markup=markup)
    safe_delete(chat_id, msg.message_id, ttl)
    return msg


def answer_cb(call, text: str = "") -> None:
    try:
        bot.answer_callback_query(call.id, text)
    except Exception:
        pass


def edit_or_send(target, text: str, markup: InlineKeyboardMarkup | None = None):
    try:
        if hasattr(target, "message"):
            bot.edit_message_text(text, target.message.chat.id, target.message.message_id, reply_markup=markup)
            remember_ui_message(target.message.chat.id, target.from_user.id, target.message.message_id)
            return
    except Exception:
        pass
    key = ui_key_for_target(target)
    if key:
        chat_id, user_id = key
        prev_id = LAST_UI_MESSAGE.get((chat_id, user_id))
        if prev_id:
            try:
                bot.edit_message_text(text, chat_id, prev_id, reply_markup=markup)
                return
            except Exception:
                pass
        msg = bot.send_message(chat_id, text, reply_markup=markup)
        remember_ui_message(chat_id, user_id, msg.message_id)
        return
    if hasattr(target, "chat"):
        bot.send_message(target.chat.id, text, reply_markup=markup)
    else:
        bot.send_message(target.message.chat.id, text, reply_markup=markup)


def sync_user(message: Message) -> None:
    if not player_exists(message.from_user.id):
        create_player(message.from_user.id, message.from_user.username or "", full_name_from_user(message.from_user), 0)
    touch_identity(message.from_user.id, message.from_user.username or "", full_name_from_user(message.from_user))


def stats_for_user(user_id: int) -> dict[str, Any]:
    p = get_player(user_id) or {}
    return effective_profile(p, get_equipment(user_id), get_buffs(user_id), get_player_extras(user_id))


def extras_for_user(user_id: int) -> dict[str, Any]:
    return get_player_extras(user_id)


def is_private_target(target) -> bool:
    if hasattr(target, "chat"):
        return getattr(target.chat, "type", "") == "private"
    if hasattr(target, "message") and hasattr(target.message, "chat"):
        return getattr(target.message.chat, "type", "") == "private"
    return False


def category_title_ru(key: str) -> str:
    return CATEGORY_NAMES.get(key, str(key).replace('_', ' '))


def group_hub_text() -> str:
    return (
        f"{GAME_TITLE} <b>{VERSION}</b>\n"
        f"В групповом чате управление сделано в основном текстом, а inline-кнопки появляются только на активной карточке дуэли.\n\n"
        f"<b>Быстрые команды:</b> /p /inv /pvp /mk /top /info\n"
        f"<b>По-русски тоже работает:</b> профиль, инвентарь, пвп, рынок, топ, инфо\n\n"
        f"<b>Дуэль:</b> <code>пвп @username</code> или ответь на сообщение словом <code>дуэль</code>.\n"
        f"<b>Принятие:</b> ответь на карточку дуэли словом <code>принять</code> или <code>отклонить</code>.\n"
        f"<b>Ставка:</b> ответь на карточку дуэли сообщением <code>ставка 50 монет @username</code>."
    )


def resolve_pvp_request_for_bet(message: Message) -> dict[str, Any] | None:
    if message.reply_to_message:
        req = get_pvp_request_by_message(message.chat.id, message.reply_to_message.message_id)
        if req:
            return req
    return get_latest_chat_pvp(message.chat.id)


def resolve_pending_pvp_request(message: Message) -> dict[str, Any] | None:
    if message.reply_to_message:
        req = get_pvp_request_by_message(message.chat.id, message.reply_to_message.message_id)
        if req and req.get('status') == 'pending':
            return req
    return get_latest_chat_pvp(message.chat.id)


def resolve_target_from_message(message: Message, text: str | None = None) -> dict[str, Any] | None:
    if message.reply_to_message and message.reply_to_message.from_user:
        return get_player(message.reply_to_message.from_user.id)
    src = text or (message.text or "")
    m = re.search(r"@([A-Za-z0-9_]{4,})", src)
    if m:
        return get_player_by_username(m.group(1))
    nums = re.findall(r"\b\d{6,12}\b", src)
    if nums:
        return get_player(int(nums[-1]))
    return None


def parse_json_safe(value: Any, default: Any):
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def request_stake_payload(req: dict[str, Any]) -> list[dict[str, Any]]:
    return parse_json_safe(req.get('stake_payload_json'), [])


def stake_payload_text(payload: list[dict[str, Any]]) -> str:
    if not payload:
        return 'без ставки'
    return ' + '.join(format_item_line(int(row['item_id']), int(row['amount'])) for row in payload)


def reserve_payload(user_id: int, payload: list[dict[str, Any]]) -> tuple[bool, str]:
    if not payload:
        return True, 'Без ставки.'
    for row in payload:
        if get_item_amount(user_id, int(row['item_id'])) < int(row['amount']):
            return False, f'Не хватает для ставки: {format_item_line(int(row["item_id"]), int(row["amount"]))}'
    for row in payload:
        remove_item(user_id, int(row['item_id']), int(row['amount']))
    return True, 'Ставка зарезервирована.'


def refund_payload(user_id: int, payload: list[dict[str, Any]]) -> None:
    for row in payload:
        add_item(user_id, int(row['item_id']), int(row['amount']))


def pvp_request_markup(req: dict[str, Any]) -> InlineKeyboardMarkup:
    req_id = int(req['id'])
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton('✅ Принять', callback_data=f'pvp:accept:{req_id}'), InlineKeyboardButton('❌ Отклонить', callback_data=f'pvp:decline:{req_id}'))
    kb.add(InlineKeyboardButton(f'📈 Ставка на {get_display_name(int(req["from_user"]))}', callback_data=f'pvp:bet:{req_id}:{int(req["from_user"])}'))
    kb.add(InlineKeyboardButton(f'📉 Ставка на {get_display_name(int(req["to_user"]))}', callback_data=f'pvp:bet:{req_id}:{int(req["to_user"])}'))
    return kb


def render_pvp_card(req_id: int, for_private: bool = False) -> tuple[str, InlineKeyboardMarkup | None]:
    req = get_pvp_request(req_id)
    if not req:
        return 'Дуэль не найдена.', None
    a = get_player(int(req['from_user'])) or {}
    d = get_player(int(req['to_user'])) or {}
    bets = get_pvp_bets(req_id)
    payload = request_stake_payload(req)
    bet_lines: list[str] = []
    if bets:
        grouped: dict[tuple[int, int], int] = {}
        for bet in bets:
            key = (int(bet['pick_user']), int(bet['item_id']))
            grouped[key] = grouped.get(key, 0) + int(bet['amount'])
        for (pick_user, item_id), amount in list(grouped.items())[:8]:
            item = get_item(item_id)
            bet_lines.append(f"• на {get_display_name(pick_user)}: {item['emoji']} {item['name']} x{amount}")
    else:
        bet_lines.append('• Ставок пока нет.')
    lines = [
        f"⚔️ <b>Дуэль #{req_id}</b>",
        f"{get_display_name(int(req['from_user']))} — рейтинг {int(a.get('rating', 1000))} · {league_name(int(a.get('rating', 1000)))}",
        "против",
        f"{get_display_name(int(req['to_user']))} — рейтинг {int(d.get('rating', 1000))} · {league_name(int(d.get('rating', 1000)))}",
        "",
        f"Статус: {'ожидание ответа' if req.get('status') == 'pending' else req.get('status')}",
        f"Ставка дуэлянтов: <b>{stake_payload_text(payload)}</b>",
        "Режим боя: пошаговый. Кнопки появляются на карточке боя по очереди.",
        f"За бой можно использовать не больше {BATTLE_ITEM_LIMIT} предметов на каждого зверя и не больше одного предмета за ход.",
        f"Ставки зрителей: комиссия {int(PVP_BET_COMMISSION_RATE * 100)}% · доля победителю {int(PVP_WINNER_BET_SHARE_RATE * 100)}%",
        "Разрешены: валюта и материалы.",
        "",
        "<b>Текущие ставки:</b>",
        *bet_lines,
    ]
    text = "\n".join(lines)
    return text, pvp_request_markup(req)


def battle_state_key(req_id: int) -> str:
    return f'pvp_battle:{req_id}'


def get_battle_state(req_id: int) -> dict[str, Any] | None:
    return get_world_state(battle_state_key(req_id), None)


def save_battle_state(req_id: int, state: dict[str, Any]) -> None:
    set_world_state(battle_state_key(req_id), state)


def clear_battle_state(req_id: int) -> None:
    set_world_state(battle_state_key(req_id), {})


def battle_opponent(battle: dict[str, Any], user_id: int) -> int:
    return int(battle['to_user']) if int(battle['from_user']) == int(user_id) else int(battle['from_user'])


def battle_actor_line(battle: dict[str, Any], user_id: int) -> str:
    hp = int(battle['hp'][str(user_id)])
    en = int(battle['energy'][str(user_id)])
    st = battle['stats'][str(user_id)]
    statuses = battle['statuses'].get(str(user_id), {})
    status_parts = []
    if statuses.get('bleed', 0):
        status_parts.append(f"кровотечение {statuses['bleed']}")
    if statuses.get('poison', 0):
        status_parts.append(f"яд {statuses['poison']}")
    if statuses.get('stun', 0):
        status_parts.append(f"оглушение {statuses['stun']}")
    if statuses.get('shield', 0):
        status_parts.append(f"щит {statuses['shield']}")
    suffix = f" · эффекты: {', '.join(status_parts)}" if status_parts else ''
    return f"• {get_display_name(user_id)} — ❤️ {hp}/{st['max_hp']} · ⚡ {en}/{st['max_energy']}{suffix}"


def battle_action_markup(battle: dict[str, Any], item_menu: bool = False, page: int = 0) -> InlineKeyboardMarkup | None:
    if battle.get('status') != 'active':
        return None
    req_id = int(battle['req_id'])
    kb = InlineKeyboardMarkup(row_width=2)
    actor_id = int(battle['turn_user'])
    if item_menu:
        inv = [r for r in get_inventory(actor_id) if r['item']['category'] in {'food', 'elixir', 'scroll'} and int(r['amount']) > 0]
        per_page = 6
        chunk = inv[page*per_page:(page+1)*per_page]
        for row in chunk:
            item = row['item']
            kb.add(InlineKeyboardButton(f"{item['emoji']} {item['name']} x{row['amount']}", callback_data=f"pvp:itempick:{req_id}:{int(row['item_id'])}"))
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton('◀️', callback_data=f'pvp:itemmenu:{req_id}:{page-1}'))
        if (page + 1) * per_page < len(inv):
            nav.append(InlineKeyboardButton('▶️', callback_data=f'pvp:itemmenu:{req_id}:{page+1}'))
        if nav:
            kb.row(*nav)
        kb.add(InlineKeyboardButton('⬅️ Назад к ходу', callback_data=f'pvp:back:{req_id}'))
        return kb
    kb.add(InlineKeyboardButton('⚔️ Ударить', callback_data=f'pvp:hit:{req_id}'), InlineKeyboardButton('🛡 Пропустить', callback_data=f'pvp:skip:{req_id}'))
    kb.add(InlineKeyboardButton('🧪 Применить предмет', callback_data=f'pvp:itemmenu:{req_id}:0'), InlineKeyboardButton('🏳️ Сдаться', callback_data=f'pvp:surrender:{req_id}'))
    return kb


def render_battle_text(battle: dict[str, Any], item_menu: bool = False) -> str:
    req = get_pvp_request(int(battle['req_id'])) or {}
    left = battle_actor_line(battle, int(battle['from_user']))
    right = battle_actor_line(battle, int(battle['to_user']))
    turn_user = int(battle['turn_user'])
    left_items = int(battle['items_used'].get(str(turn_user), 0))
    time_left = max(0, int(battle['expires_at']) - now_ts())
    lines = [
        f"⚔️ <b>Пошаговая дуэль #{battle['req_id']}</b>",
        left,
        right,
        '',
        f"Ход: <b>{get_display_name(turn_user)}</b>",
        f"Предметов использовано этим бойцом: {left_items}/{BATTLE_ITEM_LIMIT}",
        f"До автоматического завершения: {format_seconds(time_left)}",
        f"Ставка дуэлянтов: {stake_payload_text(request_stake_payload(req))}",
    ]
    if item_menu:
        lines.append('')
        lines.append('<b>Выбери предмет из инвентаря</b>')
        lines.append('За ход можно применить только один предмет. За весь бой — не более двух.')
    if battle.get('log'):
        lines.append('')
        lines.append('<b>Последние действия</b>')
        for row in battle['log'][-6:]:
            lines.append('• ' + row)
    return "\n".join(lines)


def apply_battle_status(battle: dict[str, Any], user_id: int) -> list[str]:
    logs = []
    st = battle['statuses'].setdefault(str(user_id), {})
    hp = int(battle['hp'][str(user_id)])
    max_hp = int(battle['stats'][str(user_id)]['max_hp'])
    enemy_id = battle_opponent(battle, user_id)
    enemy_stats = battle['stats'][str(enemy_id)]
    if int(st.get('bleed', 0)) > 0:
        dmg = max(2, max_hp // 38)
        hp = max(0, hp - dmg)
        st['bleed'] = max(0, int(st['bleed']) - 1)
        logs.append(f'{get_display_name(user_id)} теряет {dmg} HP от кровотечения.')
    if int(st.get('poison', 0)) > 0:
        dmg = max(3, int(enemy_stats.get('luck', 0)) // 6)
        hp = max(0, hp - dmg)
        st['poison'] = max(0, int(st['poison']) - 1)
        logs.append(f'{get_display_name(user_id)} получает {dmg} урона от яда.')
    battle['hp'][str(user_id)] = hp
    return logs


def battle_switch_turn(battle: dict[str, Any]) -> None:
    battle['turn_user'] = battle_opponent(battle, int(battle['turn_user']))
    battle['turn_no'] = int(battle.get('turn_no', 1)) + 1
    battle['turn_item_used'] = False


def battle_attack(battle: dict[str, Any], actor_id: int) -> list[str]:
    import random as _r
    logs = []
    target_id = battle_opponent(battle, actor_id)
    actor_stats = battle['stats'][str(actor_id)]
    target_stats = battle['stats'][str(target_id)]
    actor_status = battle['statuses'].setdefault(str(actor_id), {})
    target_status = battle['statuses'].setdefault(str(target_id), {})
    if int(actor_status.get('stun', 0)) > 0:
        actor_status['stun'] = max(0, int(actor_status['stun']) - 1)
        logs.append(f'{get_display_name(actor_id)} оглушён и пропускает ход.')
        battle_switch_turn(battle)
        return logs
    rnd = _r.Random(now_ts() + actor_id + target_id + int(battle.get('turn_no', 1)) * 17)
    dodge_chance = min(0.22, target_stats['speed'] / (actor_stats['speed'] + target_stats['speed'] + 140))
    if rnd.random() < dodge_chance:
        logs.append(f'{get_display_name(target_id)} уклоняется от атаки.')
        battle['energy'][str(actor_id)] = max(0, int(battle['energy'][str(actor_id)]) - 6)
        battle_switch_turn(battle)
        return logs
    char_key = battle['characters'].get(str(actor_id), 'wolf')
    extra = 0
    if char_key == 'wolf':
        extra = max(1, actor_stats['attack'] // 9)
        if rnd.random() < 0.34:
            target_status['bleed'] = max(int(target_status.get('bleed', 0)), 2)
            logs.append('🐺 Когти волка вызвали кровотечение.')
    elif char_key == 'lion':
        extra = max(2, actor_stats['attack'] // 7)
        if rnd.random() < 0.22:
            target_status['stun'] = max(int(target_status.get('stun', 0)), 1)
            logs.append('🦁 Рёв льва оглушает цель.')
    elif char_key == 'fox':
        extra = max(1, actor_stats['speed'] // 8)
        if rnd.random() < 0.28:
            target_status['poison'] = max(int(target_status.get('poison', 0)), 2)
            logs.append('🦊 Лиса оставляет ядовитый след.')
    elif char_key == 'bear':
        extra = max(1, actor_stats['defense'] // 10)
        actor_status['shield'] = max(int(actor_status.get('shield', 0)), 1)
        logs.append('🐻 Медведь поднимает щит ярости.')
    elif char_key == 'eagle':
        extra = max(1, actor_stats['luck'] // 7)
        logs.append('🦅 Орёл находит уязвимое место.')
    elif char_key == 'crocodile':
        extra = max(1, actor_stats['defense'] // 11)
        if rnd.random() < 0.18:
            target_status['stun'] = max(int(target_status.get('stun', 0)), 1)
            logs.append('🐊 Захват крокодила сбивает противника с темпа.')
    elif char_key == 'rhino':
        extra = max(1, actor_stats['defense'] // 8)
        logs.append('🦏 Носорог проламывает защиту.')
    base = actor_stats['attack'] - target_stats['defense'] * (0.32 if char_key == 'rhino' else 0.45)
    crit = rnd.random() < min(0.30, actor_stats['luck'] / 190)
    dmg = max(4, int(base + extra + rnd.randint(1, max(4, actor_stats['speed'] // 7))))
    if int(target_status.get('shield', 0)) > 0:
        dmg = int(dmg * 0.76)
        target_status['shield'] = max(0, int(target_status['shield']) - 1)
        logs.append('🛡 Часть удара поглотил щит.')
    if crit:
        dmg = int(dmg * 1.55)
        logs.append('💥 Критический удар!')
    battle['hp'][str(target_id)] = max(0, int(battle['hp'][str(target_id)]) - dmg)
    battle['energy'][str(actor_id)] = max(0, int(battle['energy'][str(actor_id)]) - 10)
    logs.append(f'{get_display_name(actor_id)} наносит {dmg} урона {get_display_name(target_id)}.')
    battle_switch_turn(battle)
    return logs


def battle_use_item(battle: dict[str, Any], actor_id: int, item_id: int) -> tuple[bool, str]:
    if battle.get('turn_item_used'):
        return False, 'За этот ход уже применён предмет.'
    used = int(battle['items_used'].get(str(actor_id), 0))
    if used >= BATTLE_ITEM_LIMIT:
        return False, f'Лимит предметов на бой: {BATTLE_ITEM_LIMIT}.'
    item = get_item(item_id)
    if item['category'] not in {'food', 'elixir', 'scroll'}:
        return False, 'В бою можно применять только еду, эликсиры и свитки.'
    if get_item_amount(actor_id, item_id) <= 0:
        return False, 'Предмет закончился.'
    remove_item(actor_id, item_id, 1)
    hp = int(battle['hp'][str(actor_id)])
    en = int(battle['energy'][str(actor_id)])
    st = battle['stats'][str(actor_id)]
    hp = min(int(st['max_hp']), hp + int(item.get('hp_restore', 0)))
    en = min(int(st['max_energy']), en + int(item.get('energy_restore', 0)))
    battle['hp'][str(actor_id)] = hp
    battle['energy'][str(actor_id)] = en
    battle['items_used'][str(actor_id)] = used + 1
    battle['turn_item_used'] = True
    buffs = item.get('buffs', {}) or {}
    if buffs:
        duration = max(BATTLE_TURN_SEC * 2, int(buffs.get('duration_min', 10)) * 60)
        for key, value in buffs.items():
            if key == 'duration_min' or not value:
                continue
            if key in {'attack_pct', 'defense_pct', 'speed_pct', 'luck_pct', 'hp_pct', 'energy_pct', 'dungeon_pct', 'expedition_pct'}:
                add_buff(actor_id, key, int(value), duration, item_id)
        battle['stats'][str(actor_id)] = stats_for_user(actor_id)
    battle['log'].append(f'{get_display_name(actor_id)} использует {item["name"]}.')
    battle_switch_turn(battle)
    return True, f'Использован {item["name"]}.'


def build_battle_from_request(req_id: int) -> tuple[bool, str, dict[str, Any] | None]:
    req = get_pvp_request(req_id)
    if not req or req.get('status') != 'pending':
        return False, 'Дуэль уже недоступна.', None
    a_uid = int(req['from_user'])
    d_uid = int(req['to_user'])
    a = get_player(a_uid)
    d = get_player(d_uid)
    if not a or not d:
        return False, 'Один из игроков не найден.', None
    if get_death_remaining(a_uid) > 0 or get_death_remaining(d_uid) > 0:
        return False, 'Один из бойцов ещё восстанавливается после поражения.', None
    payload = request_stake_payload(req)
    if payload:
        ok, msg = reserve_payload(d_uid, payload)
        if not ok:
            refund_payload(a_uid, payload)
            from user_data import set_pvp_request_status
            set_pvp_request_status(req_id, 'declined')
            return False, 'Соперник не смог покрыть ставку. Ставка инициатора возвращена.', None
    a_stats = stats_for_user(a_uid)
    d_stats = stats_for_user(d_uid)
    battle = {
        'req_id': req_id,
        'from_user': a_uid,
        'to_user': d_uid,
        'turn_user': a_uid if a_stats['speed'] >= d_stats['speed'] else d_uid,
        'turn_no': 1,
        'started_at': now_ts(),
        'expires_at': now_ts() + BATTLE_MAX_SEC,
        'status': 'active',
        'hp': {str(a_uid): int(a_stats['max_hp']), str(d_uid): int(d_stats['max_hp'])},
        'energy': {str(a_uid): int(a_stats['max_energy']), str(d_uid): int(d_stats['max_energy'])},
        'stats': {str(a_uid): a_stats, str(d_uid): d_stats},
        'characters': {str(a_uid): a.get('character_key', 'wolf'), str(d_uid): d.get('character_key', 'wolf')},
        'statuses': {str(a_uid): {}, str(d_uid): {}},
        'items_used': {str(a_uid): 0, str(d_uid): 0},
        'turn_item_used': False,
        'log': ['Дуэль началась.'],
    }
    save_battle_state(req_id, battle)
    from user_data import set_pvp_request_status
    set_pvp_request_status(req_id, 'active')
    return True, 'Бой начался.', battle


def finish_battle(req_id: int, winner_id: int, loser_id: int, reason: str) -> tuple[str, None]:
    req = get_pvp_request(req_id) or {}
    from user_data import set_pvp_request_status, add_xp, advance_task
    set_pvp_request_status(req_id, 'done')
    add_win(winner_id)
    add_loss(loser_id)
    add_gold(winner_id, 28)
    add_gold(loser_id, 7)
    add_xp(winner_id, 55)
    add_xp(loser_id, 18)
    advance_task(winner_id, 'pvp', 1)
    advance_task(loser_id, 'pvp', 1)
    set_cooldown(winner_id, 'pvp', COOLDOWN_PVP)
    set_cooldown(loser_id, 'pvp', COOLDOWN_PVP)
    set_dead_until(loser_id, now_ts() + COOLDOWN_DEATH)
    payload = request_stake_payload(req)
    stake_lines = []
    if payload:
        for row in payload:
            add_item(winner_id, int(row['item_id']), int(row['amount']) * 2)
            stake_lines.append('• Дуэльная ставка: ' + format_item_line(int(row['item_id']), int(row['amount']) * 2))
    bets_result = settle_pvp_bets(req_id, winner_id)
    bet_lines = []
    for row in bets_result.get('hero_share', [])[:5]:
        bet_lines.append('• Победитель получил со ставок: ' + format_item_line(int(row['item_id']), int(row['amount'])))
    if bets_result.get('bettors'):
        bet_lines.append(f"• Победивших ставок выплачено: {len(bets_result['bettors'])}")
    if not bet_lines:
        bet_lines.append('• Выплат по ставкам не было.')
    clear_battle_state(req_id)
    lines = [
        '⚔️ <b>Дуэль завершена</b>',
        f'Причина: {reason}',
        f'Победитель: {get_display_name(winner_id)}',
        f'Проигравший: {get_display_name(loser_id)}',
        '',
        '<b>Награды победителя</b>',
        *(stake_lines if stake_lines else ['• Ставка дуэлянтов не назначалась.']),
        '',
        '<b>Ставки зрителей</b>',
        *bet_lines,
    ]
    return "\n".join(lines), None


def battle_timeout_winner(battle: dict[str, Any]) -> tuple[int, int, str]:
    a = int(battle['from_user'])
    d = int(battle['to_user'])
    a_hp = int(battle['hp'][str(a)])
    d_hp = int(battle['hp'][str(d)])
    if a_hp != d_hp:
        return (a, d, 'Время боя вышло.') if a_hp > d_hp else (d, a, 'Время боя вышло.')
    a_en = int(battle['energy'][str(a)])
    d_en = int(battle['energy'][str(d)])
    if a_en != d_en:
        return (a, d, 'Время боя вышло.') if a_en > d_en else (d, a, 'Время боя вышло.')
    return (a, d, 'Время боя вышло, победитель определён по инициативе.') if int(battle['stats'][str(a)]['speed']) >= int(battle['stats'][str(d)]['speed']) else (d, a, 'Время боя вышло, победитель определён по инициативе.')


def update_battle_message(target, req_id: int, item_menu: bool = False, page: int = 0) -> None:
    battle = get_battle_state(req_id)
    if not battle:
        return
    if int(battle.get('expires_at', 0)) <= now_ts():
        winner, loser, reason = battle_timeout_winner(battle)
        text, markup = finish_battle(req_id, winner, loser, reason)
        req = get_pvp_request(req_id) or {}
        try:
            if int(req.get('chat_id', 0)) and int(req.get('message_id', 0)):
                bot.edit_message_text(text, int(req['chat_id']), int(req['message_id']), reply_markup=None)
                return
        except Exception:
            pass
        edit_or_send(target, text, None)
        return
    text = render_battle_text(battle, item_menu=item_menu)
    markup = battle_action_markup(battle, item_menu=item_menu, page=page)
    req = get_pvp_request(req_id) or {}
    try:
        if int(req.get('chat_id', 0)) and int(req.get('message_id', 0)):
            bot.edit_message_text(text, int(req['chat_id']), int(req['message_id']), reply_markup=markup)
            return
    except Exception:
        pass
    edit_or_send(target, text, markup)


def start_pvp_battle(target, req_id: int) -> None:
    ok, msg, battle = build_battle_from_request(req_id)
    if not ok:
        edit_or_send(target, msg, None)
        return
    update_battle_message(target, req_id)

def owner_alert(text: str) -> None:
    try:
        bot.send_message(OWNER_ID, f"🚨 <b>Подозрение</b>\n{text}")
    except Exception:
        pass


def maintenance() -> None:
    close_due_auctions()
    close_expired_market()
    close_expired_buy_orders()
    apply_overdue_loans()
    for row in list_suspicions(only_unsent=True, limit=10):
        owner_alert(f"Игрок: {get_display_name(int(row['user_id']))}\nПричина: {row['reason']}\nДетали: {row['details']}")
        mark_suspicion_sent(int(row["id"]))


def item_template_keyboard(category: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for code, template in ITEM_TEMPLATE_PRESETS.get(category, {}).items():
        kb.add(InlineKeyboardButton(template['title'], callback_data=f'adminitemtpl:{code}'))
    kb.add(InlineKeyboardButton('❌ Отмена', callback_data='adminitemtpl:cancel'))
    return kb


def craft_station_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for code, title in CRAFT_STATIONS.items():
        kb.add(InlineKeyboardButton(title, callback_data=f'admincraftstation:{code}'))
    kb.add(InlineKeyboardButton('❌ Отмена', callback_data='admincraftstation:cancel'))
    return kb




def _draft_get(draft: dict[str, Any], field: str):
    if '.' not in field:
        return draft.get(field)
    root, key = field.split('.', 1)
    return (draft.get(root) or {}).get(key)


def _draft_set(draft: dict[str, Any], field: str, value) -> None:
    if '.' not in field:
        if field == 'slot':
            draft[field] = value or None
        elif field in {'description', 'emoji'}:
            draft[field] = str(value) if value is not None else ''
        else:
            draft[field] = int(value or 0)
        return
    root, key = field.split('.', 1)
    bucket = dict(draft.get(root) or {})
    if value in (None, '', 0):
        bucket.pop(key, None)
    else:
        bucket[key] = int(value)
    draft[root] = bucket


def custom_item_editor_text(draft: dict[str, Any]) -> str:
    item_id = int(draft['id'])
    category = draft.get('category', '')
    rarity = int(draft.get('rarity', 1))
    parts = [
        f"🧩 <b>Редактор предмета</b>",
        f"{draft.get('emoji', '📦')} <b>{draft.get('name', 'Без названия')}</b> [{item_id}]",
        f"Тип: {CATEGORY_NAMES.get(category, category)} · редкость {RARITY_NAMES.get(rarity, rarity)}",
        f"Цена: {int(draft.get('price', 0))} · Вес: {int(draft.get('weight', 0))}",
    ]
    if draft.get('slot'):
        parts.append(f"Слот: {SLOT_TITLES.get(draft['slot'], draft['slot'])}")
    if draft.get('stats'):
        parts.append('Статы: ' + format_bonus_dict(draft['stats']))
    if draft.get('buffs'):
        parts.append('Эффекты: ' + format_bonus_dict(draft['buffs']))
    if draft.get('hp_restore') or draft.get('energy_restore'):
        parts.append(f"Восстановление: HP {int(draft.get('hp_restore', 0))} / EN {int(draft.get('energy_restore', 0))}")
    if draft.get('max_durability'):
        parts.append(f"Прочность: {int(draft.get('max_durability', 0))}")
    if draft.get('description'):
        parts.append('Описание: ' + str(draft.get('description', '')))
    parts.append('Нажми на поле ниже, чтобы изменить его. Для чисел можно вводить отрицательные значения. Ноль очищает параметр.')
    return "\n".join(parts)


def item_editor_keyboard(draft: dict[str, Any]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for field in ITEM_EDITOR_ORDER:
        meta = ITEM_EDITOR_FIELDS[field]
        value = _draft_get(draft, field)
        if meta['type'] == 'slot':
            shown = SLOT_TITLES.get(value, 'нет') if value else 'нет'
        elif meta['type'] == 'text':
            shown = str(value or '—')[:16]
        else:
            shown = str(value if value not in (None, '') else 0)
        kb.add(InlineKeyboardButton(f"{meta['label']}: {shown}", callback_data=f"adminitemfield:{field}"))
    kb.add(InlineKeyboardButton('✅ Сохранить предмет', callback_data='adminitemsave'))
    kb.add(InlineKeyboardButton('❌ Отменить', callback_data='adminitemcancel'))
    kb.add(InlineKeyboardButton('⬅️ Админ', callback_data='menu:admin'))
    return kb


def slot_picker_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for slot in SLOT_ORDER:
        kb.add(InlineKeyboardButton(SLOT_TITLES[slot], callback_data=f'adminitemslot:{slot}'))
    kb.add(InlineKeyboardButton('Убрать слот', callback_data='adminitemslot:none'))
    kb.add(InlineKeyboardButton('⬅️ К предмету', callback_data='adminitemback'))
    return kb


def open_custom_item_editor(target, draft: dict[str, Any]) -> None:
    edit_or_send(target, custom_item_editor_text(draft), item_editor_keyboard(draft))


def save_custom_item_draft(uid: int) -> tuple[bool, str]:
    state = get_user_state(uid) or {}
    payload = state.get('payload', {})
    draft = dict(payload.get('draft') or {})
    if state.get('state_code') not in {'admin_item_editor', 'admin_item_field_input'} or not draft:
        return False, 'Черновик предмета не найден.'
    item_data = {
        'id': int(draft['id']),
        'category': draft['category'],
        'rarity': int(draft['rarity']),
        'seq': int(draft.get('seq', int(draft['id']) % 1000)),
        'name': draft['name'],
        'emoji': draft.get('emoji', '📦'),
        'price': int(draft.get('price', 1)),
        'weight': int(draft.get('weight', 1)),
        'slot': draft.get('slot'),
        'stats': draft.get('stats', {}),
        'buffs': draft.get('buffs', {}),
        'hp_restore': int(draft.get('hp_restore', 0)),
        'energy_restore': int(draft.get('energy_restore', 0)),
        'max_durability': int(draft.get('max_durability', 0)),
        'description': draft.get('description', ''),
        'tags': ['custom', 'owner_added', CATEGORY_NAMES.get(draft['category'], draft['category']).lower()],
    }
    register_runtime_item(item_data)
    save_custom_item(item_data, uid)
    clear_user_state(uid)
    item = get_item(int(item_data['id']))
    parts = [f"✅ Предмет сохранён: {item['emoji']} <b>{item['name']}</b> [{item['id']}]", f"Тип: {item['category_name']} · редкость {item['rarity_name']}"]
    if item.get('slot'):
        parts.append(f"Слот: {SLOT_TITLES.get(item['slot'], item['slot'])}")
    if item.get('stats'):
        parts.append('Статы: ' + format_bonus_dict(item['stats']))
    if item.get('buffs'):
        parts.append('Эффекты: ' + format_bonus_dict(item['buffs']))
    if item.get('hp_restore') or item.get('energy_restore'):
        parts.append(f"Восстановление: HP {int(item.get('hp_restore', 0))} / EN {int(item.get('energy_restore', 0))}")
    if item.get('description'):
        parts.append('Описание: ' + item.get('description', ''))
    return True, "\n".join(parts)



def finalize_custom_item(uid: int, template_code: str) -> tuple[bool, str]:
    state = get_user_state(uid) or {}
    payload = state.get('payload', {})
    if state.get('state_code') != 'admin_new_item_template':
        return False, 'Сначала начни создание предмета.'
    if template_code == 'cancel':
        clear_user_state(uid)
        return False, 'Создание предмета отменено.'
    category = payload.get('category', '')
    template = ITEM_TEMPLATE_PRESETS.get(category, {}).get(template_code)
    if not template:
        return False, 'Шаблон не найден.'
    item_id = int(payload['item_id'])
    rarity = int(payload['rarity'])
    seq = int(payload['seq'])
    name = str(payload['name'])
    scaled = scaled_template_data(template, rarity)
    draft = {
        'id': item_id,
        'category': category,
        'rarity': rarity,
        'seq': seq,
        'name': name,
        'emoji': scaled.get('emoji', '📦'),
        'price': int(scaled.get('price', 1)),
        'weight': int(scaled.get('weight', 1)),
        'slot': scaled.get('slot'),
        'stats': scaled.get('stats', {}),
        'buffs': scaled.get('buffs', {}),
        'hp_restore': int(scaled.get('hp_restore', 0)),
        'energy_restore': int(scaled.get('energy_restore', 0)),
        'max_durability': int(scaled.get('max_durability', 0)),
        'description': scaled.get('description', ''),
    }
    set_user_state(uid, 'admin_item_editor', {'draft': draft})
    return True, '🧩 Шаблон применён. Теперь настрой характеристики предмета и нажми «Сохранить предмет».'

def finalize_custom_recipe(uid: int, station_code: str) -> tuple[bool, str]:
    state = get_user_state(uid) or {}
    payload = state.get('payload', {})
    if state.get('state_code') != 'admin_new_craft_station':
        return False, 'Сначала начни создание крафта.'
    if station_code == 'cancel':
        clear_user_state(uid)
        return False, 'Создание крафта отменено.'
    if station_code not in CRAFT_STATIONS:
        return False, 'Неизвестная станция.'
    recipe_id = int(payload['recipe_id'])
    result_item = get_item(int(payload['result']))
    max_rarity = max([int(result_item['rarity'])] + [int(get_item(int(i))['rarity']) for i in payload['ingredients'].keys()])
    recipe_data = {
        'id': recipe_id,
        'name': payload.get('name') or f"Рецепт: {result_item['name']}",
        'result': int(payload['result']),
        'result_amount': int(payload.get('result_amount', 1)),
        'ingredients': {int(k): int(v) for k, v in payload['ingredients'].items()},
        'station': station_code,
        'required_level': max(1, max_rarity * 5),
    }
    register_runtime_recipe(recipe_data)
    save_custom_recipe(recipe_data, uid)
    clear_user_state(uid)
    ingredient_text = ', '.join([f"{get_item(int(i))['name']} x{int(a)}" for i, a in recipe_data['ingredients'].items()])
    return True, f"✅ Крафт добавлен: <b>{recipe_data['name']}</b> [#{recipe_id}]\nРезультат: {result_item['emoji']} {result_item['name']} x{recipe_data['result_amount']}\nИнгредиенты: {ingredient_text}\nСтанция: {CRAFT_STATIONS[station_code]}"


def player_ready(user_id: int) -> tuple[bool, str | None]:
    p = get_player(user_id)
    if not p:
        return False, "Профиль не найден."
    if int(p.get("blocked", 0)):
        return False, "⛔ Аккаунт заблокирован."
    if not int(p.get("rules_accepted", 0)):
        return False, "📜 Сначала нужно принять правила."
    if not int(p.get("registered", 0)):
        return False, "🐾 Сначала выбери зверя."
    return True, None


def ensure_player_or_prompt(target) -> bool:
    user_id = target.from_user.id if hasattr(target, "from_user") else target.message.from_user.id
    ok, err = player_ready(user_id)
    if ok:
        return True
    p = get_player(user_id)
    if p and not int(p.get("rules_accepted", 0)):
        edit_or_send(target, RULES_TEXT, rules_markup())
    elif p and not int(p.get("registered", 0)):
        edit_or_send(target, "Выбери своего зверя. После выбора изменить его нельзя без свитка перерождения.", chars_markup())
    else:
        edit_or_send(target, err or "Ошибка.")
    return False


def apply_level_sync(user_id: int) -> list[str]:
    p = get_player(user_id)
    if not p:
        return []
    s = sync_level(p)
    notices = []
    if s["new_level"] != int(p.get("level", 1)):
        from user_data import set_level
        set_level(user_id, s["new_level"])
        notices.append(f"🎉 Новый уровень: {s['new_level']}")
        pts = award_talent_points_for_levels(user_id, int(p.get("level", 1)), int(s["new_level"]))
        if pts:
            notices.append(f"🧬 Получено очков талантов: {pts}")
        if int(s["new_level"]) >= MAX_LEVEL:
            notices.append("👑 Достигнут потолок уровня. Можно совершить престиж.")
    p = get_player(user_id)
    title = effective_profile(p, get_equipment(user_id), get_buffs(user_id), get_player_extras(user_id))["title"]
    set_title(user_id, title)
    return notices


def reward_player(user_id: int, gold: int, xp: int, loot: list[tuple[int, int]], log_kind: str) -> str:
    from user_data import add_xp
    stats = stats_for_user(user_id)
    gold = int(gold * (1 + stats.get('gold_gain_pct', 0) / 100))
    xp = int(xp * (1 + stats.get('xp_gain_pct', 0) / 100))
    add_gold(user_id, gold)
    add_xp(user_id, xp)
    for item_id, amount in loot:
        add_item(user_id, item_id, amount)
    level_notes = apply_level_sync(user_id)
    add_log(user_id, log_kind, f"Получено: {gold} монет, {xp} опыта, предметов {len(loot)}")
    extra = "\n" + "\n".join(level_notes) if level_notes else ""
    loot_text = "\n".join(format_item_line(i, a) for i, a in loot[:6])
    return f"💰 +{gold}\n📘 +{xp}" + (f"\n{loot_text}" if loot_text else "") + extra


def open_main(target) -> None:
    if hasattr(target, 'chat') and getattr(target.chat, 'type', '') == 'private':
        ensure_private_reply_keyboard(target)
    else:
        clear_stale_reply_keyboard(target)
    uid = target.from_user.id if hasattr(target, "from_user") else target.message.from_user.id
    if is_private_target(target):
        edit_or_send(target, f"{GAME_TITLE} <b>{VERSION}</b>\nВыбирай раздел ниже.", main_menu(uid))
    else:
        edit_or_send(target, group_hub_text(), None)


# -----------------------------
# Меню
# -----------------------------

def rules_markup() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("✅ Принимаю", callback_data="reg:accept"), InlineKeyboardButton("📜 Правила", callback_data="info:rules"))
    return kb


def chars_markup() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for key, data in CHARACTERS.items():
        kb.add(InlineKeyboardButton(f"{data['emoji']} {data['title']}", callback_data=f"char:{key}"))
    return kb


def main_menu(uid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("👤 Профиль", callback_data="menu:profile"),
        InlineKeyboardButton("🎒 Инвентарь", callback_data="menu:inv:0"),
        InlineKeyboardButton("⚔️ Арена", callback_data="menu:pvp"),
        InlineKeyboardButton("🧬 Таланты", callback_data="menu:tal"),
        InlineKeyboardButton("🏛 Фракция", callback_data="menu:faction"),
        InlineKeyboardButton("🧾 Контракты", callback_data="menu:contracts"),
        InlineKeyboardButton("🧭 Экспедиция", callback_data="menu:exp"),
        InlineKeyboardButton("🏰 Подземелье", callback_data="menu:dng"),
        InlineKeyboardButton("🛒 Магазин", callback_data="menu:shop:0"),
        InlineKeyboardButton("🌑 Чёрный рынок", callback_data="menu:black:0"),
        InlineKeyboardButton("📦 Рынок", callback_data="menu:market"),
        InlineKeyboardButton("⚒ Крафт", callback_data="menu:craft:0"),
        InlineKeyboardButton("🏦 Банк", callback_data="menu:bank"),
        InlineKeyboardButton("🎯 Задания", callback_data="menu:tasks"),
        InlineKeyboardButton("🌍 Босс", callback_data="menu:boss"),
        InlineKeyboardButton("🐾 Питомец", callback_data="menu:pet"),
        InlineKeyboardButton("⛺ Лагерь", callback_data="menu:camp"),
        InlineKeyboardButton("🐺 Стая", callback_data="menu:clan"),
        InlineKeyboardButton("✉️ Почта", callback_data="menu:mail:0"),
        InlineKeyboardButton("🏆 Топы", callback_data="menu:top"),
        InlineKeyboardButton("🎁 Рефералка", callback_data="menu:ref"),
        InlineKeyboardButton("📘 Инфо", callback_data="menu:info"),
    )
    if uid == OWNER_ID:
        kb.add(InlineKeyboardButton("🔐 Админ", callback_data="menu:admin"))
    return kb


def back_to_main(uid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    return kb


def profile_menu(player: dict[str, Any]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🎒 Инвентарь", callback_data="menu:inv:0"), InlineKeyboardButton("🧰 Экипировка", callback_data="menu:gear"))
    kb.add(InlineKeyboardButton("🧬 Таланты", callback_data="menu:tal"), InlineKeyboardButton("🏛 Фракция", callback_data="menu:faction"))
    kb.add(InlineKeyboardButton("📜 Логи", callback_data="menu:logs"), InlineKeyboardButton("✉️ Почта", callback_data="menu:mail:0"))
    if int(player.get("level", 1)) >= 20 and not player.get("specialization"):
        kb.add(InlineKeyboardButton("✨ Специализация", callback_data="menu:spec"))
    if int(player.get("level", 1)) >= MAX_LEVEL:
        kb.add(InlineKeyboardButton("👑 Престиж", callback_data="prestige:do"))
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    return kb


def inventory_menu(page: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("Еда", callback_data="invcat:food:0"), InlineKeyboardButton("Материалы", callback_data="invcat:material:0"))
    kb.add(InlineKeyboardButton("Экипировка", callback_data="invcat:equipment:0"), InlineKeyboardButton("Эликсиры", callback_data="invcat:elixir:0"))
    kb.add(InlineKeyboardButton("Свитки", callback_data="invcat:scroll:0"), InlineKeyboardButton("Все", callback_data="menu:inv:0"))
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    return kb


def simple_back(section: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data=section))
    return kb


def top_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("⭐ Уровни", callback_data="top:lvl"),
        InlineKeyboardButton("⚔️ Арена", callback_data="top:pvp"),
        InlineKeyboardButton("💰 Богачи", callback_data="top:rich"),
        InlineKeyboardButton("🤝 Репутация", callback_data="top:rep"),
        InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"),
    )
    return kb


def pvp_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🏆 Топ арены", callback_data="top:pvp"),
        InlineKeyboardButton("📜 Как вызвать", callback_data="pvp:guide"),
        InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"),
    )
    return kb


def info_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📜 Правила", callback_data="info:rules"),
        InlineKeyboardButton("🌍 Лор", callback_data="info:lore"),
        InlineKeyboardButton("🗺 Карта", callback_data="info:map"),
        InlineKeyboardButton("⌨️ Команды", callback_data="info:cmd"),
        InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"),
    )
    return kb


def market_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🧺 Лоты", callback_data="market:list:0"),
        InlineKeyboardButton("🔨 Аукционы", callback_data="auction:list:0"),
        InlineKeyboardButton("📝 Заказы", callback_data="orders:list:0"),
        InlineKeyboardButton("➕ Продать", callback_data="owned:list:sell:0"),
        InlineKeyboardButton("🔨 Мой аукцион", callback_data="owned:list:auction:0"),
        InlineKeyboardButton("📦 Мой заказ", callback_data="state:order"),
        InlineKeyboardButton("🎁 Подарок", callback_data="owned:list:gift:0"),
        InlineKeyboardButton("🤝 Сделка", callback_data="state:deal"),
        InlineKeyboardButton("🙏 Запрос предмета", callback_data="state:request"),
        InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"),
    )
    return kb


def bank_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🏦 Взять кредит", callback_data="bank:loan"), InlineKeyboardButton("✅ Погасить", callback_data="bank:repay"))
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    return kb


def task_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("📅 Ежедневные", callback_data="tasks:daily"), InlineKeyboardButton("🗓 Недельные", callback_data="tasks:weekly"))
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    return kb


def pet_menu(player: dict[str, Any]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    if player.get("pet_species"):
        kb.add(InlineKeyboardButton("🍼 Тренировать", callback_data="pet:train"))
    else:
        for key, data in PET_SPECIES.items():
            short_bonus = format_bonus_dict(data['bonus'])
            kb.add(InlineKeyboardButton(f"{data['emoji']} {data['title']} · {short_bonus}", callback_data=f"pet:set:{key}"))
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    return kb


def pet_selection_text() -> str:
    lines = [
        "🐾 <b>Питомец</b>",
        f"Для приручения нужен жетон [{PET_TOKEN_ID}] или специальная награда.",
        "Ниже сначала описание каждого компаньона, а затем кнопки выбора.",
        "",
        "<b>Порядок просмотра:</b> роль → пассивный бонус → особенность.",
        "",
    ]
    for data in PET_SPECIES.values():
        lines.append(f"{data['emoji']} <b>{data['title']}</b>")
        lines.append(f"Роль: {data.get('role', 'компаньон')}")
        lines.append("Пассивный бонус: " + format_bonus_dict(data.get('bonus', {})))
        if data.get('ability_name') or data.get('ability_desc'):
            lines.append(f"Особенность: <b>{data.get('ability_name', '—')}</b> — {data.get('ability_desc', 'Описание появится позже.')}")
        lines.append("")
    return "\n".join(lines).strip()


def camp_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(InlineKeyboardButton("1ч", callback_data="camp:start:1"), InlineKeyboardButton("4ч", callback_data="camp:start:4"), InlineKeyboardButton("8ч", callback_data="camp:start:8"))
    kb.add(InlineKeyboardButton("🎒 Забрать", callback_data="camp:claim"), InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    return kb


def clan_menu(player: dict[str, Any]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    if int(player.get("clan_id", 0)):
        kb.add(InlineKeyboardButton("📊 Моя стая", callback_data="clan:my"), InlineKeyboardButton("💰 Внести в казну", callback_data="state:clan_donate"))
        kb.add(InlineKeyboardButton("🚪 Покинуть", callback_data="clan:leave"))
    else:
        kb.add(InlineKeyboardButton("➕ Создать", callback_data="state:clan_create"), InlineKeyboardButton("📜 Список", callback_data="clan:list"))
        kb.add(InlineKeyboardButton("📥 Вступить", callback_data="state:clan_join"))
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    return kb


def admin_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💎 Паки", callback_data="admin:packs"),
        InlineKeyboardButton("🎟 Промокоды", callback_data="admin:promos"),
        InlineKeyboardButton("🚨 Подозрения", callback_data="admin:sus"),
        InlineKeyboardButton("🆕 Новый предмет", callback_data="state:admin_new_item"),
        InlineKeyboardButton("🧪 Новый крафт", callback_data="state:admin_new_craft"),
        InlineKeyboardButton("✏️ Изменить предмет", callback_data="admin:edit_menu"),
        InlineKeyboardButton("🎁 Выдать пак", callback_data="admin:pack_menu"),
        InlineKeyboardButton("🎒 Выдать предмет", callback_data="admin:give_menu"),
        InlineKeyboardButton("🗑 Забрать предмет", callback_data="admin:take_menu"),
        InlineKeyboardButton("🏦 Долг банка", callback_data="state:admin_bank_debt"),
        InlineKeyboardButton("💫 Донат", callback_data="admin:donate"),
        InlineKeyboardButton("⭐ Уровень", callback_data="state:admin_level"),
        InlineKeyboardButton("⛔ Блок", callback_data="state:admin_block"),
        InlineKeyboardButton("✅ Разблок", callback_data="state:admin_unblock"),
        InlineKeyboardButton("👮 Админ +", callback_data="state:admin_add"),
        InlineKeyboardButton("👤 Админ -", callback_data="state:admin_del"),
        InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"),
    )
    return kb


def admin_choose_menu(action: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    titles = {
        'give': 'Выдать предмет',
        'take': 'Забрать предмет',
        'pack': 'Выдать пак',
        'edit': 'Изменить предмет',
    }
    if action == 'pack':
        kb.add(InlineKeyboardButton('✍️ Написать название пака', callback_data='state:admin_pack'))
        kb.add(InlineKeyboardButton('📚 Выбрать пак из списка', callback_data='admin:pickpack:0'))
    else:
        kb.add(InlineKeyboardButton('✍️ Написать название предмета', callback_data=f'state:admin_{action}'))
        kb.add(InlineKeyboardButton('📚 Выбрать предмет из списка', callback_data=f'admin:pickcat:{action}:0'))
    kb.add(InlineKeyboardButton('⬅️ Админ', callback_data='menu:admin'))
    return kb


def admin_item_categories_page(action: str, page: int = 0) -> InlineKeyboardMarkup:
    categories = list(CATEGORY_NAMES.items())
    per_page = 4
    chunk = categories[page*per_page:(page+1)*per_page]
    kb = InlineKeyboardMarkup(row_width=2)
    for key, title in chunk:
        kb.add(InlineKeyboardButton(title, callback_data=f'admin:pickitem:{action}:{key}:0'))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton('◀️', callback_data=f'admin:pickcat:{action}:{page-1}'))
    if (page + 1) * per_page < len(categories):
        nav.append(InlineKeyboardButton('▶️', callback_data=f'admin:pickcat:{action}:{page+1}'))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton('⬅️ Назад', callback_data=f'admin:{action}_menu'))
    return kb


def show_admin_item_picker(target, action: str, category: str, page: int = 0) -> None:
    rows = sorted([item for item in ITEMS.values() if item['category'] == category], key=lambda x: (x['rarity'], x['name']))
    per_page = 8
    chunk = rows[page*per_page:(page+1)*per_page]
    title = {'give': 'Выдача', 'take': 'Изъятие', 'edit': 'Редактирование'}.get(action, 'Выбор')
    prompt = 'Нажми на предмет, затем укажи игрока ответом, @username или ID.' if action in {'give','take'} else 'Нажми на предмет, чтобы открыть редактор его характеристик.'
    lines = [f'📚 <b>{title}: {CATEGORY_NAMES.get(category, category)}</b>', prompt, '']
    kb = InlineKeyboardMarkup(row_width=1)
    for item in chunk:
        lines.append(f"• {item['emoji']} {item['name']} · {item['rarity_name']} · [{item['id']}]")
        kb.add(InlineKeyboardButton(f"{item['emoji']} {item['name'][:28]}", callback_data=f"admin:pickdo:{action}:{item['id']}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton('◀️', callback_data=f'admin:pickitem:{action}:{category}:{page-1}'))
    if (page + 1) * per_page < len(rows):
        nav.append(InlineKeyboardButton('▶️', callback_data=f'admin:pickitem:{action}:{category}:{page+1}'))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton('⬅️ Категории', callback_data=f'admin:pickcat:{action}:0'))
    edit_or_send(target, '\n'.join(lines), kb)


def show_admin_pack_picker(target, page: int = 0) -> None:
    rows = list_packs()
    per_page = 8
    chunk = rows[page*per_page:(page+1)*per_page]
    lines = ['🎁 <b>Выдача пака</b>', 'Нажми на пак, затем укажи игрока ответом, @username или ID.', '']
    kb = InlineKeyboardMarkup(row_width=1)
    for row in chunk:
        state = 'вкл.' if row['enabled'] else 'выкл.'
        lines.append(f"• {row['name']} ({row['code']}) · {row.get('price_stars', 0)} ⭐ · {state}")
        kb.add(InlineKeyboardButton(f"🎁 {row['name'][:28]}", callback_data=f"admin:pickpackdo:{row['code']}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton('◀️', callback_data=f'admin:pickpack:{page-1}'))
    if (page + 1) * per_page < len(rows):
        nav.append(InlineKeyboardButton('▶️', callback_data=f'admin:pickpack:{page+1}'))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton('⬅️ Назад', callback_data='admin:pack_menu'))
    edit_or_send(target, '\n'.join(lines), kb)


def show_owned_item_picker(target, uid: int, action: str, page: int = 0) -> None:
    inv = [row for row in get_inventory(uid) if int(row['amount']) > 0]
    per_page = 8
    chunk = inv[page*per_page:(page+1)*per_page]
    titles = {
        'sell': 'Продажа на рынок',
        'auction': 'Выставление аукциона',
        'gift': 'Подарок игроку',
    }
    prompts = {
        'sell': 'Выбери предмет из своего инвентаря. Затем бот попросит количество и цену за 1 шт.',
        'auction': 'Выбери предмет из своего инвентаря. Затем бот попросит количество, стартовую ставку и часы.',
        'gift': 'Выбери предмет из своего инвентаря. Затем укажи игрока ответом, @username или ID и количество.',
    }
    lines = [f"🎒 <b>{titles.get(action, 'Выбор предмета')}</b>", prompts.get(action, 'Выбери предмет.'), '']
    kb = InlineKeyboardMarkup(row_width=1)
    if not chunk:
        lines.append('В инвентаре нет подходящих предметов.')
    for row in chunk:
        item = row['item']
        lines.append(f"• {item['emoji']} {item['name']} x{row['amount']} · [{row['item_id']}]")
        kb.add(InlineKeyboardButton(f"{item['emoji']} {item['name'][:26]} x{row['amount']}", callback_data=f"owned:pick:{action}:{row['item_id']}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton('◀️', callback_data=f'owned:list:{action}:{page-1}'))
    if (page + 1) * per_page < len(inv):
        nav.append(InlineKeyboardButton('▶️', callback_data=f'owned:list:{action}:{page+1}'))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton('⬅️ К рынку', callback_data='menu:market'))
    edit_or_send(target, '\n'.join(lines), kb)


def spec_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for key, data in SPECIALIZATIONS.items():
        kb.add(InlineKeyboardButton(data["title"], callback_data=f"spec:{key}"))
    kb.add(InlineKeyboardButton("⬅️ Профиль", callback_data="menu:profile"))
    return kb


def talent_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    for code, data in TALENTS.items():
        kb.add(InlineKeyboardButton(f"{data['emoji']} {data['title']}", callback_data=f"talent:up:{code}"))
    kb.add(InlineKeyboardButton("♻️ Сброс", callback_data="talent:reset"), InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    return kb


def faction_menu(uid: int) -> InlineKeyboardMarkup:
    extra = extras_for_user(uid)
    kb = InlineKeyboardMarkup(row_width=2)
    if extra.get('faction_key'):
        kb.add(InlineKeyboardButton("🎖 Получить жалование", callback_data="faction:claim"))
    else:
        for key, data in FACTIONS.items():
            kb.add(InlineKeyboardButton(f"{data['emoji']} {data['title']}", callback_data=f"faction:join:{key}"))
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    return kb


def contracts_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for row in daily_contract_board():
        kb.add(InlineKeyboardButton(f"{row['emoji']} {row['title']}", callback_data=f"contract:run:{row['code']}"))
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    return kb


def referral_menu(uid: int) -> InlineKeyboardMarkup:
    refs = get_referrals(uid)
    kb = InlineKeyboardMarkup(row_width=2)
    for row in refs[:4]:
        if not int(row.get("reward_claimed", 0)):
            kb.add(InlineKeyboardButton(f"💰 За {row['referred_id']}", callback_data=f"ref:claim:{row['referred_id']}:gold"), InlineKeyboardButton(f"🎁 За {row['referred_id']}", callback_data=f"ref:claim:{row['referred_id']}:item"))
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    return kb


# -----------------------------
# Отрисовка разделов
# -----------------------------

def show_profile(target, uid: int) -> None:
    p = get_player(uid)
    extra = extras_for_user(uid)
    stats = stats_for_user(uid)
    pet_txt = "нет"
    if p.get("pet_species"):
        pet = PET_SPECIES[p["pet_species"]]
        pet_txt = f"{pet['emoji']} {pet['title']} ур.{p['pet_level']}"
    spec = SPECIALIZATIONS[p['specialization']]['title'] if p.get('specialization') in SPECIALIZATIONS else 'не выбрана'
    clan_txt = f"стая #{p['clan_id']}" if int(p.get("clan_id", 0)) else "нет"
    faction_txt = 'нет'
    if extra.get('faction_key') in FACTIONS:
        f = FACTIONS[extra['faction_key']]
        faction_txt = f"{f['emoji']} {f['title']} · реп {extra['faction_rep']}"
    season = season_info()
    text = (
        f"👤 <b>{get_display_name(uid)}</b>\n"
        f"{stats['character']['emoji']} {stats['character']['title']} · <b>{stats['title']}</b>\n"
        f"⭐ Ур.{p['level']} · {profile_progress(p)}\n"
        f"👑 Престиж: {extra['prestige']} · 🧬 Очки талантов: {extra['talent_points']}\n"
        f"💰 {p['gold']} · 💎 {p['premium']} · 🏆 {p['rating']} ({stats['league']})\n"
        f"❤️ Здоровье: {stats['max_hp']} · ⚡ Энергия: {stats['max_energy']}\n"
        f"🗡 Атака {stats['attack']} · 🛡 Защита {stats['defense']} · 💨 Скорость {stats['speed']} · 🍀 Удача {stats['luck']}\n"
        f"Бонусы: +{stats.get('gold_gain_pct',0)}% золота · +{stats.get('xp_gain_pct',0)}% опыта\n"
        f"Спец.: {spec}\n"
        f"Питомец: {pet_txt}\n"
        f"Фракция: {faction_txt}\n"
        f"Стая: {clan_txt}\n"
        f"Репутация: {p['reputation']}\n"
        f"Кодекс: {get_codex_count(uid)}/{len(ITEMS)}\n"
        f"Поединки: {p['wins']} / {p['losses']}\n"
        f"Сезон #{season['season_no']} · осталось {season['days_left']} дн."
    )
    edit_or_send(target, text, profile_menu(p) if is_private_target(target) else None)


def show_gear(target, uid: int) -> None:
    eq = get_equipment(uid)
    lines = ["🧰 <b>Экипировка</b>"]
    kb = InlineKeyboardMarkup(row_width=2)
    for slot in SLOT_ORDER:
        if slot in eq:
            item = eq[slot]["item"]
            lines.append(f"• {SLOT_TITLES[slot]}: {item['emoji']} {item['name']} [{eq[slot]['item_id']}] · {eq[slot]['durability']}/{item['max_durability']}")
            kb.add(InlineKeyboardButton(f"Снять {SLOT_TITLES[slot]}", callback_data=f"gear:off:{slot}"))
        else:
            lines.append(f"• {SLOT_TITLES[slot]}: —")
    kb.add(InlineKeyboardButton("🔧 Починить всё", callback_data="gear:repair"), InlineKeyboardButton("⬅️ Профиль", callback_data="menu:profile"))
    edit_or_send(target, "\n".join(lines), kb if is_private_target(target) else None)


def show_inventory(target, uid: int, category: str = "all", page: int = 0) -> None:
    inv = get_inventory(uid)
    if category != "all":
        inv = [row for row in inv if row["item"]["category"] == category]
    per_page = 8
    chunk = inv[page*per_page:(page+1)*per_page]
    stats = inventory_stats(uid)
    lines = [f"🎒 <b>Инвентарь</b> · слоты {stats['used_slots']}/{stats['max_slots']} · вес {stats['weight']}/{stats['max_weight']}", f"Фильтр: {category}", ""]
    kb = InlineKeyboardMarkup(row_width=1)
    if not chunk:
        lines.append("Пусто.")
    for row in chunk:
        item = row["item"]
        lines.append(f"• {item['emoji']} {item['name']} x{row['amount']} [{row['item_id']}] · {item['rarity_name']}")
        kb.add(InlineKeyboardButton(f"{item['emoji']} {item['name'][:22]}", callback_data=f"item:{row['item_id']}:{category}:{page}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"invcat:{category}:{page-1}" if category != 'all' else f"menu:inv:{page-1}"))
    if (page+1)*per_page < len(inv):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"invcat:{category}:{page+1}" if category != 'all' else f"menu:inv:{page+1}"))
    if nav:
        kb.row(*nav)
    cats = inventory_menu(page)
    # merge buttons
    for row in cats.keyboard:
        kb.keyboard.append(row)
    edit_or_send(target, "\n".join(lines), kb if is_private_target(target) else None)


def show_item(target, uid: int, item_id: int, back_cat: str, back_page: int) -> None:
    amount = get_item_amount(uid, item_id)
    text = item_effect_text(item_id) + f"\n\nВ инвентаре: {amount}"
    kb = InlineKeyboardMarkup(row_width=2)
    if is_equipment(item_id):
        kb.add(InlineKeyboardButton("🧰 Экипировать", callback_data=f"use:equip:{item_id}"))
    elif is_consumable(item_id):
        kb.add(InlineKeyboardButton("⚡ Использовать", callback_data=f"use:item:{item_id}"))
    back_cb = f"invcat:{back_cat}:{back_page}" if back_cat != 'all' else f"menu:inv:{back_page}"
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data=back_cb))
    edit_or_send(target, text, kb)


def show_shop(target, black: bool = False, page: int = 0) -> None:
    stock = generate_black_market_stock() if black else generate_shop_stock()
    eco = economy_snapshot()
    title = "🌑 <b>Чёрный рынок</b>" if black else "🛒 <b>Магазин</b>"
    per_page = 6
    chunk = stock[page*per_page:(page+1)*per_page]
    lines = [title, f"Тренд дня: спрос на {category_title_ru(eco['demand'])} · избыток {category_title_ru(eco['surplus'])}", ""]
    kb = InlineKeyboardMarkup(row_width=1)
    for row in chunk:
        item = get_item(row['item_id'])
        lines.append(f"• {item['emoji']} {item['name']} [{row['item_id']}] — {row['price']} мон.")
        kb.add(InlineKeyboardButton(f"Купить {item['name'][:20]}", callback_data=f"shopbuy:{row['item_id']}:{1 if black else 0}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"menu:{'black' if black else 'shop'}:{page-1}"))
    if (page+1)*per_page < len(stock):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"menu:{'black' if black else 'shop'}:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    edit_or_send(target, "\n".join(lines), kb if is_private_target(target) else None)


def show_craft(target, uid: int, page: int = 0) -> None:
    all_recipes = list(RECIPES.values())
    per_page = 6
    chunk = all_recipes[page*per_page:(page+1)*per_page]
    lines = ["⚒ <b>Крафт</b>", "Выбери рецепт. Бот проверит материалы автоматически.", ""]
    kb = InlineKeyboardMarkup(row_width=1)
    for r in chunk:
        item = get_item(r['result'])
        lines.append(f"• #{r['id']} {item['emoji']} {item['name']} x{r['result_amount']} · ур.{r['required_level']}")
        kb.add(InlineKeyboardButton(f"Крафт #{r['id']} {item['name'][:18]}", callback_data=f"craft:{r['id']}:{page}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"menu:craft:{page-1}"))
    if (page+1)*per_page < len(all_recipes):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"menu:craft:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    edit_or_send(target, "\n".join(lines), kb)


def show_market_root(target) -> None:
    text = "📦 <b>Рынок и обмен</b>"
    if not is_private_target(target):
        text += "\nВ группе используй текстовые действия: подарок, сделка, запрос, рынок, аукцион. Для выбора предметов удобнее открыть ЛС с ботом."
    edit_or_send(target, text, market_menu() if is_private_target(target) else None)


def show_market_list(target, page: int = 0) -> None:
    rows = get_market_listings(50)
    per_page = 8
    chunk = rows[page*per_page:(page+1)*per_page]
    lines = ["🧺 <b>Лоты рынка</b>", ""]
    kb = InlineKeyboardMarkup(row_width=1)
    if not chunk:
        lines.append("Открытых лотов нет.")
    for row in chunk:
        item = get_item(int(row['item_id']))
        total = int(row['amount']) * int(row['price_each'])
        lines.append(f"• #{row['id']} {item['emoji']} {item['name']} x{row['amount']} — {row['price_each']} / шт. (итого {total})")
        kb.add(InlineKeyboardButton(f"Купить #{row['id']}", callback_data=f"market:buy:{row['id']}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"market:list:{page-1}"))
    if (page+1)*per_page < len(rows):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"market:list:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("⬅️ К рынку", callback_data="menu:market"))
    edit_or_send(target, "\n".join(lines), kb if is_private_target(target) else None)


def show_auctions(target, page: int = 0) -> None:
    rows = list_auctions(50)
    per_page = 8
    chunk = rows[page*per_page:(page+1)*per_page]
    lines = ["🔨 <b>Аукционы</b>", ""]
    kb = InlineKeyboardMarkup(row_width=1)
    if not chunk:
        lines.append("Открытых аукционов нет.")
    for row in chunk:
        item = get_item(int(row['item_id']))
        lines.append(f"• #{row['id']} {item['emoji']} {item['name']} x{row['amount']} — ставка {row['current_bid']}")
        kb.add(InlineKeyboardButton(f"Ставка на #{row['id']}", callback_data=f"auction:bid:{row['id']}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"auction:list:{page-1}"))
    if (page+1)*per_page < len(rows):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"auction:list:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("⬅️ К рынку", callback_data="menu:market"))
    edit_or_send(target, "\n".join(lines), kb if is_private_target(target) else None)


def show_orders(target, page: int = 0) -> None:
    rows = list_buy_orders(50)
    per_page = 8
    chunk = rows[page*per_page:(page+1)*per_page]
    lines = ["📝 <b>Заказы на покупку</b>", ""]
    kb = InlineKeyboardMarkup(row_width=1)
    if not chunk:
        lines.append("Открытых заказов нет.")
    for row in chunk:
        item = get_item(int(row['item_id']))
        lines.append(f"• #{row['id']} {item['emoji']} {item['name']} — нужно {row['amount_left']} по {row['price_each']}")
        kb.add(InlineKeyboardButton(f"Продать в заказ #{row['id']}", callback_data=f"orders:fill:{row['id']}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"orders:list:{page-1}"))
    if (page+1)*per_page < len(rows):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"orders:list:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("⬅️ К рынку", callback_data="menu:market"))
    edit_or_send(target, "\n".join(lines), kb if is_private_target(target) else None)


def show_bank(target, uid: int) -> None:
    p = get_player(uid)
    offer = loan_offer(p)
    debt = int(p.get("bank_debt", 0))
    remain = max(0, int(p.get("bank_due_ts", 0)) - now_ts()) if debt else 0
    text = (
        f"🏦 <b>Игровой банк</b>\n"
        f"Твой лимит: {offer['amount']} монет.\n"
        f"Если взять сейчас, к возврату будет: {offer['debt']}.\n"
        + (f"Текущий долг: {debt}. Осталось: {format_seconds(remain)}" if debt else "Текущий долг: нет")
    )
    edit_or_send(target, text, bank_menu() if is_private_target(target) else None)


def ensure_task_sets(uid: int) -> tuple[str, str]:
    day = time.strftime("d:%Y%m%d")
    week = time.strftime("w:%Y%W")
    ensure_tasks(uid, day, "daily", choose_task_defs(DAILY_TASK_POOL, uid, 4, int(time.time()//86400)))
    ensure_tasks(uid, week, "weekly", choose_task_defs(WEEKLY_TASK_POOL, uid, 4, int(time.time()//(7*86400))))
    return day, week


def show_tasks(target, uid: int, kind: str = "daily") -> None:
    day, week = ensure_task_sets(uid)
    key = day if kind == 'daily' else week
    tasks = list_tasks(uid, key, kind)
    lines = ["🎯 <b>Задания</b>", ""]
    kb = InlineKeyboardMarkup(row_width=1)
    for t in tasks:
        lines.append(f"• {t['title']}: {t['progress']}/{t['target']} {'✅' if t['claimed'] else ''}")
        if int(t['progress']) >= int(t['target']) and not int(t['claimed']):
            kb.add(InlineKeyboardButton(f"Получить: {t['title'][:20]}", callback_data=f"task:{kind}:{t['task_code']}"))
    for row in task_menu().keyboard:
        kb.keyboard.append(row)
    edit_or_send(target, "\n".join(lines), kb)


def get_boss_state() -> dict[str, Any]:
    day = int(time.time() // 86400)
    boss = world_boss_today()
    state = get_world_state("world_boss", {}) or {}
    if state.get("day") != day:
        state = {"day": day, "boss": boss, "hp_left": boss['max_hp'], "damage": {}, "attacks": {}, "killed": False}
        set_world_state("world_boss", state)
    return state


def show_boss(target, uid: int) -> None:
    state = get_boss_state()
    boss = state['boss']
    dealt = int(state['damage'].get(str(uid), 0))
    attacks = int(state['attacks'].get(str(uid), 0))
    text = (
        f"🌍 <b>{boss['emoji']} {boss['title']}</b>\n"
        f"HP: {state['hp_left']}/{boss['max_hp']}\n"
        f"Твой урон сегодня: {dealt}\n"
        f"Атак: {attacks}/5\n"
        f"Награда идёт за участие и добивание."
    )
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("⚔️ Ударить", callback_data="boss:hit"), InlineKeyboardButton("🏅 Топ урона", callback_data="boss:top"))
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    edit_or_send(target, text, kb)


def show_pet(target, uid: int) -> None:
    p = get_player(uid)
    if p.get("pet_species"):
        pet = PET_SPECIES[p['pet_species']]
        text = (
            f"🐾 <b>{pet['emoji']} {pet['title']}</b>\n"
            f"Роль: {pet.get('role', 'компаньон')}\n"
            f"Уровень: {p['pet_level']}\n"
            f"Пассивный бонус: {format_bonus_dict(pet['bonus'])}\n"
            f"Особенность: <b>{pet.get('ability_name', '—')}</b> — {pet.get('ability_desc', 'Описание появится позже.')}"
        )
    else:
        text = pet_selection_text()
    edit_or_send(target, text, pet_menu(p))

def show_camp(target, uid: int) -> None:
    p = get_player(uid)
    remain = max(0, int(p.get("camp_until", 0)) - now_ts())
    text = "⛺ <b>Лагерь офлайн</b>\n"
    if remain > 0:
        text += f"Лагерь работает ещё {format_seconds(remain)}."
    else:
        text += "Выбери длительность ниже. Лагерь даёт умеренную награду без спама в чат."
    edit_or_send(target, text, camp_menu())


def show_clan(target, uid: int) -> None:
    p = get_player(uid)
    if int(p.get("clan_id", 0)):
        clan = get_clan(int(p['clan_id']))
        members = get_clan_members(int(p['clan_id']))
        lines = [f"🐺 <b>{clan['name']}</b>", f"Казна: {clan['treasury']}", f"Репутация стаи: {clan['reputation']}", f"Участники: {len(members)}"]
        for m in members[:10]:
            lines.append(f"• {get_display_name(int(m['user_id']))} — {m['role']} · вклад {m['contribution']}")
        edit_or_send(target, "\n".join(lines), clan_menu(p))
    else:
        text = f"🐺 <b>Стаи / кланы</b>\nСоздание стаи стоит {CLAN_CREATE_PRICE} монет.\nСтая даёт социальную цель, общую казну и престиж."
        edit_or_send(target, text, clan_menu(p))


def show_mail(target, uid: int, page: int = 0) -> None:
    rows = list_mail(uid, 40)
    per_page = 8
    chunk = rows[page*per_page:(page+1)*per_page]
    lines = ["✉️ <b>Почта</b>", ""]
    kb = InlineKeyboardMarkup(row_width=1)
    if not chunk:
        lines.append("Писем пока нет.")
    for row in chunk:
        lines.append(f"• #{row['id']} {'📩' if not row['is_read'] else '✉️'} {row['subject']}")
        kb.add(InlineKeyboardButton(f"Открыть #{row['id']} {row['subject'][:18]}", callback_data=f"mail:{row['id']}:{page}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"menu:mail:{page-1}"))
    if (page+1)*per_page < len(rows):
        nav.append(InlineKeyboardButton("▶️", callback_data=f"menu:mail:{page+1}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    edit_or_send(target, "\n".join(lines), kb)


def show_logs(target, uid: int) -> None:
    rows = list_logs(uid, 20)
    text = "📜 <b>Последние действия</b>\n\n" + "\n".join([f"• {row['kind']}: {row['text']}" for row in rows] or ["Пусто."])
    edit_or_send(target, text, back_to_main(uid))


def show_top(target, mode: str) -> None:
    if mode == 'lvl':
        rows = top_by_level(TOP_PAGE)
        lines = [f"{i+1}. {get_display_name(int(r['user_id']))} — ур.{r['level']}" for i, r in enumerate(rows)]
        title = "⭐ Топ по уровню"
    elif mode == 'pvp':
        rows = top_by_wins(TOP_PAGE)
        lines = [f"{i+1}. {get_display_name(int(r['user_id']))} — побед {r['wins']} · рейтинг {r['rating']}" for i, r in enumerate(rows)]
        title = "⚔️ Топ дуэлей"
    elif mode == 'rich':
        rows = top_by_rich(TOP_PAGE)
        lines = [f"{i+1}. {get_display_name(int(r['user_id']))} — {r['gold']} монет" for i, r in enumerate(rows)]
        title = "💰 Самые богатые"
    else:
        rows = top_by_rep(TOP_PAGE)
        lines = [f"{i+1}. {get_display_name(int(r['user_id']))} — репутация {r['reputation']}" for i, r in enumerate(rows)]
        title = "🤝 Топ репутации"
    edit_or_send(target, f"<b>{title}</b>\n\n" + "\n".join(lines or ["Пока пусто."]), top_menu())


def show_talents(target, uid: int) -> None:
    extra = extras_for_user(uid)
    lines = [f"🧬 <b>Таланты</b>", f"Свободно очков: {extra['talent_points']}", ""]
    for code, data in TALENTS.items():
        rank = int(extra.get('talents', {}).get(code, 0))
        lines.append(f"{data['emoji']} <b>{data['title']}</b> — {rank}/{data['max_rank']}\n{data['desc']}")
    edit_or_send(target, "\n\n".join(lines), talent_menu())


def show_faction(target, uid: int) -> None:
    extra = extras_for_user(uid)
    lines = ["🏛 <b>Фракции</b>"]
    if extra.get('faction_key') in FACTIONS:
        data = FACTIONS[extra['faction_key']]
        lines.append(f"Текущая фракция: {data['emoji']} <b>{data['title']}</b>")
        lines.append(data['description'])
        lines.append(f"Репутация фракции: {extra['faction_rep']}")
    else:
        lines.append("Ты ещё не вступил во фракцию. Фракция даёт пассивные бонусы, жалование и усиление контрактов.")
    lines.append("")
    for key, data in FACTIONS.items():
        lines.append(f"{data['emoji']} <b>{data['title']}</b>\n{data['description']}\nБонусы: {format_bonus_dict(data['bonus'])}")
    edit_or_send(target, "\n\n".join(lines), faction_menu(uid) if is_private_target(target) else None)


def show_contracts(target, uid: int) -> None:
    state = extras_for_user(uid)
    c_state = state.get('contracts', {'day':0,'done':[]})
    day_key = int(time.time() // 86400)
    lines = ["🧾 <b>Контракты дня</b>", f"Выполнено сегодня: {len(c_state.get('done', [])) if c_state.get('day') == day_key else 0}/{len(daily_contract_board())}", ""]
    for row in daily_contract_board():
        done = '✅' if row['code'] in c_state.get('done', []) and c_state.get('day') == day_key else '▫️'
        lines.append(f"{done} {row['emoji']} <b>{row['title']}</b>\n{row['desc']}\nНаграда: ~{row['gold']} золота, ~{row['xp']} опыта")
    edit_or_send(target, "\n\n".join(lines), contracts_menu())


def show_pvp_hub(target, uid: int) -> None:
    p = get_player(uid) or {}
    text = (
        f"⚔️ <b>Арена и дуэли</b>\n"
        f"Твой рейтинг: <b>{int(p.get('rating', 1000))}</b> · лига: <b>{league_name(int(p.get('rating', 1000)))}</b>\n"
        f"Победы: {int(p.get('wins', 0))} · Поражения: {int(p.get('losses', 0))}\n\n"
        f"<b>Как сражаться в группе:</b>\n"
        f"• напиши <code>пвп @username</code> или ответь на сообщение словом <code>дуэль</code>\n"
        f"• вызванный игрок отвечает на карточку словом «принять» или «отклонить»\n"
        f"• зрители могут ставить на победителя валютой или материалами\n"
        f"• победитель получает трофей из инвентаря проигравшего и долю от ставок\n\n"
        f"<b>Ставка зрителя:</b> ответь на карточку дуэли текстом <code>ставка 50 монет @username</code>.\n"
        f"Можно ставить и материалами: <code>ставка 5 железная руда</code>."
    )
    edit_or_send(target, text, pvp_menu() if is_private_target(target) else None)


def show_ref(target, uid: int) -> None:
    bot_info = bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{uid}"
    refs = get_referrals(uid)
    text = f"🎁 <b>Рефералка</b>\nТвоя ссылка:\n<code>{link}</code>\n\nПриглашено: {len(refs)}\nЗа каждого игрока можно выбрать одну награду: немного золота или реферальный предмет."
    edit_or_send(target, text, referral_menu(uid))


def donate_menu_markup() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    for row in list_packs():
        if not int(row.get('enabled', 1)) or not int(row.get('stars_enabled', 0)) or int(row.get('price_stars', 0)) <= 0:
            continue
        kb.add(InlineKeyboardButton(f"⭐ {row['name']} — {row['price_stars']} звёзд", callback_data=f"donate:buy:{row['code']}"))
    kb.add(InlineKeyboardButton('⬅️ В меню', callback_data='menu:main'))
    return kb


def show_donate(target, uid: int) -> None:
    if not donation_enabled():
        edit_or_send(target, '💫 Донат сейчас отключён владельцем.', back_to_main(uid) if is_private_target(target) else None)
        return
    rows = [r for r in list_packs() if int(r.get('enabled', 1)) and int(r.get('stars_enabled', 0)) and int(r.get('price_stars', 0)) > 0]
    lines = ['💫 <b>Поддержка проекта</b>', 'Покупки внутри Telegram идут в звёздах. Выбери пак ниже.', '']
    if not rows:
        lines.append('Сейчас нет доступных предложений.')
    for row in rows:
        reward = row.get('reward_json') or ''
        lines.append(f"• {row['name']} — {row['price_stars']} ⭐")
    edit_or_send(target, '\n'.join(lines), donate_menu_markup() if is_private_target(target) else None)


def show_info(target) -> None:
    edit_or_send(target, INFO_TEXT, info_menu() if is_private_target(target) else None)


def show_admin(target) -> None:
    edit_or_send(target, "🔐 <b>Панель владельца</b>\nВсе инструменты ниже доступны только владельцу. Даже знание пароля не даст доступ другим аккаунтам.", admin_menu())


# -----------------------------
# Игровые действия
# -----------------------------

def use_item_logic(uid: int, item_id: int) -> tuple[bool, str]:
    if get_item_amount(uid, item_id) <= 0:
        return False, "Предмет не найден."
    item = get_item(item_id)
    p = get_player(uid)
    eff = stats_for_user(uid)
    if is_food(item_id):
        remove_item(uid, item_id, 1)
        hp = min(eff['max_hp'], int(p['hp']) + item['hp_restore'])
        energy = min(eff['max_energy'], int(p['energy']) + item['energy_restore'])
        set_hp_energy(uid, hp, energy)
        return True, f"Съедено {item['name']}. Здоровье {hp}/{eff['max_hp']} · энергия {energy}/{eff['max_energy']}"
    if is_elixir(item_id) or is_scroll(item_id):
        remove_item(uid, item_id, 1)
        texts = [f"Использован {item['name']}."]
        if item['hp_restore'] or item['energy_restore']:
            hp = min(eff['max_hp'], int(p['hp']) + item['hp_restore'])
            energy = min(eff['max_energy'], int(p['energy']) + item['energy_restore'])
            set_hp_energy(uid, hp, energy)
        duration = int(item.get('buffs', {}).get('duration_min', 20)) * 60
        for key, value in item.get('buffs', {}).items():
            if not value or key == 'duration_min':
                continue
            if key == 'slots_plus':
                adjust_player_limits(uid, slots_plus=int(value))
                texts.append(f"Слоты инвентаря +{value}")
            elif key == 'weight_plus':
                adjust_player_limits(uid, weight_plus=int(value))
                texts.append(f"Макс. вес +{value}")
            elif key == 'reroll':
                reset_character_for_reroll(uid)
                texts.append("Персонаж сброшен. Выбери нового зверя заново.")
            elif key == 'steal':
                if random.random() < 0.28:
                    spend_gold(uid, 25)
                    change_reputation(uid, -3)
                    texts.append("Тебя поймали. Штраф 25 монет.")
                else:
                    add_gold(uid, 35)
                    texts.append("Вылазка удалась. +35 монет.")
            elif key == 'spy':
                rows = top_by_rich(1)
                if rows:
                    texts.append(f"Разведка: самый богатый сейчас {get_display_name(int(rows[0]['user_id']))} с {rows[0]['gold']} монетами.")
            elif key == 'pet_token':
                texts.append("Теперь можно выбрать питомца в меню питомца.")
            elif key == 'gift_bonus':
                change_reputation(uid, 2)
                texts.append("Репутация дарителя выросла.")
            else:
                add_buff(uid, key, int(value), duration, item_id)
                texts.append('Активирован эффект: ' + format_bonus_dict({key: int(value)}))
        return True, "\n".join(texts)
    return False, "Этот предмет нельзя использовать таким образом."


def maybe_flag_transfer(sender_id: int, receiver_id: int, item_id: int, amount: int, tag: str) -> None:
    s = get_player(sender_id) or {}
    r = get_player(receiver_id) or {}
    if int(s.get('level', 1)) <= 3 and int(s.get('referrer_id', 0)) == receiver_id:
        add_suspicion(sender_id, "Подозрительный перевод рефералу", f"{tag}: свежий аккаунт перевёл [{item_id}] x{amount} пригласившему игроку.")
    if int(r.get('level', 1)) <= 3 and int(r.get('referrer_id', 0)) == sender_id:
        add_suspicion(receiver_id, "Подозрительный перевод новому рефералу", f"{tag}: основной аккаунт перевёл [{item_id}] x{amount} свежему рефералу.")


def try_spawn_chat_event(message: Message) -> None:
    if message.chat.type == 'private':
        return
    key = f"chat_event:{message.chat.id}"
    current = get_world_state(key, {}) or {}
    if current and current.get('expires_at', 0) > now_ts():
        return
    if random.randint(1, 100) > 2:
        return
    event = maybe_chat_event(message.chat.id)
    state = {"code": event['code'], "title": event['title'], "claimed_by": 0, "expires_at": now_ts() + COOLDOWN_CHAT_EVENT}
    set_world_state(key, state)
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⚡ Участвовать", callback_data=f"chat_event:{message.chat.id}"))
    bot.send_message(message.chat.id, f"✨ <b>{event['title']}</b>\n{event['text']}", reply_markup=kb)


def finish_pvp_request(target, req_id: int) -> None:
    # Совместимость со старыми вызовами: теперь это запуск пошаговой дуэли.
    start_pvp_battle(target, req_id)


def decline_pvp_request(target, req_id: int) -> None:
    from user_data import set_pvp_request_status
    set_pvp_request_status(req_id, 'declined')
    try:
        req = get_pvp_request(req_id) or {}
        if int(req.get('chat_id', 0)) and int(req.get('message_id', 0)):
            bot.edit_message_text('❌ Вызов на арену отклонён.', int(req['chat_id']), int(req['message_id']), reply_markup=None)
            return
    except Exception:
        pass
    edit_or_send(target, '❌ Вызов на арену отклонён.', None)


def parse_interaction_trigger(message: Message) -> bool:
    text = (message.text or '').strip()
    lowered = text.lower()
    uid = message.from_user.id
    target = resolve_target_from_message(message, text)

    gift_words = ['подар', 'переда', 'отда', 'отправь', 'дарю']
    deal_words = ['сделк', 'обмен']
    request_words = ['попрос', 'запрос', 'прошу', 'нужн']
    pvp_words = ['пвп', 'дуэл', 'поедин', 'вызов', 'бой']
    stake_words = ['ставк', 'постав', 'болею', 'голос']
    friend_words = ['друг', 'друж']
    accept_words = ['принят', 'соглас', 'ок', 'го']
    decline_words = ['отклон', 'отказ', 'не буду', 'пас']

    req_pending = resolve_pending_pvp_request(message) if message.chat.type != 'private' else None
    if req_pending and int(req_pending.get('to_user', 0)) == uid and any(word in lowered for word in accept_words):
        start_pvp_battle(message, int(req_pending['id']))
        return True
    if req_pending and uid in {int(req_pending.get('to_user', 0)), int(req_pending.get('from_user', 0))} and any(word in lowered for word in decline_words):
        decline_pvp_request(message, int(req_pending['id']))
        return True

    if any(word in lowered for word in gift_words):
        if not target or int(target['user_id']) == uid:
            send_temp(message.chat.id, 'Укажи игрока ответом на сообщение или через @username.')
            return True
        _, item, amount, err = parse_target_amount_and_item(message, text, verbs=['подарить', 'подарок', 'дарю', 'передать', 'передай', 'отдать', 'отдай', 'отправить'], categories=None)
        if err:
            send_temp(message.chat.id, err)
            return True
        if transfer_item(uid, int(target['user_id']), int(item['id']), int(amount)):
            maybe_flag_transfer(uid, int(target['user_id']), int(item['id']), int(amount), 'Подарок')
            change_reputation(uid, 1)
            send_temp(message.chat.id, f"🎁 {get_display_name(uid)} подарил {get_display_name(int(target['user_id']))}: {format_item_line(int(item['id']), int(amount))}")
        else:
            send_temp(message.chat.id, 'Не удалось отправить подарок. Проверь количество и наличие предмета.')
        return True

    if any(word in lowered for word in deal_words):
        if not target or int(target['user_id']) == uid:
            send_temp(message.chat.id, 'Укажи игрока ответом на сообщение или через @username.')
            return True
        clean = strip_target_tokens(lowered, remove_numeric_ids=True)
        clean = re.sub(r'\b(сделка|обмен)\b', ' ', clean).strip()
        m = re.search(r'(\d+)\s+(.+?)\s+на\s+(\d+)\s+(.+)', clean)
        if not m:
            send_temp(message.chat.id, 'Формат сделки: сделка 3 яблоко на 2 вода')
            return True
        offer_amount = int(m.group(1))
        offer_query = m.group(2).strip()
        want_amount = int(m.group(3))
        want_query = m.group(4).strip()
        offer_item, err1 = resolve_item_query(offer_query)
        want_item, err2 = resolve_item_query(want_query)
        if err1 or err2:
            send_temp(message.chat.id, err1 or err2)
            return True
        deal_id = create_deal(uid, int(target['user_id']), int(offer_item['id']), offer_amount, int(want_item['id']), want_amount, now_ts() + 1200)
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(InlineKeyboardButton('✅ Принять', callback_data=f'deal:ok:{deal_id}'), InlineKeyboardButton('❌ Отклонить', callback_data=f'deal:no:{deal_id}'))
        msg = bot.send_message(message.chat.id, f'🤝 {get_display_name(uid)} предлагает {get_display_name(int(target["user_id"]))} сделку: {format_item_line(int(offer_item["id"]), offer_amount)} ↔️ {format_item_line(int(want_item["id"]), want_amount)}', reply_markup=kb)
        if message.chat.type != 'private':
            safe_delete(message.chat.id, msg.message_id, 300)
        return True

    if any(word in lowered for word in request_words):
        item, amount, err = parse_amount_and_item_query(text, ['попросить', 'запрос', 'прошу', 'нужно', 'нужен', 'нужна'])
        if err:
            send_temp(message.chat.id, err)
            return True
        req_id = create_item_request(uid, int(item['id']), int(amount), now_ts() + 86400)
        send_temp(message.chat.id, f'🙏 Запрос #{req_id} создан: {format_item_line(int(item["id"]), int(amount))}. Другие игроки могут закрыть его частями.')
        return True

    if any(word in lowered for word in stake_words):
        req = resolve_pvp_request_for_bet(message)
        if not req:
            send_temp(message.chat.id, 'Активная дуэль для ставки не найдена. Ответь на карточку дуэли сообщением со ставкой.', ttl=12)
            return True
        if uid in {int(req['from_user']), int(req['to_user'])}:
            send_temp(message.chat.id, 'Участники дуэли не могут ставить на собственный бой.', ttl=12)
            return True
        mentioned = resolve_target_from_message(message, text)
        pick_user = int(mentioned['user_id']) if mentioned and int(mentioned['user_id']) in {int(req['from_user']), int(req['to_user'])} else 0
        if not pick_user:
            low = normalize_lookup(text)
            if 'инициатор' in low or 'перв' in low or 'лев' in low:
                pick_user = int(req['from_user'])
            elif 'защит' in low or 'втор' in low or 'прав' in low:
                pick_user = int(req['to_user'])
        if not pick_user:
            send_temp(message.chat.id, 'Укажи, на кого ставишь: ответь на карточку и напиши, например, «ставка 50 монет @username».', ttl=16)
            return True
        item, amount, err = parse_amount_and_item_query(text, verbs=['ставка', 'ставлю', 'поставить', 'болею', 'голосую'], categories=['currency', 'material'])
        if err:
            send_temp(message.chat.id, err, ttl=16)
            return True
        ok, resp = create_pvp_bet(uid, int(req['id']), pick_user, int(item['id']), int(amount))
        if ok:
            send_temp(message.chat.id, f'📈 Ставка принята: {format_item_line(int(item["id"]), int(amount))} на {get_display_name(pick_user)}', ttl=14)
            try:
                text2, kb2 = render_pvp_card(int(req['id']), for_private=message.chat.type == 'private')
                bot.edit_message_text(text2, int(req['chat_id']), int(req['message_id']), reply_markup=kb2)
            except Exception:
                pass
        else:
            send_temp(message.chat.id, resp, ttl=14)
        return True

    if any(word in lowered for word in pvp_words):
        if target and int(target['user_id']) != uid:
            payload = []
            clean = strip_target_tokens(text, remove_numeric_ids=True)
            clean = re.sub(r'(?i)\b(пвп|дуэль|дуэлька|поединок|вызов|бой)\b', ' ', clean).strip()
            if ' на ' in normalize_lookup(clean):
                suffix = re.split(r'(?i)\bна\b', clean, maxsplit=1)[1].strip()
                stake_item, stake_amount, stake_err = parse_amount_and_item_query(suffix, verbs=[], categories=['currency', 'material'])
                if stake_err:
                    send_temp(message.chat.id, 'Ставка дуэлянтов: ' + stake_err)
                    return True
                payload = [{'item_id': int(stake_item['id']), 'amount': int(stake_amount)}]
                ok, msg_stake = reserve_payload(uid, payload)
                if not ok:
                    send_temp(message.chat.id, msg_stake)
                    return True
            req_id = create_pvp_request(uid, int(target['user_id']), 0, True, now_ts() + 900, message.chat.id, 0, 'mirror', payload)
            text_card, kb = render_pvp_card(req_id, for_private=True)
            msg = bot.send_message(message.chat.id, text_card, reply_markup=kb)
            update_pvp_request_message(req_id, message.chat.id, msg.message_id)
            return True

    if any(word in lowered for word in friend_words):
        if target and int(target['user_id']) != uid:
            add_friend(uid, int(target['user_id']))
            send_temp(message.chat.id, f"🤝 {get_display_name(uid)} и {get_display_name(int(target['user_id']))} теперь друзья.")
            return True
    return False


# -----------------------------
# Команды
# -----------------------------
@bot.pre_checkout_query_handler(func=lambda q: True)
def pre_checkout(pre_checkout_query) -> None:
    try:
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    except Exception:
        pass


@bot.message_handler(content_types=['successful_payment'])
def successful_payment_handler(message: Message) -> None:
    try:
        payload = getattr(message.successful_payment, 'invoice_payload', '') or ''
    except Exception:
        payload = ''
    if not payload.startswith('pack:'):
        return
    code = payload.split(':', 1)[1]
    ok, resp = grant_pack_to_user(message.from_user.id, code)
    if ok:
        edit_or_send(message, f'⭐ <b>Оплата получена</b>\nПак «{code}» выдан.\n{resp}', back_to_main(message.from_user.id))
    else:
        edit_or_send(message, f'⭐ Оплата прошла, но пак выдать не удалось автоматически.\n{resp}', back_to_main(message.from_user.id))


@bot.message_handler(commands=['start'])
def start_cmd(message: Message) -> None:
    maintenance()
    if message.chat.type == 'private':
        ensure_private_reply_keyboard(message, force=True)
    else:
        clear_stale_reply_keyboard(message, force=True)
    raw = message.text or '/start'
    referrer = 0
    m = re.search(r'ref_(\d+)', raw)
    if m:
        referrer = int(m.group(1))
    create_player(message.from_user.id, message.from_user.username or '', full_name_from_user(message.from_user), referrer)
    touch_identity(message.from_user.id, message.from_user.username or '', full_name_from_user(message.from_user))
    p = get_player(message.from_user.id)
    if referrer and referrer != message.from_user.id and suspicious_referral_count(referrer) >= 3:
        add_suspicion(message.from_user.id, 'Много рефералов за сутки', f'Игрок пришёл по ссылке {referrer}. Требуется ручная проверка.')
    if not int(p.get('rules_accepted', 0)):
        bot.send_message(message.chat.id, RULES_TEXT, reply_markup=rules_markup())
        return
    if not int(p.get('registered', 0)):
        bot.send_message(message.chat.id, 'Выбери зверя. После выбора изменить его нельзя без редкого свитка.', reply_markup=chars_markup())
        return
    open_main(message)




@bot.message_handler(commands=['rmkb', 'clearkb'])
def clear_keyboard_cmd(message: Message) -> None:
    clear_stale_reply_keyboard(message, force=True)
    send_temp(message.chat.id, '🧹 Старые кнопки очищены. В личных сообщениях включена новая клавиатура навигации.', ttl=8)



def busy_activity_kind(user_id: int) -> str | None:
    exp = get_world_state(f'expedition_active:{user_id}', None) or {}
    if exp.get('status') == 'active':
        return 'exp'
    dng = get_world_state(f'dungeon_active:{user_id}', None) or {}
    if dng.get('status') == 'active':
        return 'dng'
    return None


def short_menu_command(message: Message, action: str) -> None:
    if message.chat.type == 'private':
        ensure_private_reply_keyboard(message)
    else:
        clear_stale_reply_keyboard(message)
    sync_user(message)
    maintenance()
    safe_delete(message.chat.id, message.message_id, 2)
    if not ensure_player_or_prompt(message):
        return
    if action in {'exp', 'dng'} and message.chat.type != 'private':
        send_temp(message.chat.id, 'Эта активность доступна только в личных сообщениях с ботом.')
        return
    busy_kind = busy_activity_kind(message.from_user.id)
    if busy_kind == 'exp' and action != 'exp':
        show_expedition_menu(message)
        return
    if busy_kind == 'dng' and action != 'dng':
        show_dungeon_menu(message)
        return
    if action == 'main':
        open_main(message)
    elif action == 'profile':
        show_profile(message, message.from_user.id)
    elif action == 'inv':
        show_inventory(message, message.from_user.id, 'all', 0)
    elif action == 'pvp':
        show_pvp_hub(message, message.from_user.id)
    elif action == 'exp':
        show_expedition_menu(message)
    elif action == 'dng':
        show_dungeon_menu(message)
    elif action == 'shop':
        show_shop(message, False, 0)
    elif action == 'black':
        show_shop(message, True, 0)
    elif action == 'market':
        show_market_root(message)
    elif action == 'craft':
        show_craft(message, message.from_user.id, 0)
    elif action == 'bank':
        show_bank(message, message.from_user.id)
    elif action == 'tasks':
        show_tasks(message, message.from_user.id, 'daily')
    elif action == 'boss':
        show_boss(message, message.from_user.id)
    elif action == 'pet':
        show_pet(message, message.from_user.id)
    elif action == 'camp':
        show_camp(message, message.from_user.id)
    elif action == 'clan':
        show_clan(message, message.from_user.id)
    elif action == 'mail':
        show_mail(message, message.from_user.id, 0)
    elif action == 'top':
        edit_or_send(message, '🏆 <b>Рейтинги</b>', top_menu())
    elif action == 'ref':
        show_ref(message, message.from_user.id)
    elif action == 'info':
        show_info(message)
    elif action == 'tal':
        show_talents(message, message.from_user.id)
    elif action == 'fac':
        show_faction(message, message.from_user.id)
    elif action == 'ct':
        show_contracts(message, message.from_user.id)


for cmd, action in [

    ('m', 'main'), ('menu', 'main'), ('p', 'profile'), ('profile', 'profile'), ('inv', 'inv'), ('pvp', 'pvp'), ('x', 'exp'), ('d', 'dng'),
    ('s', 'shop'), ('bm', 'black'), ('mk', 'market'), ('c', 'craft'), ('b', 'bank'), ('task', 'tasks'), ('boss', 'boss'),
    ('pet', 'pet'), ('camp', 'camp'), ('clan', 'clan'), ('mail', 'mail'), ('top', 'top'), ('ref', 'ref'), ('info', 'info'), ('help', 'info'),
    ('tal', 'tal'), ('fac', 'fac'), ('ct', 'ct')
]:
    def _factory(action_name):
        @bot.message_handler(commands=[cmd])
        def _handler(message: Message, action_name=action_name):
            short_menu_command(message, action_name)
        return _handler
    _factory(action)


@bot.message_handler(commands=['adm'])
def admin_login(message: Message) -> None:
    sync_user(message)
    if message.from_user.id != OWNER_ID:
        send_temp(message.chat.id, '⛔ Эта панель доступна только владельцу.')
        return
    parts = (message.text or '').split(maxsplit=1)
    # Для владельца панель открывается даже без пароля: защита идёт по OWNER_ID.
    # Пароль сохранён только как совместимый дополнительный вариант входа.
    if len(parts) >= 2 and parts[1].strip() and parts[1].strip() != ADMIN_PASSWORD:
        send_temp(message.chat.id, '🔐 Неверный пароль. Для владельца можно просто написать /adm')
        return
    OWNER_AUTHED.add(message.from_user.id)
    safe_delete(message.chat.id, message.message_id, 2)
    show_admin(message)


# -----------------------------
# Обработчик текстовых состояний
# -----------------------------

def ask_state(chat_id: int, user_id: int, code: str, prompt: str, payload: dict[str, Any] | None = None) -> None:
    set_user_state(user_id, code, payload or {})
    send_temp(chat_id, prompt, ttl=80)


def handle_state(message: Message, state: dict[str, Any]) -> bool:
    uid = message.from_user.id
    text = (message.text or '').strip()
    code = state['state_code']
    payload = state['payload']
    try:
        if code == 'pvp_bet':
            req = get_pvp_request(int(payload['request_id']))
            if not req:
                clear_user_state(uid)
                send_temp(message.chat.id, 'Дуэль уже недоступна.')
                return True
            item, amount, err = parse_amount_and_item_query(text, verbs=['ставка', 'ставлю', 'поставить', 'болею', 'голосую'], categories=['currency', 'material'])
            if err:
                send_temp(message.chat.id, err)
                return True
            ok, resp = create_pvp_bet(uid, int(payload['request_id']), int(payload['pick_user']), int(item['id']), int(amount))
            if ok:
                clear_user_state(uid)
                send_temp(message.chat.id, f"📈 Ставка принята: {format_item_line(int(item['id']), int(amount))} на {get_display_name(int(payload['pick_user']))}.")
                try:
                    text2, kb2 = render_pvp_card(int(payload['request_id']), for_private=message.chat.type == 'private')
                    bot.edit_message_text(text2, int(req['chat_id']), int(req['message_id']), reply_markup=kb2)
                except Exception:
                    pass
            else:
                send_temp(message.chat.id, resp)
            return True
        if code == 'gift':
            target = resolve_target_from_message(message, text)
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID.')
                return True
            item, amount, err = parse_amount_and_item_query(text, categories=None)
            if err:
                send_temp(message.chat.id, err)
                return True
            if transfer_item(uid, int(target['user_id']), int(item['id']), int(amount)):
                maybe_flag_transfer(uid, int(target['user_id']), int(item['id']), int(amount), 'Подарок')
                change_reputation(uid, 1)
                clear_user_state(uid)
                send_temp(message.chat.id, f'🎁 Подарок отправлен: {format_item_line(int(item["id"]), int(amount))}')
            else:
                send_temp(message.chat.id, 'Не удалось отправить подарок.')
            return True
        if code == 'deal':
            target = resolve_target_from_message(message, text)
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID.')
                return True
            clean = strip_target_tokens(text, remove_numeric_ids=True).lower()
            m = re.search(r'(\d+)\s+(.+?)\s+на\s+(\d+)\s+(.+)', clean)
            if not m:
                send_temp(message.chat.id, 'Формат: @user 3 яблоко на 2 вода')
                return True
            offer_amount = int(m.group(1))
            offer_item, err1 = resolve_item_query(m.group(2).strip())
            want_amount = int(m.group(3))
            want_item, err2 = resolve_item_query(m.group(4).strip())
            if err1 or err2:
                send_temp(message.chat.id, err1 or err2)
                return True
            deal_id = create_deal(uid, int(target['user_id']), int(offer_item['id']), offer_amount, int(want_item['id']), want_amount, now_ts() + 1200)
            clear_user_state(uid)
            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(InlineKeyboardButton('✅ Принять', callback_data=f'deal:ok:{deal_id}'), InlineKeyboardButton('❌ Отклонить', callback_data=f'deal:no:{deal_id}'))
            bot.send_message(message.chat.id, f'🤝 Сделка #{deal_id}: {format_item_line(int(offer_item["id"]), offer_amount)} ↔️ {format_item_line(int(want_item["id"]), want_amount)}', reply_markup=kb)
            return True
        if code == 'request':
            item, amount, err = parse_amount_and_item_query(text)
            if err:
                send_temp(message.chat.id, err)
                return True
            req_id = create_item_request(uid, int(item['id']), int(amount), now_ts() + 86400)
            clear_user_state(uid)
            send_temp(message.chat.id, f'🙏 Запрос #{req_id} создан: {format_item_line(int(item["id"]), int(amount))}.')
            return True
        if code == 'sell':
            clean = strip_target_tokens(text)
            m = re.match(r'(.+?)\s+(\d+)\s+(\d+)$', clean)
            if not m:
                send_temp(message.chat.id, 'Формат: название_предмета количество цена_за_штуку')
                return True
            item, err = resolve_item_query(m.group(1).strip())
            if err:
                send_temp(message.chat.id, err)
                return True
            amount = int(m.group(2))
            price_each = int(m.group(3))
            ok, resp = create_market_listing(uid, int(item['id']), amount, price_each, now_ts() + 86400)
            clear_user_state(uid)
            send_temp(message.chat.id, f'Лот создан #{resp}' if ok else str(resp))
            return True
        if code == 'auction':
            clean = strip_target_tokens(text)
            m = re.match(r'(.+?)\s+(\d+)\s+(\d+)\s+(\d+)$', clean)
            if not m:
                send_temp(message.chat.id, 'Формат: название_предмета количество стартовая_ставка часы')
                return True
            item, err = resolve_item_query(m.group(1).strip())
            if err:
                send_temp(message.chat.id, err)
                return True
            amount = int(m.group(2))
            start_bid = int(m.group(3))
            hours = int(m.group(4))
            ok, resp = create_auction(uid, int(item['id']), amount, start_bid, now_ts() + hours * 3600)
            clear_user_state(uid)
            send_temp(message.chat.id, f'Аукцион создан #{resp}' if ok else str(resp))
            return True
        if code == 'order':
            clean = strip_target_tokens(text)
            m = re.match(r'(.+?)\s+(\d+)\s+(\d+)\s+(\d+)$', clean)
            if not m:
                send_temp(message.chat.id, 'Формат: название_предмета количество цена_за_штуку часы')
                return True
            item, err = resolve_item_query(m.group(1).strip())
            if err:
                send_temp(message.chat.id, err)
                return True
            amount = int(m.group(2))
            price_each = int(m.group(3))
            hours = int(m.group(4))
            ok, resp = create_buy_order(uid, int(item['id']), amount, price_each, now_ts() + hours * 3600)
            clear_user_state(uid)
            send_temp(message.chat.id, f'Заказ создан #{resp}' if ok else str(resp))
            return True
        if code == 'sell_selected':
            nums = [int(n) for n in re.findall(r'\d+', text)]
            if len(nums) < 2:
                send_temp(message.chat.id, 'Напиши: количество цена_за_штуку')
                return True
            amount, price_each = nums[0], nums[1]
            item_id = int(payload['item_id'])
            ok, resp = create_market_listing(uid, item_id, amount, price_each, now_ts() + 86400)
            clear_user_state(uid)
            send_temp(message.chat.id, f'Лот создан #{resp}: {format_item_line(item_id, amount)} по {price_each} мон./шт.' if ok else str(resp))
            return True
        if code == 'auction_selected':
            nums = [int(n) for n in re.findall(r'\d+', text)]
            if len(nums) < 3:
                send_temp(message.chat.id, 'Напиши: количество стартовая_ставка часы')
                return True
            amount, start_bid, hours = nums[0], nums[1], nums[2]
            item_id = int(payload['item_id'])
            ok, resp = create_auction(uid, item_id, amount, start_bid, now_ts() + hours * 3600)
            clear_user_state(uid)
            send_temp(message.chat.id, f'Аукцион создан #{resp}: {format_item_line(item_id, amount)} · старт {start_bid} · {hours} ч.' if ok else str(resp))
            return True
        if code == 'gift_selected':
            target, amount = parse_target_and_amount(message, text, default_amount=1)
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID. После этого напиши количество.')
                return True
            item_id = int(payload['item_id'])
            if transfer_item(uid, int(target['user_id']), item_id, int(amount)):
                maybe_flag_transfer(uid, int(target['user_id']), item_id, int(amount), 'Подарок')
                change_reputation(uid, 1)
                clear_user_state(uid)
                send_temp(message.chat.id, f'🎁 Подарок отправлен: {get_display_name(int(target["user_id"]))} получил {format_item_line(item_id, int(amount))}.')
            else:
                send_temp(message.chat.id, 'Не удалось отправить подарок.')
            return True
        if code == 'auction_bid':
            amount = int(text)
            ok, resp = place_bid(uid, int(payload['auction_id']), amount)
            clear_user_state(uid)
            send_temp(message.chat.id, resp)
            return True
        if code == 'order_fill':
            amount = int(text)
            ok, resp = fulfill_buy_order(uid, int(payload['order_id']), amount)
            clear_user_state(uid)
            send_temp(message.chat.id, resp)
            return True
        if code == 'clan_create':
            ok, resp = create_clan(uid, text[:32])
            clear_user_state(uid)
            send_temp(message.chat.id, f'Стая создана #{resp}' if ok else str(resp))
            return True
        if code == 'clan_join':
            ok, resp = join_clan(uid, int(text))
            clear_user_state(uid)
            send_temp(message.chat.id, resp)
            return True
        if code == 'clan_donate':
            ok, resp = donate_clan_treasury(uid, int(text))
            clear_user_state(uid)
            send_temp(message.chat.id, resp)
            return True
        if code == 'promo':
            ok, resp = redeem_promo(uid, text)
            clear_user_state(uid)
            send_temp(message.chat.id, resp)
            return True
        if code == 'admin_new_item' and uid == OWNER_ID:
            if message.chat.type != 'private':
                send_temp(message.chat.id, 'Этот инструмент работает только в ЛС с ботом.')
                return True
            raw = text.split(maxsplit=1)
            if len(raw) < 2:
                send_temp(message.chat.id, 'Формат: item_id Название предмета')
                return True
            item_id = int(raw[0])
            name = raw[1].strip()[:64]
            if item_id in ITEMS:
                send_temp(message.chat.id, 'Такой ID уже занят. Используй новый ID.')
                return True
            category, rarity, seq = parse_item_identity(item_id)
            payload = {'item_id': item_id, 'name': name, 'category': category, 'rarity': rarity, 'seq': seq}
            set_user_state(uid, 'admin_new_item_template', payload)
            send_temp(message.chat.id, f"🆕 Новый предмет: <b>{name}</b> [{item_id}]\nТип: {CATEGORY_NAMES[category]} · редкость {rarity}\nТеперь выбери шаблон действия.", ttl=120, markup=item_template_keyboard(category))
            return True
        if code == 'admin_new_craft' and uid == OWNER_ID:
            if message.chat.type != 'private':
                send_temp(message.chat.id, 'Этот инструмент работает только в ЛС с ботом.')
                return True
            parts = text.split()
            if len(parts) < 4:
                send_temp(message.chat.id, 'Формат: recipe_id result_item result_amount ingredient_id:qty,ingredient_id:qty')
                return True
            recipe_id = int(parts[0])
            result_item = int(parts[1])
            result_amount = int(parts[2])
            if recipe_id in RECIPES:
                send_temp(message.chat.id, 'Такой ID крафта уже занят.')
                return True
            if result_item not in ITEMS:
                send_temp(message.chat.id, 'Результирующий предмет не найден.')
                return True
            ingredients_raw = ''.join(parts[3:]).split(',')
            ingredients: dict[int, int] = {}
            for chunk in ingredients_raw:
                if ':' not in chunk:
                    raise ValueError
                item_part, amount_part = chunk.split(':', 1)
                ing_id = int(item_part)
                ing_amount = int(amount_part)
                if ing_id not in ITEMS or ing_amount <= 0:
                    raise ValueError
                ingredients[ing_id] = ing_amount
            payload = {
                'recipe_id': recipe_id,
                'result': result_item,
                'result_amount': result_amount,
                'ingredients': ingredients,
                'name': f"Рецепт: {get_item(result_item)['name']}",
            }
            set_user_state(uid, 'admin_new_craft_station', payload)
            send_temp(message.chat.id, '🧪 Крафт разобран. Теперь выбери станцию.', ttl=120, markup=craft_station_keyboard())
            return True
        if code == 'admin_pack' and uid == OWNER_ID:
            target = resolve_target_from_message(message, text)
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID.')
                return True
            clean = strip_target_tokens(text, remove_numeric_ids=True)
            pack, err = resolve_pack_query(clean)
            if err:
                send_temp(message.chat.id, err)
                return True
            ok, resp = grant_pack_to_user(str(pack['code']), int(target['user_id']))
            clear_user_state(uid)
            send_temp(message.chat.id, resp)
            return True
        if code == 'admin_give' and uid == OWNER_ID:
            target = resolve_target_from_message(message, text)
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID.')
                return True
            item, amount, err = parse_amount_and_item_query(text)
            if err:
                send_temp(message.chat.id, err)
                return True
            add_item(int(target['user_id']), int(item['id']), int(amount))
            clear_user_state(uid)
            send_temp(message.chat.id, f'Предмет выдан: {get_display_name(int(target["user_id"]))} получил {format_item_line(int(item["id"]), int(amount))}.')
            return True
        if code == 'admin_take' and uid == OWNER_ID:
            target = resolve_target_from_message(message, text)
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID.')
                return True
            item, amount, err = parse_amount_and_item_query(text)
            if err:
                send_temp(message.chat.id, err)
                return True
            remove_item(int(target['user_id']), int(item['id']), int(amount))
            clear_user_state(uid)
            send_temp(message.chat.id, f'Предмет удалён: у {get_display_name(int(target["user_id"]))} изъято {format_item_line(int(item["id"]), int(amount))}.')
            return True
        if code == 'admin_level' and uid == OWNER_ID:
            target = resolve_target_from_message(message, text)
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID.')
                return True
            cleaned = strip_target_tokens(text, remove_numeric_ids=True)
            nums = [int(n) for n in re.findall(r'\b\d+\b', cleaned)]
            if not nums:
                send_temp(message.chat.id, 'Укажи новый уровень числом.')
                return True
            lvl = nums[0]
            from user_data import set_level
            set_level(int(target['user_id']), lvl)
            clear_user_state(uid)
            send_temp(message.chat.id, f'Уровень изменён: {get_display_name(int(target["user_id"]))} → {lvl}.')
            return True
        if code == 'admin_block' and uid == OWNER_ID:
            target = resolve_target_from_message(message, text)
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID.')
                return True
            set_blocked(int(target['user_id']), True)
            clear_user_state(uid)
            send_temp(message.chat.id, f'Игрок заблокирован: {get_display_name(int(target["user_id"]))}.')
            return True
        if code == 'admin_unblock' and uid == OWNER_ID:
            target = resolve_target_from_message(message, text)
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID.')
                return True
            set_blocked(int(target['user_id']), False)
            clear_user_state(uid)
            send_temp(message.chat.id, f'Игрок разблокирован: {get_display_name(int(target["user_id"]))}.')
            return True
        if code == 'admin_add' and uid == OWNER_ID:
            target = resolve_target_from_message(message, text)
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID.')
                return True
            add_admin(int(target['user_id']))
            clear_user_state(uid)
            send_temp(message.chat.id, f'Админ добавлен: {get_display_name(int(target["user_id"]))}.')
            return True
        if code == 'admin_del' and uid == OWNER_ID:
            target = resolve_target_from_message(message, text)
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID.')
                return True
            remove_admin(int(target['user_id']))
            clear_user_state(uid)
            send_temp(message.chat.id, f'Админ удалён: {get_display_name(int(target["user_id"]))}.')
            return True
        if code == 'admin_bank_debt' and uid == OWNER_ID:
            target = resolve_target_from_message(message, text)
            parts = text.split()
            amount_part = None
            for token in reversed(parts):
                if re.fullmatch(r'-?\d+', token):
                    amount_part = token
                    break
            if not target or amount_part is None:
                send_temp(message.chat.id, 'Формат: @username сумма. 0 — аннулировать, отрицательное число — уменьшить долг, положительное — установить долг.')
                return True
            amount_val = int(amount_part)
            if amount_val < 0:
                ok2, msg2 = reduce_bank_debt_admin(int(target['user_id']), abs(amount_val))
            else:
                ok2, msg2 = set_bank_debt_admin(int(target['user_id']), amount_val)
            clear_user_state(uid)
            send_temp(message.chat.id, msg2)
            return True
        if code == 'admin_pack_stars_price' and uid == OWNER_ID:
            parts = text.split()
            if len(parts) != 2:
                send_temp(message.chat.id, 'Формат: код_пака цена_в_звёздах. Пример: starter_pack 35')
                return True
            ok2, msg2 = set_pack_stars_price(parts[0], int(parts[1]))
            clear_user_state(uid)
            send_temp(message.chat.id, msg2)
            return True
        if code == 'admin_give_selected' and uid == OWNER_ID:
            target, amount = parse_target_and_amount(message, text, default_amount=1)
            item_id = int(payload['item_id'])
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID. После этого напиши количество.')
                return True
            add_item(int(target['user_id']), item_id, int(amount))
            clear_user_state(uid)
            send_temp(message.chat.id, f'Предмет выдан: {get_display_name(int(target["user_id"]))} получил {format_item_line(item_id, int(amount))}.')
            return True
        if code == 'admin_take_selected' and uid == OWNER_ID:
            target, amount = parse_target_and_amount(message, text, default_amount=1)
            item_id = int(payload['item_id'])
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID. После этого напиши количество.')
                return True
            remove_item(int(target['user_id']), item_id, int(amount))
            clear_user_state(uid)
            send_temp(message.chat.id, f'Предмет удалён: у {get_display_name(int(target["user_id"]))} изъято {format_item_line(item_id, int(amount))}.')
            return True
        if code == 'admin_pack_selected' and uid == OWNER_ID:
            target = resolve_target_from_message(message, text)
            if not target:
                send_temp(message.chat.id, 'Укажи игрока ответом на сообщение, через @username или ID.')
                return True
            ok, resp = grant_pack_to_user(str(payload['pack_code']), int(target['user_id']))
            clear_user_state(uid)
            send_temp(message.chat.id, resp)
            return True
        if code == 'admin_promo' and uid == OWNER_ID:
            parts = text.split()
            if len(parts) < 4:
                send_temp(message.chat.id, 'Понятный формат: КОД количество_активаций золото премиум. Пример: VESNA2026 50 100 2')
                return True
            code_promo, uses, gold, premium = parts[0], int(parts[1]), int(parts[2]), int(parts[3])
            create_promo(code_promo, {'gold': gold, 'premium': premium}, uses)
            clear_user_state(uid)
            send_temp(message.chat.id, f'Промокод создан: {code_promo} · активаций {uses} · золото {gold} · премиум {premium}.')
            return True
    except Exception:
        send_temp(message.chat.id, 'Неверный формат данных для этого действия.')
        return True
    return False


# -----------------------------
# Callback-кнопки
# -----------------------------

def show_expedition_menu(target) -> None:
    kb = InlineKeyboardMarkup(row_width=2)
    for code, label in [('easy', 'Лёгкая'), ('normal', 'Нормальная'), ('hard', 'Сложная'), ('nightmare', 'Кошмарная')]:
        kb.add(InlineKeyboardButton(label, callback_data=f'exp:{code}'))
    kb.add(InlineKeyboardButton('⬅️ В меню', callback_data='menu:main'))
    edit_or_send(target, '🧭 <b>Экспедиция</b>\nВыбери сложность.', kb)


def show_dungeon_menu(target) -> None:
    kb = InlineKeyboardMarkup(row_width=3)
    for diff, label in [('easy', 'Лёгк.'), ('medium', 'Сред.'), ('hard', 'Сложн.')]:
        for floor in [1, 5, 10, 15]:
            kb.add(InlineKeyboardButton(f'{label} {floor}', callback_data=f'dng:{diff}:{floor}'))
    kb.add(InlineKeyboardButton('⬅️ В меню', callback_data='menu:main'))
    edit_or_send(target, '🏰 <b>Подземелья</b>\nСегодняшний модификатор выбирается автоматически.', kb)


@bot.callback_query_handler(func=lambda call: True)
def callbacks(call) -> None:
    maintenance()
    uid = call.from_user.id
    data = call.data or ''
    if data.startswith('reg:accept'):
        set_rules_accepted(uid)
        answer_cb(call, 'Правила приняты')
        edit_or_send(call, 'Теперь выбери зверя. Это решение необратимо без редкого свитка.', chars_markup())
        return
    if data.startswith('char:'):
        key = data.split(':', 1)[1]
        p = get_player(uid)
        if int(p.get('registered', 0)):
            answer_cb(call, 'Персонаж уже выбран')
            return
        register_character(uid, key)
        answer_cb(call, 'Зверь выбран')
        open_main(call)
        return

    if not ensure_player_or_prompt(call):
        return

    busy_kind = busy_activity_kind(uid)
    if busy_kind == 'exp' and not (data == 'menu:exp' or data.startswith('exp:')):
        show_expedition_menu(call)
        return
    if busy_kind == 'dng' and not (data == 'menu:dng' or data.startswith('dng:') or data.startswith('dngb:')):
        show_dungeon_menu(call)
        return

    if data.startswith('adminitemtpl:') and uid == OWNER_ID:
        template_code = data.split(':', 1)[1]
        ok, msg = finalize_custom_item(uid, template_code)
        answer_cb(call, 'Готово' if ok else 'Отменено')
        edit_or_send(call, msg, admin_menu() if ok else simple_back('menu:admin'))
        return
    if data.startswith('admincraftstation:') and uid == OWNER_ID:
        station_code = data.split(':', 1)[1]
        ok, msg = finalize_custom_recipe(uid, station_code)
        answer_cb(call, 'Готово' if ok else 'Отменено')
        edit_or_send(call, msg, admin_menu() if ok else simple_back('menu:admin'))
        return

    if data == 'menu:main':
        answer_cb(call)
        open_main(call)
        return
    if data == 'menu:profile':
        show_profile(call, uid)
        return
    if data == 'menu:pvp':
        show_pvp_hub(call, uid)
        return
    if data == 'menu:gear':
        show_gear(call, uid)
        return
    if data == 'menu:tal':
        show_talents(call, uid)
        return
    if data == 'menu:faction':
        show_faction(call, uid)
        return
    if data == 'menu:contracts':
        show_contracts(call, uid)
        return
    if data.startswith('menu:inv:'):
        show_inventory(call, uid, 'all', int(data.split(':')[2]))
        return
    if data.startswith('invcat:'):
        _, cat, page = data.split(':')
        show_inventory(call, uid, cat, int(page))
        return
    if data.startswith('item:'):
        _, item_id, cat, page = data.split(':')
        show_item(call, uid, int(item_id), cat, int(page))
        return
    if data.startswith('use:equip:'):
        ok, msg = equip_item(uid, int(data.split(':')[2]))
        answer_cb(call, msg)
        show_gear(call, uid)
        return
    if data.startswith('use:item:'):
        ok, msg = use_item_logic(uid, int(data.split(':')[2]))
        answer_cb(call, msg[:100])
        edit_or_send(call, msg, back_to_main(uid))
        return
    if data.startswith('gear:off:'):
        ok, msg = unequip_slot(uid, data.split(':')[2])
        answer_cb(call, msg)
        show_gear(call, uid)
        return
    if data == 'gear:repair':
        cost, count = repair_all(uid)
        if cost == -1:
            answer_cb(call, 'Не хватает золота')
        else:
            answer_cb(call, f'Починено слотов: {count}, цена: {cost}')
        show_gear(call, uid)
        return

    if data == 'menu:exp':
        show_expedition_menu(call)
        return
    if data.startswith('exp:'):
        if not is_private_target(call.message):
            answer_cb(call, 'Экспедиция доступна только в ЛС')
            return
        parts = data.split(':')
        active = get_active_expedition(uid)
        if len(parts) >= 2 and parts[1] == 'claim':
            if not active:
                answer_cb(call, 'Активной экспедиции нет')
                show_expedition_menu(call)
                return
            left = max(0, int(active['ends_at']) - now_ts())
            if left > 0:
                answer_cb(call, f'Ещё осталось {format_seconds(left)}')
                show_expedition_menu(call)
                return
            damage_equipment(uid, 1)
            from user_data import advance_task
            advance_task(uid, 'expeditions', 1)
            res = active['result']
            reward = reward_player(uid, int(res['gold']), int(res['xp']), res['loot'], 'expedition' if res['success'] else 'expedition_fail')
            clear_active_expedition(uid)
            text = f"🧭 <b>Экспедиция завершена</b>\nСложность: {active['title']}\n" + "\n".join(expedition_result_lines(active)) + f"\n\n{reward}"
            edit_or_send(call, text, back_to_main(uid))
            answer_cb(call, 'Награда получена')
            return
        if len(parts) >= 2 and parts[1] == 'stop':
            if not active:
                answer_cb(call, 'Активной экспедиции нет')
                show_expedition_menu(call)
                return
            clear_active_expedition(uid)
            set_cooldown(uid, 'exp', max(300, COOLDOWN_EXPEDITION // 3))
            edit_or_send(call, '⏹ Экспедиция прервана. Награда не выдана, герой возвращается с пустыми лапами.', back_to_main(uid))
            answer_cb(call, 'Экспедиция прервана')
            return
        if len(parts) >= 3 and parts[1] == 'start':
            diff = parts[2]
            if active:
                show_expedition_menu(call)
                answer_cb(call, 'Сначала заверши текущую экспедицию')
                return
            rem = get_cooldown_remaining(uid, 'exp')
            if rem > 0:
                answer_cb(call, f'Откат {format_seconds(rem)}')
                return
            if get_death_remaining(uid) > 0:
                answer_cb(call, f'Ты ранен ещё {format_seconds(get_death_remaining(uid))}')
                return
            res = run_expedition(get_player(uid), get_equipment(uid), get_buffs(uid), diff, extras_for_user(uid))
            state = {
                'status': 'active',
                'difficulty': diff,
                'title': {'easy': 'Лёгкая', 'normal': 'Нормальная', 'hard': 'Сложная', 'nightmare': 'Кошмарная'}[diff],
                'started_at': now_ts(),
                'ends_at': now_ts() + int(EXPEDITION_DURATIONS.get(diff, 1800)),
                'result': res,
            }
            save_active_expedition(uid, state)
            set_cooldown(uid, 'exp', int(EXPEDITION_DURATIONS.get(diff, 1800)))
            show_expedition_menu(call)
            answer_cb(call, 'Экспедиция началась')
            return
    if data == 'menu:dng':
        show_dungeon_menu(call)
        return
    if data.startswith('dng:'):
        if not is_private_target(call.message):
            answer_cb(call, 'Подземелье доступно только в ЛС')
            return
        parts = data.split(':')
        if len(parts) >= 4 and parts[1] == 'start':
            active = get_active_dungeon(uid)
            if active:
                show_dungeon_menu(call)
                answer_cb(call, 'Сначала заверши текущий поход')
                return
            rem = get_cooldown_remaining(uid, 'dng')
            if rem > 0:
                answer_cb(call, f'Откат {format_seconds(rem)}')
                return
            diff = parts[2]
            floor = int(parts[3])
            ok, msg, state = build_dungeon_battle(uid, diff, floor)
            if not ok or not state:
                answer_cb(call, msg)
                show_dungeon_menu(call)
                return
            save_active_dungeon(uid, state)
            answer_cb(call, 'Поход начался')
            show_dungeon_menu(call)
            return
    if data.startswith('dngb:'):
        if not is_private_target(call.message):
            answer_cb(call, 'Подземелье доступно только в ЛС')
            return
        state = get_active_dungeon(uid)
        if not state:
            answer_cb(call, 'Активного похода нет')
            show_dungeon_menu(call)
            return
        if int(state.get('expires_at', 0)) <= now_ts():
            dungeon_finish_fail(call, state, 'Время на зачистку истекло.')
            answer_cb(call, 'Поход сорван')
            return
        parts = data.split(':')
        action = parts[1]
        if action == 'itemmenu':
            page = int(parts[2]) if len(parts) > 2 else 0
            edit_or_send(call, dungeon_text(state, item_menu=True), dungeon_markup(state, item_menu=True, page=page))
            answer_cb(call)
            return
        if action == 'itempick':
            item_id = int(parts[2])
            ok, msg = dungeon_use_item(state, item_id)
            if ok:
                dungeon_enemy_turn(state)
                save_active_dungeon(uid, state)
                if int(state['player']['hp']) <= 0:
                    dungeon_finish_fail(call, state, 'Герой пал после применения предмета.')
                else:
                    show_dungeon_menu(call)
            else:
                edit_or_send(call, dungeon_text(state, item_menu=True), dungeon_markup(state, item_menu=True, page=0))
            answer_cb(call, msg[:180])
            return
        if action == 'flee':
            clear_active_dungeon(uid)
            set_cooldown(uid, 'dng', max(300, COOLDOWN_DUNGEON // 3))
            edit_or_send(call, '🏃 Ты покинул подземелье. Награда не выдана.', back_to_main(uid))
            answer_cb(call, 'Ты сбежал')
            return
        if action == 'dodge':
            state['dodging'] = True
            state['player']['energy'] = min(int(state['stats']['max_energy']), int(state['player']['energy']) + 10)
            state['log'].append('Ты уходишь в уклонение и готовишься к ответному ходу.')
            dungeon_enemy_turn(state)
            save_active_dungeon(uid, state)
            if int(state['player']['hp']) <= 0:
                dungeon_finish_fail(call, state, 'Противник догнал тебя даже в уклонении.')
            else:
                show_dungeon_menu(call)
            answer_cb(call)
            return
        if action == 'hit':
            dungeon_player_attack(state)
            if int(state['enemy']['hp']) <= 0:
                dungeon_finish_victory(call, state)
                answer_cb(call, 'Победа!')
                return
            dungeon_enemy_turn(state)
            save_active_dungeon(uid, state)
            if int(state['player']['hp']) <= 0:
                dungeon_finish_fail(call, state, 'Герой пал в бою.')
            else:
                show_dungeon_menu(call)
            answer_cb(call)
            return
    if data.startswith('menu:shop:'):
        show_shop(call, False, int(data.split(':')[2]))
        return
    if data.startswith('menu:black:'):
        show_shop(call, True, int(data.split(':')[2]))
        return
    if data.startswith('shopbuy:'):
        _, item_id, black = data.split(':')
        stock = generate_black_market_stock() if black == '1' else generate_shop_stock()
        row = next((x for x in stock if x['item_id'] == int(item_id)), None)
        if not row:
            answer_cb(call, 'Товар уже обновился')
            return
        if not spend_gold(uid, int(row['price'])):
            answer_cb(call, 'Не хватает монет')
            return
        add_item(uid, int(item_id), 1)
        from user_data import advance_task
        advance_task(uid, 'buy_market', 1)
        answer_cb(call, 'Покупка успешна')
        show_shop(call, black == '1', 0)
        return
    if data == 'menu:market':
        show_market_root(call)
        return
    if data.startswith('market:list:'):
        show_market_list(call, int(data.split(':')[2]))
        return
    if data.startswith('market:buy:'):
        ok, msg = buy_market_listing(uid, int(data.split(':')[2]))
        answer_cb(call, msg)
        show_market_list(call, 0)
        return
    if data.startswith('auction:list:'):
        show_auctions(call, int(data.split(':')[2]))
        return
    if data.startswith('auction:bid:'):
        ask_state(call.message.chat.id, uid, 'auction_bid', f'Введи сумму ставки для аукциона #{data.split(":")[2]}', {'auction_id': int(data.split(':')[2])})
        answer_cb(call, 'Жду ставку в следующем сообщении')
        return
    if data.startswith('orders:list:'):
        show_orders(call, int(data.split(':')[2]))
        return
    if data.startswith('orders:fill:'):
        ask_state(call.message.chat.id, uid, 'order_fill', f'Введи количество предмета для заказа #{data.split(":")[2]}', {'order_id': int(data.split(':')[2])})
        answer_cb(call, 'Жду количество')
        return
    if data == 'menu:craft:0' or data.startswith('menu:craft:'):
        show_craft(call, uid, int(data.split(':')[2]))
        return
    if data.startswith('craft:'):
        _, recipe_id, page = data.split(':')
        inventory_amounts = {row['item_id']: row['amount'] for row in get_inventory(uid)}
        preview = craft_preview(int(recipe_id), inventory_amounts)
        recipe = preview['recipe']
        if preview['missing']:
            missing_lines = [f"• {get_item(i)['name']} x{a}" for i, a in preview['missing']]
            edit_or_send(call, f"Не хватает материалов для рецепта #{recipe_id}:\n" + "\n".join(missing_lines), simple_back(f'menu:craft:{page}'))
            return
        p = get_player(uid)
        if int(p.get('level', 1)) < int(recipe['required_level']):
            answer_cb(call, 'Мало уровня')
            return
        for item_id, amount in recipe['ingredients'].items():
            remove_item(uid, item_id, amount)
        add_item(uid, int(recipe['result']), int(recipe['result_amount']))
        from user_data import advance_task
        advance_task(uid, 'craft', 1)
        edit_or_send(call, f"⚒ Скрафчено:\n{format_item_line(int(recipe['result']), int(recipe['result_amount']))}", simple_back(f'menu:craft:{page}'))
        return
    if data == 'menu:bank':
        show_bank(call, uid)
        return
    if data == 'bank:loan':
        rem = get_cooldown_remaining(uid, 'bank')
        if rem > 0:
            answer_cb(call, f'Откат {format_seconds(rem)}')
            return
        offer = loan_offer(get_player(uid))
        ok, msg = create_loan(uid, offer['amount'])
        set_cooldown(uid, 'bank', COOLDOWN_BANK)
        edit_or_send(call, msg, back_to_main(uid))
        return
    if data == 'bank:repay':
        ok, msg = repay_loan(uid)
        edit_or_send(call, msg, back_to_main(uid))
        return
    if data == 'menu:tasks':
        show_tasks(call, uid, 'daily')
        return
    if data == 'tasks:daily':
        show_tasks(call, uid, 'daily')
        return
    if data == 'tasks:weekly':
        show_tasks(call, uid, 'weekly')
        return
    if data.startswith('task:'):
        _, kind, code = data.split(':')
        day, week = ensure_task_sets(uid)
        key = day if kind == 'daily' else week
        ok, msg = claim_task(uid, key, kind, code)
        answer_cb(call, msg)
        show_tasks(call, uid, kind)
        return
    if data == 'menu:boss':
        show_boss(call, uid)
        return
    if data == 'boss:hit':
        rem = get_cooldown_remaining(uid, 'boss')
        if rem > 0:
            answer_cb(call, f'Откат {format_seconds(rem)}')
            return
        state = get_boss_state()
        stats = stats_for_user(uid)
        result = world_boss_attack(get_player(uid), stats, int(state['attacks'].get(str(uid), 0)))
        if not result['ok']:
            answer_cb(call, result['text'])
            return
        state['hp_left'] = max(0, int(state['hp_left']) - int(result['damage']))
        state['damage'][str(uid)] = int(state['damage'].get(str(uid), 0)) + int(result['damage'])
        state['attacks'][str(uid)] = int(state['attacks'].get(str(uid), 0)) + 1
        save = f"Критический удар!" if result['crit'] else 'Удар засчитан.'
        if state['hp_left'] == 0 and not state.get('killed'):
            state['killed'] = True
            add_gold(uid, result['reward_gold'] + 120)
            from user_data import add_xp, advance_task
            add_xp(uid, result['reward_xp'] + WORLD_BOSS_KILL_BONUS)
            advance_task(uid, 'boss', 1)
            edit_or_send(call, f"🌍 Босс повержен!\nТвой урон: {result['damage']}\n{save}\nНаграда усилена добиванием.", back_to_main(uid))
        else:
            add_gold(uid, result['reward_gold'])
            from user_data import add_xp, advance_task
            add_xp(uid, result['reward_xp'] + WORLD_BOSS_PARTICIPATION_XP)
            advance_task(uid, 'boss', 1)
            edit_or_send(call, f"🌍 Урон по боссу: {result['damage']}\nОсталось HP: {state['hp_left']}\n{save}", back_to_main(uid))
        set_world_state('world_boss', state)
        set_cooldown(uid, 'boss', COOLDOWN_WORLD_BOSS)
        apply_level_sync(uid)
        return
    if data == 'boss:top':
        state = get_boss_state()
        ranking = sorted(state['damage'].items(), key=lambda x: x[1], reverse=True)[:10]
        lines = ["🏅 <b>Топ урона по боссу</b>"]
        for i, (user_id, dmg) in enumerate(ranking, start=1):
            lines.append(f"{i}. {get_display_name(int(user_id))} — {dmg}")
        edit_or_send(call, "\n".join(lines), simple_back('menu:boss'))
        return
    if data == 'menu:pet':
        show_pet(call, uid)
        return
    if data.startswith('pet:set:'):
        if get_item_amount(uid, PET_TOKEN_ID) <= 0 and not get_player(uid).get('pet_species'):
            answer_cb(call, 'Нужен жетон питомца')
            return
        if not get_player(uid).get('pet_species'):
            remove_item(uid, PET_TOKEN_ID, 1)
        set_pet(uid, data.split(':')[2])
        show_pet(call, uid)
        return
    if data == 'pet:train':
        if not spend_gold(uid, 50):
            answer_cb(call, 'Нужно 50 монет')
            return
        train_pet(uid, 1)
        show_pet(call, uid)
        return
    if data == 'menu:camp':
        show_camp(call, uid)
        return
    if data.startswith('camp:start:'):
        rem = get_cooldown_remaining(uid, 'camp')
        if rem > 0:
            answer_cb(call, f'Откат {format_seconds(rem)}')
            return
        hours = int(data.split(':')[2])
        from user_data import set_camp
        set_camp(uid, now_ts() + hours*3600, hours)
        set_cooldown(uid, 'camp', COOLDOWN_CAMP_START)
        show_camp(call, uid)
        return
    if data == 'camp:claim':
        p = get_player(uid)
        remain = max(0, int(p.get('camp_until', 0)) - now_ts())
        if remain > 0:
            answer_cb(call, f'Ещё {format_seconds(remain)}')
            return
        hours = max(0, int(p.get('camp_hours', 0)))
        if hours <= 0:
            answer_cb(call, 'Лагерь не активен')
            return
        reward = camp_rewards(p, hours)
        clear_camp(uid)
        text = reward_player(uid, reward['gold'], reward['xp'], reward['loot'], 'camp')
        edit_or_send(call, f"⛺ Награда лагеря\n\n{text}", back_to_main(uid))
        return
    if data == 'menu:clan':
        show_clan(call, uid)
        return
    if data == 'clan:list':
        rows = list_clans(12)
        text = "🐺 <b>Стаи</b>\n\n" + "\n".join([f"#{r['id']} {r['name']} · казна {r['treasury']} · реп {r['reputation']}" for r in rows] or ['Стай пока нет.'])
        edit_or_send(call, text, simple_back('menu:clan'))
        return
    if data == 'clan:my':
        show_clan(call, uid)
        return
    if data == 'clan:leave':
        ok, msg = leave_clan(uid)
        edit_or_send(call, msg, back_to_main(uid))
        return
    if data == 'menu:mail:0' or data.startswith('menu:mail:'):
        show_mail(call, uid, int(data.split(':')[2]))
        return
    if data.startswith('mail:'):
        _, mail_id, page = data.split(':')
        row = read_mail(int(mail_id))
        if row and int(row['to_user']) == uid:
            mark_mail_read(int(mail_id))
            edit_or_send(call, f"✉️ <b>{row['subject']}</b>\n\n{row['body']}", simple_back(f'menu:mail:{page}'))
        return
    if data == 'menu:logs':
        show_logs(call, uid)
        return
    if data == 'menu:top':
        edit_or_send(call, '🏆 <b>Рейтинги</b>', top_menu())
        return
    if data.startswith('top:'):
        show_top(call, data.split(':')[1])
        return
    if data == 'menu:ref':
        show_ref(call, uid)
        return
    if data.startswith('ref:claim:'):
        _, _, referred_id, choice = data.split(':')
        ok, msg = set_referral_reward_choice(int(referred_id), choice)
        answer_cb(call, msg)
        show_ref(call, uid)
        return
    if data == 'menu:info':
        show_info(call)
        return
    if data == 'info:rules':
        edit_or_send(call, RULES_TEXT, info_menu())
        return
    if data == 'info:lore':
        edit_or_send(call, LORE_TEXT, info_menu())
        return
    if data == 'info:map':
        edit_or_send(call, MAP_TEXT, info_menu())
        return
    if data == 'info:cmd':
        lines = ['⌨️ <b>Команды и русские аналоги</b>', '']
        order = [
            ('main', '/m', 'главное меню'), ('profile', '/p', 'профиль'), ('inv', '/inv', 'инвентарь'), ('exp', '/x', 'экспедиция'),
            ('dng', '/d', 'подземелье'), ('shop', '/s', 'магазин'), ('black', '/bm', 'чёрный рынок'), ('market', '/mk', 'рынок и аукцион'),
            ('craft', '/c', 'крафт'), ('bank', '/b', 'банк'), ('tasks', '/task', 'задания'), ('boss', '/boss', 'мировой босс'),
            ('pet', '/pet', 'питомец'), ('camp', '/camp', 'лагерь офлайн'), ('clan', '/clan', 'стая / клан'), ('mail', '/mail', 'почта'),
            ('top', '/top', 'рейтинги'), ('ref', '/ref', 'рефералка'), ('info', '/info', 'инфо и правила'), ('tal', '/tal', 'таланты'),
            ('fac', '/fac', 'фракция'), ('ct', '/ct', 'контракты'), ('adm', '/adm', 'секретная панель владельца'),
        ]
        for action, cmd, desc in order:
            lines.append(f"{cmd} — {desc}")
            lines.append('Русские варианты: ' + ', '.join(COMMAND_RU_SYNONYMS.get(action, [])[:5]))
            lines.append('')
        edit_or_send(call, '\n'.join(lines), info_menu())
        return
    if data == 'info:economy':
        eco = economy_snapshot()
        txt = f"📈 <b>Экономика дня</b>\nСпрос: {category_title_ru(eco['demand'])}\nИзбыток: {category_title_ru(eco['surplus'])}\nМагазин автоматически подстраивает цены и ассортимент под тренд дня."
        edit_or_send(call, txt, info_menu())
        return
    if data == 'menu:spec':
        edit_or_send(call, '✨ <b>Выбери специализацию</b>', spec_menu())
        return
    if data.startswith('spec:'):
        set_specialization(uid, data.split(':')[1])
        show_profile(call, uid)
        return
    if data.startswith('talent:up:'):
        code = data.split(':')[2]
        talent = TALENTS.get(code)
        if not talent:
            answer_cb(call, 'Талант не найден')
            return
        ok, msg = learn_talent(uid, code, int(talent['max_rank']))
        answer_cb(call, msg)
        show_talents(call, uid)
        return
    if data == 'talent:reset':
        ok, msg = reset_talents(uid)
        answer_cb(call, msg)
        show_talents(call, uid)
        return
    if data.startswith('faction:join:'):
        key = data.split(':')[2]
        if key not in FACTIONS:
            answer_cb(call, 'Фракция не найдена')
            return
        ok, msg = set_faction(uid, key)
        answer_cb(call, msg)
        show_faction(call, uid)
        return
    if data == 'faction:claim':
        extra = extras_for_user(uid)
        if not extra.get('faction_key'):
            answer_cb(call, 'Сначала вступи во фракцию')
            return
        ok, payload = claim_faction_daily(uid, int(time.time() // 86400))
        if not ok:
            answer_cb(call, payload.get('reason', 'Уже забрано'))
            return
        reward = faction_daily_reward(extra)
        if reward.get('gold'):
            add_gold(uid, int(reward['gold']))
        if reward.get('item'):
            add_item(uid, int(reward['item']), 1)
        add_faction_rep(uid, 2)
        txt = f"🏛 Жалование фракции получено.\n💰 +{reward.get('gold',0)}"
        if reward.get('item'):
            txt += f"\n{format_item_line(int(reward['item']), 1)}"
        edit_or_send(call, txt, simple_back('menu:faction'))
        return
    if data.startswith('contract:run:'):
        code = data.split(':')[2]
        ok, reason = can_run_contract(uid, code, int(time.time() // 86400))
        if not ok:
            answer_cb(call, reason)
            return
        res = run_contract(get_player(uid), get_equipment(uid), get_buffs(uid), code, extras_for_user(uid))
        if not res.get('ok'):
            answer_cb(call, res.get('text', 'Ошибка'))
            return
        mark_contract_done(uid, code, int(time.time() // 86400))
        add_faction_rep(uid, 1)
        text = reward_player(uid, int(res['gold']), int(res['xp']), res['loot'], 'contract')
        head = f"🧾 <b>{res['contract']['title']}</b>\nСтатус: {res['text']}\nШанс: {int(res['chance']*100)}%\n\n"
        edit_or_send(call, head + text, simple_back('menu:contracts'))
        return
    if data == 'prestige:do':
        ok, msg = perform_prestige(uid)
        answer_cb(call, msg[:90])
        show_profile(call, uid)
        return
    if data == 'menu:admin':
        if uid != OWNER_ID:
            answer_cb(call, 'Только владелец бота')
            return
        OWNER_AUTHED.add(uid)
        show_admin(call)
        return
    if data == 'admin:packs' and uid == OWNER_ID:
        rows = list_packs()
        lines = ['💎 <b>Донат-паки</b>']
        kb = InlineKeyboardMarkup(row_width=1)
        for row in rows:
            lines.append(f"• {row['code']} · {row['name']} · {row.get('price_stars', 0)} ⭐ · {'вкл.' if row['enabled'] else 'выкл.'}")
            kb.add(InlineKeyboardButton(f"Переключить {row['code']}", callback_data=f"admin:togglepack:{row['code']}"))
        kb.add(InlineKeyboardButton('⬅️ Админ', callback_data='menu:admin'))
        edit_or_send(call, '\n'.join(lines), kb)
        return
    if data.startswith('admin:togglepack:') and uid == OWNER_ID:
        toggle_pack(data.split(':')[2])
        show_admin(call)
        return
    if data == 'admin:promos' and uid == OWNER_ID:
        rows = list_promos()
        text = '🎟 <b>Промокоды</b>\n\n' + '\n'.join([f"• {r['code']} · осталось активаций {r['uses_left']}" for r in rows] or ['Пусто.'])
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton('➕ Создать', callback_data='state:admin_promo'), InlineKeyboardButton('⬅️ Админ', callback_data='menu:admin'))
        edit_or_send(call, text, kb)
        return
    if data == 'admin:sus' and uid == OWNER_ID:
        rows = list_suspicions(False, 20)
        text = '🚨 <b>Подозрения</b>\n\n' + '\n'.join([f"• #{r['id']} {get_display_name(int(r['user_id']))}: {r['reason']}" for r in rows] or ['Пусто.'])
        edit_or_send(call, text, simple_back('menu:admin'))
        return
    if data == 'admin:donate' and uid == OWNER_ID:
        rows = list_packs()
        state = 'включён' if donation_enabled() else 'выключен'
        lines = [f'💫 <b>Донат и звёзды</b>', f'Глобальный статус: <b>{state}</b>', '', 'Каждый пак можно отдельно включать и выключать, а также задавать цену в звёздах.']
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton('🔁 Вкл/выкл весь донат', callback_data='admin:donate:toggle'))
        kb.add(InlineKeyboardButton('💠 Цена в звёздах', callback_data='state:admin_pack_stars_price'))
        for row in rows:
            lines.append(f"• {row['code']} · {row['name']} · {row.get('price_stars', 0)} ⭐ · {'звёзды вкл.' if row.get('stars_enabled') else 'звёзды выкл.'}")
            kb.add(InlineKeyboardButton(f"Переключить ⭐ {row['code']}", callback_data=f"admin:starspack:{row['code']}"))
        kb.add(InlineKeyboardButton('⬅️ Админ', callback_data='menu:admin'))
        edit_or_send(call, '\n'.join(lines), kb)
        return
    if data == 'admin:donate:toggle' and uid == OWNER_ID:
        toggle_donation_enabled()
        # reopen donation menu
        rows = list_packs()
        state = 'включён' if donation_enabled() else 'выключен'
        lines = [f'💫 <b>Донат и звёзды</b>', f'Глобальный статус: <b>{state}</b>', '', 'Каждый пак можно отдельно включать и выключать, а также задавать цену в звёздах.']
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton('🔁 Вкл/выкл весь донат', callback_data='admin:donate:toggle'))
        kb.add(InlineKeyboardButton('💠 Цена в звёздах', callback_data='state:admin_pack_stars_price'))
        for row in rows:
            lines.append(f"• {row['code']} · {row['name']} · {row.get('price_stars', 0)} ⭐ · {'звёзды вкл.' if row.get('stars_enabled') else 'звёзды выкл.'}")
            kb.add(InlineKeyboardButton(f"Переключить ⭐ {row['code']}", callback_data=f"admin:starspack:{row['code']}"))
        kb.add(InlineKeyboardButton('⬅️ Админ', callback_data='menu:admin'))
        edit_or_send(call, '\n'.join(lines), kb)
        return
    if data.startswith('admin:starspack:') and uid == OWNER_ID:
        _, _, code_pack = data.split(':')
        ok2, msg2 = toggle_pack_stars(code_pack)
        answer_cb(call, msg2[:80])
        # reopen screen
        rows = list_packs()
        state = 'включён' if donation_enabled() else 'выключен'
        lines = [f'💫 <b>Донат и звёзды</b>', f'Глобальный статус: <b>{state}</b>', '', 'Каждый пак можно отдельно включать и выключать, а также задавать цену в звёздах.']
        kb = InlineKeyboardMarkup(row_width=1)
        kb.add(InlineKeyboardButton('🔁 Вкл/выкл весь донат', callback_data='admin:donate:toggle'))
        kb.add(InlineKeyboardButton('💠 Цена в звёздах', callback_data='state:admin_pack_stars_price'))
        for row in rows:
            lines.append(f"• {row['code']} · {row['name']} · {row.get('price_stars', 0)} ⭐ · {'звёзды вкл.' if row.get('stars_enabled') else 'звёзды выкл.'}")
            kb.add(InlineKeyboardButton(f"Переключить ⭐ {row['code']}", callback_data=f"admin:starspack:{row['code']}"))
        kb.add(InlineKeyboardButton('⬅️ Админ', callback_data='menu:admin'))
        edit_or_send(call, '\n'.join(lines), kb)
        return
    if data == 'admin:give_menu' and uid == OWNER_ID:
        edit_or_send(call, '🎒 <b>Выдача предмета</b>\nМожно написать название предмета вручную или выбрать его из списка.', admin_choose_menu('give'))
        return
    if data == 'admin:take_menu' and uid == OWNER_ID:
        edit_or_send(call, '🗑 <b>Изъятие предмета</b>\nМожно написать название предмета вручную или выбрать его из списка.', admin_choose_menu('take'))
        return
    if data == 'admin:pack_menu' and uid == OWNER_ID:
        edit_or_send(call, '🎁 <b>Выдача пака</b>\nМожно написать название пака вручную или выбрать его из списка.', admin_choose_menu('pack'))
        return
    if data.startswith('admin:pickcat:') and uid == OWNER_ID:
        _, _, action, page = data.split(':')
        edit_or_send(call, f'📚 <b>Категории предметов</b>\nВыбери раздел для действия: {"выдать" if action == "give" else "изъять"}.', admin_item_categories_page(action, int(page)))
        return
    if data.startswith('admin:pickitem:') and uid == OWNER_ID:
        _, _, action, category, page = data.split(':')
        show_admin_item_picker(call, action, category, int(page))
        return

    if data.startswith('admin:pickdo:') and uid == OWNER_ID:
        _, _, action, item_id = data.split(':')
        item = get_item(int(item_id))
        if action == 'edit':
            draft = {
                'id': int(item['id']), 'category': item['category'], 'rarity': int(item['rarity']), 'seq': int(item['id']) % 1000,
                'name': item['name'], 'emoji': item.get('emoji', '📦'), 'price': int(item.get('price', 1)), 'weight': int(item.get('weight', 1)),
                'slot': item.get('slot'), 'stats': dict(item.get('stats', {})), 'buffs': dict(item.get('buffs', {})),
                'hp_restore': int(item.get('hp_restore', 0)), 'energy_restore': int(item.get('energy_restore', 0)),
                'max_durability': int(item.get('max_durability', 0)), 'description': item.get('description', ''),
            }
            set_user_state(uid, 'admin_item_editor', {'draft': draft})
            open_custom_item_editor(call, draft)
            return
        set_user_state(uid, f'admin_{action}_selected', {'item_id': int(item_id)})
        text = f"{'🎒 Выдача' if action == 'give' else '🗑 Изъятие'} выбрано: {item['emoji']} <b>{item['name']}</b>\nТеперь укажи игрока ответом на сообщение, через @username или ID, а затем количество.\nПримеры:\n@Treninem 3\n2097006037 5"
        edit_or_send(call, text, simple_back('menu:admin'))
        return

    if data == 'admin:edit_menu' and uid == OWNER_ID:
        edit_or_send(call, '✏️ <b>Изменение предмета</b>\nВыбери способ поиска предмета.', admin_choose_menu('edit'))
        return
    if data.startswith('adminitemtpl:') and uid == OWNER_ID:
        ok, msg = finalize_custom_item(uid, data.split(':')[1])
        answer_cb(call, 'Готово' if ok else 'Отмена')
        state = get_user_state(uid) or {}
        if ok and state.get('state_code') == 'admin_item_editor':
            draft = (state.get('payload') or {}).get('draft') or {}
            open_custom_item_editor(call, draft)
        else:
            edit_or_send(call, msg, admin_menu())
        return
    if data.startswith('adminitemfield:') and uid == OWNER_ID:
        field = data.split(':', 1)[1]
        state = get_user_state(uid) or {}
        payload = state.get('payload', {})
        draft = dict(payload.get('draft') or {})
        if not draft or field not in ITEM_EDITOR_FIELDS:
            answer_cb(call, 'Черновик не найден')
            return
        meta = ITEM_EDITOR_FIELDS[field]
        if meta['type'] == 'slot':
            edit_or_send(call, 'Выбери слот экипировки для предмета.', slot_picker_keyboard())
            return
        set_user_state(uid, 'admin_item_field_input', {'draft': draft, 'field': field})
        prompt = f"✍️ <b>{meta['label']}</b>\n"
        if meta['type'] == 'text':
            prompt += 'Отправь новое текстовое значение следующим сообщением.'
        else:
            prompt += 'Отправь целое число следующим сообщением. Можно отрицательное значение. Ноль очистит параметр.'
        edit_or_send(call, prompt, simple_back('menu:admin'))
        return
    if data.startswith('adminitemslot:') and uid == OWNER_ID:
        slot_val = data.split(':', 1)[1]
        state = get_user_state(uid) or {}
        payload = state.get('payload', {})
        draft = dict(payload.get('draft') or {})
        if not draft:
            answer_cb(call, 'Черновик не найден')
            return
        _draft_set(draft, 'slot', None if slot_val == 'none' else slot_val)
        set_user_state(uid, 'admin_item_editor', {'draft': draft})
        open_custom_item_editor(call, draft)
        return
    if data == 'adminitemback' and uid == OWNER_ID:
        state = get_user_state(uid) or {}
        draft = ((state.get('payload') or {}).get('draft') or {})
        if draft:
            set_user_state(uid, 'admin_item_editor', {'draft': draft})
            open_custom_item_editor(call, draft)
        else:
            edit_or_send(call, 'Черновик предмета не найден.', admin_menu())
        return
    if data == 'adminitemsave' and uid == OWNER_ID:
        ok, msg = save_custom_item_draft(uid)
        edit_or_send(call, msg, admin_menu())
        return
    if data == 'adminitemcancel' and uid == OWNER_ID:
        clear_user_state(uid)
        edit_or_send(call, 'Создание или редактирование предмета отменено.', admin_menu())
        return
    if data.startswith('admin:pickpack:') and uid == OWNER_ID:
        show_admin_pack_picker(call, int(data.split(':')[2]))
        return
    if data.startswith('admin:pickpackdo:') and uid == OWNER_ID:
        pack_code = data.split(':')[2]
        set_user_state(uid, 'admin_pack_selected', {'pack_code': pack_code})
        edit_or_send(call, f'🎁 Выбран пак <b>{pack_code}</b>\nТеперь укажи игрока ответом на сообщение, через @username или ID.', simple_back('menu:admin'))
        return
    if data.startswith('donate:buy:'):
        if not is_private_target(call.message):
            answer_cb(call, 'Покупка доступна только в личных сообщениях')
            return
        if not donation_enabled():
            answer_cb(call, 'Донат выключен владельцем')
            return
        code_pack = data.split(':')[2]
        row = next((r for r in list_packs() if r['code'] == code_pack), None)
        if not row or not int(row.get('enabled', 1)) or not int(row.get('stars_enabled', 0)) or int(row.get('price_stars', 0)) <= 0:
            answer_cb(call, 'Пак недоступен')
            return
        try:
            bot.send_invoice(
                call.message.chat.id,
                title=row['name'],
                description=f"Игровой пак «{row['name']}» для бота {GAME_TITLE}.",
                invoice_payload=f"pack:{code_pack}",
                provider_token='',
                currency='XTR',
                prices=[LabeledPrice(label=row['name'], amount=int(row['price_stars']))],
                start_parameter=f"pack_{code_pack}",
            )
            answer_cb(call, 'Счёт отправлен')
        except Exception:
            answer_cb(call, 'Не удалось отправить счёт')
        return

    if data.startswith('pvp:back:'):
        req_id = int(data.split(':')[2])
        update_battle_message(call, req_id)
        answer_cb(call)
        return
    if data.startswith('pvp:itemmenu:'):
        _, _, req_id, page = data.split(':', 3)
        battle = get_battle_state(int(req_id))
        if not battle:
            answer_cb(call, 'Бой не найден')
            return
        if int(battle['turn_user']) != uid:
            answer_cb(call, 'Сейчас не твой ход')
            return
        update_battle_message(call, int(req_id), item_menu=True, page=int(page))
        answer_cb(call)
        return
    if data.startswith('pvp:itempick:'):
        _, _, req_id, item_id = data.split(':', 3)
        battle = get_battle_state(int(req_id))
        if not battle:
            answer_cb(call, 'Бой не найден')
            return
        if int(battle['turn_user']) != uid:
            answer_cb(call, 'Сейчас не твой ход')
            return
        ok, msg = battle_use_item(battle, uid, int(item_id))
        if ok:
            battle['log'].append(msg)
            save_battle_state(int(req_id), battle)
            target_id = battle_opponent(battle, uid)
            if int(battle['hp'][str(target_id)]) <= 0:
                text_fin, _ = finish_battle(int(req_id), uid, target_id, 'Противник пал после применения предмета.')
                req = get_pvp_request(int(req_id)) or {}
                try:
                    bot.edit_message_text(text_fin, int(req['chat_id']), int(req['message_id']), reply_markup=None)
                except Exception:
                    edit_or_send(call, text_fin, None)
            else:
                update_battle_message(call, int(req_id))
        answer_cb(call, msg[:180])
        return
    if data.startswith('pvp:hit:'):
        req_id = int(data.split(':')[2])
        battle = get_battle_state(req_id)
        if not battle:
            answer_cb(call, 'Бой не найден')
            return
        if int(battle['turn_user']) != uid:
            answer_cb(call, 'Сейчас не твой ход')
            return
        logs = apply_battle_status(battle, uid)
        battle['log'].extend(logs)
        if int(battle['hp'][str(uid)]) <= 0:
            text_fin, _ = finish_battle(req_id, battle_opponent(battle, uid), uid, 'Боец пал от эффектов в начале хода.')
            req = get_pvp_request(req_id) or {}
            try:
                bot.edit_message_text(text_fin, int(req['chat_id']), int(req['message_id']), reply_markup=None)
            except Exception:
                edit_or_send(call, text_fin, None)
            answer_cb(call)
            return
        battle['log'].extend(battle_attack(battle, uid))
        save_battle_state(req_id, battle)
        target_id = battle_opponent(battle, uid)
        if int(battle['hp'][str(target_id)]) <= 0:
            text_fin, _ = finish_battle(req_id, uid, target_id, 'Противник потерял всё здоровье.')
            req = get_pvp_request(req_id) or {}
            try:
                bot.edit_message_text(text_fin, int(req['chat_id']), int(req['message_id']), reply_markup=None)
            except Exception:
                edit_or_send(call, text_fin, None)
            answer_cb(call)
            return
        update_battle_message(call, req_id)
        answer_cb(call)
        return
    if data.startswith('pvp:skip:'):
        req_id = int(data.split(':')[2])
        battle = get_battle_state(req_id)
        if not battle:
            answer_cb(call, 'Бой не найден')
            return
        if int(battle['turn_user']) != uid:
            answer_cb(call, 'Сейчас не твой ход')
            return
        battle['energy'][str(uid)] = min(int(battle['stats'][str(uid)]['max_energy']), int(battle['energy'][str(uid)]) + 12)
        battle['log'].append(f'{get_display_name(uid)} пропускает ход и восстанавливает силы.')
        battle_switch_turn(battle)
        save_battle_state(req_id, battle)
        update_battle_message(call, req_id)
        answer_cb(call)
        return
    if data.startswith('pvp:surrender:'):
        req_id = int(data.split(':')[2])
        battle = get_battle_state(req_id)
        if not battle:
            answer_cb(call, 'Бой не найден')
            return
        if uid not in {int(battle['from_user']), int(battle['to_user'])}:
            answer_cb(call, 'Это не твоя дуэль')
            return
        winner = battle_opponent(battle, uid)
        text_fin, _ = finish_battle(req_id, winner, uid, 'Один из бойцов сдался.')
        req = get_pvp_request(req_id) or {}
        try:
            bot.edit_message_text(text_fin, int(req['chat_id']), int(req['message_id']), reply_markup=None)
        except Exception:
            edit_or_send(call, text_fin, None)
        answer_cb(call)
        return

    if data.startswith('owned:list:'):
        _, _, action, page = data.split(':')
        show_owned_item_picker(call, uid, action, int(page))
        return
    if data.startswith('owned:pick:'):
        _, _, action, item_id = data.split(':')
        item = get_item(int(item_id))
        if action == 'sell':
            set_user_state(uid, 'sell_selected', {'item_id': int(item_id)})
            edit_or_send(call, f'🧺 Выбран предмет: {item["emoji"]} <b>{item["name"]}</b>\nТеперь напиши: количество цена_за_штуку\nПример: 5 120', simple_back('menu:market'))
            return
        if action == 'auction':
            set_user_state(uid, 'auction_selected', {'item_id': int(item_id)})
            edit_or_send(call, f'🔨 Выбран предмет: {item["emoji"]} <b>{item["name"]}</b>\nТеперь напиши: количество стартовая_ставка часы\nПример: 3 500 24', simple_back('menu:market'))
            return
        if action == 'gift':
            set_user_state(uid, 'gift_selected', {'item_id': int(item_id)})
            edit_or_send(call, f'🎁 Выбран предмет: {item["emoji"]} <b>{item["name"]}</b>\nТеперь укажи игрока ответом на сообщение, через @username или ID, а затем количество.\nПримеры:\n@Treninem 2\n2097006037 1', simple_back('menu:market'))
            return
    if data == 'pvp:guide':
        edit_or_send(call, '⚔️ В группе вызови соперника сообщением <code>пвп @username</code>, <code>дуэль @username</code> или ответом на сообщение. Зрители ставят текстом ответом на карточку дуэли.', pvp_menu())
        return
    if data.startswith('state:'):
        code = data.split(':')[1]
        prompts = {
            'gift': 'Формат: @username название_предмета количество или ответом на сообщение: подарить 3 яблока',
            'deal': 'Формат: @username 3 яблоко на 2 вода',
            'request': 'Формат: название_предмета количество',
            'sell': 'Формат: название_предмета количество цена_за_штуку',
            'auction': 'Формат: название_предмета количество стартовая_ставка часы',
            'order': 'Формат: название_предмета количество цена_за_штуку часы',
            'pvp_bet': 'Формат: 50 монет или 5 железная руда',
            'clan_create': 'Введи название стаи',
            'clan_join': 'Введи ID стаи',
            'clan_donate': 'Введи сумму доната в казну',
            'admin_new_item': 'Только ЛС. Формат: item_id Название предмета',
            'admin_new_craft': 'Только ЛС. Формат: recipe_id result_item result_amount ingredient_id:qty,ingredient_id:qty',
            'admin_pack': 'Формат: @username название_пака или код_пака',
            'admin_give': 'Формат: @username название_предмета количество',
            'admin_take': 'Формат: @username название_предмета количество',
            'admin_edit': 'Формат: название_предмета или ID предмета',
            'admin_level': 'Формат: @username уровень',
            'admin_block': 'Формат: @user или ответ на сообщение',
            'admin_unblock': 'Формат: @user или ответ на сообщение',
            'admin_add': 'Формат: @user или ответ на сообщение',
            'admin_del': 'Формат: @user или ответ на сообщение',
            'admin_bank_debt': 'Формат: @username сумма. 0 — аннулировать, -500 — уменьшить на 500, 1200 — установить долг 1200.',
            'admin_pack_stars_price': 'Формат: код_пака цена_в_звёздах. Пример: starter_pack 35',
            'admin_promo': 'Формат по-русски: КОД количество_активаций золото премиум. Пример: VESNA2026 50 100 2',
        }
        if code.startswith('admin') and uid != OWNER_ID:
            answer_cb(call, 'Недоступно')
            return
        ask_state(call.message.chat.id, uid, code, prompts.get(code, 'Введи данные'))
        answer_cb(call, 'Жду следующее сообщение')
        return
    if data.startswith('pvp:bet:'):
        _, _, req_id, pick_user = data.split(':')
        req = get_pvp_request(int(req_id))
        if not req or req.get('status') != 'pending':
            answer_cb(call, 'Дуэль уже закрыта')
            return
        if uid in {int(req['from_user']), int(req['to_user'])}:
            answer_cb(call, 'Участники дуэли не могут ставить')
            return
        ask_state(call.message.chat.id, uid, 'pvp_bet', f'Ставка на {get_display_name(int(pick_user))}. Напиши сумму и предмет: например «50 монет» или «5 железная руда».', {'request_id': int(req_id), 'pick_user': int(pick_user)})
        answer_cb(call, 'Жду сообщение со ставкой')
        return
    if data.startswith('pvp:accept:'):
        req_id = int(data.split(':')[2])
        req = get_pvp_request(req_id)
        if not req or req['status'] != 'pending':
            answer_cb(call, 'Запрос устарел')
            return
        if int(req['to_user']) != uid:
            answer_cb(call, 'Это не твой запрос')
            return
        start_pvp_battle(call, req_id)
        return
    if data.startswith('pvp:decline:'):
        req_id = int(data.split(':')[2])
        req = get_pvp_request(req_id)
        if not req or req['status'] != 'pending':
            answer_cb(call, 'Запрос устарел')
            return
        if uid not in {int(req['to_user']), int(req['from_user'])}:
            answer_cb(call, 'Это не твой запрос')
            return
        decline_pvp_request(call, req_id)
        return
    if data.startswith('deal:ok:'):
        ok, msg = complete_deal(int(data.split(':')[2]))
        edit_or_send(call, msg, back_to_main(uid))
        return
    if data.startswith('deal:no:'):
        from user_data import set_deal_status
        set_deal_status(int(data.split(':')[2]), 'declined')
        edit_or_send(call, '❌ Сделка отклонена.', back_to_main(uid))
        return
    if data.startswith('chat_event:'):
        key = f"chat_event:{data.split(':')[1]}"
        state = get_world_state(key, {}) or {}
        if not state or state.get('claimed_by'):
            answer_cb(call, 'Событие уже закрыто')
            return
        state['claimed_by'] = uid
        set_world_state(key, state)
        from user_data import add_xp
        add_gold(uid, CHAT_EVENT_GOLD)
        add_xp(uid, CHAT_EVENT_XP)
        apply_level_sync(uid)
        answer_cb(call, 'Награда получена')
        edit_or_send(call, f"✨ Событие забрал {get_display_name(uid)}. Награда: {CHAT_EVENT_GOLD} монет и {CHAT_EVENT_XP} XP.", back_to_main(uid))
        return


# -----------------------------
# Сообщения текста
# -----------------------------

@bot.message_handler(content_types=['text'])
def all_text(message: Message) -> None:
    sync_user(message)
    maintenance()
    if message.text and message.text.startswith('/'):
        return
    state = get_user_state(message.from_user.id)
    if state:
        if handle_state(message, state):
            safe_delete(message.chat.id, message.message_id, 2)
            return
    ok, _ = player_ready(message.from_user.id)
    if ok and parse_interaction_trigger(message):
        safe_delete(message.chat.id, message.message_id, 2)
        return
    raw = (message.text or '').strip().lower()
    norm = re.sub(r'\s+', ' ', re.sub(r'[^\w\sё-]', ' ', raw)).strip()
    action = None
    for key, variants in COMMAND_RU_SYNONYMS.items():
        if norm in variants:
            action = key
            break
    if not action:
        partial_map = [
            ('проф', 'profile'), ('инв', 'inv'), ('пвп', 'pvp'), ('дуэл', 'pvp'), ('арен', 'pvp'), ('бой', 'pvp'), ('магаз', 'shop'), ('рынок', 'market'), ('аукцион', 'market'), ('крафт', 'craft'), ('ремесло', 'craft'),
            ('банк', 'bank'), ('топ', 'top'), ('правил', 'info'), ('справ', 'info'), ('задан', 'tasks'), ('квест', 'tasks'), ('босс', 'boss'),
            ('стая', 'clan'), ('клан', 'clan'), ('питом', 'pet'), ('компаньон', 'pet'), ('лагерь', 'camp'), ('почта', 'mail'), ('реф', 'ref'),
            ('фракц', 'fac'), ('контракт', 'ct'), ('талант', 'tal'), ('умени', 'tal'), ('админ', 'adm')
        ]
        for needle, act in partial_map:
            if needle in norm and len(norm.split()) <= 4:
                action = act
                break
    if action:
        if action == 'adm':
            admin_login(message)
        else:
            action_map = {
                'main': 'main', 'profile': 'profile', 'inv': 'inv', 'pvp': 'pvp', 'exp': 'exp', 'dng': 'dng', 'shop': 'shop',
                'black': 'black', 'market': 'market', 'craft': 'craft', 'bank': 'bank', 'tasks': 'tasks', 'boss': 'boss',
                'pet': 'pet', 'camp': 'camp', 'clan': 'clan', 'mail': 'mail', 'top': 'top', 'ref': 'ref', 'info': 'info',
                'tal': 'tal', 'fac': 'fac', 'ct': 'ct'
            }
            short_menu_command(message, action_map[action])
        safe_delete(message.chat.id, message.message_id, 2)
        return
    try_spawn_chat_event(message)


if __name__ == '__main__':
    register_telegram_commands()
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
