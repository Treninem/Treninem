"""Заготовка под интеграцию с Yandex Cloud / Object Storage.

На Bothost этот модуль можно не использовать.
Он оставлен для совместимости архитектуры.
"""
from __future__ import annotations

from dataclasses import dataclass

from config.credentials import (
    YANDEX_ACCESS_KEY,
    YANDEX_CLOUD_FOLDER_ID,
    YANDEX_SECRET_KEY,
    YANDEX_STORAGE_BUCKET,
)


@dataclass
class YandexCloudConfig:
    folder_id: str = YANDEX_CLOUD_FOLDER_ID
    bucket: str = YANDEX_STORAGE_BUCKET
    access_key: str = YANDEX_ACCESS_KEY
    secret_key: str = YANDEX_SECRET_KEY


def is_configured() -> bool:
    return all([YANDEX_CLOUD_FOLDER_ID, YANDEX_STORAGE_BUCKET, YANDEX_ACCESS_KEY, YANDEX_SECRET_KEY])


def upload_text(filename: str, content: str) -> str:
    """Заглушка загрузки текста в Object Storage.
    Возвращает локальный псевдо-путь.
    """
    return f"local://{filename}"
