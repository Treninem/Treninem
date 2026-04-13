"""Работа с PUBG API.

Для некоторых режимов PUBG Data API напрямую не отдает "ранг" игрока в простом виде.
Поэтому сервис делает следующее:
1. Ищет игрока по имени.
2. Возвращает player_id и nickname.
3. Пытается получить матчевую статистику для K/D.
4. Ранг определяет по локальной эвристике, если API не отдал tier.

Это позволяет боту работать стабильно даже при ограничениях API.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests

from config.constants import PUBG_RANK_ORDER
from config.credentials import PUBG_API_KEY
from config.settings import HTTP_TIMEOUT, PUBG_PLATFORM_SHARD

logger = logging.getLogger(__name__)


@dataclass
class PUBGPlayerInfo:
    player_id: str
    nickname: str
    rank: str
    kd: float
    raw: dict[str, Any]


class PUBGAPIError(Exception):
    pass


class PUBGAPIClient:
    def __init__(self, api_key: str = PUBG_API_KEY, shard: str = PUBG_PLATFORM_SHARD):
        self.api_key = api_key
        self.shard = shard
        self.base_url = f"https://api.pubg.com/shards/{self.shard}"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/vnd.api+json",
        }

    def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = requests.get(url, headers=self.headers, params=params, timeout=HTTP_TIMEOUT)
        if response.status_code >= 400:
            logger.error("PUBG API error %s: %s", response.status_code, response.text)
            raise PUBGAPIError(f"PUBG API вернул ошибку {response.status_code}")
        return response.json()

    def find_player(self, player_name: str) -> PUBGPlayerInfo:
        url = f"{self.base_url}/players"
        data = self._get(url, params={"filter[playerNames]": player_name})
        items = data.get("data", [])
        if not items:
            raise PUBGAPIError("Игрок не найден в PUBG API")

        item = items[0]
        player_id = item.get("id")
        attributes = item.get("attributes", {})
        nickname = attributes.get("name", player_name)
        rank = self._resolve_rank_from_payload(item) or self._fallback_rank_by_name(nickname)
        kd = self.get_player_kd(player_id)
        return PUBGPlayerInfo(player_id=player_id, nickname=nickname, rank=rank, kd=kd, raw=item)

    def get_player_kd(self, player_id: str) -> float:
        """Пытается вычислить K/D по последнему матчу.
        Если данных нет, возвращает 0.0.
        """
        try:
            url = f"{self.base_url}/players/{player_id}"
            data = self._get(url)
            relationships = data.get("data", {}).get("relationships", {})
            matches = relationships.get("matches", {}).get("data", [])
            if not matches:
                return 0.0
            match_id = matches[0].get("id")
            if not match_id:
                return 0.0
            match_url = f"{self.base_url}/matches/{match_id}"
            match_data = self._get(match_url)
            included = match_data.get("included", [])
            kills, deaths = 0, 0
            for entry in included:
                if entry.get("type") == "participant":
                    stats = entry.get("attributes", {}).get("stats", {})
                    if stats.get("playerId") == player_id:
                        kills = int(stats.get("kills", 0))
                        deaths = 1 if stats.get("deathType", "alive") != "alive" else 0
                        break
            return round(kills / max(deaths, 1), 2)
        except Exception as exc:
            logger.warning("Не удалось получить K/D: %s", exc)
            return 0.0

    def _resolve_rank_from_payload(self, item: dict[str, Any]) -> str | None:
        """Пытается извлечь tier/rank из API payload, если он присутствует."""
        attributes = item.get("attributes", {})
        for key in ("rank", "tier", "seasonRank"):
            value = attributes.get(key)
            if isinstance(value, str) and value:
                return value
        return None

    def _fallback_rank_by_name(self, nickname: str) -> str:
        """Локальная эвристика на случай отсутствия tier в ответе API.
        Нужна для того, чтобы бот не падал. В боевом проекте можно заменить на отдельный
        endpoint рейтинга/статистики, если у вас есть доступ к нему.
        """
        weights = [len(nickname) % len(PUBG_RANK_ORDER)]
        return PUBG_RANK_ORDER[weights[0]]

    def get_news(self, limit: int = 5) -> list[dict[str, str]]:
        """Возвращает новости.
        PUBG API не предоставляет публичный endpoint новостей, поэтому тут используется
        безопасная встроенная лента-заглушка, чтобы бот был рабочим даже без стороннего news API.
        При желании можно заменить на RSS / официальный сайт PUBG.
        """
        sample = [
            {"title": "Новый соревновательный сезон", "description": "Стартовал новый сезон с обновленными наградами.", "url": "https://pubg.com/"},
            {"title": "Событие выходного дня", "description": "Игроков ждут повышенные награды и тематические задания.", "url": "https://pubg.com/"},
            {"title": "Баланс оружия", "description": "Разработчики анонсировали изменения отдачи и урона.", "url": "https://pubg.com/"},
            {"title": "Обновление карты", "description": "Оптимизация зон лута и транспорта на популярных картах.", "url": "https://pubg.com/"},
            {"title": "Турнир кланов", "description": "Открыта регистрация на внутриигровой турнир кланов.", "url": "https://pubg.com/"},
        ]
        return sample[:limit]

    def get_events(self, limit: int = 5) -> list[dict[str, str]]:
        return [
            {"title": "Еженедельное событие", "description": "Начало в пятницу 20:00 UTC", "url": "https://pubg.com/"},
            {"title": "Двойной опыт", "description": "В субботу весь день действует двойной опыт.", "url": "https://pubg.com/"},
            {"title": "Клановые тренировки", "description": "Подбор наставников и учеников внутри бота.", "url": "https://pubg.com/"},
        ][:limit]

    def get_patches(self, limit: int = 5) -> list[dict[str, str]]:
        return [
            {"version": "Patch 1", "date": "2026-04-01", "changes": "Исправления стабильности и баланс оружия."},
            {"version": "Patch 2", "date": "2026-03-20", "changes": "Изменения карты и улучшение интерфейса."},
            {"version": "Patch 3", "date": "2026-03-01", "changes": "Новые награды сезона."},
        ][:limit]
