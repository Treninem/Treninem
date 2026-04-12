from __future__ import annotations

import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from .config import DB_PATH, LINK_CODE_TTL_MINUTES, SESSION_TTL_DAYS
from .seed_data import ITEMS, RECIPES, CHARACTERS


def utcnow() -> datetime:
    return datetime.utcnow()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def now_str() -> str:
    return utcnow().isoformat()


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def _ensure_column(conn: sqlite3.Connection, table: str, name: str, ddl: str):
    cols = _table_columns(conn, table)
    if name not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vk_user_id INTEGER UNIQUE,
                username TEXT,
                display_name TEXT NOT NULL,
                avatar_url TEXT DEFAULT '',
                character_key TEXT DEFAULT '',
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 500,
                hp INTEGER DEFAULT 100,
                max_hp INTEGER DEFAULT 100,
                energy INTEGER DEFAULT 100,
                max_energy INTEGER DEFAULT 100,
                attack INTEGER DEFAULT 10,
                defense INTEGER DEFAULT 10,
                speed INTEGER DEFAULT 10,
                inventory_slots INTEGER DEFAULT 30,
                weight_limit REAL DEFAULT 50,
                pvp_wins INTEGER DEFAULT 0,
                pvp_losses INTEGER DEFAULT 0,
                dungeon_level INTEGER DEFAULT 1,
                bank_debt INTEGER DEFAULT 0,
                bank_due_at TEXT DEFAULT '',
                settings_json TEXT DEFAULT '{}',
                is_banned INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS item_defs (
                item_code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                rarity TEXT NOT NULL,
                description TEXT NOT NULL,
                weight REAL NOT NULL,
                price INTEGER NOT NULL,
                effect_kind TEXT NOT NULL,
                effect_stat TEXT NOT NULL,
                effect_value INTEGER NOT NULL,
                effect_duration INTEGER NOT NULL,
                equip_slot TEXT NOT NULL,
                is_consumable INTEGER NOT NULL,
                is_stackable INTEGER NOT NULL,
                icon TEXT NOT NULL,
                is_custom INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_code TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                equipped INTEGER DEFAULT 0,
                UNIQUE(user_id, item_code, equipped),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(item_code) REFERENCES item_defs(item_code) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS recipes (
                recipe_code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                ingredients_json TEXT NOT NULL,
                result_item_code TEXT NOT NULL,
                result_qty INTEGER NOT NULL,
                difficulty TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS shop_offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slot_index INTEGER NOT NULL,
                item_code TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price INTEGER NOT NULL,
                generated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS market_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_id INTEGER NOT NULL,
                item_code TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                FOREIGN KEY(seller_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(item_code) REFERENCES item_defs(item_code) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cooldowns (
                user_id INTEGER NOT NULL,
                action_key TEXT NOT NULL,
                ready_at TEXT NOT NULL,
                PRIMARY KEY(user_id, action_key)
            );

            CREATE TABLE IF NOT EXISTS link_codes (
                code TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS reward_claims (
                user_id INTEGER NOT NULL,
                claim_key TEXT NOT NULL,
                payload TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                PRIMARY KEY(user_id, claim_key),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )
        _ensure_column(conn, 'users', 'bank_debt', "INTEGER DEFAULT 0")
        _ensure_column(conn, 'users', 'bank_due_at', "TEXT DEFAULT ''")
        _ensure_column(conn, 'users', 'settings_json', "TEXT DEFAULT '{}' ")
        seed_defaults(conn)
        refresh_shop_if_needed(conn)


def seed_defaults(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.executemany(
        '''INSERT OR IGNORE INTO item_defs (
            item_code, name, category, rarity, description, weight, price,
            effect_kind, effect_stat, effect_value, effect_duration, equip_slot,
            is_consumable, is_stackable, icon, is_custom
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)''',
        [(
            i['item_code'], i['name'], i['category'], i['rarity'], i['description'], i['weight'], i['price'],
            i['effect_kind'], i['effect_stat'], i['effect_value'], i['effect_duration'], i['equip_slot'],
            i['is_consumable'], i['is_stackable'], i['icon']
        ) for i in ITEMS],
    )
    cur.executemany(
        'INSERT OR IGNORE INTO recipes (recipe_code, name, ingredients_json, result_item_code, result_qty, difficulty) VALUES (?, ?, ?, ?, ?, ?)',
        [(
            r['recipe_code'], r['name'], json.dumps(r['ingredients'], ensure_ascii=False),
            r['result_item_code'], r['result_qty'], r['difficulty']
        ) for r in RECIPES],
    )


def get_or_create_user(vk_user_id: Optional[int], display_name: str, avatar_url: str = '') -> Dict[str, Any]:
    with get_conn() as conn:
        cur = conn.cursor()
        if vk_user_id is not None:
            cur.execute('SELECT id FROM users WHERE vk_user_id=?', (vk_user_id,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    'UPDATE users SET display_name=?, avatar_url=?, updated_at=? WHERE id=?',
                    (display_name, avatar_url, now_str(), row['id']),
                )
                return get_user_with_conn(conn, row['id'])
        created = now_str()
        cur.execute(
            '''INSERT INTO users (vk_user_id, username, display_name, avatar_url, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (vk_user_id, display_name.lower().replace(' ', '_'), display_name, avatar_url, created, created),
        )
        user_id = cur.lastrowid
        add_item(conn, user_id, 'ID101001', 3)
        add_item(conn, user_id, 'ID301001', 5)
        add_item(conn, user_id, 'ID501001', 1)
        record_activity(conn, user_id, 'account_created', {'display_name': display_name})
        return get_user_with_conn(conn, user_id)


def get_user_with_conn(conn: sqlite3.Connection, user_id: int) -> Dict[str, Any]:
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE id=?', (user_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError('User not found')
    user = dict(row)
    user['character'] = CHARACTERS.get(user['character_key'])
    user['equipment'] = get_equipped_items(conn, user_id)
    user['activity_today'] = get_activity_counters(conn, user_id, since=start_of_day())
    return user


def get_user(user_id: int) -> Dict[str, Any]:
    with get_conn() as conn:
        return get_user_with_conn(conn, user_id)


def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute('SELECT user_id, expires_at FROM sessions WHERE token=?', (token,)).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row['expires_at']) < utcnow():
            conn.execute('DELETE FROM sessions WHERE token=?', (token,))
            return None
        return get_user_with_conn(conn, int(row['user_id']))


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)',
            (token, user_id, now_str(), (utcnow() + timedelta(days=SESSION_TTL_DAYS)).isoformat()),
        )
    return token


def set_character(user_id: int, character_key: str):
    if character_key not in CHARACTERS:
        raise ValueError('Unknown character')
    data = CHARACTERS[character_key]['stats']
    with get_conn() as conn:
        conn.execute(
            '''UPDATE users SET character_key=?, hp=?, max_hp=?, energy=?, max_energy=?, attack=?, defense=?, speed=?, updated_at=?
               WHERE id=? AND (character_key='' OR character_key IS NULL)''',
            (character_key, data['hp'], data['hp'], data['energy'], data['energy'], data['attack'], data['defense'], data['speed'], now_str(), user_id),
        )
        record_activity(conn, user_id, 'character_selected', {'character_key': character_key})


# ---------- Items & Inventory ----------

def get_item_def(conn: sqlite3.Connection, item_code: str) -> Dict[str, Any]:
    row = conn.execute('SELECT * FROM item_defs WHERE item_code=?', (item_code,)).fetchone()
    if not row:
        raise ValueError(f'Unknown item {item_code}')
    return dict(row)


def list_inventory(user_id: int) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            '''SELECT i.item_code, i.quantity, i.equipped, d.name, d.category, d.rarity, d.description,
                      d.weight, d.price, d.effect_kind, d.effect_stat, d.effect_value, d.effect_duration,
                      d.equip_slot, d.icon, d.is_consumable, d.is_stackable
               FROM inventory i JOIN item_defs d ON i.item_code=d.item_code
               WHERE i.user_id=? ORDER BY d.category, d.rarity, d.name''',
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_equipped_items(conn: sqlite3.Connection, user_id: int) -> Dict[str, Dict[str, Any]]:
    rows = conn.execute(
        '''SELECT i.item_code, d.name, d.equip_slot, d.effect_stat, d.effect_value, d.icon, d.rarity
           FROM inventory i JOIN item_defs d ON i.item_code=d.item_code
           WHERE i.user_id=? AND i.equipped=1''',
        (user_id,),
    ).fetchall()
    return {row['equip_slot']: dict(row) for row in rows}


def count_inventory_slots(conn: sqlite3.Connection, user_id: int) -> int:
    return int(conn.execute('SELECT COUNT(*) FROM inventory WHERE user_id=? AND quantity>0', (user_id,)).fetchone()[0])


def current_inventory_weight(conn: sqlite3.Connection, user_id: int) -> float:
    row = conn.execute(
        '''SELECT COALESCE(SUM(i.quantity*d.weight),0) FROM inventory i
           JOIN item_defs d ON i.item_code=d.item_code WHERE i.user_id=?''',
        (user_id,),
    ).fetchone()
    return float(row[0] or 0)


def add_item(conn: sqlite3.Connection, user_id: int, item_code: str, qty: int = 1):
    if qty <= 0:
        return
    item = get_item_def(conn, item_code)
    user = conn.execute('SELECT inventory_slots, weight_limit FROM users WHERE id=?', (user_id,)).fetchone()
    if not user:
        raise ValueError('User not found')
    row = conn.execute('SELECT quantity FROM inventory WHERE user_id=? AND item_code=? AND equipped=0', (user_id, item_code)).fetchone()
    if row is None and count_inventory_slots(conn, user_id) >= int(user['inventory_slots']):
        raise ValueError('Недостаточно слотов в инвентаре')
    if current_inventory_weight(conn, user_id) + item['weight'] * qty > float(user['weight_limit']):
        raise ValueError('Превышен лимит веса')
    if row:
        conn.execute('UPDATE inventory SET quantity=quantity+? WHERE user_id=? AND item_code=? AND equipped=0', (qty, user_id, item_code))
    else:
        conn.execute('INSERT INTO inventory (user_id, item_code, quantity, equipped) VALUES (?, ?, ?, 0)', (user_id, item_code, qty))


def remove_item(conn: sqlite3.Connection, user_id: int, item_code: str, qty: int = 1):
    row = conn.execute('SELECT id, quantity FROM inventory WHERE user_id=? AND item_code=? AND equipped=0', (user_id, item_code)).fetchone()
    if not row or row['quantity'] < qty:
        raise ValueError('Недостаточно предметов')
    left = int(row['quantity']) - qty
    if left <= 0:
        conn.execute('DELETE FROM inventory WHERE id=?', (row['id'],))
    else:
        conn.execute('UPDATE inventory SET quantity=? WHERE id=?', (left, row['id']))


def remove_any_item_for_admin(conn: sqlite3.Connection, user_id: int, item_code: str, qty: int = 1):
    remove_item(conn, user_id, item_code, qty)


def recalc_stats(conn: sqlite3.Connection, user_id: int):
    user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    if not user:
        raise ValueError('User not found')
    char = CHARACTERS.get(user['character_key'])
    if not char:
        return
    base = dict(char['stats'])
    level = int(user['level'])
    if level <= 50:
        growth = 1 + (level - 1) * 0.24
    else:
        linear50 = 1 + 49 * 0.24
        t = (level - 50) / 50
        growth = linear50 + (43.65 - linear50) * (t ** 1.7)
    scaled = {
        'max_hp': int(base['hp'] * growth),
        'max_energy': int(base['energy'] * (1 + (growth - 1) * 0.85)),
        'attack': int(base['attack'] * (1 + (growth - 1) * 0.92)),
        'defense': int(base['defense'] * (1 + (growth - 1) * 0.95)),
        'speed': int(base['speed'] * (1 + (growth - 1) * 0.78)),
    }
    for eq in conn.execute(
        '''SELECT d.effect_stat, d.effect_value FROM inventory i
           JOIN item_defs d ON i.item_code=d.item_code
           WHERE i.user_id=? AND i.equipped=1''',
        (user_id,),
    ).fetchall():
        stat, val = eq['effect_stat'], int(eq['effect_value'])
        if stat == 'hp':
            scaled['max_hp'] += val
        elif stat == 'energy':
            scaled['max_energy'] += val
        elif stat in ('attack', 'defense', 'speed'):
            scaled[stat] += val
    hp = min(int(user['hp']), scaled['max_hp']) if int(user['hp']) else scaled['max_hp']
    energy = min(int(user['energy']), scaled['max_energy']) if int(user['energy']) else scaled['max_energy']
    conn.execute(
        '''UPDATE users SET max_hp=?, max_energy=?, attack=?, defense=?, speed=?, hp=?, energy=?, updated_at=? WHERE id=?''',
        (scaled['max_hp'], scaled['max_energy'], scaled['attack'], scaled['defense'], scaled['speed'], hp, energy, now_str(), user_id),
    )


def get_item_definitions() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        return [dict(r) for r in conn.execute('SELECT * FROM item_defs ORDER BY category, rarity, name').fetchall()]


def get_recipes() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = [dict(r) for r in conn.execute('SELECT * FROM recipes ORDER BY recipe_code').fetchall()]
        for row in rows:
            row['ingredients'] = json.loads(row['ingredients_json'])
        return rows


# ---------- Shop & Market ----------

def refresh_shop(conn: Optional[sqlite3.Connection] = None):
    import random

    owns = conn is None
    if owns:
        ctx = get_conn()
        conn = ctx.__enter__()
    try:
        items = [dict(r) for r in conn.execute("SELECT * FROM item_defs WHERE category != 'currency' ORDER BY item_code").fetchall()]
        conn.execute('DELETE FROM shop_offers')
        weights = [{'trash': 30, 'common': 35, 'rare': 18, 'epic': 10, 'legendary': 5, 'mythic': 2}.get(item['rarity'], 10) for item in items]
        picks = random.choices(items, weights=weights, k=18)
        ts = now_str()
        for idx, item in enumerate(picks, start=1):
            qty = 1 if item['category'] == 'equipment' else random.randint(1, 4)
            price = max(1, int(item['price'] * random.uniform(0.9, 1.35)))
            conn.execute(
                'INSERT INTO shop_offers (slot_index, item_code, quantity, price, generated_at) VALUES (?, ?, ?, ?, ?)',
                (idx, item['item_code'], qty, price, ts),
            )
    finally:
        if owns:
            ctx.__exit__(None, None, None)


def refresh_shop_if_needed(conn: sqlite3.Connection):
    row = conn.execute('SELECT MAX(generated_at) AS generated_at FROM shop_offers').fetchone()
    if not row or not row['generated_at']:
        refresh_shop(conn)
        return
    from .config import SHOP_REFRESH_HOURS
    if datetime.fromisoformat(row['generated_at']) + timedelta(hours=SHOP_REFRESH_HOURS) <= utcnow():
        refresh_shop(conn)


def get_shop_offers() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        refresh_shop_if_needed(conn)
        rows = conn.execute(
            '''SELECT s.id, s.slot_index, s.item_code, s.quantity, s.price, s.generated_at,
                      d.name, d.rarity, d.category, d.icon, d.description
               FROM shop_offers s JOIN item_defs d ON s.item_code=d.item_code
               ORDER BY s.slot_index'''
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Activity / Rewards ----------

def start_of_day() -> datetime:
    now = utcnow()
    return datetime(now.year, now.month, now.day)


def record_activity(conn: sqlite3.Connection, user_id: int, kind: str, payload: Dict[str, Any]):
    conn.execute(
        'INSERT INTO activity_logs (user_id, kind, payload, created_at) VALUES (?, ?, ?, ?)',
        (user_id, kind, json.dumps(payload, ensure_ascii=False), now_str()),
    )


def get_recent_activity(user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT kind, payload, created_at FROM activity_logs WHERE user_id=? ORDER BY id DESC LIMIT ?',
            (user_id, limit),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item['payload'] = json.loads(item['payload'])
            out.append(item)
        return out


def get_activity_counters(conn: sqlite3.Connection, user_id: int, since: datetime) -> Dict[str, int]:
    rows = conn.execute(
        'SELECT kind, COUNT(*) AS cnt FROM activity_logs WHERE user_id=? AND created_at>=? GROUP BY kind',
        (user_id, since.isoformat()),
    ).fetchall()
    return {row['kind']: int(row['cnt']) for row in rows}


def get_claim(user_id: int, claim_key: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute('SELECT payload, created_at FROM reward_claims WHERE user_id=? AND claim_key=?', (user_id, claim_key)).fetchone()
        if not row:
            return None
        return {'payload': json.loads(row['payload']), 'created_at': row['created_at']}


def set_claim(conn: sqlite3.Connection, user_id: int, claim_key: str, payload: Dict[str, Any]):
    conn.execute(
        'INSERT OR REPLACE INTO reward_claims (user_id, claim_key, payload, created_at) VALUES (?, ?, ?, ?)',
        (user_id, claim_key, json.dumps(payload, ensure_ascii=False), now_str()),
    )


def list_claims_with_prefix(conn: sqlite3.Connection, user_id: int, prefix: str) -> List[str]:
    rows = conn.execute('SELECT claim_key FROM reward_claims WHERE user_id=? AND claim_key LIKE ?', (user_id, f'{prefix}%')).fetchall()
    return [row['claim_key'] for row in rows]


# ---------- Admin ----------

def log_admin(actor_user_id: int, action: str, details: Dict[str, Any]):
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO admin_logs (actor_user_id, action, details, created_at) VALUES (?, ?, ?, ?)',
            (actor_user_id, action, json.dumps(details, ensure_ascii=False), now_str()),
        )


def get_admin_logs(limit: int = 100) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            '''SELECT a.id, a.actor_user_id, a.action, a.details, a.created_at, u.display_name AS actor_name
               FROM admin_logs a LEFT JOIN users u ON a.actor_user_id=u.id
               ORDER BY a.id DESC LIMIT ?''',
            (limit,),
        ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item['details'] = json.loads(item['details'])
            out.append(item)
        return out


def delete_custom_item_definition(item_code: str):
    with get_conn() as conn:
        row = conn.execute('SELECT is_custom FROM item_defs WHERE item_code=?', (item_code,)).fetchone()
        if not row:
            raise ValueError('Предмет не найден')
        if not int(row['is_custom']):
            raise ValueError('Можно удалять только предметы, созданные через админку')
        conn.execute('DELETE FROM market_listings WHERE item_code=?', (item_code,))
        conn.execute('DELETE FROM item_defs WHERE item_code=?', (item_code,))


# ---------- Social / Linking ----------

def generate_link_code(user_id: int) -> str:
    code = secrets.token_hex(4).upper()
    with get_conn() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO link_codes (code, user_id, expires_at, used) VALUES (?, ?, ?, 0)',
            (code, user_id, (utcnow() + timedelta(minutes=LINK_CODE_TTL_MINUTES)).isoformat()),
        )
    return code


def consume_link_code(code: str) -> Optional[int]:
    with get_conn() as conn:
        row = conn.execute('SELECT * FROM link_codes WHERE code=?', (code.upper(),)).fetchone()
        if not row:
            return None
        if int(row['used']) or datetime.fromisoformat(row['expires_at']) < utcnow():
            return None
        conn.execute('UPDATE link_codes SET used=1 WHERE code=?', (code.upper(),))
        return int(row['user_id'])
