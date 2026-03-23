# models/database.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "bot_database.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH.as_posix())
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        character TEXT,
        hp INTEGER,
        energy INTEGER,
        hunger INTEGER,
        level INTEGER,
        exp INTEGER,
        coins INTEGER,
        crystals INTEGER,
        vip BOOLEAN DEFAULT 0,
        inventory_slots INTEGER DEFAULT 60
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        item_id INTEGER,
        quantity INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY,
        name TEXT,
        rarity TEXT,
        type TEXT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS market (
        id INTEGER PRIMARY KEY,
        seller_id INTEGER,
        item_id INTEGER,
        price INTEGER,
        quantity INTEGER,
        FOREIGN KEY(seller_id) REFERENCES users(id),
        FOREIGN KEY(item_id) REFERENCES items(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expeditions (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        type TEXT,
        start_time TEXT,
        status TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    conn.commit()
    conn.close()

# вызов инициализации можно выполнять в on_startup