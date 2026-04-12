from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'game.db'
STATIC_DIR = BASE_DIR / 'static'

# =========================
# ВСТАВЬ СВОИ ДАННЫЕ НИЖЕ
# =========================
VK_APP_ID = 54539686             # <-- сюда вставь ID VK Mini App
VK_APP_SECRET = 'PbGE7fhnmIDzPtRi3DbD'  # <-- сюда вставь защищённый ключ приложения VK
PUBLIC_WEB_URL = 'https://example.com'      # <-- сюда вставь публичный HTTPS URL, на котором будет открыт backend
OWNER_VK_IDS = [224402322]       # <-- сюда вставь свой VK ID
ADMIN_PASSWORD = 'Topor4iki980'   # <-- сюда вставь пароль секретной админ-панели
ALLOW_DEV_LOGIN = True           # Для локальной разработки; на проде лучше поставить False
SESSION_TTL_DAYS = 30
SHOP_REFRESH_HOURS = 4
LINK_CODE_TTL_MINUTES = 15
CREATOR_NAME = 'Treninem'
APP_TITLE = 'Beast Legends by Treninem'
