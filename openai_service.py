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

    @staticmethod
    def _candidate_models(primary: str, fallbacks: list[str]) -> list[str]:
        result: list[str] = []
        for item in [primary, *fallbacks]:
            model = (item or '').strip()
            if model and model not in result:
                result.append(model)
        return result

    @staticmethod
    def _should_try_next_model(exc: Exception) -> bool:
        raw = str(exc).lower()
        markers = (
            'model',
            'unsupported',
            'does not exist',
            'not found',
            'permission',
            'access',
            'unavailable',
        )
        return any(marker in raw for marker in markers)

    def edit_image(self, source_path: Path, prompt: str) -> bytes:
        last_exc: Exception | None = None
        models = self._candidate_models(self.settings.openai_image_model, ['gpt-image-1.5', 'gpt-image-1'])
        for model in models:
            try:
                with source_path.open('rb') as image_file:
                    result = self.client.images.edit(
                        model=model,
                        image=image_file,
                        prompt=prompt,
                        input_fidelity='high' if model != 'gpt-image-1-mini' else 'low',
                    )
                if not result.data or not result.data[0].b64_json:
                    raise RuntimeError('OpenAI не вернул картинку.')
                return base64.b64decode(result.data[0].b64_json)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if not self._should_try_next_model(exc) or model == models[-1]:
                    break
        raise RuntimeError(str(last_exc) if last_exc else 'OpenAI не вернул картинку.')

    def generate_text(self, kind: str, user_brief: str) -> str:
        last_exc: Exception | None = None
        models = self._candidate_models(self.settings.openai_text_model, ['gpt-4.1-mini', 'gpt-4o-mini'])
        for model in models:
            try:
                response = self.client.responses.create(
                    model=model,
                    input=text_generation_prompt(kind, user_brief),
                )
                text = (response.output_text or '').strip()
                if not text:
                    raise RuntimeError('OpenAI не вернул текст.')
                return text
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if not self._should_try_next_model(exc) or model == models[-1]:
                    break
        raise RuntimeError(str(last_exc) if last_exc else 'OpenAI не вернул текст.')

    def suggest_presets_for_photo(self, source_path: Path) -> list[str]:
        mime_type, _ = mimetypes.guess_type(source_path.name)
        mime_type = mime_type or 'image/jpeg'
        with source_path.open('rb') as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        last_exc: Exception | None = None
        models = self._candidate_models(self.settings.openai_vision_model, ['gpt-4.1-mini', 'gpt-4o-mini'])
        for model in models:
            try:
                response = self.client.responses.create(
                    model=model,
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
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if not self._should_try_next_model(exc) or model == models[-1]:
                    break
        raise RuntimeError(str(last_exc) if last_exc else 'OpenAI не вернул ответ.')
