from __future__ import annotations

from presets import MaskPreset, MASK_PRESETS


BASE_EDIT_RULES = (
    'Edit the provided real user photo. Preserve identity, face shape, age range, natural skin tone, '
    'hairstyle essence, pose, hands, and overall recognizability. Keep the result high-quality, photorealistic, '
    'tasteful, and social-media ready. Do not add text, watermarks, extra people, duplicate limbs, or deformed facial features.'
)


def preset_edit_prompt(preset: MaskPreset, stronger: bool = False) -> str:
    strength = 'Increase the visual effect intensity by about 25% while still keeping the face natural and recognizable.' if stronger else 'Balance stylization with realism.'
    return (
        f'{BASE_EDIT_RULES} Apply this mask/effect: {preset.effect_prompt}. '
        f'{strength} Keep the background coherent with the style and make the image polished and premium.'
    )



def custom_edit_prompt(user_text: str, stronger: bool = False) -> str:
    safe_text = user_text.strip()
    strength = 'Increase the intensity by about 25% while preserving realism and likeness.' if stronger else 'Keep it polished and believable.'
    return (
        f'{BASE_EDIT_RULES} Apply the following user-requested creative effect: {safe_text}. '
        f'{strength} If the request is vague, choose the most attractive premium social-media interpretation.'
    )


TEXT_TYPE_GUIDE = {
    'poem': ('стих', 'рифма, образность, красивый ритм'),
    'song': ('песня', 'куплеты и припев, цепляющие строки'),
    'poema': ('поэма', 'развернуто, образно, эмоционально'),
    'greeting': ('поздравление', 'тепло, искренне, персонально'),
    'quote': ('выражения', 'коротко, ярко, цитатно'),
    'status': ('статус', 'кратко, эффектно, запоминаемо'),
    'toast': ('тост', 'празднично, уверенно, красиво'),
    'caption': ('подпись к посту', 'вирусно, красиво, с эмоцией'),
    'rap': ('рэп/панчлайны', 'ритм, ударные строки, смелая подача'),
    'custom': ('свой формат', 'подстройся под запрос пользователя'),
}



def text_generation_prompt(kind: str, user_brief: str) -> str:
    human_name, style_note = TEXT_TYPE_GUIDE.get(kind, TEXT_TYPE_GUIDE['custom'])
    return (
        'Ты сильный русскоязычный креативный автор. '
        f'Создай {human_name} по запросу пользователя. '
        f'Ориентир по стилю: {style_note}. '
        'Пиши естественно, без канцелярита, без пояснений перед результатом. '
        'Используй слова и идеи пользователя как основу, но улучшай подачу. '
        'Если уместно, дай 2-3 варианта, чтобы пользователю было из чего выбрать. '
        f'Запрос пользователя: {user_brief.strip()}'
    )



def preset_suggestion_prompt() -> str:
    lines = [f'- {preset.key}: {preset.title} — {preset.short_note}' for preset in MASK_PRESETS]
    catalog = '\n'.join(lines)
    return (
        'Ты стилист для AI-фото-бота. Посмотри на фото и выбери ровно 5 лучших пресетов из каталога ниже. '
        'Оцени ракурс, одежду, выражение лица, освещение и общий вайб. '
        'Верни только 5 ключей preset key через запятую, без пояснений и без лишнего текста.\n\n'
        f'Каталог пресетов:\n{catalog}'
    )
