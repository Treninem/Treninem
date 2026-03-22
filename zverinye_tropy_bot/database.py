from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, ForeignKey, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from config import DATABASE_URL

Base = declarative_base()

# Создаём движок и сессию
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    nickname = Column(String(16))
    character = Column(String(20))
    level = Column(Integer, default=1)
    exp = Column(Integer, default=0)
    money = Column(Float, default=100)
    crystals = Column(Float, default=0)  # Премиум валюта
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    energy = Column(Integer, default=10)
    max_energy = Column(Integer, default=10)
    satiety = Column(Integer, default=10)
    max_satiety = Column(Integer, default=10)
    damage = Column(Integer, default=5)
    inventory = Column(JSON, default={})
    is_vip = Column(Boolean, default=False)
    vip_expires = Column(DateTime)
    favorite_resource = Column(String(20))  # Любимый тип ресурса
    warnings = Column(Integer, default=0)
    is_banned = Column(Boolean, default=False)
    last_activity = Column(DateTime, default=datetime.utcnow)
    respawn_time = Column(DateTime)

class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(300))
    rarity = Column(String(20), default="обычный")
    type = Column(String(20), default="ресурс")
    price = Column(Float, default=0)
    heal_amount = Column(Integer, default=0)
    energy_boost = Column(Integer, default=0)

class Expedition(Base):
    __tablename__ = 'expeditions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    level = Column(Integer, nullable=False)  # 1–4
    status = Column(String(20), default="в пути")
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)

class CraftRecipe(Base):
    __tablename__ = 'craft_recipes'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    result_item_id = Column(Integer, ForeignKey('items.id'))
    result_quantity = Column(Integer, default=1)
    materials = Column(JSON, nullable=False)
    level_required = Column(Integer, default=1)

class MarketLot(Base):
    __tablename__ = 'market_lots'
    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, nullable=False)
    item_id = Column(Integer, ForeignKey('items.id'))
    price = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
