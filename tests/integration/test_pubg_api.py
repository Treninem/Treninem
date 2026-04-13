from services.pubg_api import PUBGAPIClient


class DummyResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = ""

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")


def test_fetch_latest_news(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return DummyResponse(
            payload={
                "appnews": {
                    "newsitems": [
                        {
                            "title": "Patch Notes 35.1",
                            "contents": "New update deployed.",
                            "url": "https://example.com/news",
                            "date": 1700000000,
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr("requests.get", fake_get)
    client = PUBGAPIClient(api_key="test-key")
    items = client.fetch_latest_news(count=1)
    assert len(items) == 1
    assert items[0]["category"] == "patch"


def test_resolve_player_profile_aggregates_stats(monkeypatch):
    player_payload = {
        "data": [
            {
                "id": "account.test123",
                "attributes": {
                    "name": "Tester",
                },
            }
        ]
    }
    lifetime_payload = {
        "data": {
            "attributes": {
                "gameModeStats": {
                    "solo": {
                        "roundsPlayed": 10,
                        "wins": 2,
                        "kills": 15,
                        "losses": 8,
                        "damageDealt": 2500,
                        "headshotKills": 3,
                        "top10s": 5,
                        "survivalLevel": 27,
                    },
                    "duo": {
                        "roundsPlayed": 20,
                        "wins": 4,
                        "kills": 30,
                        "losses": 16,
                        "damageDealt": 5000,
                        "headshotKills": 6,
                        "top10s": 10,
                    },
                }
            }
        }
    }
    ranked_payload = {
        "data": {
            "attributes": {
                "rankedGameModeStats": {
                    "squad": {
                        "currentTier": {"tier": "diamond", "subTier": "3"}
                    }
                }
            }
        }
    }

    def fake_request(self, method, url, timeout=None, params=None, **kwargs):
        if url.endswith("/players"):
            return DummyResponse(payload=player_payload)
        if url.endswith("/seasons"):
            return DummyResponse(payload={"data": [{"id": "season-1", "attributes": {"isCurrentSeason": True}}]})
        if url.endswith("/players/account.test123/seasons/lifetime"):
            return DummyResponse(payload=lifetime_payload)
        if url.endswith("/players/account.test123/seasons/season-1/ranked"):
            return DummyResponse(payload=ranked_payload)
        raise AssertionError(url)

    monkeypatch.setattr("requests.sessions.Session.request", fake_request)
    client = PUBGAPIClient(api_key="test-key")
    profile = client.resolve_player_profile("Tester")

    assert profile.player_id == "account.test123"
    assert profile.nickname == "Tester"
    assert profile.rank == "Diamond 3"
    assert profile.level == 27
    assert profile.total_matches == 30
    assert profile.total_wins == 6
    assert profile.total_kills == 45
    assert profile.headshot_kills == 9
    assert profile.top10s == 15
    assert profile.kd == "1.88"
