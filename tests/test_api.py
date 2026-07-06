"""Tests for the Nexus Analytics FastAPI endpoints.

All BigQuery calls are mocked — no GCP credentials required.
Auth uses a fixed test key injected via the NEXUS_API_KEY env variable.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app

VALID_KEY = "test-key"
HEADERS = {"X-API-Key": VALID_KEY}

PLAYER_ROW = {
    "player_id": "Player:Rekkles",
    "player_name": "Rekkles",
    "total_games": 42,
    "win_rate_pct": 60.0,
    "avg_kills": 4.5,
    "avg_deaths": 1.2,
    "avg_assists": 7.8,
    "avg_cs": 230.1,
    "teams_played_for": 2,
    "avg_damage": 18000.0,
    "avg_vision_score": 30.5,
    "total_wins": 25,
}

MATCH_ROW = {
    "game_id": "LFLSP2025-1234",
    "match_id": "LFLSP2025-12",
    "overview_page": "LFL/2025 Season/Spring Split",
    "datetime_utc": "2025-03-01T15:00:00",
    "team1": "Karmine Corp",
    "team2": "Team BDS",
    "win_team": "Karmine Corp",
    "gamelength_seconds": 1800,
    "patch": "14.5",
    "n_game_in_match": 1,
}

CHAMPION_ROW = {
    "champion": "Yone",
    "total_games_played": 87,
    "total_picks": 90,
    "win_rate_pct": 52.3,
    "avg_kills": 4.2,
    "avg_deaths": 2.1,
    "avg_assists": 5.0,
    "picks_top": 60,
    "picks_jungle": 0,
    "picks_mid": 27,
    "picks_bot": 0,
    "picks_support": 0,
}

DRAFT_ACTION_ROW = {
    "game_id": "LFLSP2025-1234",
    "overview_page": "LFL/2025 Season/Spring Split",
    "datetime_utc": "2025-03-01T15:00:00",
    "patch": "14.5",
    "team_side": 1,
    "action_type": "ban",
    "action_order": 1,
    "champion": "Yone",
    "team_won": True,
}

META_TREND_ROW = {
    "overview_page": "LFL/2025 Season/Spring Split",
    "patch": "14.5",
    "champion": "Yone",
    "picks": 12,
    "wins": 7,
    "pick_rate_pct": 40.0,
    "win_rate_pct": 58.3,
}


@pytest.fixture
def client(monkeypatch):
    """TestClient with NEXUS_API_KEY set and BigQuery not called."""
    monkeypatch.setenv("NEXUS_API_KEY", VALID_KEY)
    # Re-load settings so the monkeypatched env var is picked up.
    from ingestion import utils as utils_module

    utils_module.settings.nexus_api_key = VALID_KEY
    return TestClient(app, raise_server_exceptions=True)


# ─── Health ──────────────────────────────────────────────────────────────────


class TestHealthCheck:
    def test_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ─── Authentication ───────────────────────────────────────────────────────────


class TestAuthentication:
    def test_missing_key_returns_401(self, client):
        response = client.get("/players")
        assert response.status_code == 401

    def test_wrong_key_returns_401(self, client):
        response = client.get("/players", headers={"X-API-Key": "wrong"})
        assert response.status_code == 401

    def test_valid_key_accepted(self, client):
        with patch("api.main.query_players", return_value=[]):
            response = client.get("/players", headers=HEADERS)
        assert response.status_code == 200


# ─── GET /players ─────────────────────────────────────────────────────────────


class TestListPlayers:
    def test_returns_player_list(self, client):
        with patch("api.main.query_players", return_value=[PLAYER_ROW]):
            response = client.get("/players", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["player_id"] == "Player:Rekkles"
        assert data[0]["total_games"] == 42

    def test_empty_list_is_valid(self, client):
        with patch("api.main.query_players", return_value=[]):
            response = client.get("/players", headers=HEADERS)
        assert response.status_code == 200
        assert response.json() == []

    def test_min_games_param_forwarded(self, client):
        mock_fn = MagicMock(return_value=[])
        with patch("api.main.query_players", mock_fn):
            client.get("/players?min_games=30&limit=10", headers=HEADERS)
        mock_fn.assert_called_once_with(min_games=30, limit=10, offset=0)

    def test_limit_above_200_rejected(self, client):
        response = client.get("/players?limit=500", headers=HEADERS)
        assert response.status_code == 422


# ─── GET /players/{player_id} ─────────────────────────────────────────────────


class TestGetPlayer:
    def test_returns_player_detail(self, client):
        with patch("api.main.query_player_by_id", return_value=PLAYER_ROW):
            response = client.get("/players/Player:Rekkles", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["player_name"] == "Rekkles"
        assert data["total_wins"] == 25

    def test_unknown_player_returns_404(self, client):
        with patch("api.main.query_player_by_id", return_value=None):
            response = client.get("/players/Player:Unknown", headers=HEADERS)
        assert response.status_code == 404

    def test_player_id_passed_correctly(self, client):
        mock_fn = MagicMock(return_value=PLAYER_ROW)
        with patch("api.main.query_player_by_id", mock_fn):
            client.get("/players/Player:Rekkles", headers=HEADERS)
        mock_fn.assert_called_once_with("Player:Rekkles")


# ─── GET /matches ─────────────────────────────────────────────────────────────


class TestListMatches:
    def test_returns_match_list(self, client):
        with patch("api.main.query_matches", return_value=[MATCH_ROW]):
            response = client.get("/matches", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["game_id"] == "LFLSP2025-1234"
        assert data[0]["win_team"] == "Karmine Corp"

    def test_team_filter_forwarded(self, client):
        mock_fn = MagicMock(return_value=[])
        with patch("api.main.query_matches", mock_fn):
            client.get("/matches?team=Karmine+Corp&season=LFL/2025", headers=HEADERS)
        mock_fn.assert_called_once_with(team="Karmine Corp", season="LFL/2025", limit=50, offset=0)

    def test_no_filters_returns_all(self, client):
        mock_fn = MagicMock(return_value=[MATCH_ROW])
        with patch("api.main.query_matches", mock_fn):
            response = client.get("/matches", headers=HEADERS)
        assert response.status_code == 200
        mock_fn.assert_called_once_with(team=None, season=None, limit=50, offset=0)

    def test_limit_above_200_rejected(self, client):
        response = client.get("/matches?limit=999", headers=HEADERS)
        assert response.status_code == 422


# ─── GET /meta/champion-stats ─────────────────────────────────────────────────


class TestListChampionStats:
    def test_returns_champion_list(self, client):
        with patch("api.main.query_champion_stats", return_value=[CHAMPION_ROW]):
            response = client.get("/meta/champion-stats", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["champion"] == "Yone"
        assert data[0]["total_games_played"] == 87
        assert data[0]["win_rate_pct"] == 52.3

    def test_empty_list_is_valid(self, client):
        with patch("api.main.query_champion_stats", return_value=[]):
            response = client.get("/meta/champion-stats", headers=HEADERS)
        assert response.status_code == 200
        assert response.json() == []

    def test_params_forwarded(self, client):
        mock_fn = MagicMock(return_value=[])
        with patch("api.main.query_champion_stats", mock_fn):
            client.get("/meta/champion-stats?min_games=10&limit=20&offset=5", headers=HEADERS)
        mock_fn.assert_called_once_with(min_games=10, limit=20, offset=5)

    def test_requires_auth(self, client):
        response = client.get("/meta/champion-stats")
        assert response.status_code == 401


# ─── GET /teams/{team}/draft-history ─────────────────────────────────────────


class TestGetTeamDraftHistory:
    def test_returns_draft_actions(self, client):
        with patch("api.main.query_team_draft_history", return_value=[DRAFT_ACTION_ROW]):
            response = client.get("/teams/Karmine%20Corp/draft-history", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["champion"] == "Yone"
        assert data[0]["action_type"] == "ban"
        assert data[0]["team_won"] is True

    def test_empty_list_is_valid(self, client):
        with patch("api.main.query_team_draft_history", return_value=[]):
            response = client.get("/teams/Karmine%20Corp/draft-history", headers=HEADERS)
        assert response.status_code == 200
        assert response.json() == []

    def test_filters_forwarded(self, client):
        mock_fn = MagicMock(return_value=[])
        with patch("api.main.query_team_draft_history", mock_fn):
            client.get(
                "/teams/Karmine%20Corp/draft-history?patch=14.5&action_type=ban",
                headers=HEADERS,
            )
        mock_fn.assert_called_once_with(
            team="Karmine Corp", patch="14.5", action_type="ban", limit=100, offset=0
        )

    def test_requires_auth(self, client):
        response = client.get("/teams/Karmine%20Corp/draft-history")
        assert response.status_code == 401


# ─── GET /meta/trends ────────────────────────────────────────────────────────


class TestListMetaTrends:
    def test_returns_trends(self, client):
        with patch("api.main.query_meta_trends", return_value=[META_TREND_ROW]):
            response = client.get("/meta/trends", headers=HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["champion"] == "Yone"
        assert data[0]["pick_rate_pct"] == 40.0
        assert data[0]["win_rate_pct"] == 58.3

    def test_empty_list_is_valid(self, client):
        with patch("api.main.query_meta_trends", return_value=[]):
            response = client.get("/meta/trends", headers=HEADERS)
        assert response.status_code == 200
        assert response.json() == []

    def test_patch_filter_forwarded(self, client):
        mock_fn = MagicMock(return_value=[])
        with patch("api.main.query_meta_trends", mock_fn):
            client.get("/meta/trends?patch=14.5&limit=30", headers=HEADERS)
        mock_fn.assert_called_once_with(patch="14.5", overview_page=None, limit=30, offset=0)

    def test_requires_auth(self, client):
        response = client.get("/meta/trends")
        assert response.status_code == 401
