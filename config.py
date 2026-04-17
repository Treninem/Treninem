from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    openai_api_key: str
    openai_text_model: str
    openai_image_model: str
    openai_vision_model: str
    db_path: Path
    temp_dir: Path
    result_dir: Path
    preview_dir: Path
    free_trial_credits: int
    child_owner_daily_free: int
    small_pack_price: int
    small_pack_credits: int
    big_pack_price: int
    big_pack_credits: int
    pro_30_price: int
    pro_30_days: int
    request_timeout_seconds: int
    admin_user_ids: tuple[int, ...]
    root_owner_user_id: int | None
    suspicious_burst_limit: int
    suspicious_burst_window_minutes: int
    direct_commission_permille: int
    parent_commission_permille: int
    grandparent_commission_permille: int
    platform_commission_permille: int


@dataclass(frozen=True)
class CommissionPlan:
    direct_permille: int
    parent_permille: int
    grandparent_permille: int
    platform_permille: int


def _parse_admin_ids(raw_value: str) -> tuple[int, ...]:
    items: list[int] = []
    for part in raw_value.split(','):
        part = part.strip()
        if not part:
            continue
        try:
            items.append(int(part))
        except ValueError:
            continue
    return tuple(dict.fromkeys(items))


def load_settings() -> Settings:
    telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '').strip()
    openai_api_key = os.getenv('OPENAI_API_KEY', '').strip()
    admin_user_ids = _parse_admin_ids(os.getenv('ADMIN_USER_IDS', ''))
    root_owner_raw = os.getenv('ROOT_OWNER_USER_ID', '').strip()
    root_owner_user_id = int(root_owner_raw) if root_owner_raw.isdigit() else (admin_user_ids[0] if admin_user_ids else None)

    free_trial = os.getenv('FREE_TRIAL_REQUESTS') or os.getenv('FREE_TRIAL_CREDITS') or '5'

    settings = Settings(
        telegram_bot_token=telegram_bot_token,
        openai_api_key=openai_api_key,
        openai_text_model=os.getenv('OPENAI_TEXT_MODEL', 'gpt-4.1-mini').strip(),
        openai_image_model=os.getenv('OPENAI_IMAGE_MODEL', 'gpt-image-1.5').strip(),
        openai_vision_model=os.getenv('OPENAI_VISION_MODEL', 'gpt-4.1-mini').strip(),
        db_path=Path(os.getenv('DB_PATH', BASE_DIR / 'data' / 'bot.sqlite3')),
        temp_dir=Path(os.getenv('TEMP_DIR', BASE_DIR / 'data' / 'temp')),
        result_dir=Path(os.getenv('RESULT_DIR', BASE_DIR / 'data' / 'results')),
        preview_dir=Path(os.getenv('PREVIEW_DIR', BASE_DIR)),
        free_trial_credits=int(free_trial),
        child_owner_daily_free=int(os.getenv('CHILD_OWNER_DAILY_FREE', '10')),
        small_pack_price=int(os.getenv('STARS_SMALL_PACK_PRICE', '79')),
        small_pack_credits=int(os.getenv('SMALL_PACK_CREDITS', '5')),
        big_pack_price=int(os.getenv('STARS_BIG_PACK_PRICE', '199')),
        big_pack_credits=int(os.getenv('BIG_PACK_CREDITS', '15')),
        pro_30_price=int(os.getenv('STARS_PRO30_PRICE', '449')),
        pro_30_days=int(os.getenv('PRO_30_DAYS', '30')),
        request_timeout_seconds=int(os.getenv('REQUEST_TIMEOUT_SECONDS', '180')),
        admin_user_ids=admin_user_ids,
        root_owner_user_id=root_owner_user_id,
        suspicious_burst_limit=int(os.getenv('SUSPICIOUS_BURST_LIMIT', '8')),
        suspicious_burst_window_minutes=int(os.getenv('SUSPICIOUS_BURST_WINDOW_MINUTES', '10')),
        direct_commission_permille=int(os.getenv('DIRECT_COMMISSION_PERMILLE', '200')),
        parent_commission_permille=int(os.getenv('PARENT_COMMISSION_PERMILLE', '70')),
        grandparent_commission_permille=int(os.getenv('GRANDPARENT_COMMISSION_PERMILLE', '30')),
        platform_commission_permille=int(os.getenv('PLATFORM_COMMISSION_PERMILLE', '100')),
    )

    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    settings.result_dir.mkdir(parents=True, exist_ok=True)
    settings.preview_dir.mkdir(parents=True, exist_ok=True)
    return settings


def get_commission_plan(settings: Settings) -> CommissionPlan:
    return CommissionPlan(
        direct_permille=settings.direct_commission_permille,
        parent_permille=settings.parent_commission_permille,
        grandparent_permille=settings.grandparent_commission_permille,
        platform_permille=settings.platform_commission_permille,
    )
