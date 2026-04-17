from __future__ import annotations

from pathlib import Path

from presets import MASK_PRESETS

PRESETS_PER_PAGE = 6
ASSETS_DIR = Path(__file__).resolve().parent


def preview_page_count() -> int:
    return max(1, (len(MASK_PRESETS) + PRESETS_PER_PAGE - 1) // PRESETS_PER_PAGE)



def preview_page_path(page: int) -> Path:
    page = max(0, min(page, preview_page_count() - 1))
    return ASSETS_DIR / f'page_{page + 1}.jpg'



def preview_page_caption(page: int) -> str:
    total_pages = preview_page_count()
    page = max(0, min(page, total_pages - 1))
    start = page * PRESETS_PER_PAGE
    chunk = MASK_PRESETS[start : start + PRESETS_PER_PAGE]
    lines = [
        f'🖼 Примеры масок — страница {page + 1}/{total_pages}',
        '',
        'Ниже — визуальные карточки для быстрого выбора вайба. Нажми на нужную маску под изображением.',
        '',
    ]
    for idx, preset in enumerate(chunk, start=start + 1):
        lines.append(f'{idx}. {preset.emoji} {preset.title} — {preset.short_note}')
    return '\n'.join(lines)
