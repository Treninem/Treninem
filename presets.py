from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaskPreset:
    key: str
    title: str
    emoji: str
    effect_prompt: str
    short_note: str


MASK_PRESETS: list[MaskPreset] = [
    MaskPreset('album_duo_gloss', 'Фото из альбома Клавы Коки и Димы Масленникова', '💿', 'glossy pop-adventure album photoshoot, premium styling, direct flash, warm skin tones, polished magazine finish, subtle romantic tension, luxury editorial atmosphere', 'Глянцевый альбомный вайб'),
    MaskPreset('y2k_popstar', 'Поп-звезда Y2K', '💖', 'early-2000s pop star glam, baby pink and chrome accents, lip gloss shine, flashy direct flash, playful magazine energy', 'Глянец 2000-х'),
    MaskPreset('coquette_bow', 'Бантики кокетки', '🎀', 'coquette aesthetic, satin bows, soft blush tones, pearly highlights, dreamy beauty editorial', 'Нежная кокетка'),
    MaskPreset('cyber_goth', 'Кибер-готика неон', '🖤', 'cyber goth club portrait, chrome details, deep blacks, acid accents, digital noise, rave mood', 'Тёмный неон'),
    MaskPreset('paparazzi_flash', 'Вспышка папарацци', '📸', 'celebrity paparazzi snapshot, bold direct flash, luxury nightlife mood, cinematic candid energy', 'Свет вспышки и звёздность'),
    MaskPreset('disposable_film', 'Плёночная мыльница', '🎞', 'disposable camera look, nostalgic film grain, slightly imperfect exposure, candid youth energy', 'Зерно и ностальгия'),
    MaskPreset('chrome_editorial', 'Хромовый журнал', '✨', 'futuristic chrome fashion editorial, clean metallic reflections, premium styling, high-fashion composition', 'Хром и мода'),
    MaskPreset('dark_romance', 'Тёмная романтика', '🌹', 'dark romance portrait, velvety shadows, burgundy palette, elegant mood, cinematic beauty lighting', 'Романтика и глубина'),
    MaskPreset('dreamcore_clouds', 'Сонные облака', '☁️', 'dreamcore portrait with glowing clouds, pastel haze, surreal softness, airy fantasy vibe', 'Воздушная сказка'),
    MaskPreset('street_grunge', 'Уличный гранж', '🧷', 'street grunge editorial, distressed textures, urban style, raw flash, cool attitude', 'Городская дерзость'),
    MaskPreset('angel_aura', 'Ангельская аура', '😇', 'ethereal angel portrait, luminous aura, feather-light glow, heavenly softness, elegant wings motif', 'Светлая аура'),
    MaskPreset('devil_glam', 'Дьявольский глянец', '😈', 'stylish devil glam portrait, red accents, glossy makeup, confident fashion attitude, dramatic lighting', 'Красный дерзкий стиль'),
    MaskPreset('anime_neon', 'Аниме-неон', '🪩', 'anime-inspired neon portrait, expressive eyes, vibrant cyber lights, polished stylization while preserving likeness', 'Аниме-неон'),
    MaskPreset('mafia_noir', 'Мафия-нуар', '🕶', 'modern mafia noir portrait, black suit mood, smoky shadows, luxury crime-drama atmosphere', 'Чёрный нуар'),
    MaskPreset('old_money', 'Эстетика старых денег', '🥂', 'old money portrait, aristocratic elegance, beige and cream palette, refined luxury, timeless class', 'Сдержанная роскошь'),
    MaskPreset('rockstar_stage', 'Рок-звезда на сцене', '🎸', 'rockstar portrait, backstage glam, leather and spotlight mood, strong concert attitude', 'Сцена и драйв'),
    MaskPreset('festival_boho', 'Фестивальный бохо', '🌼', 'festival boho portrait, sun-kissed skin, layered jewelry, free-spirited summer styling', 'Фестивальная свобода'),
    MaskPreset('futuristic_visor', 'Футуристичный визор', '🛸', 'futuristic visor portrait, sci-fi fashion, luminous reflections, clean sleek future aesthetic', 'Научная фантастика'),
    MaskPreset('kpop_cover', 'К-поп обложка', '🎤', 'K-pop inspired cover portrait, flawless beauty lighting, vibrant styling, polished idol aesthetic', 'Обложка K-pop'),
    MaskPreset('luxury_cover', 'Люксовая обложка', '📰', 'luxury fashion cover portrait, flawless editorial retouch, premium typography space, high-end magazine energy', 'Журнальная обложка'),
    MaskPreset('glitch_glam', 'Глитч-гламур', '⚡', 'glitch glam portrait, digital distortions, holographic accents, trendy future-pop style', 'Глитч и блеск'),
    MaskPreset('marble_statue', 'Мраморная аура', '🗿', 'classical marble aura portrait, sculptural lighting, elegant stone textures, artistic museum vibe', 'Скульптурный арт'),
    MaskPreset('fairy_forest', 'Лесная фея', '🧚', 'enchanted forest fairy portrait, botanical glow, soft magical particles, fairytale mood', 'Лесная фея'),
    MaskPreset('streamer_rgb', 'Стример RGB', '🎮', 'gaming streamer portrait, RGB glow, futuristic room mood, bold internet-star styling', 'Игровой неон'),
    MaskPreset('space_chrome', 'Космический хром', '🚀', 'space chrome portrait, cosmic reflections, futuristic metallic textures, celestial atmosphere', 'Космический хром'),
    MaskPreset('mermaid_pearl', 'Жемчужная русалка', '🧜', 'mermaid-inspired beauty portrait, pearlescent shimmer, ocean glow, elegant fantasy styling', 'Жемчужная русалка'),
    MaskPreset('ice_queen', 'Снежная королева', '❄️', 'ice queen portrait, cool crystal glow, silver-blue palette, regal winter elegance', 'Холодная королева'),
    MaskPreset('gold_royal', 'Королевское золото', '👑', 'royal gold portrait, ornate elegance, rich highlights, throne-room luxury vibe', 'Золотая корона'),
    MaskPreset('retro_vhs', 'Ретро VHS', '📼', 'retro VHS portrait, tape artifacts, nostalgic color bleed, vintage club mood', 'Ретро-кассета'),
    MaskPreset('comic_poster', 'Комикс-постер', '💥', 'bold comic-book poster portrait, graphic outlines, punchy dynamic composition, pop-art energy', 'Комикс-постер'),
]

PRESET_BY_KEY = {preset.key: preset for preset in MASK_PRESETS}
