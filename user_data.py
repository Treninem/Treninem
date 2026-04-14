"""SQLite-слой для хранения аккаунтов, инвентаря, рынка и социальных систем."""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Iterator

from config import (
    CLAN_CREATE_PRICE,
    DB_NAME,
    DEFAULT_INVENTORY_SLOTS,
    DEFAULT_MAX_WEIGHT,
    LOAN_TERM_HOURS,
    MARKET_FEE_RATE,
    OWNER_ID,
    REFERRAL_GOLD_REWARD,
    REFERRAL_ITEM_REWARD_AMOUNT,
    REFERRAL_NEW_PLAYER_GOLD,
    START_GOLD,
    START_PREMIUM,
    TALENT_RESET_PRICE,
    MAX_LEVEL,
    PVP_BET_COMMISSION_RATE,
    PVP_WINNER_BET_SHARE_RATE,
    PVP_LOSER_TRIBUTE_RATE,
    PVP_LOSER_TRIBUTE_CAP,
    PVP_AUTO_TROPHY_BASE_RATE,
    PVP_AUTO_TROPHY_MIN_VALUE,
    PVP_AUTO_TROPHY_MAX_VALUE,
    PVP_AUTO_TROPHY_CURRENCY_RESERVE_RATE,
    PVP_DEBT_TERM_HOURS,
)
from data_items import CURRENCY_ID, ITEMS, PREMIUM_ID, SLOT_ORDER, CATEGORY_NAMES, get_item, is_equipment


# -----------------------------
# Вспомогательные утилиты
# -----------------------------

def now_ts() -> int:
    return int(time.time())


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def parse_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


# -----------------------------
# Инициализация БД
# -----------------------------

def init_db() -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS players (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                registered INTEGER DEFAULT 0,
                rules_accepted INTEGER DEFAULT 0,
                blocked INTEGER DEFAULT 0,
                character_key TEXT DEFAULT '',
                specialization TEXT DEFAULT '',
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 0,
                premium INTEGER DEFAULT 0,
                hp INTEGER DEFAULT 100,
                energy INTEGER DEFAULT 100,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                rating INTEGER DEFAULT 1000,
                reputation INTEGER DEFAULT 0,
                title TEXT DEFAULT '',
                inventory_slots INTEGER DEFAULT 120,
                max_weight INTEGER DEFAULT 12000,
                dead_until INTEGER DEFAULT 0,
                bank_debt INTEGER DEFAULT 0,
                bank_due_ts INTEGER DEFAULT 0,
                bank_discount INTEGER DEFAULT 0,
                referrer_id INTEGER DEFAULT 0,
                referred_at INTEGER DEFAULT 0,
                clan_id INTEGER DEFAULT 0,
                pet_species TEXT DEFAULT '',
                pet_level INTEGER DEFAULT 0,
                camp_until INTEGER DEFAULT 0,
                camp_hours INTEGER DEFAULT 0,
                season_points INTEGER DEFAULT 0,
                dungeon_hard_wins INTEGER DEFAULT 0,
                last_seen INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inventory (
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                PRIMARY KEY (user_id, item_id)
            );

            CREATE TABLE IF NOT EXISTS equipment (
                user_id INTEGER NOT NULL,
                slot TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                durability INTEGER NOT NULL,
                PRIMARY KEY (user_id, slot)
            );

            CREATE TABLE IF NOT EXISTS buffs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                power INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                source_item_id INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS cooldowns (
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                until_ts INTEGER NOT NULL,
                PRIMARY KEY (user_id, code)
            );

            CREATE TABLE IF NOT EXISTS user_state (
                user_id INTEGER PRIMARY KEY,
                state_code TEXT NOT NULL,
                payload_json TEXT DEFAULT '{}',
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS friends (
                user_id INTEGER NOT NULL,
                friend_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, friend_id)
            );

            CREATE TABLE IF NOT EXISTS pvp_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user INTEGER NOT NULL,
                to_user INTEGER NOT NULL,
                stake_gold INTEGER DEFAULT 0,
                ranked INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                chat_id INTEGER DEFAULT 0,
                message_id INTEGER DEFAULT 0,
                stake_mode TEXT DEFAULT 'auto',
                stake_payload_json TEXT DEFAULT '[]',
                stake_value INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS pvp_bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                pick_user INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pvp_debts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                debtor_user INTEGER NOT NULL,
                creditor_user INTEGER NOT NULL,
                amount_gold INTEGER NOT NULL,
                paid_gold INTEGER DEFAULT 0,
                status TEXT DEFAULT 'open',
                reason TEXT DEFAULT '',
                due_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user INTEGER NOT NULL,
                to_user INTEGER NOT NULL,
                offer_item INTEGER NOT NULL,
                offer_amount INTEGER NOT NULL,
                want_item INTEGER NOT NULL,
                want_amount INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS item_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                target_amount INTEGER NOT NULL,
                current_amount INTEGER NOT NULL DEFAULT 0,
                status TEXT DEFAULT 'open',
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS item_request_contrib (
                request_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY (request_id, user_id, created_at)
            );

            CREATE TABLE IF NOT EXISTS market_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                price_each INTEGER NOT NULL,
                status TEXT DEFAULT 'open',
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auctions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                start_bid INTEGER NOT NULL,
                current_bid INTEGER NOT NULL,
                current_bidder INTEGER DEFAULT 0,
                status TEXT DEFAULT 'open',
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS buy_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buyer_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                amount_left INTEGER NOT NULL,
                price_each INTEGER NOT NULL,
                reserved_gold INTEGER NOT NULL,
                status TEXT DEFAULT 'open',
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS mails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                to_user INTEGER NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                payload_json TEXT DEFAULT '{}',
                is_read INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS clans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                leader_id INTEGER NOT NULL,
                treasury INTEGER DEFAULT 0,
                reputation INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS clan_members (
                clan_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                contribution INTEGER DEFAULT 0,
                joined_at INTEGER NOT NULL,
                PRIMARY KEY (clan_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                user_id INTEGER NOT NULL,
                period_key TEXT NOT NULL,
                task_kind TEXT NOT NULL,
                task_code TEXT NOT NULL,
                title TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                target INTEGER NOT NULL,
                reward_gold INTEGER DEFAULT 0,
                reward_xp INTEGER DEFAULT 0,
                claimed INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, period_key, task_kind, task_code)
            );

            CREATE TABLE IF NOT EXISTS world_state (
                state_key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL UNIQUE,
                reward_choice TEXT DEFAULT '',
                reward_claimed INTEGER DEFAULT 0,
                suspicious INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS suspicions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                details TEXT NOT NULL,
                sent_to_owner INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS codex (
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                discovered_at INTEGER NOT NULL,
                PRIMARY KEY (user_id, item_id)
            );

            CREATE TABLE IF NOT EXISTS monetization_packs (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                price_rub INTEGER NOT NULL,
                reward_json TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                stock INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS promo_codes (
                code TEXT PRIMARY KEY,
                reward_json TEXT NOT NULL,
                uses_left INTEGER NOT NULL,
                expires_at INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS player_extras (
                user_id INTEGER PRIMARY KEY,
                prestige INTEGER DEFAULT 0,
                talent_points INTEGER DEFAULT 0,
                talents_json TEXT DEFAULT '{}',
                faction_key TEXT DEFAULT '',
                faction_rep INTEGER DEFAULT 0,
                faction_last_claim INTEGER DEFAULT 0,
                contracts_json TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS custom_items (
                item_id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                rarity INTEGER NOT NULL,
                seq INTEGER NOT NULL,
                name TEXT NOT NULL,
                emoji TEXT NOT NULL,
                price INTEGER NOT NULL,
                weight INTEGER NOT NULL,
                slot TEXT DEFAULT '',
                stats_json TEXT DEFAULT '{}',
                buffs_json TEXT DEFAULT '{}',
                hp_restore INTEGER DEFAULT 0,
                energy_restore INTEGER DEFAULT 0,
                max_durability INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                tags_json TEXT DEFAULT '[]',
                created_by INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS custom_recipes (
                recipe_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                result INTEGER NOT NULL,
                result_amount INTEGER NOT NULL,
                ingredients_json TEXT NOT NULL,
                station TEXT DEFAULT 'craft',
                required_level INTEGER DEFAULT 1,
                created_by INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL
            );
            """
        )
        cur.execute("INSERT OR IGNORE INTO admins(user_id, created_at) VALUES (?, ?)", (OWNER_ID, now_ts()))
        ensure_column(conn, 'pvp_requests', 'chat_id', 'INTEGER DEFAULT 0')
        ensure_column(conn, 'pvp_requests', 'message_id', 'INTEGER DEFAULT 0')
        ensure_column(conn, 'pvp_requests', 'stake_mode', "TEXT DEFAULT 'auto'")
        ensure_column(conn, 'pvp_requests', 'stake_payload_json', "TEXT DEFAULT '[]'")
        ensure_column(conn, 'pvp_requests', 'stake_value', 'INTEGER DEFAULT 0')
        ensure_column(conn, 'monetization_packs', 'price_stars', 'INTEGER DEFAULT 0')
        ensure_column(conn, 'monetization_packs', 'stars_enabled', 'INTEGER DEFAULT 0')


# -----------------------------
# Игроки и базовые проверки
# -----------------------------

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


def is_admin(user_id: int) -> bool:
    if is_owner(user_id):
        return True
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)).fetchone()
        return bool(row)


def add_admin(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO admins(user_id, created_at) VALUES (?, ?)", (user_id, now_ts()))


def remove_admin(user_id: int) -> None:
    if is_owner(user_id):
        return
    with get_conn() as conn:
        conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))


def list_admins() -> list[int]:
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id FROM admins ORDER BY created_at").fetchall()
        return [int(r[0]) for r in rows]


def player_exists(user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM players WHERE user_id = ?", (user_id,)).fetchone()
        return bool(row)


def create_player(user_id: int, username: str, full_name: str, referrer_id: int = 0) -> None:
    if player_exists(user_id):
        touch_identity(user_id, username, full_name)
        if referrer_id:
            set_referrer_if_empty(user_id, referrer_id)
        return
    ts = now_ts()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO players(
                user_id, username, full_name, registered, rules_accepted, blocked,
                level, xp, gold, premium, hp, energy, wins, losses, rating,
                inventory_slots, max_weight, created_at, last_seen, referrer_id, referred_at
            ) VALUES (?, ?, ?, 0, 0, 0, 1, 0, ?, ?, 100, 100, 0, 0, 1000, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, username or "", full_name or "", START_GOLD, START_PREMIUM, DEFAULT_INVENTORY_SLOTS, DEFAULT_MAX_WEIGHT, ts, ts, referrer_id, ts if referrer_id else 0),
        )
    add_item(user_id, CURRENCY_ID, START_GOLD)
    add_item(user_id, PREMIUM_ID, START_PREMIUM)
    add_log(user_id, "account", "Создан новый игровой профиль.")
    if referrer_id and referrer_id != user_id:
        with get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO referrals(referrer_id, referred_id, created_at) VALUES (?, ?, ?)",
                (referrer_id, user_id, ts),
            )
        add_gold(user_id, REFERRAL_NEW_PLAYER_GOLD)
        send_mail(user_id, "Реферальная награда", f"Ты пришёл по приглашению и получил {REFERRAL_NEW_PLAYER_GOLD} монет.")
    ensure_player_extras(user_id)


def set_referrer_if_empty(user_id: int, referrer_id: int) -> None:
    if not referrer_id or referrer_id == user_id:
        return
    with get_conn() as conn:
        conn.execute(
            "UPDATE players SET referrer_id = CASE WHEN referrer_id = 0 THEN ? ELSE referrer_id END, referred_at = CASE WHEN referrer_id = 0 THEN ? ELSE referred_at END WHERE user_id = ?",
            (referrer_id, now_ts(), user_id),
        )


def touch_identity(user_id: int, username: str, full_name: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE players SET username = ?, full_name = ?, last_seen = ? WHERE user_id = ?",
            (username or "", full_name or "", now_ts(), user_id),
        )


def get_player(user_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)).fetchone()
        return row_to_dict(row)


def get_player_by_username(username: str) -> dict[str, Any] | None:
    username = username.lstrip("@").lower()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM players WHERE lower(username) = ?", (username,)).fetchone()
        return row_to_dict(row)


def get_display_name(user_id: int) -> str:
    player = get_player(user_id)
    if not player:
        return f"id{user_id}"
    return f"@{player['username']}" if player.get("username") else (player.get("full_name") or f"id{user_id}")


def set_rules_accepted(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET rules_accepted = 1 WHERE user_id = ?", (user_id,))


def register_character(user_id: int, character_key: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET registered = 1, character_key = ?, hp = 100, energy = 100 WHERE user_id = ?", (character_key, user_id))
    add_log(user_id, "character", f"Выбран персонаж: {character_key}")


def set_specialization(user_id: int, spec_key: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET specialization = ? WHERE user_id = ?", (spec_key, user_id))
    add_log(user_id, "specialization", f"Выбрана специализация: {spec_key}")


def set_blocked(user_id: int, blocked: bool) -> None:
    if is_owner(user_id):
        return
    with get_conn() as conn:
        conn.execute("UPDATE players SET blocked = ? WHERE user_id = ?", (1 if blocked else 0, user_id))


def add_xp(user_id: int, amount: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET xp = xp + ? WHERE user_id = ?", (int(amount), user_id))


def set_level(user_id: int, level: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET level = ? WHERE user_id = ?", (level, user_id))




def adjust_player_limits(user_id: int, slots_plus: int = 0, weight_plus: int = 0) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE players SET inventory_slots = inventory_slots + ?, max_weight = max_weight + ? WHERE user_id = ?",
            (slots_plus, weight_plus, user_id),
        )


def reset_character_for_reroll(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE players SET registered = 0, character_key = '', specialization = '', level = 1, xp = 0, hp = 100, energy = 100, wins = 0, losses = 0, rating = 1000 WHERE user_id = ?",
            (user_id,),
        )

def set_hp_energy(user_id: int, hp: int, energy: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET hp = ?, energy = ? WHERE user_id = ?", (max(1, hp), max(0, energy), user_id))


def change_stat_fields(user_id: int, **changes: int) -> None:
    if not changes:
        return
    sets = ", ".join(f"{k} = {k} + ?" for k in changes.keys())
    params = list(changes.values()) + [user_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE players SET {sets} WHERE user_id = ?", params)


def set_dead_until(user_id: int, until_ts: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET dead_until = ? WHERE user_id = ?", (until_ts, user_id))


def get_death_remaining(user_id: int) -> int:
    player = get_player(user_id)
    if not player:
        return 0
    return max(0, int(player.get("dead_until", 0)) - now_ts())


def add_win(user_id: int, rating_delta: int = 12) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET wins = wins + 1, rating = rating + ?, season_points = season_points + 8 WHERE user_id = ?", (rating_delta, user_id))


def add_loss(user_id: int, rating_delta: int = 8) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET losses = losses + 1, rating = MAX(0, rating - ?), season_points = season_points + 2 WHERE user_id = ?", (rating_delta, user_id))


def change_reputation(user_id: int, delta: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET reputation = reputation + ? WHERE user_id = ?", (delta, user_id))


def set_title(user_id: int, title: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET title = ? WHERE user_id = ?", (title, user_id))


# -----------------------------
# Инвентарь и экипировка
# -----------------------------

def add_codex(user_id: int, item_id: int) -> None:
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO codex(user_id, item_id, discovered_at) VALUES (?, ?, ?)", (user_id, item_id, now_ts()))


def get_codex_count(user_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) c FROM codex WHERE user_id = ?", (user_id,)).fetchone()
        return int(row[0]) if row else 0


def list_codex(user_id: int, limit: int = 12) -> list[int]:
    with get_conn() as conn:
        rows = conn.execute("SELECT item_id FROM codex WHERE user_id = ? ORDER BY discovered_at DESC LIMIT ?", (user_id, limit)).fetchall()
        return [int(r[0]) for r in rows]


def add_item(user_id: int, item_id: int, amount: int) -> None:
    if amount <= 0:
        return
    add_codex(user_id, item_id)
    with get_conn() as conn:
        row = conn.execute("SELECT amount FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id)).fetchone()
        if row:
            conn.execute("UPDATE inventory SET amount = amount + ? WHERE user_id = ? AND item_id = ?", (amount, user_id, item_id))
        else:
            conn.execute("INSERT INTO inventory(user_id, item_id, amount) VALUES (?, ?, ?)", (user_id, item_id, amount))
        if item_id == CURRENCY_ID:
            conn.execute("UPDATE players SET gold = gold + ? WHERE user_id = ?", (amount, user_id))
        if item_id == PREMIUM_ID:
            conn.execute("UPDATE players SET premium = premium + ? WHERE user_id = ?", (amount, user_id))


def remove_item(user_id: int, item_id: int, amount: int) -> bool:
    if amount <= 0:
        return True
    with get_conn() as conn:
        row = conn.execute("SELECT amount FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id)).fetchone()
        have = int(row[0]) if row else 0
        if have < amount:
            return False
        new_amount = have - amount
        if new_amount == 0:
            conn.execute("DELETE FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id))
        else:
            conn.execute("UPDATE inventory SET amount = ? WHERE user_id = ? AND item_id = ?", (new_amount, user_id, item_id))
        if item_id == CURRENCY_ID:
            conn.execute("UPDATE players SET gold = MAX(0, gold - ?) WHERE user_id = ?", (amount, user_id))
        if item_id == PREMIUM_ID:
            conn.execute("UPDATE players SET premium = MAX(0, premium - ?) WHERE user_id = ?", (amount, user_id))
        return True


def delete_item_everywhere(item_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM inventory WHERE item_id = ?", (item_id,))
        conn.execute("DELETE FROM equipment WHERE item_id = ?", (item_id,))


def get_item_amount(user_id: int, item_id: int) -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT amount FROM inventory WHERE user_id = ? AND item_id = ?", (user_id, item_id)).fetchone()
        return int(row[0]) if row else 0


def get_inventory(user_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT item_id, amount FROM inventory WHERE user_id = ? ORDER BY item_id", (user_id,)).fetchall()
    result = []
    for row in rows:
        item = ITEMS.get(int(row["item_id"]))
        if not item:
            continue
        result.append({"item_id": int(row["item_id"]), "amount": int(row["amount"]), "item": item})
    return result


def inventory_stats(user_id: int) -> dict[str, int]:
    player = get_player(user_id) or {}
    current_weight = 0
    used_slots = 0
    for row in get_inventory(user_id):
        used_slots += 1
        current_weight += row["item"]["weight"] * row["amount"]
    return {
        "used_slots": used_slots,
        "max_slots": int(player.get("inventory_slots", DEFAULT_INVENTORY_SLOTS)),
        "weight": current_weight,
        "max_weight": int(player.get("max_weight", DEFAULT_MAX_WEIGHT)),
    }


def get_gold(user_id: int) -> int:
    player = get_player(user_id) or {}
    return int(player.get("gold", 0))


def add_gold(user_id: int, amount: int) -> None:
    add_item(user_id, CURRENCY_ID, amount)


def spend_gold(user_id: int, amount: int) -> bool:
    return remove_item(user_id, CURRENCY_ID, amount)


def add_premium(user_id: int, amount: int) -> None:
    add_item(user_id, PREMIUM_ID, amount)


def spend_premium(user_id: int, amount: int) -> bool:
    return remove_item(user_id, PREMIUM_ID, amount)


def get_equipment(user_id: int) -> dict[str, dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT slot, item_id, durability FROM equipment WHERE user_id = ?", (user_id,)).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = int(row["item_id"])
        result[row["slot"]] = {"item_id": item_id, "durability": int(row["durability"]), "item": ITEMS[item_id]}
    return result


def equip_item(user_id: int, item_id: int) -> tuple[bool, str]:
    if not is_equipment(item_id):
        return False, "Это не экипировка."
    if get_item_amount(user_id, item_id) <= 0:
        return False, "Предмета нет в инвентаре."
    item = get_item(item_id)
    slot = item["slot"]
    if not slot:
        return False, "У предмета не указан слот."
    with get_conn() as conn:
        old = conn.execute("SELECT item_id, durability FROM equipment WHERE user_id = ? AND slot = ?", (user_id, slot)).fetchone()
        if old:
            conn.execute("DELETE FROM equipment WHERE user_id = ? AND slot = ?", (user_id, slot))
            add_item(user_id, int(old["item_id"]), 1)
        if not remove_item(user_id, item_id, 1):
            return False, "Не удалось переместить предмет из инвентаря."
        conn.execute(
            "INSERT OR REPLACE INTO equipment(user_id, slot, item_id, durability) VALUES (?, ?, ?, ?)",
            (user_id, slot, item_id, item["max_durability"] or 50),
        )
    add_log(user_id, "equip", f"Экипирован предмет {item['name']}.")
    return True, f"Экипирован {item['emoji']} {item['name']} в слот {slot}."


def unequip_slot(user_id: int, slot: str) -> tuple[bool, str]:
    with get_conn() as conn:
        row = conn.execute("SELECT item_id FROM equipment WHERE user_id = ? AND slot = ?", (user_id, slot)).fetchone()
        if not row:
            return False, "Слот пуст."
        item_id = int(row["item_id"])
        conn.execute("DELETE FROM equipment WHERE user_id = ? AND slot = ?", (user_id, slot))
    add_item(user_id, item_id, 1)
    return True, f"Снято: {get_item(item_id)['name']}"


def damage_equipment(user_id: int, amount: int = 1) -> None:
    with get_conn() as conn:
        rows = conn.execute("SELECT slot, durability FROM equipment WHERE user_id = ?", (user_id,)).fetchall()
        for row in rows:
            new_val = max(0, int(row["durability"]) - amount)
            conn.execute("UPDATE equipment SET durability = ? WHERE user_id = ? AND slot = ?", (new_val, user_id, row["slot"]))


def repair_all(user_id: int) -> tuple[int, int]:
    total_cost = 0
    repaired = 0
    eq = get_equipment(user_id)
    for slot, data in eq.items():
        item = data["item"]
        max_d = item.get("max_durability", 0) or 1
        missing = max(0, max_d - data["durability"])
        if missing <= 0:
            continue
        cost = max(1, missing // 5)
        total_cost += cost
        repaired += 1
    if total_cost <= 0:
        return 0, 0
    if not spend_gold(user_id, total_cost):
        return -1, 0
    with get_conn() as conn:
        for slot, data in eq.items():
            max_d = data["item"].get("max_durability", 0) or 1
            conn.execute("UPDATE equipment SET durability = ? WHERE user_id = ? AND slot = ?", (max_d, user_id, slot))
    add_log(user_id, "repair", f"Починка экипировки за {total_cost} монет.")
    return total_cost, repaired


def transfer_item(from_user: int, to_user: int, item_id: int, amount: int) -> bool:
    if amount <= 0:
        return False
    if not remove_item(from_user, item_id, amount):
        return False
    add_item(to_user, item_id, amount)
    add_log(from_user, "transfer", f"Передан предмет [{item_id}] x{amount} игроку {to_user}.")
    add_log(to_user, "transfer", f"Получен предмет [{item_id}] x{amount} от игрока {from_user}.")
    return True


# -----------------------------
# Бафы и откаты
# -----------------------------

def cleanup_buffs(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM buffs WHERE user_id = ? AND expires_at <= ?", (user_id, now_ts()))


def add_buff(user_id: int, code: str, power: int, duration_sec: int, source_item_id: int = 0) -> None:
    cleanup_buffs(user_id)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO buffs(user_id, code, power, expires_at, source_item_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, code, power, now_ts() + duration_sec, source_item_id),
        )


def get_buffs(user_id: int) -> list[dict[str, Any]]:
    cleanup_buffs(user_id)
    with get_conn() as conn:
        rows = conn.execute("SELECT code, power, expires_at, source_item_id FROM buffs WHERE user_id = ? ORDER BY expires_at", (user_id,)).fetchall()
        return [dict(row) for row in rows]


def set_cooldown(user_id: int, code: str, seconds: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cooldowns(user_id, code, until_ts) VALUES (?, ?, ?)",
            (user_id, code, now_ts() + seconds),
        )


def get_cooldown_remaining(user_id: int, code: str) -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT until_ts FROM cooldowns WHERE user_id = ? AND code = ?", (user_id, code)).fetchone()
        return max(0, int(row[0]) - now_ts()) if row else 0


# -----------------------------
# Состояние диалога
# -----------------------------

def set_user_state(user_id: int, state_code: str, payload: dict[str, Any] | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO user_state(user_id, state_code, payload_json, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, state_code, json.dumps(payload or {}, ensure_ascii=False), now_ts()),
        )


def get_user_state(user_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT state_code, payload_json, updated_at FROM user_state WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return None
        return {"state_code": row["state_code"], "payload": parse_json(row["payload_json"], {}), "updated_at": int(row["updated_at"])}


def clear_user_state(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM user_state WHERE user_id = ?", (user_id,))


# -----------------------------
# Пользовательские предметы и крафты
# -----------------------------

def save_custom_item(item_data: dict[str, Any], created_by: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO custom_items(
                item_id, category, rarity, seq, name, emoji, price, weight, slot,
                stats_json, buffs_json, hp_restore, energy_restore, max_durability,
                description, tags_json, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(item_data['id']),
                item_data['category'],
                int(item_data['rarity']),
                int(item_data.get('seq', int(item_data['id']) % 1000)),
                item_data['name'],
                item_data.get('emoji', '📦'),
                int(item_data.get('price', 1)),
                int(item_data.get('weight', 1)),
                item_data.get('slot') or '',
                json.dumps(item_data.get('stats', {}), ensure_ascii=False),
                json.dumps(item_data.get('buffs', {}), ensure_ascii=False),
                int(item_data.get('hp_restore', 0)),
                int(item_data.get('energy_restore', 0)),
                int(item_data.get('max_durability', 0)),
                item_data.get('description', ''),
                json.dumps(item_data.get('tags', []), ensure_ascii=False),
                created_by,
                now_ts(),
            ),
        )


def load_custom_items() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM custom_items ORDER BY item_id").fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        d['stats'] = parse_json(d.pop('stats_json', '{}'), {})
        d['buffs'] = parse_json(d.pop('buffs_json', '{}'), {})
        d['tags'] = parse_json(d.pop('tags_json', '[]'), [])
        d['slot'] = d.get('slot') or None
        d['category_name'] = CATEGORY_NAMES.get(d['category'], d['category'])
        result.append(d)
    return result


def save_custom_recipe(recipe_data: dict[str, Any], created_by: int) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO custom_recipes(
                recipe_id, name, result, result_amount, ingredients_json, station,
                required_level, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(recipe_data['id']),
                recipe_data['name'],
                int(recipe_data['result']),
                int(recipe_data.get('result_amount', 1)),
                json.dumps(recipe_data.get('ingredients', {}), ensure_ascii=False),
                recipe_data.get('station', 'craft'),
                int(recipe_data.get('required_level', 1)),
                created_by,
                now_ts(),
            ),
        )


def load_custom_recipes() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM custom_recipes ORDER BY recipe_id").fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        raw_ingredients = parse_json(d.pop('ingredients_json', '{}'), {})
        d['ingredients'] = {int(k): int(v) for k, v in raw_ingredients.items()}
        result.append(d)
    return result


# -----------------------------
# Социальные функции
# -----------------------------

def add_friend(user_id: int, friend_id: int) -> None:
    ts = now_ts()
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO friends(user_id, friend_id, created_at) VALUES (?, ?, ?)", (user_id, friend_id, ts))
        conn.execute("INSERT OR IGNORE INTO friends(user_id, friend_id, created_at) VALUES (?, ?, ?)", (friend_id, user_id, ts))
    change_reputation(user_id, 1)
    change_reputation(friend_id, 1)


def get_friends(user_id: int) -> list[int]:
    with get_conn() as conn:
        rows = conn.execute("SELECT friend_id FROM friends WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
        return [int(r[0]) for r in rows]


def pvp_package_value(payload: list[dict[str, Any]] | None) -> int:
    total = 0
    for row in payload or []:
        item_id = int(row.get('item_id', 0) or 0)
        amount = int(row.get('amount', 0) or 0)
        item = get_item(item_id)
        unit_price = max(1, int(item.get('price', 1)))
        total += unit_price * max(0, amount)
    return int(total)


def create_pvp_request(
    from_user: int,
    to_user: int,
    stake_gold: int,
    ranked: bool,
    expires_at: int,
    chat_id: int = 0,
    message_id: int = 0,
    stake_mode: str = 'auto',
    stake_payload: list[dict[str, Any]] | None = None,
) -> int:
    payload = stake_payload or []
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO pvp_requests(from_user, to_user, stake_gold, ranked, created_at, expires_at, chat_id, message_id, stake_mode, stake_payload_json, stake_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                from_user,
                to_user,
                stake_gold,
                1 if ranked else 0,
                now_ts(),
                expires_at,
                chat_id,
                message_id,
                stake_mode,
                json.dumps(payload, ensure_ascii=False),
                pvp_package_value(payload),
            ),
        )
        return int(cur.lastrowid)


def get_pvp_request(request_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM pvp_requests WHERE id = ?", (request_id,)).fetchone()
        return row_to_dict(row)


def get_latest_chat_pvp(chat_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM pvp_requests WHERE chat_id = ? AND status = 'pending' AND expires_at > ? ORDER BY id DESC LIMIT 1",
            (chat_id, now_ts()),
        ).fetchone()
        return row_to_dict(row)


def get_pvp_request_by_message(chat_id: int, message_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM pvp_requests WHERE chat_id = ? AND message_id = ? AND status = 'pending' AND expires_at > ? ORDER BY id DESC LIMIT 1",
            (chat_id, message_id, now_ts()),
        ).fetchone()
        return row_to_dict(row)


def update_pvp_request_message(request_id: int, chat_id: int, message_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE pvp_requests SET chat_id = ?, message_id = ? WHERE id = ?", (chat_id, message_id, request_id))


def set_pvp_request_status(request_id: int, status: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE pvp_requests SET status = ? WHERE id = ?", (status, request_id))


def create_pvp_bet(user_id: int, request_id: int, pick_user: int, item_id: int, amount: int) -> tuple[bool, str]:
    req = get_pvp_request(request_id)
    if not req or req.get('status') != 'pending' or int(req.get('expires_at', 0)) <= now_ts():
        return False, 'Эта дуэль уже закрыта.'
    if user_id in {int(req['from_user']), int(req['to_user'])}:
        return False, 'Участники дуэли не могут ставить на свой бой.'
    if pick_user not in {int(req['from_user']), int(req['to_user'])}:
        return False, 'Неверная сторона ставки.'
    if amount <= 0:
        return False, 'Ставка должна быть больше нуля.'
    if not remove_item(user_id, item_id, amount):
        return False, 'Не хватает предметов или валюты для ставки.'
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO pvp_bets(request_id, user_id, pick_user, item_id, amount, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (request_id, user_id, pick_user, item_id, amount, now_ts()),
        )
    add_log(user_id, 'pvp_bet', f'Ставка на дуэль #{request_id}: предмет [{item_id}] x{amount} на игрока {pick_user}.')
    return True, 'Ставка принята.'


def get_pvp_bets(request_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM pvp_bets WHERE request_id = ? ORDER BY id", (request_id,)).fetchall()
        return [dict(r) for r in rows]


def create_pvp_debt(debtor_user: int, creditor_user: int, amount_gold: int, reason: str = '') -> int:
    amount_gold = max(0, int(amount_gold))
    if amount_gold <= 0:
        return 0
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO pvp_debts(debtor_user, creditor_user, amount_gold, paid_gold, status, reason, due_at, created_at) VALUES (?, ?, ?, 0, 'open', ?, ?, ?)",
            (debtor_user, creditor_user, amount_gold, reason, now_ts() + PVP_DEBT_TERM_HOURS * 3600, now_ts()),
        )
        return int(cur.lastrowid)


def list_pvp_debts(user_id: int, mode: str = 'all') -> list[dict[str, Any]]:
    where = []
    args: list[Any] = []
    if mode == 'debtor':
        where.append('debtor_user = ?')
        args.append(user_id)
    elif mode == 'creditor':
        where.append('creditor_user = ?')
        args.append(user_id)
    else:
        where.append('(debtor_user = ? OR creditor_user = ?)')
        args.extend([user_id, user_id])
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM pvp_debts WHERE {' AND '.join(where)} ORDER BY status = 'open' DESC, created_at DESC",
            tuple(args),
        ).fetchall()
        return [dict(r) for r in rows]


def _surplus_transferable_amount(item_id: int, amount: int) -> int:
    item = get_item(item_id)
    cat = item['category']
    if item_id == PREMIUM_ID:
        return 0
    if item_id == CURRENCY_ID:
        reserve = max(60, int(amount * PVP_AUTO_TROPHY_CURRENCY_RESERVE_RATE))
        return max(0, amount - reserve)
    if cat == 'material':
        reserve = max(12, int(amount * 0.65))
    elif cat in {'food', 'elixir', 'scroll'}:
        reserve = max(5, int(amount * 0.70))
    elif cat == 'recipe':
        reserve = max(1, int(amount * 0.80))
    elif cat == 'equipment':
        reserve = 1
    else:
        reserve = 0
    return max(0, amount - reserve)


def _surplus_priority(item_id: int) -> tuple[int, int]:
    item = get_item(item_id)
    cat = item['category']
    pri = {
        'material': 1,
        'food': 2,
        'elixir': 3,
        'scroll': 4,
        'currency': 5,
        'recipe': 6,
        'equipment': 7,
    }.get(cat, 9)
    return pri, max(1, int(item.get('price', 1)))


def take_pvp_tribute(loser_id: int, winner_id: int, winner_luck: int = 0, loser_luck: int = 0) -> dict[str, Any]:
    inv = [row for row in get_inventory(loser_id) if int(row['item_id']) not in {PREMIUM_ID}]
    if not inv:
        return {'items': [], 'value': 0, 'debt_gold': 0, 'loan_used': 0}
    wealth = 0
    candidates: list[dict[str, Any]] = []
    for row in inv:
        item_id = int(row['item_id'])
        amount = int(row['amount'])
        item = row['item']
        unit_value = max(1, int(item.get('price', 1)))
        wealth += unit_value * amount
        transferable = _surplus_transferable_amount(item_id, amount)
        if transferable <= 0:
            continue
        candidates.append({
            'item_id': item_id,
            'amount': amount,
            'transferable': transferable,
            'unit_value': unit_value,
            'priority': _surplus_priority(item_id),
            'item': item,
        })
    if not candidates:
        return {'items': [], 'value': 0, 'debt_gold': 0, 'loan_used': 0}
    luck_shift = max(-0.12, min(0.12, (int(winner_luck) - int(loser_luck)) / 600))
    target_value = int(wealth * (PVP_AUTO_TROPHY_BASE_RATE + luck_shift))
    target_value = max(PVP_AUTO_TROPHY_MIN_VALUE, min(PVP_AUTO_TROPHY_MAX_VALUE, target_value))
    candidates.sort(key=lambda row: (row['priority'][0], row['priority'][1], -row['transferable']))
    moved: list[dict[str, Any]] = []
    moved_value = 0
    remaining = target_value
    for row in candidates:
        if remaining <= 0:
            break
        qty = min(row['transferable'], max(1, remaining // row['unit_value']))
        if remaining > 0 and qty * row['unit_value'] < remaining and row['transferable'] > qty:
            qty = min(row['transferable'], qty + 1)
        if qty <= 0:
            continue
        if transfer_item(loser_id, winner_id, int(row['item_id']), int(qty)):
            value = qty * row['unit_value']
            moved.append({'item_id': int(row['item_id']), 'amount': int(qty), 'value': value})
            moved_value += value
            remaining = max(0, target_value - moved_value)
    debt_gold = 0
    loan_used = 0
    if moved_value < target_value:
        shortfall = target_value - moved_value
        player = get_player(loser_id) or {}
        if int(player.get('bank_debt', 0)) <= 0:
            from game_logic import loan_offer
            offer = loan_offer(player)
            if int(offer.get('amount', 0)) >= shortfall:
                ok, _ = create_loan(loser_id, shortfall)
                if ok and transfer_item(loser_id, winner_id, CURRENCY_ID, shortfall):
                    loan_used = shortfall
                    moved.append({'item_id': CURRENCY_ID, 'amount': shortfall, 'value': shortfall})
                    moved_value += shortfall
                    shortfall = 0
        if shortfall > 0:
            create_pvp_debt(loser_id, winner_id, shortfall, 'Дуэльный долг за недостающий трофей')
            debt_gold = shortfall
    return {'items': moved, 'value': moved_value, 'debt_gold': debt_gold, 'loan_used': loan_used}


def settle_pvp_bets(request_id: int, actual_winner_id: int) -> dict[str, Any]:
    req = get_pvp_request(request_id)
    if not req:
        return {'hero_share': [], 'bettors': []}
    bets = get_pvp_bets(request_id)
    by_item: dict[int, list[dict[str, Any]]] = {}
    for bet in bets:
        by_item.setdefault(int(bet['item_id']), []).append(bet)
    hero_rewards: list[dict[str, Any]] = []
    bettor_rewards: list[dict[str, Any]] = []
    for item_id, rows in by_item.items():
        winning_rows = [r for r in rows if int(r['pick_user']) == int(actual_winner_id)]
        losing_rows = [r for r in rows if int(r['pick_user']) != int(actual_winner_id)]
        total_w = sum(int(r['amount']) for r in winning_rows)
        total_l = sum(int(r['amount']) for r in losing_rows)
        hero_share = int(total_l * PVP_WINNER_BET_SHARE_RATE) if total_l else 0
        commission = int(total_l * PVP_BET_COMMISSION_RATE) if total_l else 0
        distributable = max(0, total_l - hero_share - commission)
        paid_out = 0
        if winning_rows and total_w > 0:
            for idx, row in enumerate(winning_rows, start=1):
                own_back = int(row['amount'])
                if idx == len(winning_rows):
                    bonus = max(0, distributable - paid_out)
                else:
                    bonus = int(distributable * own_back / total_w) if distributable else 0
                    paid_out += bonus
                payout = own_back + bonus
                if payout > 0:
                    add_item(int(row['user_id']), item_id, payout)
                    bettor_rewards.append({'user_id': int(row['user_id']), 'item_id': item_id, 'amount': payout})
        else:
            hero_share += distributable
        if hero_share > 0:
            add_item(actual_winner_id, item_id, hero_share)
            hero_rewards.append({'item_id': item_id, 'amount': hero_share})
    return {'hero_share': hero_rewards, 'bettors': bettor_rewards}


def create_deal(from_user: int, to_user: int, offer_item: int, offer_amount: int, want_item: int, want_amount: int, expires_at: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO deals(from_user, to_user, offer_item, offer_amount, want_item, want_amount, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (from_user, to_user, offer_item, offer_amount, want_item, want_amount, now_ts(), expires_at),
        )
        return int(cur.lastrowid)


def get_deal(deal_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM deals WHERE id = ?", (deal_id,)).fetchone()
        return row_to_dict(row)


def set_deal_status(deal_id: int, status: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE deals SET status = ? WHERE id = ?", (status, deal_id))


def complete_deal(deal_id: int) -> tuple[bool, str]:
    deal = get_deal(deal_id)
    if not deal or deal["status"] != "pending":
        return False, "Сделка недоступна."
    if get_item_amount(int(deal["from_user"]), int(deal["offer_item"])) < int(deal["offer_amount"]):
        return False, "У автора сделки больше нет нужного предмета."
    if get_item_amount(int(deal["to_user"]), int(deal["want_item"])) < int(deal["want_amount"]):
        return False, "У второй стороны нет нужного предмета."
    transfer_item(int(deal["from_user"]), int(deal["to_user"]), int(deal["offer_item"]), int(deal["offer_amount"]))
    transfer_item(int(deal["to_user"]), int(deal["from_user"]), int(deal["want_item"]), int(deal["want_amount"]))
    set_deal_status(deal_id, "done")
    change_reputation(int(deal["from_user"]), 2)
    change_reputation(int(deal["to_user"]), 2)
    return True, "Сделка завершена."


def create_item_request(user_id: int, item_id: int, target_amount: int, expires_at: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO item_requests(user_id, item_id, target_amount, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, item_id, target_amount, now_ts(), expires_at),
        )
        return int(cur.lastrowid)


def get_item_request(request_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM item_requests WHERE id = ?", (request_id,)).fetchone()
        return row_to_dict(row)


def get_open_item_requests(limit: int = 10) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM item_requests WHERE status = 'open' AND expires_at > ? ORDER BY created_at DESC LIMIT ?", (now_ts(), limit)).fetchall()
        return [dict(r) for r in rows]


def contribute_request(request_id: int, helper_id: int, amount: int) -> tuple[bool, str]:
    req = get_item_request(request_id)
    if not req or req["status"] != "open":
        return False, "Запрос не найден."
    item_id = int(req["item_id"])
    target_left = int(req["target_amount"]) - int(req["current_amount"])
    if target_left <= 0:
        return False, "Запрос уже закрыт."
    amount = min(amount, target_left)
    if get_item_amount(helper_id, item_id) < amount:
        return False, "У тебя нет такого количества предметов."
    if not transfer_item(helper_id, int(req["user_id"]), item_id, amount):
        return False, "Передача не удалась."
    with get_conn() as conn:
        conn.execute("UPDATE item_requests SET current_amount = current_amount + ? WHERE id = ?", (amount, request_id))
        conn.execute("INSERT INTO item_request_contrib(request_id, user_id, amount, created_at) VALUES (?, ?, ?, ?)", (request_id, helper_id, amount, now_ts()))
        conn.execute(
            "UPDATE item_requests SET status = CASE WHEN current_amount + ? >= target_amount THEN 'done' ELSE status END WHERE id = ?",
            (amount, request_id),
        )
    change_reputation(helper_id, 2)
    return True, f"Внесено {amount} шт."


# -----------------------------
# Рынок, аукционы, заказы
# -----------------------------

def create_market_listing(seller_id: int, item_id: int, amount: int, price_each: int, expires_at: int) -> tuple[bool, str | int]:
    if get_item_amount(seller_id, item_id) < amount:
        return False, "Не хватает предметов."
    if not remove_item(seller_id, item_id, amount):
        return False, "Не удалось снять предмет с инвентаря."
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO market_listings(seller_id, item_id, amount, price_each, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            (seller_id, item_id, amount, price_each, now_ts(), expires_at),
        )
        listing_id = int(cur.lastrowid)
    add_log(seller_id, "market", f"Выставлен лот #{listing_id} [{item_id}] x{amount} по {price_each}.")
    return True, listing_id


def get_market_listings(limit: int = 20, only_open: bool = True) -> list[dict[str, Any]]:
    q = "SELECT * FROM market_listings"
    params: list[Any] = []
    if only_open:
        q += " WHERE status = 'open' AND expires_at > ?"
        params.append(now_ts())
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def get_listing(listing_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM market_listings WHERE id = ?", (listing_id,)).fetchone()
        return row_to_dict(row)


def close_expired_market() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM market_listings WHERE status = 'open' AND expires_at <= ?", (now_ts(),)).fetchall()
        for row in rows:
            conn.execute("UPDATE market_listings SET status = 'expired' WHERE id = ?", (row["id"],))
            add_item(int(row["seller_id"]), int(row["item_id"]), int(row["amount"]))
        return [dict(r) for r in rows]


def buy_market_listing(buyer_id: int, listing_id: int) -> tuple[bool, str]:
    lot = get_listing(listing_id)
    if not lot or lot["status"] != "open" or int(lot["expires_at"]) <= now_ts():
        return False, "Лот недоступен."
    total = int(lot["amount"]) * int(lot["price_each"])
    fee = max(1, int(total * MARKET_FEE_RATE))
    if not spend_gold(buyer_id, total):
        return False, "Не хватает валюты."
    add_item(buyer_id, int(lot["item_id"]), int(lot["amount"]))
    add_gold(int(lot["seller_id"]), total - fee)
    with get_conn() as conn:
        conn.execute("UPDATE market_listings SET status = 'sold' WHERE id = ?", (listing_id,))
    send_mail(int(lot["seller_id"]), "Рынок", f"Твой лот #{listing_id} продан. Получено {total-fee} монет после комиссии.")
    return True, f"Куплен лот #{listing_id}."


def create_auction(seller_id: int, item_id: int, amount: int, start_bid: int, expires_at: int) -> tuple[bool, str | int]:
    if get_item_amount(seller_id, item_id) < amount:
        return False, "Не хватает предметов."
    if not remove_item(seller_id, item_id, amount):
        return False, "Не удалось снять предмет."
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO auctions(seller_id, item_id, amount, start_bid, current_bid, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (seller_id, item_id, amount, start_bid, start_bid, now_ts(), expires_at),
        )
        return True, int(cur.lastrowid)


def list_auctions(limit: int = 20) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM auctions WHERE status = 'open' AND expires_at > ? ORDER BY created_at DESC LIMIT ?", (now_ts(), limit)).fetchall()
        return [dict(r) for r in rows]


def get_auction(auction_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM auctions WHERE id = ?", (auction_id,)).fetchone()
        return row_to_dict(row)


def place_bid(user_id: int, auction_id: int, amount: int) -> tuple[bool, str]:
    auc = get_auction(auction_id)
    if not auc or auc["status"] != "open" or int(auc["expires_at"]) <= now_ts():
        return False, "Аукцион закрыт."
    if amount <= int(auc["current_bid"]):
        return False, "Ставка должна быть выше текущей."
    if not spend_gold(user_id, amount):
        return False, "Недостаточно монет."
    prev_bid = int(auc["current_bid"])
    prev_bidder = int(auc["current_bidder"])
    if prev_bidder:
        add_gold(prev_bidder, prev_bid)
        send_mail(prev_bidder, "Аукцион", f"Твою ставку по аукциону #{auction_id} перебили. Средства возвращены.")
    with get_conn() as conn:
        conn.execute("UPDATE auctions SET current_bid = ?, current_bidder = ? WHERE id = ?", (amount, user_id, auction_id))
    return True, "Ставка принята."


def close_due_auctions() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM auctions WHERE status = 'open' AND expires_at <= ?", (now_ts(),)).fetchall()
        for row in rows:
            if int(row["current_bidder"]):
                add_item(int(row["current_bidder"]), int(row["item_id"]), int(row["amount"]))
                add_gold(int(row["seller_id"]), int(row["current_bid"]))
                send_mail(int(row["seller_id"]), "Аукцион", f"Аукцион #{row['id']} завершён. Получено {row['current_bid']} монет.")
                send_mail(int(row["current_bidder"]), "Аукцион", f"Ты выиграл аукцион #{row['id']}.")
                status = "sold"
            else:
                add_item(int(row["seller_id"]), int(row["item_id"]), int(row["amount"]))
                status = "expired"
            conn.execute("UPDATE auctions SET status = ? WHERE id = ?", (status, row["id"]))
        return [dict(r) for r in rows]


def create_buy_order(buyer_id: int, item_id: int, amount: int, price_each: int, expires_at: int) -> tuple[bool, str | int]:
    total = amount * price_each
    if not spend_gold(buyer_id, total):
        return False, "Не хватает монет для резервирования заказа."
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO buy_orders(buyer_id, item_id, amount_left, price_each, reserved_gold, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (buyer_id, item_id, amount, price_each, total, now_ts(), expires_at),
        )
        return True, int(cur.lastrowid)


def list_buy_orders(limit: int = 20) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM buy_orders WHERE status = 'open' AND expires_at > ? ORDER BY created_at DESC LIMIT ?", (now_ts(), limit)).fetchall()
        return [dict(r) for r in rows]


def fulfill_buy_order(seller_id: int, order_id: int, amount: int) -> tuple[bool, str]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM buy_orders WHERE id = ?", (order_id,)).fetchone()
        if not row:
            return False, "Заказ не найден."
        order = dict(row)
    if order["status"] != "open" or int(order["expires_at"]) <= now_ts():
        return False, "Заказ закрыт."
    amount = min(amount, int(order["amount_left"]))
    if get_item_amount(seller_id, int(order["item_id"])) < amount:
        return False, "У тебя не хватает предметов."
    if not remove_item(seller_id, int(order["item_id"]), amount):
        return False, "Не удалось снять предмет."
    add_item(int(order["buyer_id"]), int(order["item_id"]), amount)
    payout = amount * int(order["price_each"])
    add_gold(seller_id, payout)
    with get_conn() as conn:
        conn.execute("UPDATE buy_orders SET amount_left = amount_left - ?, reserved_gold = reserved_gold - ? WHERE id = ?", (amount, payout, order_id))
        conn.execute("UPDATE buy_orders SET status = 'done' WHERE id = ? AND amount_left - ? <= 0", (order_id, amount))
    return True, f"Заказ частично/полностью выполнен. Получено {payout} монет."


def close_expired_buy_orders() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM buy_orders WHERE status = 'open' AND expires_at <= ?", (now_ts(),)).fetchall()
        for row in rows:
            if int(row["reserved_gold"]) > 0:
                add_gold(int(row["buyer_id"]), int(row["reserved_gold"]))
            conn.execute("UPDATE buy_orders SET status = 'expired' WHERE id = ?", (row["id"],))
        return [dict(r) for r in rows]


# -----------------------------
# Почта и логи
# -----------------------------

def send_mail(to_user: int, subject: str, body: str, payload: dict[str, Any] | None = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO mails(to_user, subject, body, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (to_user, subject, body, json.dumps(payload or {}, ensure_ascii=False), now_ts()),
        )
        return int(cur.lastrowid)


def list_mail(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM mails WHERE to_user = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit)).fetchall()
        return [dict(r) for r in rows]


def read_mail(mail_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM mails WHERE id = ?", (mail_id,)).fetchone()
        return row_to_dict(row)


def mark_mail_read(mail_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE mails SET is_read = 1 WHERE id = ?", (mail_id,))


def add_log(user_id: int, kind: str, text: str) -> None:
    with get_conn() as conn:
        conn.execute("INSERT INTO logs(user_id, kind, text, created_at) VALUES (?, ?, ?, ?)", (user_id, kind, text, now_ts()))
        conn.execute(
            "DELETE FROM logs WHERE id NOT IN (SELECT id FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT 200) AND user_id = ?",
            (user_id, user_id),
        )


def list_logs(user_id: int, limit: int = 15) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)).fetchall()
        return [dict(r) for r in rows]


# -----------------------------
# Кланы / стаи
# -----------------------------

def create_clan(leader_id: int, name: str) -> tuple[bool, str | int]:
    player = get_player(leader_id)
    if not player:
        return False, "Игрок не найден."
    if int(player.get("clan_id", 0)):
        return False, "Ты уже состоишь в стае."
    if not spend_gold(leader_id, CLAN_CREATE_PRICE):
        return False, f"Для создания стаи нужно {CLAN_CREATE_PRICE} монет."
    try:
        with get_conn() as conn:
            cur = conn.execute("INSERT INTO clans(name, leader_id, treasury, reputation, created_at) VALUES (?, ?, 0, 0, ?)", (name, leader_id, now_ts()))
            clan_id = int(cur.lastrowid)
            conn.execute("INSERT INTO clan_members(clan_id, user_id, role, joined_at) VALUES (?, ?, 'leader', ?)", (clan_id, leader_id, now_ts()))
            conn.execute("UPDATE players SET clan_id = ? WHERE user_id = ?", (clan_id, leader_id))
        return True, clan_id
    except sqlite3.IntegrityError:
        add_gold(leader_id, CLAN_CREATE_PRICE)
        return False, "Такое имя стаи уже занято."


def list_clans(limit: int = 12) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM clans ORDER BY treasury DESC, reputation DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def get_clan(clan_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM clans WHERE id = ?", (clan_id,)).fetchone()
        return row_to_dict(row)


def get_clan_members(clan_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM clan_members WHERE clan_id = ? ORDER BY role, contribution DESC", (clan_id,)).fetchall()
        return [dict(r) for r in rows]


def join_clan(user_id: int, clan_id: int) -> tuple[bool, str]:
    player = get_player(user_id) or {}
    if int(player.get("clan_id", 0)):
        return False, "Ты уже состоишь в стае."
    with get_conn() as conn:
        conn.execute("INSERT OR REPLACE INTO clan_members(clan_id, user_id, role, joined_at) VALUES (?, ?, 'member', ?)", (clan_id, user_id, now_ts()))
        conn.execute("UPDATE players SET clan_id = ? WHERE user_id = ?", (clan_id, user_id))
    return True, "Ты вступил в стаю."


def leave_clan(user_id: int) -> tuple[bool, str]:
    player = get_player(user_id) or {}
    clan_id = int(player.get("clan_id", 0))
    if not clan_id:
        return False, "Ты не состоишь в стае."
    with get_conn() as conn:
        row = conn.execute("SELECT role FROM clan_members WHERE clan_id = ? AND user_id = ?", (clan_id, user_id)).fetchone()
        role = row[0] if row else "member"
        if role == "leader":
            count = conn.execute("SELECT COUNT(*) FROM clan_members WHERE clan_id = ?", (clan_id,)).fetchone()[0]
            if count > 1:
                return False, "Сначала передай лидерство или распусти стаю."
            conn.execute("DELETE FROM clans WHERE id = ?", (clan_id,))
            conn.execute("DELETE FROM clan_members WHERE clan_id = ?", (clan_id,))
        else:
            conn.execute("DELETE FROM clan_members WHERE clan_id = ? AND user_id = ?", (clan_id, user_id))
        conn.execute("UPDATE players SET clan_id = 0 WHERE user_id = ?", (user_id,))
    return True, "Ты покинул стаю."


def donate_clan_treasury(user_id: int, amount: int) -> tuple[bool, str]:
    player = get_player(user_id) or {}
    clan_id = int(player.get("clan_id", 0))
    if not clan_id:
        return False, "Ты не в стае."
    if not spend_gold(user_id, amount):
        return False, "Не хватает монет."
    with get_conn() as conn:
        conn.execute("UPDATE clans SET treasury = treasury + ?, reputation = reputation + ? WHERE id = ?", (amount, max(1, amount // 20), clan_id))
        conn.execute("UPDATE clan_members SET contribution = contribution + ? WHERE clan_id = ? AND user_id = ?", (amount, clan_id, user_id))
    return True, f"В казну внесено {amount} монет."


# -----------------------------
# Задания
# -----------------------------

def ensure_tasks(user_id: int, period_key: str, task_kind: str, task_defs: list[dict[str, Any]]) -> None:
    with get_conn() as conn:
        existing = conn.execute("SELECT 1 FROM tasks WHERE user_id = ? AND period_key = ? AND task_kind = ? LIMIT 1", (user_id, period_key, task_kind)).fetchone()
        if existing:
            return
        for task in task_defs:
            conn.execute(
                "INSERT INTO tasks(user_id, period_key, task_kind, task_code, title, progress, target, reward_gold, reward_xp, claimed) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, 0)",
                (user_id, period_key, task_kind, task["code"], task["title"], task["target"], task["reward_gold"], task["reward_xp"]),
            )


def list_tasks(user_id: int, period_key: str, task_kind: str) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? AND period_key = ? AND task_kind = ? ORDER BY task_code",
            (user_id, period_key, task_kind),
        ).fetchall()
        return [dict(r) for r in rows]


def advance_task(user_id: int, task_code: str, amount: int = 1) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET progress = MIN(target, progress + ?) WHERE user_id = ? AND task_code = ? AND claimed = 0",
            (amount, user_id, task_code),
        )


def claim_task(user_id: int, period_key: str, task_kind: str, task_code: str) -> tuple[bool, str]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? AND period_key = ? AND task_kind = ? AND task_code = ?",
            (user_id, period_key, task_kind, task_code),
        ).fetchone()
        if not row:
            return False, "Задание не найдено."
        task = dict(row)
        if int(task["claimed"]):
            return False, "Награда уже получена."
        if int(task["progress"]) < int(task["target"]):
            return False, "Задание ещё не выполнено."
        conn.execute(
            "UPDATE tasks SET claimed = 1 WHERE user_id = ? AND period_key = ? AND task_kind = ? AND task_code = ?",
            (user_id, period_key, task_kind, task_code),
        )
    add_gold(user_id, int(task["reward_gold"]))
    add_xp(user_id, int(task["reward_xp"]))
    add_log(user_id, "task", f"Получена награда за задание {task['title']}.")
    return True, f"Награда: {task['reward_gold']} монет и {task['reward_xp']} XP."


# -----------------------------
# Мир и сезон
# -----------------------------

def get_world_state(state_key: str, default: Any = None) -> Any:
    with get_conn() as conn:
        row = conn.execute("SELECT value_json FROM world_state WHERE state_key = ?", (state_key,)).fetchone()
        return parse_json(row[0], default) if row else default


def set_world_state(state_key: str, value: Any) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO world_state(state_key, value_json, updated_at) VALUES (?, ?, ?)",
            (state_key, json.dumps(value, ensure_ascii=False), now_ts()),
        )


# -----------------------------
# Рефералка и подозрительная активность
# -----------------------------

def get_referrals(referrer_id: int) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM referrals WHERE referrer_id = ? ORDER BY created_at DESC", (referrer_id,)).fetchall()
        return [dict(r) for r in rows]


def set_referral_reward_choice(referred_id: int, choice: str) -> tuple[bool, str]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM referrals WHERE referred_id = ?", (referred_id,)).fetchone()
        if not row:
            return False, "Реферал не найден."
        ref = dict(row)
        if int(ref["reward_claimed"]):
            return False, "Награда уже выбрана."
        conn.execute(
            "UPDATE referrals SET reward_choice = ?, reward_claimed = 1 WHERE referred_id = ?",
            (choice, referred_id),
        )
    if choice == "gold":
        add_gold(int(ref["referrer_id"]), REFERRAL_GOLD_REWARD)
        send_mail(int(ref["referrer_id"]), "Реферальная награда", f"За приглашение игрока ты получил {REFERRAL_GOLD_REWARD} монет.")
    else:
        from data_items import REFERRAL_GIFT_ITEM
        add_item(int(ref["referrer_id"]), REFERRAL_GIFT_ITEM, REFERRAL_ITEM_REWARD_AMOUNT)
        send_mail(int(ref["referrer_id"]), "Реферальная награда", f"За приглашение игрока ты получил предмет [{REFERRAL_GIFT_ITEM}] x{REFERRAL_ITEM_REWARD_AMOUNT}.")
    return True, "Награда выдана."


def add_suspicion(user_id: int, reason: str, details: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO suspicions(user_id, reason, details, created_at) VALUES (?, ?, ?, ?)",
            (user_id, reason, details, now_ts()),
        )
        return int(cur.lastrowid)


def list_suspicions(only_unsent: bool = False, limit: int = 25) -> list[dict[str, Any]]:
    q = "SELECT * FROM suspicions"
    params: list[Any] = []
    if only_unsent:
        q += " WHERE sent_to_owner = 0"
    q += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]


def mark_suspicion_sent(suspicion_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE suspicions SET sent_to_owner = 1 WHERE id = ?", (suspicion_id,))


def suspicious_referral_count(referrer_id: int, hours: int = 24) -> int:
    cutoff = now_ts() - hours * 3600
    with get_conn() as conn:
        row = conn.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND created_at >= ?", (referrer_id, cutoff)).fetchone()
        return int(row[0]) if row else 0


# -----------------------------
# Почта, лагерь, питомцы
# -----------------------------

def set_pet(user_id: int, species: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET pet_species = ?, pet_level = CASE WHEN pet_level < 1 THEN 1 ELSE pet_level END WHERE user_id = ?", (species, user_id))


def train_pet(user_id: int, delta: int = 1) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET pet_level = pet_level + ? WHERE user_id = ?", (delta, user_id))


def set_camp(user_id: int, until_ts: int, hours: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET camp_until = ?, camp_hours = ? WHERE user_id = ?", (until_ts, hours, user_id))


def clear_camp(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE players SET camp_until = 0, camp_hours = 0 WHERE user_id = ?", (user_id,))


# -----------------------------
# Банк
# -----------------------------

def create_loan(user_id: int, amount: int) -> tuple[bool, str]:
    player = get_player(user_id) or {}
    if int(player.get("bank_debt", 0)) > 0:
        return False, "Сначала погаси старый кредит."
    add_gold(user_id, amount)
    debt = int(amount * (1 + 0.12))
    with get_conn() as conn:
        conn.execute("UPDATE players SET bank_debt = ?, bank_due_ts = ? WHERE user_id = ?", (debt, now_ts() + LOAN_TERM_HOURS * 3600, user_id))
    return True, f"Кредит выдан. К возврату: {debt} монет."


def repay_loan(user_id: int) -> tuple[bool, str]:
    player = get_player(user_id) or {}
    debt = int(player.get("bank_debt", 0))
    if debt <= 0:
        return False, "У тебя нет кредита."
    if not spend_gold(user_id, debt):
        return False, "Не хватает монет для погашения."
    with get_conn() as conn:
        conn.execute("UPDATE players SET bank_debt = 0, bank_due_ts = 0 WHERE user_id = ?", (user_id,))
    return True, "Кредит погашен."


def apply_overdue_loans() -> list[int]:
    debtors = []
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id, bank_debt FROM players WHERE bank_debt > 0 AND bank_due_ts > 0 AND bank_due_ts <= ?", (now_ts(),)).fetchall()
        for row in rows:
            debtors.append(int(row["user_id"]))
            conn.execute("UPDATE players SET bank_debt = CAST(bank_debt * 1.025 AS INTEGER), bank_due_ts = ? WHERE user_id = ?", (now_ts() + 24 * 3600, row["user_id"]))
    return debtors


# -----------------------------
# Топы
# -----------------------------

def top_by_level(limit: int = 10) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id, username, full_name, level, xp FROM players WHERE registered = 1 ORDER BY level DESC, xp DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def top_by_wins(limit: int = 10) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id, username, full_name, wins, rating FROM players WHERE registered = 1 ORDER BY wins DESC, rating DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def top_by_rich(limit: int = 10) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id, username, full_name, gold FROM players WHERE registered = 1 ORDER BY gold DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


def top_by_rep(limit: int = 10) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id, username, full_name, reputation FROM players WHERE registered = 1 ORDER BY reputation DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]


# -----------------------------
# Монетизация для админ-панели
# -----------------------------

def ensure_default_packs(defaults: list[dict[str, Any]]) -> None:
    with get_conn() as conn:
        for pack in defaults:
            conn.execute(
                "INSERT OR IGNORE INTO monetization_packs(code, name, price_rub, reward_json, enabled, stock, price_stars, stars_enabled) VALUES (?, ?, ?, ?, 1, 0, ?, ?)",
                (
                    pack["code"],
                    pack["name"],
                    pack["price_rub"],
                    json.dumps(pack["reward"], ensure_ascii=False),
                    int(pack.get("price_stars", 0) or 0),
                    1 if int(pack.get("price_stars", 0) or 0) > 0 else 0,
                ),
            )


def list_packs() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM monetization_packs ORDER BY price_rub, code").fetchall()
        return [dict(r) for r in rows]


def toggle_pack(code: str) -> tuple[bool, str]:
    with get_conn() as conn:
        row = conn.execute("SELECT enabled FROM monetization_packs WHERE code = ?", (code,)).fetchone()
        if not row:
            return False, "Пак не найден."
        new_val = 0 if int(row[0]) else 1
        conn.execute("UPDATE monetization_packs SET enabled = ? WHERE code = ?", (new_val, code))
        return True, "Пак обновлён."

def toggle_pack_stars(code: str) -> tuple[bool, str]:
    with get_conn() as conn:
        row = conn.execute("SELECT stars_enabled, price_stars FROM monetization_packs WHERE code = ?", (code,)).fetchone()
        if not row:
            return False, "Пак не найден."
        if int(row['price_stars'] if isinstance(row, sqlite3.Row) else row[1]) <= 0:
            return False, "Сначала укажи цену в звёздах для этого пака."
        current = int(row['stars_enabled'] if isinstance(row, sqlite3.Row) else row[0])
        new_val = 0 if current else 1
        conn.execute("UPDATE monetization_packs SET stars_enabled = ? WHERE code = ?", (new_val, code))
        return True, "Продажа за звёзды обновлена."


def set_pack_stars_price(code: str, price_stars: int) -> tuple[bool, str]:
    price_stars = max(0, int(price_stars))
    with get_conn() as conn:
        row = conn.execute("SELECT code FROM monetization_packs WHERE code = ?", (code,)).fetchone()
        if not row:
            return False, "Пак не найден."
        conn.execute("UPDATE monetization_packs SET price_stars = ?, stars_enabled = ? WHERE code = ?", (price_stars, 1 if price_stars > 0 else 0, code))
        return True, "Цена в звёздах сохранена."


def donation_enabled() -> bool:
    state = get_world_state('donation_settings', {}) or {}
    return bool(state.get('enabled', 0))


def toggle_donation_enabled() -> tuple[bool, str]:
    state = get_world_state('donation_settings', {}) or {}
    new_val = 0 if state.get('enabled') else 1
    state['enabled'] = new_val
    set_world_state('donation_settings', state)
    return True, 'Донат включён.' if new_val else 'Донат выключен.'


def set_bank_debt_admin(user_id: int, target_debt: int) -> tuple[bool, str]:
    player = get_player(user_id)
    if not player:
        return False, 'Игрок не найден.'
    target_debt = max(0, int(target_debt))
    due_ts = now_ts() + 72 * 3600 if target_debt > 0 else 0
    with get_conn() as conn:
        conn.execute("UPDATE players SET bank_debt = ?, bank_due_ts = ? WHERE user_id = ?", (target_debt, due_ts, user_id))
    if target_debt > 0:
        return True, f'Банковский долг игрока установлен: {target_debt} монет.'
    return True, 'Банковский долг полностью аннулирован.'


def reduce_bank_debt_admin(user_id: int, amount: int) -> tuple[bool, str]:
    player = get_player(user_id)
    if not player:
        return False, 'Игрок не найден.'
    amount = max(0, int(amount))
    current = int(player.get('bank_debt', 0))
    new_val = max(0, current - amount)
    due_ts = int(player.get('bank_due_ts', 0)) if new_val > 0 else 0
    with get_conn() as conn:
        conn.execute("UPDATE players SET bank_debt = ?, bank_due_ts = ? WHERE user_id = ?", (new_val, due_ts, user_id))
    if new_val == current:
        return True, 'Долг не изменился.'
    if new_val == 0:
        return True, 'Банковский долг полностью погашен админом.'
    return True, f'Банковский долг уменьшен. Осталось: {new_val} монет.'


def grant_pack_to_user(code: str, user_id: int) -> tuple[bool, str]:
    with get_conn() as conn:
        row = conn.execute("SELECT reward_json FROM monetization_packs WHERE code = ?", (code,)).fetchone()
        if not row:
            return False, "Пак не найден."
        reward = parse_json(row[0], {})
    if reward.get("gold"):
        add_gold(user_id, int(reward["gold"]))
    if reward.get("premium"):
        add_premium(user_id, int(reward["premium"]))
    send_mail(user_id, "Донат-награда", f"Тебе выдан пакет {code}: {reward}")
    return True, "Пак выдан."


def create_promo(code: str, reward: dict[str, Any], uses_left: int, expires_at: int = 0) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO promo_codes(code, reward_json, uses_left, expires_at) VALUES (?, ?, ?, ?)",
            (code.upper(), json.dumps(reward, ensure_ascii=False), uses_left, expires_at),
        )


def list_promos() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM promo_codes ORDER BY code").fetchall()
        return [dict(r) for r in rows]


def redeem_promo(user_id: int, code: str) -> tuple[bool, str]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM promo_codes WHERE code = ?", (code.upper(),)).fetchone()
        if not row:
            return False, "Промокод не найден."
        promo = dict(row)
        if int(promo["uses_left"]) <= 0:
            return False, "Промокод исчерпан."
        if int(promo["expires_at"]) and int(promo["expires_at"]) < now_ts():
            return False, "Промокод истёк."
        conn.execute("UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code = ?", (code.upper(),))
    reward = parse_json(promo["reward_json"], {})
    if reward.get("gold"):
        add_gold(user_id, int(reward["gold"]))
    if reward.get("premium"):
        add_premium(user_id, int(reward["premium"]))
    if reward.get("item_id"):
        add_item(user_id, int(reward["item_id"]), int(reward.get("amount", 1)))
    return True, f"Промокод активирован: {reward}"


# -----------------------------
# Эндгейм 3.0: престиж, таланты, фракции, контракты
# -----------------------------

def ensure_player_extras(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO player_extras(user_id, prestige, talent_points, talents_json, faction_key, faction_rep, faction_last_claim, contracts_json) VALUES (?, 0, 0, '{}', '', 0, 0, '{}')",
            (user_id,),
        )


def get_player_extras(user_id: int) -> dict[str, Any]:
    ensure_player_extras(user_id)
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM player_extras WHERE user_id = ?", (user_id,)).fetchone()
    out = row_to_dict(row) or {
        "user_id": user_id,
        "prestige": 0,
        "talent_points": 0,
        "talents_json": '{}',
        "faction_key": '',
        "faction_rep": 0,
        "faction_last_claim": 0,
        "contracts_json": '{}',
    }
    out["talents"] = parse_json(out.get("talents_json"), {})
    out["contracts"] = parse_json(out.get("contracts_json"), {"day": 0, "done": []})
    return out


def add_talent_points(user_id: int, amount: int) -> None:
    ensure_player_extras(user_id)
    with get_conn() as conn:
        conn.execute("UPDATE player_extras SET talent_points = talent_points + ? WHERE user_id = ?", (int(amount), user_id))


def award_talent_points_for_levels(user_id: int, old_level: int, new_level: int) -> int:
    if new_level <= old_level:
        return 0
    points = 0
    for lvl in range(old_level + 1, new_level + 1):
        if lvl % 10 == 0:
            points += 1
        if lvl % 100 == 0:
            points += 1
    if points:
        add_talent_points(user_id, points)
    return points


def learn_talent(user_id: int, talent_code: str, max_rank: int = 3) -> tuple[bool, str]:
    extra = get_player_extras(user_id)
    points = int(extra.get("talent_points", 0))
    talents = dict(extra.get("talents", {}))
    rank = int(talents.get(talent_code, 0))
    if points <= 0:
        return False, "Нет свободных очков талантов."
    if rank >= max_rank:
        return False, "Этот талант уже изучен на максимум."
    talents[talent_code] = rank + 1
    with get_conn() as conn:
        conn.execute(
            "UPDATE player_extras SET talent_points = talent_points - 1, talents_json = ? WHERE user_id = ?",
            (json.dumps(talents, ensure_ascii=False), user_id),
        )
    add_log(user_id, "talent", f"Улучшен талант {talent_code} до ранга {rank + 1}")
    return True, "Талант улучшен."


def reset_talents(user_id: int, price: int = TALENT_RESET_PRICE) -> tuple[bool, str]:
    extra = get_player_extras(user_id)
    talents = dict(extra.get("talents", {}))
    spent = sum(int(v) for v in talents.values())
    if spent <= 0:
        return False, "Сбрасывать нечего."
    if not spend_gold(user_id, price):
        return False, "Не хватает монет для сброса."
    with get_conn() as conn:
        conn.execute(
            "UPDATE player_extras SET talent_points = talent_points + ?, talents_json = '{}' WHERE user_id = ?",
            (spent, user_id),
        )
    add_log(user_id, "talent_reset", f"Таланты сброшены за {price} монет.")
    return True, f"Таланты сброшены. Возвращено очков: {spent}."


def set_faction(user_id: int, faction_key: str) -> tuple[bool, str]:
    extra = get_player_extras(user_id)
    current = extra.get("faction_key", "")
    if current == faction_key:
        return False, "Ты уже в этой фракции."
    with get_conn() as conn:
        conn.execute(
            "UPDATE player_extras SET faction_key = ?, faction_rep = CASE WHEN faction_key = ? THEN faction_rep ELSE 0 END WHERE user_id = ?",
            (faction_key, faction_key, user_id),
        )
    add_log(user_id, "faction", f"Вступление во фракцию {faction_key}")
    return True, "Фракция выбрана."


def add_faction_rep(user_id: int, delta: int) -> None:
    ensure_player_extras(user_id)
    with get_conn() as conn:
        conn.execute("UPDATE player_extras SET faction_rep = MAX(0, faction_rep + ?) WHERE user_id = ?", (int(delta), user_id))


def claim_faction_daily(user_id: int, day_key: int) -> tuple[bool, dict[str, Any]]:
    extra = get_player_extras(user_id)
    if int(extra.get("faction_last_claim", 0)) == int(day_key):
        return False, {"reason": "Сегодня награда уже получена."}
    with get_conn() as conn:
        conn.execute("UPDATE player_extras SET faction_last_claim = ? WHERE user_id = ?", (int(day_key), user_id))
    return True, {"faction_key": extra.get("faction_key", ""), "rep": int(extra.get("faction_rep", 0))}


def contract_state(user_id: int) -> dict[str, Any]:
    extra = get_player_extras(user_id)
    state = dict(extra.get("contracts", {"day": 0, "done": []}))
    if not isinstance(state.get("done"), list):
        state["done"] = []
    return state


def can_run_contract(user_id: int, contract_code: str, day_key: int) -> tuple[bool, str]:
    state = contract_state(user_id)
    if int(state.get("day", 0)) != int(day_key):
        return True, ""
    if contract_code in state.get("done", []):
        return False, "Этот контракт уже выполнен сегодня."
    return True, ""


def mark_contract_done(user_id: int, contract_code: str, day_key: int) -> None:
    state = contract_state(user_id)
    if int(state.get("day", 0)) != int(day_key):
        state = {"day": int(day_key), "done": []}
    done = list(state.get("done", []))
    if contract_code not in done:
        done.append(contract_code)
    state = {"day": int(day_key), "done": done}
    with get_conn() as conn:
        conn.execute("UPDATE player_extras SET contracts_json = ? WHERE user_id = ?", (json.dumps(state, ensure_ascii=False), user_id))


def can_prestige(user_id: int) -> bool:
    p = get_player(user_id) or {}
    return int(p.get("level", 1)) >= MAX_LEVEL


def perform_prestige(user_id: int) -> tuple[bool, str]:
    if not can_prestige(user_id):
        return False, f"Для престижа нужен {MAX_LEVEL} уровень."
    ensure_player_extras(user_id)
    with get_conn() as conn:
        conn.execute("UPDATE players SET level = 1, xp = 0, hp = 100, energy = 100, dead_until = 0 WHERE user_id = ?", (user_id,))
        conn.execute("UPDATE player_extras SET prestige = prestige + 1, talent_points = talent_points + 2 WHERE user_id = ?", (user_id,))
    add_premium(user_id, 1)
    add_log(user_id, "prestige", "Совершён престиж: сброшен уровень, получены постоянные бонусы.")
    send_mail(user_id, "Престиж совершен", "Ты завершил престиж. Получен 1 лунный кристалл и 2 очка талантов.")
    return True, "Престиж совершен. Уровень сброшен до 1, но бонусы престижа сохранены."
