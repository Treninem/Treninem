from __future__ import annotations

import os
os.environ.setdefault('TELEGRAM_BOT_TOKEN', '123:TEST')
os.environ.setdefault('OPENAI_API_KEY', 'sk-test')

from config import load_settings
from db import Database


def main() -> None:
    settings = load_settings()
    preview_files = sorted(settings.preview_dir.glob('page_*.jpg'))
    if len(preview_files) < 5:
        raise RuntimeError('Не найдены preview-файлы масок.')

    db_path = settings.db_path.parent / 'smoke_test.sqlite3'
    if db_path.exists():
        db_path.unlink()

    db = Database(db_path, settings.free_trial_credits, settings.child_owner_daily_free)
    db.init()

    for uid, username, first_name in [(1, 'rootowner', 'Root'), (2, 'alice', 'Alice'), (3, 'bob', 'Bob'), (4, 'eve', 'Eve')]:
        db.upsert_user(uid, username, first_name)

    root_id = db.ensure_root_bot('123:TEST', 111, 'rootbot', 'Root Bot')
    child_id = db.create_child_bot('456:TEST', 222, 'childbot', 'Child Bot', 2, root_id, None)

    db.ensure_bot_user_state(child_id, 2)
    db.ensure_bot_user_state(child_id, 4)

    ok, reason = db.consume_request(child_id, 4)
    if not ok or reason not in {'trial', 'credit', 'owner_daily', 'platform_vip', 'premium', 'admin', 'global_bonus'}:
        raise RuntimeError(f'Не удалось списать тестовый запрос: {ok=}, {reason=}')

    db.add_bot_paid_credits(child_id, 4, 2)
    db.save_job(child_id, 4, 'image_custom', 'source.jpg', 'result.jpg', None, 'neon wolf', 'done')
    payment_id = db.save_payment(4, child_id, 'payload_smoke', 'pack_small', 79, 'XTR', 'tg_charge', 'provider_charge')
    db.record_commission(payment_id, 2, child_id, 15, 1, 'smoke')

    stats = dict(db.dashboard_stats())
    if stats['total_users'] < 4 or stats['active_bots'] < 2:
        raise RuntimeError(f'Статистика выглядит некорректной: {stats}')

    print('Smoke test OK')
    print(f'Preview files: {len(preview_files)}')
    print(f'Users: {stats["total_users"]}, active bots: {stats["active_bots"]}, revenue: {stats["stars_revenue"]}')


if __name__ == '__main__':
    main()
