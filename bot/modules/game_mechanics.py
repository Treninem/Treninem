from database import SessionLocal, Expedition, User
from datetime import datetime, timedelta
import random

EXPEDITION_CHANCES = {
    "easy": 0.9,
    "medium": 0.6,
    "hard": 0.2,
    "nightmare": 0.05
}

RESOURCE_RARITIES = ["обычная", "редкая", "эпическая", "легендарная"]
RARITY_CHANCES = [0.6, 0.25, 0.1, 0.05]

def start_expedition(user_id: int, difficulty: str) -> dict:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "message": "Пользователь не найден"}

        # Проверяем энергию и сытость
        if user.energy < 5:
            return {"success": False, "message": "Недостаточно энергии"}
        if user.satiety < 2:
            return {"success": False, "message": "Персонаж слишком голоден"}

        # Тратим ресурсы
        user.energy -= 5
        user.satiety -= 2

        # Создаём экспедицию
        expedition = Expedition(
            user_id=user_id,
            difficulty=difficulty,
            status="active"
        )
        db.add(expedition)
        db.commit()

        return {
            "success": True,
            "message": f"Экспедиция уровня '{difficulty}' начата!",
            "expedition_id": expedition.id
        }
    finally:
        db.close()

def complete_expedition(expedition_id: int) -> dict:
    db = SessionLocal()
    try:
        expedition = db.query(Expedition).filter(Expedition.id == expedition_id).first()
        if not expedition or expedition.status != "active":
            return {"success": False, "message": "Экспедиция не найдена или уже завершена"}

        user = db.query(User).filter(User.id == expedition.user_id).first()
        chance = EXPEDITION_CHANCES[expedition.difficulty]

        if random.random() <= chance:
            # Успех — выдаём награду
            rarity = random.choices(RESOURCE_RARITIES, RARITY_CHANCES)[0]
            reward_amount = random.randint(1, 5)

            # Здесь должна быть логика добавления предметов в инвентарь
            expedition.status = "completed"
            message = f"Успех! Найдены {reward_amount} {rarity} ресурсов."
        else:
            # Провал — возможно, штраф
            expedition.status = "failed"
            message = "Экспедиция провалилась! Вы вернулись ни с чем."

        db.commit()
        return {"success": True, "message": message}
    finally:
        db.close()
