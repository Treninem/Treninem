"""Константы проекта: меню, ранги, баллы, лимиты и текстовые шаблоны."""

from __future__ import annotations

# -----------------------------
# Кнопки главного меню
# -----------------------------
MAIN_MENU_PROFILE = "👤 Профиль"
MAIN_MENU_MENTORSHIP = "👨‍🏫 Наставничество"
MAIN_MENU_NEWS = "📰 Новости"
MAIN_MENU_PREMIUM = "💎 Премиум"
MAIN_MENU_FRIENDS = "🤝 Друзья"
MAIN_MENU_GROUPS = "🌐 Группы с ботом"
MAIN_MENU_FEEDBACK = "💬 Обратная связь"

MAIN_MENU_BUTTONS = [
    MAIN_MENU_PROFILE,
    MAIN_MENU_MENTORSHIP,
    MAIN_MENU_NEWS,
    MAIN_MENU_PREMIUM,
    MAIN_MENU_FRIENDS,
    MAIN_MENU_GROUPS,
    MAIN_MENU_FEEDBACK,
]

# -----------------------------
# Подменю «Профиль»
# -----------------------------
PROFILE_REGISTER = "🆕 Зарегистрироваться / Редактировать"
PROFILE_PROGRESS = "📊 Мой прогресс"
PROFILE_POINTS = "🏆 Мои баллы"
PROFILE_ACHIEVEMENTS = "🎯 Мои достижения"
PROFILE_BINDING = "🆔 Моя привязка"
PROFILE_SYNC = "📡 Обновить PUBG-данные"
PROFILE_CARD = "✨ Моя карточка"

PROFILE_MENU_BUTTONS = [
    PROFILE_REGISTER,
    PROFILE_PROGRESS,
    PROFILE_POINTS,
    PROFILE_ACHIEVEMENTS,
    PROFILE_BINDING,
    PROFILE_SYNC,
    PROFILE_CARD,
]

# -----------------------------
# Подменю «Наставничество»
# -----------------------------
MENTOR_APPLY = "👨‍🏫 Стать наставником"
MENTOR_SEARCH = "🔎 Поиск наставников"
MENTOR_STUDENTS = "👥 Мои подопечные"
MENTOR_TRAININGS = "🎯 Мои тренировки"
MENTOR_TASKS = "📝 Мои задания"
MENTOR_CREATE_TRAINING = "➕ Создать тренировку"
MENTOR_CREATE_TASK = "➕ Создать задание"

MENTOR_MENU_BUTTONS = [
    MENTOR_APPLY,
    MENTOR_SEARCH,
    MENTOR_STUDENTS,
    MENTOR_TRAININGS,
    MENTOR_TASKS,
    MENTOR_CREATE_TRAINING,
    MENTOR_CREATE_TASK,
]

# -----------------------------
# Подменю «Новости»
# -----------------------------
NEWS_LATEST = "📣 Последние новости"
NEWS_EVENTS = "🗓️ События"
NEWS_PATCHES = "🎮 Обновления игры"

NEWS_MENU_BUTTONS = [
    NEWS_LATEST,
    NEWS_EVENTS,
    NEWS_PATCHES,
]

# -----------------------------
# Подменю «Премиум»
# -----------------------------
PREMIUM_INFO = "💎 О премиум-статусе"
PREMIUM_BUY = "💳 Оформить/продлить"
PREMIUM_PRIVILEGES = "🎁 Мои привилегии"
PREMIUM_EXPIRES = "⏱️ Срок действия"
PREMIUM_EXCHANGE = "🔁 Обменять баллы на премиум"

PREMIUM_MENU_BUTTONS = [
    PREMIUM_INFO,
    PREMIUM_BUY,
    PREMIUM_PRIVILEGES,
    PREMIUM_EXPIRES,
    PREMIUM_EXCHANGE,
]

# -----------------------------
# Подменю «Друзья»
# -----------------------------
FRIENDS_LIST = "👥 Список друзей"
FRIENDS_ADD = "➕ Добавить друга"
FRIENDS_CHAT = "🗣️ Чат с друзьями"
FRIENDS_RATING = "🏅 Рейтинг друзей"
FRIENDS_INVITE = "🎁 Пригласить друзей"
FRIENDS_PROMO = "📣 Промо-набор"
FRIENDS_TOP = "🔥 Топ приглашений"

FRIENDS_MENU_BUTTONS = [
    FRIENDS_LIST,
    FRIENDS_ADD,
    FRIENDS_CHAT,
    FRIENDS_RATING,
    FRIENDS_INVITE,
    FRIENDS_PROMO,
    FRIENDS_TOP,
]

# -----------------------------
# Подменю «Группы с ботом»
# -----------------------------
GROUPS_LIST = "📋 Список чатов"
GROUPS_INFO = "ℹ️ Информация о чатах"
GROUPS_LEAVE = "🚪 Выйти из чата"

GROUPS_MENU_BUTTONS = [
    GROUPS_LIST,
    GROUPS_INFO,
    GROUPS_LEAVE,
]

# -----------------------------
# Подменю «Обратная связь»
# -----------------------------
FEEDBACK_REVIEW = "📝 Оставить отзыв"
FEEDBACK_REPORT = "⚠️ Пожаловаться"
FEEDBACK_QUESTION = "❓ Задать вопрос"
FEEDBACK_SUGGESTION = "📢 Предложения"

FEEDBACK_MENU_BUTTONS = [
    FEEDBACK_REVIEW,
    FEEDBACK_REPORT,
    FEEDBACK_QUESTION,
    FEEDBACK_SUGGESTION,
]

BACK_TO_MAIN = "⬅️ Назад в меню"
CANCEL_ACTION = "❌ Отмена"

# -----------------------------
# Балльная система
# -----------------------------
POINTS_DAILY_TEST = 10
POINTS_TRAINING_ATTENDANCE = 20
POINTS_TASK_COMPLETED = 50
POINTS_FRIEND_INVITE = 30
POINTS_BONUS_QUESTION = 15
POINTS_WELCOME_BONUS = 25

PENALTY_TRAINING_MISS = -20
PENALTY_INACTIVITY = -10
PENALTY_RULES_VIOLATION = -50

# -----------------------------
# Ранги бота
# -----------------------------
BOT_RANKS = [
    (0, 100, "Новичок"),
    (101, 300, "Стрелок"),
    (301, 600, "Тактик"),
    (601, 1000, "Ветеран"),
    (1001, 10**9, "Легенда"),
]

BOT_RANK_PRIVILEGES = {
    "Новичок": ["Базовый функционал", "Регистрация и базовая аналитика", "Карточка игрока"],
    "Стрелок": ["Доступ к тестам", "Добавление друзей", "Участие в рейтингах"],
    "Тактик": ["Участие в тренировках", "Расширенная статистика", "Больше аналитики по PUBG"],
    "Ветеран": ["Можно стать наставником (если PUBG ранг позволяет)", "Создание заданий", "Приоритет в подборе"],
    "Легенда": ["Приоритетная поддержка", "Обмен баллов на премиум", "Лидерские привилегии"],
}

PREMIUM_EXCHANGE_DAYS_COST = 500  # 500 баллов = 1 день премиума

# -----------------------------
# PUBG ранги наставников
# -----------------------------
MENTOR_MIN_RANK_NAMES = {
    "crown",
    "ace",
    "conqueror",
    "master",
    "grandmaster",
    "diamond",
}

PUBG_RANK_ORDER = {
    "bronze": 1,
    "silver": 2,
    "gold": 3,
    "platinum": 4,
    "diamond": 5,
    "crown": 6,
    "ace": 7,
    "master": 7,
    "grandmaster": 8,
    "conqueror": 9,
}

# -----------------------------
# Другое
# -----------------------------
DEFAULT_MENTOR_FREE_SLOTS = 3
MAX_NEWS_ITEMS = 5
MAX_FRIENDS_CHAT_MEMBERS = 10
REFERRAL_PREFIX = "clan"

FEEDBACK_TYPES = {
    FEEDBACK_REVIEW: "review",
    FEEDBACK_REPORT: "report",
    FEEDBACK_QUESTION: "question",
    FEEDBACK_SUGGESTION: "suggestion",
}

COMPLAINT_TARGETS = ["наставник", "игрок", "баг"]

NEWS_CATEGORY_EVENT_KEYWORDS = ("event", "festival", "survivor pass", "challenge", "crossover")
NEWS_CATEGORY_PATCH_KEYWORDS = ("patch", "update", "hotfix", "maintenance")

SUPPORT_TEXT = (
    "Если что-то не работает или нужна помощь, напишите владельцу: "
    "@Treninem"
)
