from database import SessionLocal, User
from datetime import datetime, timedelta
import random

CHARACTERS = {
    "лиса": {"hp": 80, "energy_per_turn": 5, "satiety_per_turn": 2, "damage": 15, "skill_cooldown": 3, "feature": "Воровство"},
    "волк": {"hp": 120, "energy_per_turn": 4, "satiety_per_turn": 3, "damage": 20, "skill_cooldown": 4, "feature": "Вой"},
    # ... остальные персонажи
}

def register_user(telegram_id: int, nickname: str, character: str) -> bool:
    db = SessionLocal()
    try:
        if db.query(User).filter(User.telegram_id == telegram_id).first():
            return False
        
        user = User(
            telegram_id=telegram_id,
            nickname=nickname,
            character=character,
            hp=CHARACTERS[character]["hp"],
            max_hp=CHARACTERS[character]["hp"],
            energy=10,
            max_energy=10,
            satiety=10,
            max_satiety=10
        )
        db.add(user)
        db.commit()
        return True
    finally:
        db.close()

def get_user_profile(telegram_id: int) -> User:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.telegram_id == telegram_id).first()
    finally:
        db.close()
