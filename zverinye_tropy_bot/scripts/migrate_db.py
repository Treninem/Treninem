import sys
import os
# Добавляем родительскую директорию в путь поиска модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base, engine

def create_tables():
    Base.metadata.create_all(engine)
    print("Все таблицы успешно созданы в базе данных!")

if __name__ == "__main__":
    create_tables()
