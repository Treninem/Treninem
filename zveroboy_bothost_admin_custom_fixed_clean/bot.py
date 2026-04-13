"""Главный файл Telegram-бота «Зверобой» 2.0.

В этой версии есть:
- регистрация с правилами и выбором зверя;
- inline-меню;
- инвентарь, экипировка, крафт, магазин, чёрный рынок;
- рынок, аукцион, заказы на покупку, подарки, сделки, просьбы;
- PvP, подземелья, экспедиции, задания, мировой босс;
- стаи, почта, питомцы, лагерь AFK, рефералка;
- owner-only админ-панель с заготовкой под монетизацию и анти-мультиаккаунт оповещения.
"""

from __future__ import annotations

import random
import re
import threading
import time
from typing import Any

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

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
    MAX_LEVEL,
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
    loan_offer,
    maybe_chat_event,
    profile_progress,
    resolve_pvp,
    run_contract,
    run_dungeon,
    run_expedition,
    season_info,
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
    get_referrals,
    get_user_state,
    get_world_state,
    grant_pack_to_user,
    init_db,
    load_custom_items,
    load_custom_recipes,
    inventory_stats,
    is_owner,
    join_clan,
    leave_clan,
    list_admins,
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
    transfer_item,
    unequip_slot,
    award_talent_points_for_levels,
    learn_talent,
    mark_contract_done,
)

if not BOT_TOKEN:
    raise RuntimeError("В .env не найден BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
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

def full_name_from_user(user) -> str:
    parts = [user.first_name or "", user.last_name or ""]
    return " ".join([p for p in parts if p]).strip() or f"id{user.id}"


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
            return
    except Exception:
        pass
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
    item_data = {
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
        'tags': ['custom', 'owner_added'],
    }
    register_runtime_item(item_data)
    save_custom_item(item_data, uid)
    clear_user_state(uid)
    item = get_item(item_id)
    parts = [f"✅ Предмет добавлен: {item['emoji']} <b>{item['name']}</b> [{item_id}]", f"Тип: {CATEGORY_NAMES[category]} · редкость {item['rarity_name']}"]
    if item.get('slot'):
        parts.append(f"Слот: {SLOT_TITLES.get(item['slot'], item['slot'])}")
    if item.get('stats'):
        parts.append('Статы: ' + ', '.join([f"{k}+{v}" for k, v in item['stats'].items()]))
    if item.get('buffs'):
        parts.append('Эффекты: ' + ', '.join([f"{k}+{v}" for k, v in item['buffs'].items()]))
    if item.get('hp_restore') or item.get('energy_restore'):
        parts.append(f"Восстановление: HP {item.get('hp_restore', 0)} / EN {item.get('energy_restore', 0)}")
    return True, '\n'.join(parts)


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
    add_log(user_id, log_kind, f"Получено: {gold} монет, {xp} XP, предметов {len(loot)}")
    extra = "\n" + "\n".join(level_notes) if level_notes else ""
    loot_text = "\n".join(format_item_line(i, a) for i, a in loot[:6])
    return f"💰 +{gold}\n📘 +{xp}" + (f"\n{loot_text}" if loot_text else "") + extra


def open_main(target) -> None:
    uid = target.from_user.id if hasattr(target, "from_user") else target.message.from_user.id
    edit_or_send(target, f"{GAME_TITLE} <b>{VERSION}</b>\nВыбирай раздел ниже.", main_menu(uid))


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
        InlineKeyboardButton("⚔️ PvP", callback_data="top:pvp"),
        InlineKeyboardButton("💰 Богачи", callback_data="top:rich"),
        InlineKeyboardButton("🤝 Репутация", callback_data="top:rep"),
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
        InlineKeyboardButton("➕ Продать", callback_data="state:sell"),
        InlineKeyboardButton("🔨 Мой аукцион", callback_data="state:auction"),
        InlineKeyboardButton("📦 Мой заказ", callback_data="state:order"),
        InlineKeyboardButton("🎁 Подарок", callback_data="state:gift"),
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
            kb.add(InlineKeyboardButton(f"{data['emoji']} {data['title']}", callback_data=f"pet:set:{key}"))
    kb.add(InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"))
    return kb


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
        InlineKeyboardButton("🎁 Выдать пак", callback_data="state:admin_pack"),
        InlineKeyboardButton("🎒 Выдать предмет", callback_data="state:admin_give"),
        InlineKeyboardButton("🗑 Забрать предмет", callback_data="state:admin_take"),
        InlineKeyboardButton("⭐ Уровень", callback_data="state:admin_level"),
        InlineKeyboardButton("⛔ Блок", callback_data="state:admin_block"),
        InlineKeyboardButton("✅ Разблок", callback_data="state:admin_unblock"),
        InlineKeyboardButton("👮 Админ +", callback_data="state:admin_add"),
        InlineKeyboardButton("👤 Админ -", callback_data="state:admin_del"),
        InlineKeyboardButton("⬅️ В меню", callback_data="menu:main"),
    )
    return kb


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
        f"❤️ {stats['max_hp']} · ⚡ {stats['max_energy']}\n"
        f"ATK {stats['attack']} · DEF {stats['defense']} · SPD {stats['speed']} · LUCK {stats['luck']}\n"
        f"Бонусы: +{stats.get('gold_gain_pct',0)}% золота · +{stats.get('xp_gain_pct',0)}% XP\n"
        f"Спец.: {spec}\n"
        f"Питомец: {pet_txt}\n"
        f"Фракция: {faction_txt}\n"
        f"Стая: {clan_txt}\n"
        f"Репутация: {p['reputation']}\n"
        f"Кодекс: {get_codex_count(uid)}/{len(ITEMS)}\n"
        f"PvP: {p['wins']} / {p['losses']}\n"
        f"Сезон #{season['season_no']} · осталось {season['days_left']} дн."
    )
    edit_or_send(target, text, profile_menu(p))


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
    edit_or_send(target, "\n".join(lines), kb)


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
    edit_or_send(target, "\n".join(lines), kb)


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
    lines = [title, f"Тренд дня: спрос на {eco['demand']} · избыток {eco['surplus']}", ""]
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
    edit_or_send(target, "\n".join(lines), kb)


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
    edit_or_send(target, "📦 <b>Рынок и обмен</b>", market_menu())


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
    edit_or_send(target, "\n".join(lines), kb)


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
    edit_or_send(target, "\n".join(lines), kb)


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
    edit_or_send(target, "\n".join(lines), kb)


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
    edit_or_send(target, text, bank_menu())


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
        text = f"🐾 <b>{pet['emoji']} {pet['title']}</b>\nУровень: {p['pet_level']}\nПассив: {pet['bonus']}"
    else:
        text = f"🐾 <b>Питомец</b>\nДля приручения нужен жетон [{PET_TOKEN_ID}] или специальная награда. Если жетон у тебя уже есть — просто выбери питомца ниже."
    edit_or_send(target, text, pet_menu(p))


def show_camp(target, uid: int) -> None:
    p = get_player(uid)
    remain = max(0, int(p.get("camp_until", 0)) - now_ts())
    text = "⛺ <b>Лагерь AFK</b>\n"
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
        title = "⚔️ Топ PvP"
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
        bonus = ', '.join(f"{k} {v}" for k, v in data['bonus'].items())
        lines.append(f"{data['emoji']} <b>{data['title']}</b>\n{data['description']}\nБонусы: {bonus}")
    edit_or_send(target, "\n\n".join(lines), faction_menu(uid))


def show_contracts(target, uid: int) -> None:
    state = extras_for_user(uid)
    c_state = state.get('contracts', {'day':0,'done':[]})
    day_key = int(time.time() // 86400)
    lines = ["🧾 <b>Контракты дня</b>", f"Выполнено сегодня: {len(c_state.get('done', [])) if c_state.get('day') == day_key else 0}/{len(daily_contract_board())}", ""]
    for row in daily_contract_board():
        done = '✅' if row['code'] in c_state.get('done', []) and c_state.get('day') == day_key else '▫️'
        lines.append(f"{done} {row['emoji']} <b>{row['title']}</b>\n{row['desc']}\nНаграда: ~{row['gold']} золота, ~{row['xp']} XP")
    edit_or_send(target, "\n\n".join(lines), contracts_menu())


def show_ref(target, uid: int) -> None:
    bot_info = bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{uid}"
    refs = get_referrals(uid)
    text = f"🎁 <b>Рефералка</b>\nТвоя ссылка:\n<code>{link}</code>\n\nПриглашено: {len(refs)}\nЗа каждого игрока можно выбрать одну награду: немного золота или реферальный предмет."
    edit_or_send(target, text, referral_menu(uid))


def show_info(target) -> None:
    edit_or_send(target, INFO_TEXT, info_menu())


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
        return True, f"Съедено {item['name']}. HP {hp}/{eff['max_hp']} · энергия {energy}/{eff['max_energy']}"
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
                texts.append(f"Активирован эффект {key}: {value}")
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


def parse_interaction_trigger(message: Message) -> bool:
    text = (message.text or '').lower()
    uid = message.from_user.id
    if 'пвп' in text:
        target = resolve_target_from_message(message, text)
        if target and int(target['user_id']) != uid:
            req_id = create_pvp_request(uid, int(target['user_id']), 0, True, now_ts() + 600)
            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(InlineKeyboardButton("✅ Принять", callback_data=f"pvp:accept:{req_id}"), InlineKeyboardButton("❌ Отклонить", callback_data=f"pvp:decline:{req_id}"))
            bot.send_message(message.chat.id, f"⚔️ {get_display_name(uid)} вызывает {get_display_name(int(target['user_id']))} на PvP!", reply_markup=kb)
            return True
    if 'друг' in text:
        target = resolve_target_from_message(message, text)
        if target and int(target['user_id']) != uid:
            add_friend(uid, int(target['user_id']))
            send_temp(message.chat.id, f"🤝 {get_display_name(uid)} и {get_display_name(int(target['user_id']))} теперь друзья.")
            return True
    return False


# -----------------------------
# Команды
# -----------------------------
@bot.message_handler(commands=['start'])
def start_cmd(message: Message) -> None:
    maintenance()
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


def short_menu_command(message: Message, action: str) -> None:
    sync_user(message)
    maintenance()
    safe_delete(message.chat.id, message.message_id, 2)
    if not ensure_player_or_prompt(message):
        return
    if action == 'main':
        open_main(message)
    elif action == 'profile':
        show_profile(message, message.from_user.id)
    elif action == 'inv':
        show_inventory(message, message.from_user.id, 'all', 0)
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
    ('m', 'main'), ('menu', 'main'), ('p', 'profile'), ('profile', 'profile'), ('inv', 'inv'), ('x', 'exp'), ('d', 'dng'),
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
    if len(parts) < 2 or parts[1].strip() != ADMIN_PASSWORD:
        send_temp(message.chat.id, '🔐 Вход: /adm <пароль>')
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
        if code == 'gift':
            parts = text.split()
            if len(parts) < 3:
                send_temp(message.chat.id, 'Формат: @user item_id amount')
                return True
            target = resolve_target_from_message(message, text)
            item_id = int(parts[-2])
            amount = int(parts[-1])
            if not target:
                send_temp(message.chat.id, 'Игрок не найден.')
                return True
            if transfer_item(uid, int(target['user_id']), item_id, amount):
                maybe_flag_transfer(uid, int(target['user_id']), item_id, amount, 'Подарок')
                change_reputation(uid, 1)
                clear_user_state(uid)
                send_temp(message.chat.id, '🎁 Подарок отправлен.')
            else:
                send_temp(message.chat.id, 'Не удалось отправить подарок.')
            return True
        if code == 'deal':
            parts = text.split()
            if len(parts) < 5:
                send_temp(message.chat.id, 'Формат: @user offer_item offer_amount want_item want_amount')
                return True
            target = resolve_target_from_message(message, text)
            if not target:
                send_temp(message.chat.id, 'Игрок не найден.')
                return True
            offer_item, offer_amount, want_item, want_amount = map(int, parts[-4:])
            deal_id = create_deal(uid, int(target['user_id']), offer_item, offer_amount, want_item, want_amount, now_ts() + 1200)
            clear_user_state(uid)
            kb = InlineKeyboardMarkup(row_width=2)
            kb.add(InlineKeyboardButton('✅ Принять', callback_data=f'deal:ok:{deal_id}'), InlineKeyboardButton('❌ Отклонить', callback_data=f'deal:no:{deal_id}'))
            bot.send_message(message.chat.id, f'🤝 Сделка #{deal_id}: {get_display_name(uid)} предлагает обмен.', reply_markup=kb)
            return True
        if code == 'request':
            item_id, amount = map(int, text.split()[:2])
            req_id = create_item_request(uid, item_id, amount, now_ts() + 86400)
            clear_user_state(uid)
            send_temp(message.chat.id, f'🙏 Запрос #{req_id} создан. Другие игроки могут закрыть его частями.')
            return True
        if code == 'sell':
            item_id, amount, price_each = map(int, text.split()[:3])
            ok, resp = create_market_listing(uid, item_id, amount, price_each, now_ts() + 86400)
            clear_user_state(uid)
            send_temp(message.chat.id, f'Лот создан #{resp}' if ok else str(resp))
            return True
        if code == 'auction':
            item_id, amount, start_bid, hours = map(int, text.split()[:4])
            ok, resp = create_auction(uid, item_id, amount, start_bid, now_ts() + hours * 3600)
            clear_user_state(uid)
            send_temp(message.chat.id, f'Аукцион создан #{resp}' if ok else str(resp))
            return True
        if code == 'order':
            item_id, amount, price_each, hours = map(int, text.split()[:4])
            ok, resp = create_buy_order(uid, item_id, amount, price_each, now_ts() + hours * 3600)
            clear_user_state(uid)
            send_temp(message.chat.id, f'Заказ создан #{resp}' if ok else str(resp))
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
            code_pack, target_id = text.split()[:2]
            ok, resp = grant_pack_to_user(code_pack, int(target_id))
            clear_user_state(uid)
            send_temp(message.chat.id, resp)
            return True
        if code == 'admin_give' and uid == OWNER_ID:
            target_id, item_id, amount = map(int, text.split()[:3])
            add_item(target_id, item_id, amount)
            clear_user_state(uid)
            send_temp(message.chat.id, 'Предмет выдан.')
            return True
        if code == 'admin_take' and uid == OWNER_ID:
            target_id, item_id, amount = map(int, text.split()[:3])
            remove_item(target_id, item_id, amount)
            clear_user_state(uid)
            send_temp(message.chat.id, 'Предмет удалён.')
            return True
        if code == 'admin_level' and uid == OWNER_ID:
            target_id, lvl = map(int, text.split()[:2])
            from user_data import set_level
            set_level(target_id, lvl)
            clear_user_state(uid)
            send_temp(message.chat.id, 'Уровень изменён.')
            return True
        if code == 'admin_block' and uid == OWNER_ID:
            set_blocked(int(text), True)
            clear_user_state(uid)
            send_temp(message.chat.id, 'Игрок заблокирован.')
            return True
        if code == 'admin_unblock' and uid == OWNER_ID:
            set_blocked(int(text), False)
            clear_user_state(uid)
            send_temp(message.chat.id, 'Игрок разблокирован.')
            return True
        if code == 'admin_add' and uid == OWNER_ID:
            add_admin(int(text))
            clear_user_state(uid)
            send_temp(message.chat.id, 'Админ добавлен.')
            return True
        if code == 'admin_del' and uid == OWNER_ID:
            remove_admin(int(text))
            clear_user_state(uid)
            send_temp(message.chat.id, 'Админ удалён.')
            return True
        if code == 'admin_promo' and uid == OWNER_ID:
            parts = text.split()
            code_promo, uses, gold, premium = parts[0], int(parts[1]), int(parts[2]), int(parts[3])
            create_promo(code_promo, {'gold': gold, 'premium': premium}, uses)
            clear_user_state(uid)
            send_temp(message.chat.id, 'Промокод создан.')
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
        diff = data.split(':')[1]
        rem = get_cooldown_remaining(uid, 'exp')
        if rem > 0:
            answer_cb(call, f'Откат {format_seconds(rem)}')
            return
        if get_death_remaining(uid) > 0:
            answer_cb(call, f'Ты ранен ещё {format_seconds(get_death_remaining(uid))}')
            return
        res = run_expedition(get_player(uid), get_equipment(uid), get_buffs(uid), diff, extras_for_user(uid))
        set_cooldown(uid, 'exp', COOLDOWN_EXPEDITION)
        damage_equipment(uid, 1)
        from user_data import advance_task
        advance_task(uid, 'expeditions', 1)
        if res['success']:
            reward = reward_player(uid, res['gold'], res['xp'], res['loot'], 'expedition')
        else:
            reward = reward_player(uid, res['gold'], res['xp'], res['loot'], 'expedition_fail')
        text = f"🧭 <b>Экспедиция: {diff}</b>\nЛокация: {res['zone']}\nСобытие: {res['event']['title']}\nСтатус: {res['status']}\nШанс: {int(res['chance']*100)}%\n\n{reward}"
        edit_or_send(call, text, back_to_main(uid))
        return
    if data == 'menu:dng':
        show_dungeon_menu(call)
        return
    if data.startswith('dng:'):
        _, diff, floor = data.split(':')
        rem = get_cooldown_remaining(uid, 'dng')
        if rem > 0:
            answer_cb(call, f'Откат {format_seconds(rem)}')
            return
        res = run_dungeon(get_player(uid), get_equipment(uid), get_buffs(uid), diff, int(floor), extras_for_user(uid))
        set_cooldown(uid, 'dng', COOLDOWN_DUNGEON)
        damage_equipment(uid, 2)
        from user_data import advance_task, change_stat_fields
        advance_task(uid, 'dungeons', 1)
        if res['success'] and diff == 'hard':
            change_stat_fields(uid, dungeon_hard_wins=1)
        reward = reward_player(uid, res['gold'], res['xp'], res['loot'], 'dungeon')
        if not res['success']:
            set_dead_until(uid, now_ts() + COOLDOWN_DEATH)
        text = f"🏰 <b>Подземелье {diff} · этаж {floor}</b>\nМодификатор: {res['modifier']['title']}\nШанс: {int(res['chance']*100)}%\n\n{reward}"
        edit_or_send(call, text, back_to_main(uid))
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
        text = '⌨️ <b>Короткие команды</b>\n\n' + '\n'.join([f'{cmd} — {desc}' for cmd, desc in HELP_COMMANDS])
        edit_or_send(call, text, info_menu())
        return
    if data == 'info:economy':
        eco = economy_snapshot()
        txt = f"📈 <b>Экономика дня</b>\nСпрос: {eco['demand']}\nИзбыток: {eco['surplus']}\nМагазин автоматически подстраивает цены и ассортимент под тренд дня."
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
        if uid != OWNER_ID or uid not in OWNER_AUTHED:
            answer_cb(call, 'Только владелец после входа /adm <пароль>')
            return
        show_admin(call)
        return
    if data == 'admin:packs' and uid == OWNER_ID:
        rows = list_packs()
        lines = ['💎 <b>Донат-паки</b>']
        kb = InlineKeyboardMarkup(row_width=1)
        for row in rows:
            lines.append(f"• {row['code']} · {row['name']} · {row['price_rub']}₽ · {'ON' if row['enabled'] else 'OFF'}")
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
        text = '🎟 <b>Промокоды</b>\n\n' + '\n'.join([f"• {r['code']} · uses {r['uses_left']}" for r in rows] or ['Пусто.'])
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton('➕ Создать', callback_data='state:admin_promo'), InlineKeyboardButton('⬅️ Админ', callback_data='menu:admin'))
        edit_or_send(call, text, kb)
        return
    if data == 'admin:sus' and uid == OWNER_ID:
        rows = list_suspicions(False, 20)
        text = '🚨 <b>Подозрения</b>\n\n' + '\n'.join([f"• #{r['id']} {get_display_name(int(r['user_id']))}: {r['reason']}" for r in rows] or ['Пусто.'])
        edit_or_send(call, text, simple_back('menu:admin'))
        return
    if data.startswith('state:'):
        code = data.split(':')[1]
        prompts = {
            'gift': 'Формат: @user item_id amount',
            'deal': 'Формат: @user offer_item offer_amount want_item want_amount',
            'request': 'Формат: item_id amount',
            'sell': 'Формат: item_id amount price_each',
            'auction': 'Формат: item_id amount start_bid hours',
            'order': 'Формат: item_id amount price_each hours',
            'clan_create': 'Введи название стаи',
            'clan_join': 'Введи ID стаи',
            'clan_donate': 'Введи сумму доната в казну',
            'admin_new_item': 'Только ЛС. Формат: item_id Название предмета',
            'admin_new_craft': 'Только ЛС. Формат: recipe_id result_item result_amount ingredient_id:qty,ingredient_id:qty',
            'admin_pack': 'Формат: pack_code user_id',
            'admin_give': 'Формат: user_id item_id amount',
            'admin_take': 'Формат: user_id item_id amount',
            'admin_level': 'Формат: user_id level',
            'admin_block': 'Формат: user_id',
            'admin_unblock': 'Формат: user_id',
            'admin_add': 'Формат: user_id',
            'admin_del': 'Формат: user_id',
            'admin_promo': 'Формат: CODE uses gold premium',
        }
        if code.startswith('admin') and uid != OWNER_ID:
            answer_cb(call, 'Недоступно')
            return
        ask_state(call.message.chat.id, uid, code, prompts.get(code, 'Введи данные'))
        answer_cb(call, 'Жду следующее сообщение')
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
        a = get_player(int(req['from_user']))
        d = get_player(int(req['to_user']))
        res = resolve_pvp(a, d, effective_profile(a, get_equipment(int(req['from_user'])), get_buffs(int(req['from_user'])), get_player_extras(int(req['from_user']))), effective_profile(d, get_equipment(uid), get_buffs(uid), get_player_extras(uid)), int(req['stake_gold']), bool(req['ranked']))
        from user_data import set_pvp_request_status, add_xp, advance_task
        set_pvp_request_status(req_id, 'done')
        win = int(res['winner_id'])
        lose = int(res['loser_id'])
        add_win(win)
        add_loss(lose)
        add_gold(win, 28)
        add_gold(lose, 7)
        add_xp(win, 55)
        add_xp(lose, 18)
        advance_task(win, 'pvp', 1)
        advance_task(lose, 'pvp', 1)
        apply_level_sync(win)
        apply_level_sync(lose)
        text = f"⚔️ <b>PvP завершено</b>\nПобедитель: {get_display_name(win)}\n\n" + '\n'.join(res['log'][:12])
        edit_or_send(call, text, back_to_main(uid))
        return
    if data.startswith('pvp:decline:'):
        from user_data import set_pvp_request_status
        set_pvp_request_status(int(data.split(':')[2]), 'declined')
        edit_or_send(call, '❌ Вызов на PvP отклонён.', back_to_main(uid))
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
    txt = (message.text or '').lower()
    if any(word in txt for word in ['проф', 'инв', 'магаз', 'рынок', 'крафт', 'банк', 'топ', 'правил', 'задан', 'босс', 'стая', 'питом', 'лагерь', 'почта', 'реф']):
        mapping = [
            ('проф', 'profile'), ('инв', 'inv'), ('магаз', 'shop'), ('рынок', 'market'), ('крафт', 'craft'), ('банк', 'bank'),
            ('топ', 'top'), ('правил', 'info'), ('задан', 'tasks'), ('босс', 'boss'), ('стая', 'clan'), ('питом', 'pet'),
            ('лагерь', 'camp'), ('почта', 'mail'), ('реф', 'ref')
        ]
        for needle, action in mapping:
            if needle in txt:
                short_menu_command(message, action)
                break
        safe_delete(message.chat.id, message.message_id, 2)
        return
    try_spawn_chat_event(message)


if __name__ == '__main__':
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
