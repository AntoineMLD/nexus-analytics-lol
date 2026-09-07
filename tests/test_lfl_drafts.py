"""Unit tests for pipeline/silver_transforms/lfl_drafts.py.

All GCS and Discord calls are mocked — no network or cloud access required.
"""

from unittest.mock import MagicMock, patch

import pytest

from pipeline.silver_transforms.lfl_drafts import (
    cast_int,
    find_latest_bronze_date,
    get_lfl_overview_pages,
    transform_rows,
    unpivot_draft_row,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_row(**overrides) -> dict:
    """Build a minimal PicksAndBansS7 Bronze row."""
    base = {
        "GameId": "LFL/2024 Season/Summer Season/Week 1/1",
        "MatchId": "LFL/2024 Season/Summer Season/Week 1",
        "OverviewPage": "LFL/2024 Season/Summer Season",
        "Team1": "Vitality Bee",
        "Team2": "LDLC OL",
        "Winner": "1",
        "Team1Score": "1",
        "Team2Score": "0",
        "Team1Ban1": "Yone",
        "Team1Ban2": "Orianna",
        "Team1Ban3": "Jinx",
        "Team1Ban4": "",
        "Team1Ban5": "",
        "Team1Pick1": "Azir",
        "Team1Pick2": "Thresh",
        "Team1Pick3": "Nautilus",
        "Team1Pick4": "Caitlyn",
        "Team1Pick5": "Garen",
        "Team2Ban1": "Sylas",
        "Team2Ban2": "Viktor",
        "Team2Ban3": "Lucian",
        "Team2Ban4": "",
        "Team2Ban5": "",
        "Team2Pick1": "Jhin",
        "Team2Pick2": "Renekton",
        "Team2Pick3": "Vex",
        "Team2Pick4": "Leona",
        "Team2Pick5": "Darius",
        "N_GameInMatch": "1",
        "N_GameInPage": "1",
    }
    base.update(overrides)
    return base


LFL_TOURNAMENTS = [
    {"OverviewPage": "LFL/2024 Season/Summer Season", "League": "La Ligue Française"},
    {"OverviewPage": "LFL/2024 Season/Spring Season", "League": "La Ligue Française"},
    {"OverviewPage": "LEC/2024 Season/Summer Season", "League": "LEC"},
]


# ─── cast_int ─────────────────────────────────────────────────────────────────


class TestCastInt:
    def test_valid_string(self):
        assert cast_int("3") == 3

    def test_zero(self):
        assert cast_int("0") == 0

    def test_none(self):
        assert cast_int(None) is None

    def test_empty_string(self):
        assert cast_int("") is None

    def test_non_numeric(self):
        assert cast_int("abc") is None

    def test_float_string(self):
        # Floats should fail because int() on "1.5" raises ValueError
        assert cast_int("1.5") is None


# ─── get_lfl_overview_pages ───────────────────────────────────────────────────


class TestGetLflOverviewPages:
    def test_returns_only_lfl_pages(self):
        pages = get_lfl_overview_pages(LFL_TOURNAMENTS)
        assert "LFL/2024 Season/Summer Season" in pages
        assert "LEC/2024 Season/Summer Season" not in pages

    def test_includes_d2(self):
        tournaments = [
            {"OverviewPage": "LFL2/2024/Summer", "League": "La Ligue Française Division 2"},
        ]
        pages = get_lfl_overview_pages(tournaments)
        assert "LFL2/2024/Summer" in pages

    def test_empty_list(self):
        assert get_lfl_overview_pages([]) == set()

    def test_no_lfl_tournaments(self):
        pages = get_lfl_overview_pages([{"OverviewPage": "LEC/2024", "League": "LEC"}])
        assert len(pages) == 0


# ─── unpivot_draft_row ────────────────────────────────────────────────────────


class TestUnpivotDraftRow:
    def test_full_row_returns_16_actions(self):
        """3 bans + 5 picks per team = 16 actions total (Team1Ban4/5 and Team2Ban4/5 are empty)."""
        row = _make_row()
        actions = unpivot_draft_row(row)
        assert len(actions) == 16

    def test_picks_are_typed_correctly(self):
        row = _make_row()
        actions = unpivot_draft_row(row)
        ban_actions = [a for a in actions if a["action_type"] == "ban"]
        pick_actions = [a for a in actions if a["action_type"] == "pick"]
        assert len(ban_actions) == 6  # 3 bans per team
        assert len(pick_actions) == 10  # 5 picks per team

    def test_team_side_is_correct(self):
        row = _make_row()
        actions = unpivot_draft_row(row)
        team1_actions = [a for a in actions if a["team_side"] == 1]
        team2_actions = [a for a in actions if a["team_side"] == 2]
        assert len(team1_actions) == 8  # 3 bans + 5 picks
        assert len(team2_actions) == 8

    def test_team_name_is_assigned(self):
        row = _make_row()
        actions = unpivot_draft_row(row)
        team1_actions = [a for a in actions if a["team_side"] == 1]
        assert all(a["team_name"] == "Vitality Bee" for a in team1_actions)

    def test_first_ban_is_team1_ban1(self):
        row = _make_row()
        actions = unpivot_draft_row(row)
        team1_bans = [a for a in actions if a["team_side"] == 1 and a["action_type"] == "ban"]
        assert team1_bans[0]["champion"] == "Yone"
        assert team1_bans[0]["action_order"] == 1

    def test_action_order_increments_per_side_and_type(self):
        row = _make_row()
        actions = unpivot_draft_row(row)
        team1_bans = sorted(
            [a for a in actions if a["team_side"] == 1 and a["action_type"] == "ban"],
            key=lambda a: a["action_order"],
        )
        assert [a["action_order"] for a in team1_bans] == [1, 2, 3]

    def test_empty_champion_is_skipped(self):
        """Team1Ban4 and Team1Ban5 are empty — should not appear in output."""
        row = _make_row()
        actions = unpivot_draft_row(row)
        champions = [a["champion"] for a in actions]
        assert "" not in champions

    def test_full_draft_10_bans(self):
        """If all 5 bans for both teams are filled, 10 ban actions returned."""
        row = _make_row(
            Team1Ban4="Lux",
            Team1Ban5="Ahri",
            Team2Ban4="Yasuo",
            Team2Ban5="Katarina",
        )
        actions = unpivot_draft_row(row)
        ban_actions = [a for a in actions if a["action_type"] == "ban"]
        assert len(ban_actions) == 10

    def test_game_id_is_propagated(self):
        row = _make_row()
        actions = unpivot_draft_row(row)
        assert all(a["game_id"] == row["GameId"] for a in actions)

    def test_winner_cast_to_int(self):
        row = _make_row(Winner="2")
        actions = unpivot_draft_row(row)
        assert all(a["winner"] == 2 for a in actions)

    def test_n_game_in_match_cast_to_int(self):
        row = _make_row()
        actions = unpivot_draft_row(row)
        assert all(a["n_game_in_match"] == 1 for a in actions)

    def test_champion_stripped_of_whitespace(self):
        row = _make_row(Team1Ban1="  Yone  ")
        actions = unpivot_draft_row(row)
        ban1 = next(a for a in actions if a["team_side"] == 1 and a["action_order"] == 1)
        assert ban1["champion"] == "Yone"

    def test_missing_game_id(self):
        row = _make_row(GameId=None)
        actions = unpivot_draft_row(row)
        assert all(a["game_id"] is None for a in actions)

    def test_all_empty_champions_returns_empty_list(self):
        row = _make_row(
            Team1Ban1="",
            Team1Ban2="",
            Team1Ban3="",
            Team1Ban4="",
            Team1Ban5="",
            Team1Pick1="",
            Team1Pick2="",
            Team1Pick3="",
            Team1Pick4="",
            Team1Pick5="",
            Team2Ban1="",
            Team2Ban2="",
            Team2Ban3="",
            Team2Ban4="",
            Team2Ban5="",
            Team2Pick1="",
            Team2Pick2="",
            Team2Pick3="",
            Team2Pick4="",
            Team2Pick5="",
        )
        actions = unpivot_draft_row(row)
        assert actions == []

    def test_n_game_in_match_fallback_with_space(self):
        """Cargo API sometimes returns 'N GameInMatch' (with space) instead of 'N_GameInMatch'."""
        row = _make_row()
        row.pop("N_GameInMatch", None)
        row["N GameInMatch"] = "3"
        actions = unpivot_draft_row(row)
        assert all(a["n_game_in_match"] == 3 for a in actions)


# ─── transform_rows ───────────────────────────────────────────────────────────


class TestTransformRows:
    def test_filters_non_lfl_rows(self):
        lfl_row = _make_row()
        other_row = _make_row(
            OverviewPage="LEC/2024 Season/Summer Season",
            GameId="LEC/2024/g1",
        )
        lfl_pages = {"LFL/2024 Season/Summer Season"}
        actions = transform_rows([lfl_row, other_row], lfl_pages)
        game_ids = {a["game_id"] for a in actions}
        assert "LEC/2024/g1" not in game_ids

    def test_empty_input(self):
        actions = transform_rows([], {"LFL/2024 Season/Summer Season"})
        assert actions == []

    def test_multiple_games_are_all_unpivoted(self):
        row1 = _make_row(GameId="game_1")
        row2 = _make_row(GameId="game_2")
        lfl_pages = {"LFL/2024 Season/Summer Season"}
        actions = transform_rows([row1, row2], lfl_pages)
        game_ids = {a["game_id"] for a in actions}
        assert game_ids == {"game_1", "game_2"}

    def test_no_lfl_pages_returns_empty(self):
        row = _make_row()
        actions = transform_rows([row], set())
        assert actions == []


# ─── find_latest_bronze_date ──────────────────────────────────────────────────


class TestFindLatestBronzeDate:
    @patch("pipeline.silver_transforms.lfl_drafts.gcs_client")
    def test_returns_latest_date(self, mock_gcs_client):
        blob1 = MagicMock()
        blob1.name = "bronze/leaguepedia/PicksAndBansS7/2026-05-01.json"
        blob2 = MagicMock()
        blob2.name = "bronze/leaguepedia/PicksAndBansS7/2026-07-01.json"

        mock_bucket = MagicMock()
        mock_bucket.list_blobs.return_value = [blob1, blob2]
        mock_gcs_client.return_value.__enter__.return_value.bucket.return_value = mock_bucket

        date = find_latest_bronze_date("my-bucket", "PicksAndBansS7")
        assert date == "2026-07-01"

    @patch("pipeline.silver_transforms.lfl_drafts.gcs_client")
    def test_raises_file_not_found_when_empty(self, mock_gcs_client):
        mock_bucket = MagicMock()
        mock_bucket.list_blobs.return_value = []
        mock_gcs_client.return_value.__enter__.return_value.bucket.return_value = mock_bucket

        with pytest.raises(FileNotFoundError):
            find_latest_bronze_date("my-bucket", "PicksAndBansS7")
