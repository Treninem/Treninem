from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from openai import OpenAI

from config import Settings
from presets import MASK_PRESETS, PRESET_BY_KEY
from prompts import preset_suggestion_prompt, text_generation_prompt


class OpenAIService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = OpenAI(api_key=settings.openai_api_key, timeout=settings.request_timeout_seconds)

    def edit_image(self, source_path: Path, prompt: str) -> bytes:
        with source_path.open('rb') as image_file:
            result = self.client.images.edit(
                model=self.settings.openai_image_model,
                image=image_file,
                prompt=prompt,
                input_fidelity='high',
            )
        if not result.data or not result.data[0].b64_json:
            raise RuntimeError('OpenAI не вернул картинку.')
        return base64.b64decode(result.data[0].b64_json)

    def generate_text(self, kind: str, user_brief: str) -> str:
        response = self.client.responses.create(
            model=self.settings.openai_text_model,
            input=text_generation_prompt(kind, user_brief),
        )
        text = (response.output_text or '').strip()
        if not text:
            raise RuntimeError('OpenAI не вернул текст.')
        return text

    def suggest_presets_for_photo(self, source_path: Path) -> list[str]:
        mime_type, _ = mimetypes.guess_type(source_path.name)
        mime_type = mime_type or 'image/jpeg'
        with source_path.open('rb') as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        response = self.client.responses.create(
            model=self.settings.openai_vision_model,
            input=[
                {
                    'role': 'user',
                    'content': [
                        {'type': 'input_text', 'text': preset_suggestion_prompt()},
                        {'type': 'input_image', 'image_url': f'data:{mime_type};base64,{base64_image}'},
                    ],
                }
            ],
        )
        raw = (response.output_text or '').strip().replace('\n', ',')
        keys: list[str] = []
        for part in raw.split(','):
            key = part.strip().strip('.').strip()
            if key in PRESET_BY_KEY and key not in keys:
                keys.append(key)
        if len(keys) < 5:
            fallback = [p.key for p in MASK_PRESETS if p.key not in keys][: 5 - len(keys)]
            keys.extend(fallback)
        return keys[:5]
