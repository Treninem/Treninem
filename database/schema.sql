-- SQL-схема БД для проекта Bot_PUBG.
-- Используется как справочный файл; реальное создание таблиц выполняет SQLAlchemy.

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    telegram_id INTEGER NOT NULL UNIQUE,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    pubg_player_id VARCHAR(255),
    pubg_name VARCHAR(255),
    pubg_rank VARCHAR(255),
    pubg_kd VARCHAR(50),
    pubg_shard VARCHAR(50),
    pubg_level INTEGER,
    pubg_total_matches INTEGER,
    pubg_total_wins INTEGER,
    pubg_total_kills INTEGER,
    pubg_total_damage FLOAT,
    pubg_headshot_kills INTEGER,
    pubg_avg_damage FLOAT,
    pubg_win_rate FLOAT,
    pubg_top10s INTEGER,
    pubg_stats_json TEXT,
    pubg_last_sync_at DATETIME,
    pubg_bound_at DATETIME,
    age INTEGER,
    hours_per_week INTEGER,
    timezone VARCHAR(100) DEFAULT 'Europe/Moscow',
    is_registered BOOLEAN DEFAULT 0,
    is_mentor BOOLEAN DEFAULT 0,
    mentor_active BOOLEAN DEFAULT 0,
    points INTEGER DEFAULT 0,
    bot_rank VARCHAR(100) DEFAULT 'Новичок',
    premium_until DATETIME,
    referred_by_user_id INTEGER,
    referral_code VARCHAR(64) UNIQUE,
    referral_points_paid BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS friends (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    friend_pubg_player_id VARCHAR(255),
    friend_pubg_name VARCHAR(255) NOT NULL,
    friend_pubg_rank VARCHAR(255),
    friend_kd VARCHAR(50),
    linked_user_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mentor_profiles (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,
    specialization VARCHAR(255) NOT NULL,
    schedule_text TEXT NOT NULL,
    teaching_style TEXT NOT NULL,
    free_slots INTEGER DEFAULT 3,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mentor_students (
    id INTEGER PRIMARY KEY,
    mentor_user_id INTEGER NOT NULL,
    student_user_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trainings (
    id INTEGER PRIMARY KEY,
    mentor_user_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    difficulty VARCHAR(100) NOT NULL,
    description TEXT,
    training_at DATETIME NOT NULL,
    status VARCHAR(50) DEFAULT 'scheduled',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS training_participants (
    id INTEGER PRIMARY KEY,
    training_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    attended BOOLEAN,
    warned_absence BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mentor_tasks (
    id INTEGER PRIMARY KEY,
    mentor_user_id INTEGER NOT NULL,
    student_user_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    due_at DATETIME,
    reward_points INTEGER DEFAULT 50,
    status VARCHAR(50) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS point_transactions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    reason VARCHAR(255) NOT NULL,
    meta_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_test_sessions (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    scheduled_for DATETIME NOT NULL,
    reminder_sent BOOLEAN DEFAULT 0,
    test_payload_json TEXT NOT NULL,
    answers_json TEXT DEFAULT '[]',
    score INTEGER DEFAULT 0,
    bonus_correct BOOLEAN DEFAULT 0,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback_tickets (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    ticket_type VARCHAR(100) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    text TEXT NOT NULL,
    screenshot_file_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'open',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_info (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL UNIQUE,
    title VARCHAR(255),
    chat_type VARCHAR(50),
    members_count INTEGER,
    added_by_user_id INTEGER,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_messages (
    id INTEGER PRIMARY KEY,
    chat_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news_cache (
    id INTEGER PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    url VARCHAR(1000) NOT NULL UNIQUE,
    category VARCHAR(50),
    published_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
