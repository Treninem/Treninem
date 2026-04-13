-- SQL-схема проекта Bot_PUBG.
-- Этот файл нужен как человекочитаемая схема.
-- На практике приложение создает таблицы автоматически через SQLAlchemy.

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    pubg_player_id VARCHAR(255),
    pubg_nickname VARCHAR(255),
    pubg_rank VARCHAR(100),
    age INTEGER,
    weekly_hours INTEGER DEFAULT 0,
    timezone VARCHAR(64) DEFAULT 'Europe/Amsterdam',
    is_registered BOOLEAN DEFAULT 0,
    is_premium BOOLEAN DEFAULT 0,
    premium_until DATETIME,
    is_mentor BOOLEAN DEFAULT 0,
    mentor_specialization VARCHAR(255),
    mentor_schedule TEXT,
    mentor_style TEXT,
    points INTEGER DEFAULT 0,
    bot_rank VARCHAR(100) DEFAULT 'Новичок',
    last_activity_at DATETIME,
    created_at DATETIME,
    updated_at DATETIME
);
