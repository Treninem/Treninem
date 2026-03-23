# bot_config.py
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "2097006037").split(",")]
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot_database.db")
ADMIN_PASSWORD_HASH = int(os.getenv("ADMIN_PASSWORD_HASH", "230598"))