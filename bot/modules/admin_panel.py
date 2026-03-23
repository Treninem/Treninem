from database import SessionLocal, User, Inventory
from config import SECRET_KEY
from cryptography.fernet import Fernet
import hashlib

# Хешируем пароль администратора
ADMIN_PASSWORD_HASH = hashlib.sha256("your_admin_password".encode()).hexdigest()
fernet = Fernet(SECRET_KEY.encode())

def check_admin_password(password: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH

def get_stats() -> dict:
    db = SessionLocal()
    try:
        users_count = db.query(User).count()
        active_expeditions = db.query(Expedition).filter(Expedition.status == "active").count()
        market_listings = db.query(Market).count()

        return {
            "total_users": users_count,
            "active_expeditions": active_expeditions,
            "market_listings": market_listings
        }
    finally:
        db.close()

def give_item(user_id: int, item_id: int, quantity: int) -> bool:
    db = SessionLocal()
    try:
        inventory_item = db.query(Inventory).filter(
            Inventory.user_id == user_id,
            Inventory.item_id == item_id
        ).first()

        if inventory_item:
            inventory_item.quantity += quantity
        else:
            new_item = Inventory(user_id=user_id, item_id=item_id, quantity=quantity)
            db.add(new_item)

        db.commit()
        return True
    finally:
        db.close()
