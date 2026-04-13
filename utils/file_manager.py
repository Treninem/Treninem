"""Работа с файлами и вложениями."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from config.credentials import STORAGE_DIR


def ensure_storage() -> Path:
    path = Path(STORAGE_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_unique_filename(prefix: str, ext: str) -> str:
    return f"{prefix}_{uuid4().hex}.{ext.lstrip('.')}"


def save_bytes(data: bytes, filename: str) -> str:
    storage = ensure_storage()
    path = storage / filename
    path.write_bytes(data)
    return str(path)


def save_text(text: str, filename: str) -> str:
    storage = ensure_storage()
    path = storage / filename
    path.write_text(text, encoding="utf-8")
    return str(path)


def file_exists(path: str) -> bool:
    return os.path.exists(path)
