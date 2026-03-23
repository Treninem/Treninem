from database import SessionLocal, User, Inventory
import hashlib

# Хешируем пароль администратора
ADMIN_PASSWORD_HASH = hashlib.sha256("your_admin_password".encode()).hexdigest()

def check_admin_password(password: str) -> bool:
    """Проверяет пароль администратора через SHA‑256"""
    return hashlib.sha256(password.encode()).hexdigest() == ADMIN_PASSWORD_HASH

def get_stats() -> dict:
    """Возвращает статистику по игре"""
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
    """Выдаёт предмет пользователю"""
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
    except Exception as e:
        print(f"Ошибка выдачи предмета: {e}")
        db.rollback()
        return False
    finally:
        db.close()
