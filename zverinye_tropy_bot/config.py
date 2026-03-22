import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
DATABASE_URL = os.getenv('DATABASE_URL')
ADMIN_IDS = [2097006037]  # ID администраторов
