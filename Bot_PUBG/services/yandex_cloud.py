"""Сервис совместимости с Yandex Object Storage.

В этом проекте основной запуск рассчитан на Bothost и локальное файловое хранилище.
Если позже понадобится S3/Object Storage, можно передать параметры через переменные окружения.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from config.credentials import STORAGE_DIR


class YandexCloudStorage:
    """Простейший адаптер хранилища.

    Сейчас работает в локальном режиме:
    - сохраняет файлы в папку storage/
    - возвращает локальный путь к файлу
    """

    def __init__(self, base_dir: str = STORAGE_DIR) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, filename: str, data: bytes) -> str:
        path = self.base_dir / filename
        path.write_bytes(data)
        return str(path)

    def save_file(self, source_path: str, target_name: str | None = None) -> str:
        source = Path(source_path)
        target = self.base_dir / (target_name or source.name)
        shutil.copy2(source, target)
        return str(target)

    def file_exists(self, filename: str) -> bool:
        return (self.base_dir / filename).exists()

    def get_path(self, filename: str) -> str:
        return str(self.base_dir / filename)
