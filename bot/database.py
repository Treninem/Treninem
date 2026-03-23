from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import config

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    nickname = Column(String(16), nullable=False)
    character = Column(String(50), nullable=False)  # ID персонажа
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    energy = Column(Integer, default=10)
    max_energy = Column(Integer, default=10)
    satiety = Column(Integer, default=10)
    max_satiety = Column(Integer, default=10)
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    coins = Column(Integer, default=0)
    crystals = Column(Integer, default=0)
    inventory_slots = Column(Integer, default=60)
    premium_until = Column(DateTime, nullable=True)
    vip_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Inventory(Base):
    __tablename__ = 'inventory'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    item_id = Column(Integer, nullable=False)
    quantity = Column(Integer, default=1)

class Market(Base):
    __tablename__ = 'market'
    
    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    item_id = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

class Expedition(Base):
    __tablename__ = 'expeditions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    difficulty = Column(String(20), nullable=False)  # easy/medium/hard/nightmare
    status = Column(String(20), default="active")  # active/completed/failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

# Инициализация базы данных
engine = create_engine(config.DATABASE_URL)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
