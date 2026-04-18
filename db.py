from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

UTC = timezone.utc


@dataclass(frozen=True)
class BotInstance:
    id: int
    kind: str
    token: str
    telegram_bot_id: int
    username: str | None
    title: str
    owner_user_id: int | None
    parent_bot_id: int | None
    sponsor_user_id: int | None
    status: str
    user_free_trial: int
    owner_daily_free: int
    created_at: str


@dataclass(frozen=True)
class UserBalance:
    bot_id: int
    user_id: int
    username: str | None
    first_name: str | None
    is_banned_global: int
    ban_reason: str | None
    is_platform_vip: int
    vip_note: str | None
    global_bonus_credits: int
    free_trial_left: int
    paid_credits: int
    premium_until: str | None
    owner_daily_left: int
    last_daily_reset: str | None
    is_bot_owner: int
    owner_daily_limit: int

    @property
    def premium_active(self) -> bool:
        if not self.premium_until:
            return False
        try:
            return datetime.fromisoformat(self.premium_until) > datetime.now(UTC)
        except ValueError:
            return False

    @property
    def unlimited_access(self) -> bool:
        return bool(self.is_platform_vip) or self.premium_active

    @property
    def total_renders_left(self) -> int | str:
        if self.unlimited_access:
            return '∞'
        return max(0, self.owner_daily_left) + max(0, self.paid_credits) + max(0, self.global_bonus_credits) + max(0, self.free_trial_left)


class Database:
    def __init__(self, db_path: Path, free_trial_credits: int, child_owner_daily_free: int) -> None:
        self.db_path = db_path
        self.free_trial_credits = int(free_trial_credits)
        self.child_owner_daily_free = int(child_owner_daily_free)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                '''
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    is_banned_global INTEGER NOT NULL DEFAULT 0,
                    ban_reason TEXT,
                    is_platform_vip INTEGER NOT NULL DEFAULT 0,
                    vip_note TEXT,
                    global_bonus_credits INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_seen_at TEXT
                );

                CREATE TABLE IF NOT EXISTS bot_instances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    token TEXT NOT NULL UNIQUE,
                    telegram_bot_id INTEGER NOT NULL UNIQUE,
                    username TEXT,
                    title TEXT NOT NULL,
                    owner_user_id INTEGER,
                    parent_bot_id INTEGER,
                    sponsor_user_id INTEGER,
                    status TEXT NOT NULL DEFAULT 'active',
                    user_free_trial INTEGER NOT NULL DEFAULT 5,
                    owner_daily_free INTEGER NOT NULL DEFAULT 10,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    launched_at TEXT,
                    FOREIGN KEY(owner_user_id) REFERENCES users(user_id),
                    FOREIGN KEY(parent_bot_id) REFERENCES bot_instances(id),
                    FOREIGN KEY(sponsor_user_id) REFERENCES users(user_id)
                );

                CREATE TABLE IF NOT EXISTS bot_users (
                    bot_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    free_trial_left INTEGER NOT NULL DEFAULT 5,
                    paid_credits INTEGER NOT NULL DEFAULT 0,
                    premium_until TEXT,
                    owner_daily_left INTEGER NOT NULL DEFAULT 0,
                    last_daily_reset TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_seen_at TEXT,
                    PRIMARY KEY (bot_id, user_id),
                    FOREIGN KEY(bot_id) REFERENCES bot_instances(id) ON DELETE CASCADE,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    job_type TEXT NOT NULL,
                    source_path TEXT,
                    result_path TEXT,
                    preset_key TEXT,
                    prompt TEXT,
                    status TEXT NOT NULL,
                    error_text TEXT,
                    created_at TEXT NOT NULL,
                    finished_at TEXT,
                    FOREIGN KEY(bot_id) REFERENCES bot_instances(id) ON DELETE CASCADE,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS usage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id INTEGER,
                    user_id INTEGER,
                    event_type TEXT NOT NULL,
                    subject TEXT,
                    details TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(bot_id) REFERENCES bot_instances(id) ON DELETE CASCADE,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS suspicious_flags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    details TEXT,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL,
                    reviewed_at TEXT,
                    FOREIGN KEY(bot_id) REFERENCES bot_instances(id) ON DELETE CASCADE,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    buyer_user_id INTEGER NOT NULL,
                    seller_bot_id INTEGER NOT NULL,
                    invoice_payload TEXT NOT NULL UNIQUE,
                    product_key TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    telegram_payment_charge_id TEXT,
                    provider_payment_charge_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(buyer_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY(seller_bot_id) REFERENCES bot_instances(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS commission_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payment_id INTEGER NOT NULL,
                    beneficiary_user_id INTEGER NOT NULL,
                    source_bot_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    level INTEGER NOT NULL,
                    note TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(payment_id) REFERENCES payments(id) ON DELETE CASCADE,
                    FOREIGN KEY(beneficiary_user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY(source_bot_id) REFERENCES bot_instances(id) ON DELETE CASCADE
                );
                '''
            )
            columns = {row['name'] for row in conn.execute("PRAGMA table_info(bot_instances)").fetchall()}
            if 'sponsor_user_id' not in columns:
                conn.execute('ALTER TABLE bot_instances ADD COLUMN sponsor_user_id INTEGER')

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def upsert_user(self, user_id: int, username: str | None, first_name: str | None) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO users (user_id, username, first_name, created_at, updated_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    updated_at=excluded.updated_at,
                    last_seen_at=excluded.last_seen_at
                ''',
                (user_id, username, first_name, now, now, now),
            )

    def touch_user(self, user_id: int) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute('UPDATE users SET last_seen_at = ?, updated_at = ? WHERE user_id = ?', (now, now, user_id))

    def ensure_root_bot(self, token: str, telegram_bot_id: int, username: str | None, title: str) -> int:
        now = self._now()
        with self._connect() as conn:
            row = conn.execute('SELECT id FROM bot_instances WHERE kind = ? ORDER BY id LIMIT 1', ('root',)).fetchone()
            if row:
                bot_id = int(row['id'])
                conn.execute(
                    '''
                    UPDATE bot_instances
                    SET token = ?, telegram_bot_id = ?, username = ?, title = ?, status = 'active', updated_at = ?, launched_at = ?
                    WHERE id = ?
                    ''',
                    (token, telegram_bot_id, username, title, now, now, bot_id),
                )
                return bot_id
            cur = conn.execute(
                '''
                INSERT INTO bot_instances (
                    kind, token, telegram_bot_id, username, title, owner_user_id, parent_bot_id,
                    status, user_free_trial, owner_daily_free, created_at, updated_at, launched_at
                ) VALUES ('root', ?, ?, ?, ?, NULL, NULL, 'active', ?, ?, ?, ?, ?)
                ''',
                (token, telegram_bot_id, username, title, self.free_trial_credits, self.child_owner_daily_free, now, now, now),
            )
            return int(cur.lastrowid)

    def list_active_bots(self) -> list[BotInstance]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT id, kind, token, telegram_bot_id, username, title, owner_user_id,
                       parent_bot_id, sponsor_user_id, status, user_free_trial, owner_daily_free, created_at
                FROM bot_instances
                WHERE status = 'active'
                ORDER BY CASE WHEN kind = 'root' THEN 0 ELSE 1 END, id ASC
                '''
            ).fetchall()
        return [BotInstance(**dict(row)) for row in rows]

    def get_bot(self, bot_id: int) -> Optional[BotInstance]:
        with self._connect() as conn:
            row = conn.execute(
                '''
                SELECT id, kind, token, telegram_bot_id, username, title, owner_user_id,
                       parent_bot_id, sponsor_user_id, status, user_free_trial, owner_daily_free, created_at
                FROM bot_instances
                WHERE id = ?
                ''',
                (bot_id,),
            ).fetchone()
        return BotInstance(**dict(row)) if row else None

    def create_child_bot(
        self,
        token: str,
        telegram_bot_id: int,
        username: str | None,
        title: str,
        owner_user_id: int,
        parent_bot_id: int | None,
        sponsor_user_id: int | None,
    ) -> int:
        now = self._now()
        with self._connect() as conn:
            existing = conn.execute('SELECT id FROM bot_instances WHERE telegram_bot_id = ?', (telegram_bot_id,)).fetchone()
            if existing:
                raise ValueError('Этот бот уже подключён к платформе.')
            cur = conn.execute(
                '''
                INSERT INTO bot_instances (
                    kind, token, telegram_bot_id, username, title, owner_user_id, parent_bot_id, sponsor_user_id,
                    status, user_free_trial, owner_daily_free, created_at, updated_at, launched_at
                ) VALUES ('child', ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
                ''',
                (token, telegram_bot_id, username, title, owner_user_id, parent_bot_id, sponsor_user_id, self.free_trial_credits, self.child_owner_daily_free, now, now, now),
            )
            bot_id = int(cur.lastrowid)
            conn.execute(
                'INSERT INTO usage_events (bot_id, user_id, event_type, subject, details, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (bot_id, owner_user_id, 'child_bot', 'created', f'parent={parent_bot_id}; sponsor={sponsor_user_id}', 'done', now),
            )
            self._ensure_bot_user_state_conn(conn, bot_id, owner_user_id)
            return bot_id

    def update_bot_profile(self, bot_id: int, username: str | None, title: str) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                'UPDATE bot_instances SET username = ?, title = ?, updated_at = ?, launched_at = ? WHERE id = ?',
                (username, title, now, now, bot_id),
            )

    def deactivate_bot(self, bot_id: int) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute('UPDATE bot_instances SET status = ?, updated_at = ? WHERE id = ?', ('paused', now, bot_id))

    def _ensure_bot_user_state_conn(self, conn: sqlite3.Connection, bot_id: int, user_id: int) -> None:
        row = conn.execute('SELECT user_free_trial, owner_daily_free, owner_user_id FROM bot_instances WHERE id = ?', (bot_id,)).fetchone()
        if not row:
            raise ValueError('Bot instance not found')
        user_free_trial = int(row['user_free_trial'])
        owner_daily_free = int(row['owner_daily_free'])
        owner_user_id = int(row['owner_user_id']) if row['owner_user_id'] is not None else None
        owner_daily_left = owner_daily_free if owner_user_id == user_id else 0
        now = self._now()
        conn.execute(
            '''
            INSERT OR IGNORE INTO bot_users (
                bot_id, user_id, free_trial_left, paid_credits, premium_until,
                owner_daily_left, last_daily_reset, created_at, updated_at, last_seen_at
            ) VALUES (?, ?, ?, 0, NULL, ?, ?, ?, ?, ?)
            ''',
            (bot_id, user_id, user_free_trial, owner_daily_left, now[:10], now, now, now),
        )

    def ensure_bot_user_state(self, bot_id: int, user_id: int) -> None:
        with self._connect() as conn:
            self._ensure_bot_user_state_conn(conn, bot_id, user_id)

    def touch_bot_user(self, bot_id: int, user_id: int) -> None:
        self.ensure_bot_user_state(bot_id, user_id)
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                'UPDATE bot_users SET last_seen_at = ?, updated_at = ? WHERE bot_id = ? AND user_id = ?',
                (now, now, bot_id, user_id),
            )

    def _refresh_owner_daily_conn(self, conn: sqlite3.Connection, bot_id: int, user_id: int) -> None:
        row = conn.execute(
            '''
            SELECT bu.owner_daily_left, bu.last_daily_reset, bi.owner_daily_free, bi.owner_user_id
            FROM bot_users bu
            JOIN bot_instances bi ON bi.id = bu.bot_id
            WHERE bu.bot_id = ? AND bu.user_id = ?
            ''',
            (bot_id, user_id),
        ).fetchone()
        if not row:
            return
        owner_user_id = row['owner_user_id']
        if owner_user_id is None or int(owner_user_id) != user_id:
            return
        today = datetime.now(UTC).date().isoformat()
        if (row['last_daily_reset'] or '') == today:
            return
        conn.execute(
            'UPDATE bot_users SET owner_daily_left = ?, last_daily_reset = ?, updated_at = ? WHERE bot_id = ? AND user_id = ?',
            (int(row['owner_daily_free']), today, self._now(), bot_id, user_id),
        )

    def get_user_balance(self, bot_id: int, user_id: int) -> Optional[UserBalance]:
        with self._connect() as conn:
            self._ensure_bot_user_state_conn(conn, bot_id, user_id)
            self._refresh_owner_daily_conn(conn, bot_id, user_id)
            row = conn.execute(
                '''
                SELECT
                    bu.bot_id,
                    u.user_id,
                    u.username,
                    u.first_name,
                    u.is_banned_global,
                    u.ban_reason,
                    u.is_platform_vip,
                    u.vip_note,
                    u.global_bonus_credits,
                    bu.free_trial_left,
                    bu.paid_credits,
                    bu.premium_until,
                    bu.owner_daily_left,
                    bu.last_daily_reset,
                    CASE WHEN bi.owner_user_id = u.user_id THEN 1 ELSE 0 END AS is_bot_owner,
                    bi.owner_daily_free AS owner_daily_limit
                FROM users u
                JOIN bot_users bu ON bu.user_id = u.user_id AND bu.bot_id = ?
                JOIN bot_instances bi ON bi.id = bu.bot_id
                WHERE u.user_id = ?
                ''',
                (bot_id, user_id),
            ).fetchone()
        return UserBalance(**dict(row)) if row else None

    def is_banned_global(self, user_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute('SELECT is_banned_global FROM users WHERE user_id = ?', (user_id,)).fetchone()
        return bool(row and int(row['is_banned_global']))

    def ban_global_user(self, user_id: int, reason: str | None = None) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                'UPDATE users SET is_banned_global = 1, ban_reason = ?, updated_at = ? WHERE user_id = ?',
                (reason or 'Заблокирован платформой', now, user_id),
            )
            conn.execute(
                'INSERT INTO usage_events (user_id, event_type, subject, details, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, 'admin', 'global_ban', reason or 'manual', 'done', now),
            )

    def unban_global_user(self, user_id: int) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                'UPDATE users SET is_banned_global = 0, ban_reason = NULL, updated_at = ? WHERE user_id = ?',
                (now, user_id),
            )
            conn.execute(
                'INSERT INTO usage_events (user_id, event_type, subject, details, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, 'admin', 'global_unban', None, 'done', now),
            )

    def set_platform_vip(self, user_id: int, enabled: bool, note: str | None = None) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                'UPDATE users SET is_platform_vip = ?, vip_note = ?, updated_at = ? WHERE user_id = ?',
                (1 if enabled else 0, note, now, user_id),
            )
            conn.execute(
                'INSERT INTO usage_events (user_id, event_type, subject, details, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, 'admin', 'platform_vip_on' if enabled else 'platform_vip_off', note, 'done', now),
            )

    def adjust_global_bonus_credits(self, user_id: int, delta: int, details: str | None = None) -> int:
        now = self._now()
        with self._connect() as conn:
            row = conn.execute('SELECT global_bonus_credits FROM users WHERE user_id = ?', (user_id,)).fetchone()
            current = int(row['global_bonus_credits']) if row else 0
            new_value = max(0, current + int(delta))
            conn.execute('UPDATE users SET global_bonus_credits = ?, updated_at = ? WHERE user_id = ?', (new_value, now, user_id))
            conn.execute(
                'INSERT INTO usage_events (user_id, event_type, subject, details, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, 'admin', 'grant_global_credits' if delta >= 0 else 'remove_global_credits', details or str(delta), 'done', now),
            )
            return new_value

    def consume_request(self, bot_id: int, user_id: int, is_admin: bool = False) -> tuple[bool, str]:
        if is_admin:
            return True, 'admin'
        with self._connect() as conn:
            self._ensure_bot_user_state_conn(conn, bot_id, user_id)
            self._refresh_owner_daily_conn(conn, bot_id, user_id)
            row = conn.execute(
                '''
                SELECT
                    u.is_banned_global,
                    u.is_platform_vip,
                    u.global_bonus_credits,
                    bu.free_trial_left,
                    bu.paid_credits,
                    bu.premium_until,
                    bu.owner_daily_left,
                    CASE WHEN bi.owner_user_id = u.user_id THEN 1 ELSE 0 END AS is_bot_owner
                FROM users u
                JOIN bot_users bu ON bu.user_id = u.user_id AND bu.bot_id = ?
                JOIN bot_instances bi ON bi.id = bu.bot_id
                WHERE u.user_id = ?
                ''',
                (bot_id, user_id),
            ).fetchone()
            if not row:
                return False, 'missing'
            if int(row['is_banned_global']):
                return False, 'banned'
            if int(row['is_platform_vip']):
                return True, 'platform_vip'
            premium_until = row['premium_until']
            if premium_until:
                try:
                    if datetime.fromisoformat(premium_until) > datetime.now(UTC):
                        return True, 'premium'
                except ValueError:
                    pass
            if int(row['is_bot_owner']) and int(row['owner_daily_left']) > 0:
                conn.execute(
                    'UPDATE bot_users SET owner_daily_left = owner_daily_left - 1, updated_at = ? WHERE bot_id = ? AND user_id = ?',
                    (self._now(), bot_id, user_id),
                )
                return True, 'owner_daily'
            if int(row['paid_credits']) > 0:
                conn.execute(
                    'UPDATE bot_users SET paid_credits = paid_credits - 1, updated_at = ? WHERE bot_id = ? AND user_id = ?',
                    (self._now(), bot_id, user_id),
                )
                return True, 'credit'
            if int(row['global_bonus_credits']) > 0:
                conn.execute(
                    'UPDATE users SET global_bonus_credits = global_bonus_credits - 1, updated_at = ? WHERE user_id = ?',
                    (self._now(), user_id),
                )
                return True, 'global_bonus'
            if int(row['free_trial_left']) > 0:
                conn.execute(
                    'UPDATE bot_users SET free_trial_left = free_trial_left - 1, updated_at = ? WHERE bot_id = ? AND user_id = ?',
                    (self._now(), bot_id, user_id),
                )
                return True, 'trial'
            return False, 'empty'

    def restore_request(self, bot_id: int, user_id: int, reason: str) -> None:
        if reason in {'admin', 'platform_vip', 'premium'}:
            return
        now = self._now()
        with self._connect() as conn:
            if reason == 'owner_daily':
                conn.execute('UPDATE bot_users SET owner_daily_left = owner_daily_left + 1, updated_at = ? WHERE bot_id = ? AND user_id = ?', (now, bot_id, user_id))
            elif reason == 'credit':
                conn.execute('UPDATE bot_users SET paid_credits = paid_credits + 1, updated_at = ? WHERE bot_id = ? AND user_id = ?', (now, bot_id, user_id))
            elif reason == 'global_bonus':
                conn.execute('UPDATE users SET global_bonus_credits = global_bonus_credits + 1, updated_at = ? WHERE user_id = ?', (now, user_id))
            elif reason == 'trial':
                conn.execute('UPDATE bot_users SET free_trial_left = free_trial_left + 1, updated_at = ? WHERE bot_id = ? AND user_id = ?', (now, bot_id, user_id))

    def add_bot_paid_credits(self, bot_id: int, user_id: int, amount: int) -> None:
        with self._connect() as conn:
            self._ensure_bot_user_state_conn(conn, bot_id, user_id)
            conn.execute(
                'UPDATE bot_users SET paid_credits = paid_credits + ?, updated_at = ? WHERE bot_id = ? AND user_id = ?',
                (amount, self._now(), bot_id, user_id),
            )

    def add_bot_premium_days(self, bot_id: int, user_id: int, days: int) -> None:
        with self._connect() as conn:
            self._ensure_bot_user_state_conn(conn, bot_id, user_id)
            row = conn.execute('SELECT premium_until FROM bot_users WHERE bot_id = ? AND user_id = ?', (bot_id, user_id)).fetchone()
            start = datetime.now(UTC)
            if row and row['premium_until']:
                try:
                    current = datetime.fromisoformat(row['premium_until'])
                    if current > start:
                        start = current
                except ValueError:
                    pass
            premium_until = (start + timedelta(days=days)).isoformat()
            conn.execute(
                'UPDATE bot_users SET premium_until = ?, updated_at = ? WHERE bot_id = ? AND user_id = ?',
                (premium_until, self._now(), bot_id, user_id),
            )

    def save_payment(
        self,
        buyer_user_id: int,
        seller_bot_id: int,
        invoice_payload: str,
        product_key: str,
        amount: int,
        currency: str,
        telegram_payment_charge_id: str | None,
        provider_payment_charge_id: str | None,
    ) -> int:
        now = self._now()
        with self._connect() as conn:
            cur = conn.execute(
                '''
                INSERT OR IGNORE INTO payments (
                    buyer_user_id, seller_bot_id, invoice_payload, product_key, amount, currency,
                    telegram_payment_charge_id, provider_payment_charge_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (buyer_user_id, seller_bot_id, invoice_payload, product_key, amount, currency, telegram_payment_charge_id, provider_payment_charge_id, now),
            )
            if cur.lastrowid:
                payment_id = int(cur.lastrowid)
            else:
                row = conn.execute('SELECT id FROM payments WHERE invoice_payload = ?', (invoice_payload,)).fetchone()
                payment_id = int(row['id'])
            conn.execute(
                'INSERT INTO usage_events (bot_id, user_id, event_type, subject, details, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (seller_bot_id, buyer_user_id, 'payment', product_key, str(amount), 'done', now),
            )
            return payment_id

    def record_commission(self, payment_id: int, beneficiary_user_id: int, source_bot_id: int, amount: int, level: int, note: str) -> None:
        if amount <= 0:
            return
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO commission_events (payment_id, beneficiary_user_id, source_bot_id, amount, level, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (payment_id, beneficiary_user_id, source_bot_id, amount, level, note, now),
            )

    def get_bot_owner_chain(self, bot_id: int, max_depth: int = 3) -> list[sqlite3.Row]:
        chain: list[sqlite3.Row] = []
        current_bot_id = bot_id
        depth = 0
        with self._connect() as conn:
            while current_bot_id and depth < max_depth:
                row = conn.execute(
                    '''
                    SELECT bi.id, bi.owner_user_id, bi.parent_bot_id, bi.sponsor_user_id, bi.title, bi.username,
                           u.username AS owner_username, u.first_name AS owner_first_name
                    FROM bot_instances bi
                    LEFT JOIN users u ON u.user_id = bi.owner_user_id
                    WHERE bi.id = ?
                    ''',
                    (current_bot_id,),
                ).fetchone()
                if not row:
                    break
                chain.append(row)
                current_bot_id = int(row['parent_bot_id']) if row['parent_bot_id'] is not None else 0
                depth += 1
        return chain

    def get_bot_sponsor_user_id(self, bot_id: int) -> int | None:
        with self._connect() as conn:
            row = conn.execute('SELECT sponsor_user_id FROM bot_instances WHERE id = ?', (bot_id,)).fetchone()
        if not row or row['sponsor_user_id'] is None:
            return None
        return int(row['sponsor_user_id'])

    def save_job(
        self,
        bot_id: int,
        user_id: int,
        job_type: str,
        source_path: str | None,
        result_path: str | None,
        preset_key: str | None,
        prompt: str | None,
        status: str,
        error_text: str | None = None,
    ) -> None:
        now = self._now()
        subject = prompt or preset_key or job_type
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO jobs (
                    bot_id, user_id, job_type, source_path, result_path, preset_key, prompt,
                    status, error_text, created_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    bot_id,
                    user_id,
                    job_type,
                    source_path,
                    result_path,
                    preset_key,
                    prompt,
                    status,
                    error_text,
                    now,
                    now if status in {'done', 'failed', 'denied'} else None,
                ),
            )
            conn.execute(
                'INSERT INTO usage_events (bot_id, user_id, event_type, subject, details, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (bot_id, user_id, job_type, subject, error_text, status, now),
            )

    def get_recent_event_count(
        self,
        bot_id: int,
        user_id: int,
        event_types: tuple[str, ...] | list[str] | None = None,
        minutes: int = 10,
        status: str | None = None,
    ) -> int:
        since = (datetime.now(UTC) - timedelta(minutes=minutes)).isoformat()
        query = 'SELECT COUNT(*) AS cnt FROM usage_events WHERE bot_id = ? AND user_id = ? AND created_at >= ?'
        params: list[Any] = [bot_id, user_id, since]
        if event_types:
            placeholders = ','.join('?' for _ in event_types)
            query += f' AND event_type IN ({placeholders})'
            params.extend(list(event_types))
        if status:
            query += ' AND status = ?'
            params.append(status)
        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
        return int(row['cnt']) if row else 0

    def create_suspicious_flag(self, bot_id: int, user_id: int, reason: str, details: str | None = None) -> int | None:
        since = (datetime.now(UTC) - timedelta(hours=12)).isoformat()
        now = self._now()
        with self._connect() as conn:
            existing = conn.execute(
                '''
                SELECT id FROM suspicious_flags
                WHERE bot_id = ? AND user_id = ? AND reason = ? AND status = 'open' AND created_at >= ?
                ORDER BY id DESC LIMIT 1
                ''',
                (bot_id, user_id, reason, since),
            ).fetchone()
            if existing:
                return None
            cur = conn.execute(
                'INSERT INTO suspicious_flags (bot_id, user_id, reason, details, status, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (bot_id, user_id, reason, details, 'open', now),
            )
            return int(cur.lastrowid)

    def mark_flag_reviewed(self, flag_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE suspicious_flags SET status = 'reviewed', reviewed_at = ? WHERE id = ?",
                (self._now(), flag_id),
            )

    def list_suspicious_flags(self, page: int = 0, page_size: int = 6) -> tuple[list[sqlite3.Row], int]:
        offset = max(0, page) * page_size
        with self._connect() as conn:
            total_row = conn.execute("SELECT COUNT(*) AS cnt FROM suspicious_flags WHERE status = 'open'").fetchone()
            rows = conn.execute(
                '''
                SELECT f.id, f.bot_id, f.user_id, f.reason, f.details, f.status, f.created_at,
                       u.username, u.first_name, u.is_banned_global, u.is_platform_vip,
                       bi.title AS bot_title, bi.username AS bot_username
                FROM suspicious_flags f
                LEFT JOIN users u ON u.user_id = f.user_id
                LEFT JOIN bot_instances bi ON bi.id = f.bot_id
                WHERE f.status = 'open'
                ORDER BY f.created_at DESC
                LIMIT ? OFFSET ?
                ''',
                (page_size, offset),
            ).fetchall()
        return list(rows), int(total_row['cnt']) if total_row else 0

    def dashboard_stats(self) -> sqlite3.Row:
        since_24h = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                '''
                SELECT
                    (SELECT COUNT(*) FROM users) AS total_users,
                    (SELECT COUNT(*) FROM users WHERE is_banned_global = 1) AS banned_users,
                    (SELECT COUNT(*) FROM users WHERE is_platform_vip = 1) AS vip_users,
                    (SELECT COUNT(*) FROM bot_instances WHERE status = 'active') AS active_bots,
                    (SELECT COUNT(*) FROM bot_instances WHERE kind = 'child' AND status = 'active') AS child_bots,
                    (SELECT COUNT(*) FROM suspicious_flags WHERE status = 'open') AS open_flags,
                    (SELECT COUNT(*) FROM jobs) AS total_jobs,
                    (SELECT COUNT(*) FROM jobs WHERE created_at >= ?) AS jobs_24h,
                    (SELECT COUNT(DISTINCT user_id) FROM jobs WHERE created_at >= ?) AS active_users_24h,
                    (SELECT COUNT(DISTINCT buyer_user_id) FROM payments) AS paid_users,
                    (SELECT COALESCE(SUM(amount), 0) FROM payments) AS stars_revenue,
                    (SELECT COALESCE(SUM(amount), 0) FROM commission_events) AS commissions_total
                ''',
                (since_24h, since_24h),
            ).fetchone()
        return row

    def popular_masks(self, limit: int = 10) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT preset_key, COUNT(*) AS cnt
                FROM jobs
                WHERE status = 'done' AND job_type = 'image_preset' AND preset_key IS NOT NULL
                GROUP BY preset_key
                ORDER BY cnt DESC, preset_key ASC
                LIMIT ?
                ''',
                (limit,),
            ).fetchall()
        return list(rows)

    def popular_prompts(self, limit: int = 10) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT prompt, COUNT(*) AS cnt, job_type
                FROM jobs
                WHERE status = 'done'
                  AND job_type IN ('text', 'image_custom')
                  AND prompt IS NOT NULL
                  AND TRIM(prompt) != ''
                GROUP BY job_type, prompt
                ORDER BY cnt DESC, MAX(created_at) DESC
                LIMIT ?
                ''',
                (limit,),
            ).fetchall()
        return list(rows)

    def top_users_by_usage(self, limit: int = 10) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT u.user_id, u.username, u.first_name, COUNT(*) AS cnt,
                       u.is_platform_vip, u.is_banned_global
                FROM jobs j
                JOIN users u ON u.user_id = j.user_id
                GROUP BY u.user_id, u.username, u.first_name, u.is_platform_vip, u.is_banned_global
                ORDER BY cnt DESC, u.user_id DESC
                LIMIT ?
                ''',
                (limit,),
            ).fetchall()
        return list(rows)

    def list_users(self, page: int = 0, page_size: int = 8) -> tuple[list[sqlite3.Row], int]:
        offset = max(0, page) * page_size
        with self._connect() as conn:
            total_row = conn.execute('SELECT COUNT(*) AS cnt FROM users').fetchone()
            rows = conn.execute(
                '''
                SELECT u.user_id, u.username, u.first_name, u.is_banned_global, u.is_platform_vip, u.global_bonus_credits,
                       COALESCE((SELECT COUNT(*) FROM jobs j WHERE j.user_id = u.user_id), 0) AS jobs_count,
                       COALESCE((SELECT COUNT(*) FROM payments p WHERE p.buyer_user_id = u.user_id), 0) AS payments_count,
                       COALESCE((SELECT COUNT(*) FROM bot_users bu WHERE bu.user_id = u.user_id), 0) AS bots_count,
                       COALESCE(u.last_seen_at, u.created_at) AS last_seen_any
                FROM users u
                ORDER BY last_seen_any DESC, u.user_id DESC
                LIMIT ? OFFSET ?
                ''',
                (page_size, offset),
            ).fetchall()
        return list(rows), int(total_row['cnt']) if total_row else 0

    def get_user_detail(self, user_id: int) -> Optional[sqlite3.Row]:
        since_24h = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
        with self._connect() as conn:
            row = conn.execute(
                '''
                SELECT u.user_id, u.username, u.first_name, u.is_banned_global, u.ban_reason,
                       u.is_platform_vip, u.vip_note, u.global_bonus_credits,
                       u.created_at, u.updated_at, u.last_seen_at,
                       COALESCE((SELECT COUNT(*) FROM jobs j WHERE j.user_id = u.user_id), 0) AS total_jobs,
                       COALESCE((SELECT COUNT(*) FROM jobs j WHERE j.user_id = u.user_id AND j.created_at >= ?), 0) AS jobs_24h,
                       COALESCE((SELECT COUNT(*) FROM payments p WHERE p.buyer_user_id = u.user_id), 0) AS total_payments,
                       COALESCE((SELECT SUM(amount) FROM payments p WHERE p.buyer_user_id = u.user_id), 0) AS total_spent,
                       COALESCE((SELECT COUNT(*) FROM suspicious_flags f WHERE f.user_id = u.user_id AND f.status = 'open'), 0) AS open_flags,
                       COALESCE((SELECT COUNT(*) FROM bot_instances bi WHERE bi.owner_user_id = u.user_id AND bi.kind = 'child'), 0) AS owned_bots,
                       COALESCE((SELECT SUM(amount) FROM commission_events c WHERE c.beneficiary_user_id = u.user_id), 0) AS earned_commissions
                FROM users u
                WHERE u.user_id = ?
                ''',
                (since_24h, user_id),
            ).fetchone()
        return row

    def get_user_memberships(self, user_id: int) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT bi.id AS bot_id, bi.title AS bot_title, bi.username AS bot_username, bi.kind,
                       CASE WHEN bi.owner_user_id = ? THEN 1 ELSE 0 END AS is_owner,
                       bu.free_trial_left, bu.paid_credits, bu.premium_until, bu.owner_daily_left,
                       COALESCE((SELECT COUNT(*) FROM jobs j WHERE j.bot_id = bi.id AND j.user_id = ?), 0) AS jobs_count
                FROM bot_users bu
                JOIN bot_instances bi ON bi.id = bu.bot_id
                WHERE bu.user_id = ?
                ORDER BY jobs_count DESC, bi.id ASC
                ''',
                (user_id, user_id, user_id),
            ).fetchall()
        return list(rows)

    def list_bots(self, page: int = 0, page_size: int = 8) -> tuple[list[sqlite3.Row], int]:
        offset = max(0, page) * page_size
        with self._connect() as conn:
            total_row = conn.execute("SELECT COUNT(*) AS cnt FROM bot_instances WHERE kind = 'child'").fetchone()
            rows = conn.execute(
                '''
                SELECT bi.id, bi.kind, bi.username, bi.title, bi.owner_user_id, bi.parent_bot_id, bi.sponsor_user_id, bi.status,
                       bi.user_free_trial, bi.owner_daily_free, bi.created_at,
                       u.username AS owner_username, u.first_name AS owner_first_name,
                       p.title AS parent_title,
                       s.username AS sponsor_username, s.first_name AS sponsor_first_name,
                       COALESCE((SELECT COUNT(*) FROM bot_users bu WHERE bu.bot_id = bi.id), 0) AS members_count,
                       COALESCE((SELECT COUNT(*) FROM jobs j WHERE j.bot_id = bi.id), 0) AS jobs_count,
                       COALESCE((SELECT COUNT(*) FROM payments pay WHERE pay.seller_bot_id = bi.id), 0) AS sales_count,
                       COALESCE((SELECT SUM(amount) FROM payments pay WHERE pay.seller_bot_id = bi.id), 0) AS stars_revenue
                FROM bot_instances bi
                LEFT JOIN users u ON u.user_id = bi.owner_user_id
                LEFT JOIN bot_instances p ON p.id = bi.parent_bot_id
                LEFT JOIN users s ON s.user_id = bi.sponsor_user_id
                WHERE bi.kind = 'child'
                ORDER BY bi.created_at DESC, bi.id DESC
                LIMIT ? OFFSET ?
                ''',
                (page_size, offset),
            ).fetchall()
        return list(rows), int(total_row['cnt']) if total_row else 0

    def get_bot_detail(self, bot_id: int) -> Optional[sqlite3.Row]:
        with self._connect() as conn:
            row = conn.execute(
                '''
                SELECT bi.id, bi.kind, bi.username, bi.title, bi.owner_user_id, bi.parent_bot_id, bi.sponsor_user_id, bi.status,
                       bi.user_free_trial, bi.owner_daily_free, bi.created_at, bi.launched_at,
                       u.username AS owner_username, u.first_name AS owner_first_name,
                       p.title AS parent_title, p.username AS parent_username,
                       s.username AS sponsor_username, s.first_name AS sponsor_first_name,
                       COALESCE((SELECT COUNT(*) FROM bot_users bu WHERE bu.bot_id = bi.id), 0) AS members_count,
                       COALESCE((SELECT COUNT(*) FROM jobs j WHERE j.bot_id = bi.id), 0) AS jobs_count,
                       COALESCE((SELECT COUNT(*) FROM payments pay WHERE pay.seller_bot_id = bi.id), 0) AS sales_count,
                       COALESCE((SELECT SUM(amount) FROM payments pay WHERE pay.seller_bot_id = bi.id), 0) AS stars_revenue
                FROM bot_instances bi
                LEFT JOIN users u ON u.user_id = bi.owner_user_id
                LEFT JOIN bot_instances p ON p.id = bi.parent_bot_id
                LEFT JOIN users s ON s.user_id = bi.sponsor_user_id
                WHERE bi.id = ?
                ''',
                (bot_id,),
            ).fetchone()
        return row

    def get_bot_tree(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                WITH RECURSIVE tree(id, title, username, owner_user_id, parent_bot_id, sponsor_user_id, depth, path) AS (
                    SELECT id, title, username, owner_user_id, parent_bot_id, sponsor_user_id, 0 AS depth, printf('%06d', id) AS path
                    FROM bot_instances
                    WHERE kind = 'root'
                    UNION ALL
                    SELECT c.id, c.title, c.username, c.owner_user_id, c.parent_bot_id, c.sponsor_user_id, t.depth + 1,
                           t.path || '/' || printf('%06d', c.id)
                    FROM bot_instances c
                    JOIN tree t ON c.parent_bot_id = t.id
                )
                SELECT tree.*, u.username AS owner_username, u.first_name AS owner_first_name,
                       s.username AS sponsor_username, s.first_name AS sponsor_first_name
                FROM tree
                LEFT JOIN users u ON u.user_id = tree.owner_user_id
                LEFT JOIN users s ON s.user_id = tree.sponsor_user_id
                ORDER BY path
                '''
            ).fetchall()
        return list(rows)

    def commission_summary(self, limit: int = 20) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                '''
                SELECT c.beneficiary_user_id, u.username, u.first_name, SUM(c.amount) AS total_amount,
                       COUNT(*) AS cnt
                FROM commission_events c
                JOIN users u ON u.user_id = c.beneficiary_user_id
                GROUP BY c.beneficiary_user_id, u.username, u.first_name
                ORDER BY total_amount DESC, cnt DESC
                LIMIT ?
                ''',
                (limit,),
            ).fetchall()
        return list(rows)
