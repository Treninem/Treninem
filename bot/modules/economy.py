from database import SessionLocal, Market, Inventory, User

def list_market_items() -> list:
    db = SessionLocal()
    try:
        items = db.query(Market).filter(Market.quantity > 0).all()
        return items
    finally:
        db.close()

def create_market_listing(seller_id: int, item_id: int, price: float, quantity: int) -> bool:
    db = SessionLocal()
    try:
        listing = Market(
            seller_id=seller_id,
            item_id=item_id,
            price=price,
            quantity=quantity
        )
        db.add(listing)
        db.commit()
        return True
    except Exception:
        return False
    finally:
        db.close()

def process_trade(buyer_id: int, listing_id: int, quantity: int) -> dict:
    db = SessionLocal()
    try:
        listing = db.query(Market).filter(Market.id == listing_id).first()
        if not listing or listing.quantity < quantity:
            return {"success": False, "message": "Лот не найден или недостаточно товара"}

        buyer = db.query(User).filter(User.id == buyer_id).first()
        seller = db.query(User).filter(User.id == listing.seller_id).first()

        total_price = listing.price * quantity
        if buyer.coins < total_price:
            return {"success": False, "message": "Недостаточно монет"}

        # Списываем монеты у покупателя
        buyer.coins -= total_price
        # Начисляем монеты продавцу
        seller.coins += total_price

        # Передаём предметы
        # Здесь должна быть логика перемещения предметов между инвентарями

        # Обновляем лот
        listing.quantity -= quantity
        if listing.quantity == 0:
            db.delete(listing)

        db.commit()
        return {"success": True, "message": "Обмен успешно завершён!"}
    finally:
        db.close()
