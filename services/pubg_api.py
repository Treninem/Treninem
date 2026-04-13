"""Клиент для работы с PUBG API и новостями о PUBG.

ВАЖНО:
- Официальный PUBG API хорошо подходит для статистики игроков.
- Для новостей отдельного официального PUBG REST API нет, поэтому здесь используется
  публичная лента новостей Steam для PUBG с fallback-парсингом.
- В коде предусмотрены гибкие fallback-ветки, чтобы бот оставался рабочим при неполных данных.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from config.constants import (
    MENTOR_MIN_RANK_NAMES,
    NEWS_CATEGORY_EVENT_KEYWORDS,
    NEWS_CATEGORY_PATCH_KEYWORDS,
)
from config.credentials import PUBG_API_KEY
from config.settings import DEFAULT_PUBG_SHARD

logger = logging.getLogger("bot_pubg.pubg_api")


class PUBGAPIError(Exception):
    """Ошибка PUBG API."""


@dataclass
class PlayerProfile:
    player_id: str
    nickname: str
    rank: str
    kd: str | None
    shard: str


@dataclass
class ExtendedPlayerProfile(PlayerProfile):
    """Расширенный профиль игрока, собранный из нескольких PUBG endpoint'ов."""

    level: int | None
    total_matches: int
    total_wins: int
    total_kills: int
    total_damage: float
    headshot_kills: int
    avg_damage: float | None
    win_rate: float | None
    top10s: int
    raw_stats: dict[str, Any]


class PUBGAPIClient:
    """Упрощённый клиент PUBG API."""

    def __init__(self, api_key: str = PUBG_API_KEY, timeout: int = 15) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/vnd.api+json",
            }
        )

    def _base(self, shard: str = DEFAULT_PUBG_SHARD) -> str:
        return f"https://api.pubg.com/shards/{shard}"

    def _request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            if response.status_code >= 400:
                raise PUBGAPIError(f"PUBG API error {response.status_code}: {response.text[:500]}")
            return response.json()
        except requests.RequestException as exc:
            raise PUBGAPIError(f"Network error: {exc}") from exc

    def _fetch_players(self, *, shard: str, player_names: list[str] | None = None, player_ids: list[str] | None = None) -> list[dict[str, Any]]:
        url = f"{self._base(shard)}/players"
        params: dict[str, str] = {}
        if player_names:
            params["filter[playerNames]"] = ",".join(player_names)
        if player_ids:
            params["filter[playerIds]"] = ",".join(player_ids)
        data = self._request("GET", url, params=params)
        return data.get("data", [])

    def find_player_by_name(self, player_name: str, shard: str = DEFAULT_PUBG_SHARD) -> PlayerProfile:
        """Найти игрока по имени, получить player_id и базовые данные."""
        items = self._fetch_players(shard=shard, player_names=[player_name])
        if not items:
            raise PUBGAPIError("Игрок не найден в PUBG API")

        player = items[0]
        player_id = player["id"]
        nickname = player.get("attributes", {}).get("name") or player_name

        rank = self.detect_player_rank(player_id, shard=shard)
        kd = self.get_lifetime_kd(player_id, shard=shard)

        return PlayerProfile(
            player_id=player_id,
            nickname=nickname,
            rank=rank,
            kd=kd,
            shard=shard,
        )

    def find_player_by_id(self, player_id: str, shard: str = DEFAULT_PUBG_SHARD) -> PlayerProfile:
        """Найти игрока по PUBG player ID."""
        items = self._fetch_players(shard=shard, player_ids=[player_id])
        if not items:
            raise PUBGAPIError("Игрок по PUBG ID не найден")

        player = items[0]
        nickname = player.get("attributes", {}).get("name") or player_id
        rank = self.detect_player_rank(player_id, shard=shard)
        kd = self.get_lifetime_kd(player_id, shard=shard)
        return PlayerProfile(
            player_id=player_id,
            nickname=nickname,
            rank=rank,
            kd=kd,
            shard=shard,
        )

    def resolve_player_profile(self, value: str, shard: str = DEFAULT_PUBG_SHARD) -> ExtendedPlayerProfile:
        """Разрешить игрока по нику или PUBG player ID и вернуть расширенный профиль."""
        value = value.strip()
        if value.startswith("account."):
            return self.get_extended_profile_by_id(value, shard=shard)
        return self.get_extended_profile_by_name(value, shard=shard)

    def get_seasons(self, shard: str = DEFAULT_PUBG_SHARD) -> list[dict[str, Any]]:
        url = f"{self._base(shard)}/seasons"
        data = self._request("GET", url)
        return data.get("data", [])

    def get_current_season_id(self, shard: str = DEFAULT_PUBG_SHARD) -> str | None:
        seasons = self.get_seasons(shard=shard)
        for item in seasons:
            attrs = item.get("attributes", {})
            if attrs.get("isCurrentSeason"):
                return item.get("id")
        return None

    def get_lifetime_stats(self, player_id: str, shard: str = DEFAULT_PUBG_SHARD) -> dict[str, Any]:
        url = f"{self._base(shard)}/players/{player_id}/seasons/lifetime"
        return self._request("GET", url)

    def get_lifetime_kd(self, player_id: str, shard: str = DEFAULT_PUBG_SHARD) -> str | None:
        """Посчитать K/D из lifetime-статистики, если данные доступны."""
        try:
            aggregated = self.get_lifetime_summary(player_id, shard=shard)
            if aggregated["total_matches"] <= 0:
                return None
            return aggregated["kd"]
        except Exception as exc:  # pragma: no cover
            logger.warning("Не удалось вычислить lifetime K/D: %s", exc)
        return None

    def get_ranked_stats(
        self,
        player_id: str,
        shard: str = DEFAULT_PUBG_SHARD,
        season_id: str | None = None,
    ) -> dict[str, Any]:
        """Получить ranked-статистику игрока за текущий сезон."""
        if season_id is None:
            season_id = self.get_current_season_id(shard=shard)
        if not season_id:
            return {}

        url = f"{self._base(shard)}/players/{player_id}/seasons/{season_id}/ranked"
        try:
            return self._request("GET", url)
        except PUBGAPIError:
            return {}

    def detect_player_rank(self, player_id: str, shard: str = DEFAULT_PUBG_SHARD) -> str:
        """Определить текстовый ранг игрока.

        Алгоритм:
        1. Пытаемся взять currentTier/subTier из ranked.
        2. Если ranked-данных нет, возвращаем fallback-текст.
        """
        ranked = self.get_ranked_stats(player_id, shard=shard)
        attributes = ranked.get("data", {}).get("attributes", {})
        ranked_game_mode_stats = attributes.get("rankedGameModeStats", {})

        for _mode_name, item in ranked_game_mode_stats.items():
            current_tier = item.get("currentTier", {})
            tier = (current_tier.get("tier") or "").strip()
            sub_tier = (current_tier.get("subTier") or "").strip()
            if tier:
                return f"{tier.title()} {sub_tier}".strip()

        return "Unranked"

    def is_mentor_rank(self, rank_name: str | None) -> bool:
        """Проверить, допускается ли ранг к роли наставника.

        Замечание:
        официальная терминология рангов в разных PUBG-продуктах отличается,
        поэтому проверка сделана по ключевым словам.
        """
        if not rank_name:
            return False

        rank_lc = rank_name.lower()
        return any(item in rank_lc for item in MENTOR_MIN_RANK_NAMES)

    def _extract_level(self, *payloads: dict[str, Any]) -> int | None:
        """Попытаться достать уровень аккаунта из разных ответов API.

        Официальный PUBG API не всегда отдаёт уровень в одинаковом месте,
        поэтому идём по нескольким вероятным ключам и fallback-рекурсии.
        """
        candidate_keys = {"level", "survivalLevel", "survivalTitleLevel", "accountLevel"}
        found: list[int] = []

        def walk(node: Any):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key in candidate_keys and isinstance(value, (int, float)):
                        ivalue = int(value)
                        if 0 <= ivalue <= 100000:
                            found.append(ivalue)
                    walk(value)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        for payload in payloads:
            walk(payload)

        return max(found) if found else None

    def _aggregate_game_mode_stats(self, game_mode_stats: dict[str, Any]) -> dict[str, Any]:
        totals = {
            "roundsPlayed": 0.0,
            "wins": 0.0,
            "kills": 0.0,
            "losses": 0.0,
            "damageDealt": 0.0,
            "headshotKills": 0.0,
            "top10s": 0.0,
            "assists": 0.0,
            "revives": 0.0,
        }

        for _mode_name, stats in game_mode_stats.items():
            if not isinstance(stats, dict):
                continue
            for key in totals:
                try:
                    totals[key] += float(stats.get(key, 0) or 0)
                except (TypeError, ValueError):
                    continue

        total_matches = int(round(totals["roundsPlayed"]))
        total_wins = int(round(totals["wins"]))
        total_kills = int(round(totals["kills"]))
        total_damage = float(round(totals["damageDealt"], 2))
        headshot_kills = int(round(totals["headshotKills"]))
        top10s = int(round(totals["top10s"]))
        losses = max(int(round(totals["losses"])), 1)

        kd = f"{(total_kills / losses):.2f}" if total_kills or losses else None
        win_rate = round((total_wins / total_matches) * 100, 2) if total_matches else None
        avg_damage = round(total_damage / total_matches, 2) if total_matches else None

        return {
            "total_matches": total_matches,
            "total_wins": total_wins,
            "total_kills": total_kills,
            "total_damage": total_damage,
            "headshot_kills": headshot_kills,
            "top10s": top10s,
            "kd": kd,
            "win_rate": win_rate,
            "avg_damage": avg_damage,
            "totals": totals,
        }

    def get_lifetime_summary(self, player_id: str, shard: str = DEFAULT_PUBG_SHARD) -> dict[str, Any]:
        """Вернуть агрегированную lifetime-статистику по всем доступным режимам."""
        lifetime = self.get_lifetime_stats(player_id, shard=shard)
        attributes = lifetime.get("data", {}).get("attributes", {})
        game_mode_stats = attributes.get("gameModeStats", {})
        aggregated = self._aggregate_game_mode_stats(game_mode_stats)
        aggregated["level"] = self._extract_level(lifetime)
        aggregated["raw_stats"] = {
            "lifetime": attributes,
            "gameModeStats": game_mode_stats,
        }
        return aggregated

    def _build_extended_profile(
        self,
        *,
        player_id: str,
        nickname: str,
        shard: str,
    ) -> ExtendedPlayerProfile:
        lifetime_summary = self.get_lifetime_summary(player_id, shard=shard)
        ranked = self.get_ranked_stats(player_id, shard=shard)
        rank = self.detect_player_rank(player_id, shard=shard)
        level = self._extract_level(lifetime_summary.get("raw_stats", {}), ranked) or lifetime_summary.get("level")

        raw_stats = {
            "lifetime": lifetime_summary.get("raw_stats", {}),
            "ranked": ranked,
        }

        return ExtendedPlayerProfile(
            player_id=player_id,
            nickname=nickname,
            rank=rank,
            kd=lifetime_summary.get("kd"),
            shard=shard,
            level=level,
            total_matches=lifetime_summary.get("total_matches", 0),
            total_wins=lifetime_summary.get("total_wins", 0),
            total_kills=lifetime_summary.get("total_kills", 0),
            total_damage=lifetime_summary.get("total_damage", 0.0),
            headshot_kills=lifetime_summary.get("headshot_kills", 0),
            avg_damage=lifetime_summary.get("avg_damage"),
            win_rate=lifetime_summary.get("win_rate"),
            top10s=lifetime_summary.get("top10s", 0),
            raw_stats=raw_stats,
        )

    def get_extended_profile_by_name(self, player_name: str, shard: str = DEFAULT_PUBG_SHARD) -> ExtendedPlayerProfile:
        items = self._fetch_players(shard=shard, player_names=[player_name])
        if not items:
            raise PUBGAPIError("Игрок не найден в PUBG API")

        player = items[0]
        player_id = player["id"]
        nickname = player.get("attributes", {}).get("name") or player_name
        return self._build_extended_profile(player_id=player_id, nickname=nickname, shard=shard)

    def get_extended_profile_by_id(self, player_id: str, shard: str = DEFAULT_PUBG_SHARD) -> ExtendedPlayerProfile:
        items = self._fetch_players(shard=shard, player_ids=[player_id])
        if not items:
            raise PUBGAPIError("Игрок по PUBG ID не найден")

        player = items[0]
        nickname = player.get("attributes", {}).get("name") or player_id
        return self._build_extended_profile(player_id=player_id, nickname=nickname, shard=shard)

    def fetch_latest_news(self, count: int = 5) -> list[dict[str, Any]]:
        """Получить свежие новости по PUBG.

        Используем публичный Steam news API для appid 578080.
        """
        url = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
        params = {
            "appid": 578080,
            "count": count,
            "maxlength": 300,
            "format": "json",
        }
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            items = response.json().get("appnews", {}).get("newsitems", [])
        except requests.RequestException as exc:
            logger.warning("Steam news API недоступен: %s", exc)
            return []

        result: list[dict[str, Any]] = []
        for item in items:
            title = item.get("title", "Без заголовка")
            description = item.get("contents", "").strip()
            url = item.get("url", "")
            published = item.get("date")
            published_dt = (
                datetime.fromtimestamp(int(published), tz=timezone.utc).replace(tzinfo=None)
                if published
                else None
            )
            category = self._guess_news_category(title=title, description=description)
            result.append(
                {
                    "title": title,
                    "description": description[:500],
                    "url": url,
                    "published_at": published_dt,
                    "category": category,
                }
            )
        return result

    def _guess_news_category(self, title: str, description: str) -> str:
        text = f"{title} {description}".lower()
        if any(keyword in text for keyword in NEWS_CATEGORY_PATCH_KEYWORDS):
            return "patch"
        if any(keyword in text for keyword in NEWS_CATEGORY_EVENT_KEYWORDS):
            return "event"
        return "news"


pubg_client = PUBGAPIClient()
