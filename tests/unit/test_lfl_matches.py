"""Unit tests for pipeline/silver_transforms/lfl_matches.py."""

import json
from unittest.mock import MagicMock, patch

from pipeline.silver_transforms.lfl_matches import (
    cast_int,
    filter_lfl_games,
    get_lfl_overview_pages,
    normalize_row,
    parse_datetime,
    parse_gamelength_seconds,
    run_transform,
    transform_rows,
)

PATCH_GCS = "pipeline.silver_transforms.lfl_matches.gcs_client"
PATCH_SETTINGS = "pipeline.silver_transforms.lfl_matches.settings"
PATCH_DISCORD = "pipeline.silver_transforms.lfl_matches.send_discord_notification"


# ---------------------------------------------------------------------------
# parse_gamelength_seconds
# ---------------------------------------------------------------------------


class TestParseGamelengthSeconds:
    def test_standard_format(self):
        assert parse_gamelength_seconds("32:15") == 1935

    def test_zero_seconds(self):
        assert parse_gamelength_seconds("0:00") == 0

    def test_none_returns_none(self):
        assert parse_gamelength_seconds(None) is None

    def test_empty_string_returns_none(self):
        assert parse_gamelength_seconds("") is None

    def test_malformed_returns_none(self):
        assert parse_gamelength_seconds("badvalue") is None


# ---------------------------------------------------------------------------
# parse_datetime
# ---------------------------------------------------------------------------


class TestParseDatetime:
    def test_standard_leaguepedia_format(self):
        result = parse_datetime("2026-01-15 18:00:00")
        assert result == "2026-01-15T18:00:00+00:00"

    def test_format_with_timezone_suffix(self):
        result = parse_datetime("2026-01-15 18:00:00+00:00")
        assert result == "2026-01-15T18:00:00+00:00"

    def test_none_returns_none(self):
        assert parse_datetime(None) is None

    def test_empty_string_returns_none(self):
        assert parse_datetime("") is None

    def test_malformed_returns_none(self):
        assert parse_datetime("not-a-date") is None


# ---------------------------------------------------------------------------
# cast_int
# ---------------------------------------------------------------------------


class TestCastInt:
    def test_valid_string(self):
        assert cast_int("42") == 42

    def test_none_returns_none(self):
        assert cast_int(None) is None

    def test_empty_string_returns_none(self):
        assert cast_int("") is None

    def test_non_numeric_returns_none(self):
        assert cast_int("abc") is None

    def test_zero(self):
        assert cast_int("0") == 0


# ---------------------------------------------------------------------------
# normalize_row
# ---------------------------------------------------------------------------


class TestNormalizeRow:
    def _make_row(self) -> dict:
        return {
            "GameId": "LOLTMNT99/12345",
            "MatchId": "LOLTMNT99/MATCH1",
            "OverviewPage": "LFL/2026 Season/Spring Season",
            "Tournament": "LFL 2026 Spring",
            "Patch": "14.5",
            "DateTime_UTC": "2026-01-15 18:00:00",
            "Team1": "Karmine Corp",
            "Team2": "Team Vitality",
            "WinTeam": "Karmine Corp",
            "LossTeam": "Team Vitality",
            "Gamelength": "32:15",
            "Gamelength_Number": "32.25",
            "Team1Score": "1",
            "Team2Score": "0",
            "Winner": "1",
            "Team1Dragons": "3",
            "Team2Dragons": "1",
            "Team1Barons": "1",
            "Team2Barons": "0",
            "Team1Towers": "9",
            "Team2Towers": "3",
            "Team1Gold": "58000",
            "Team2Gold": "48000",
            "Team1Kills": "15",
            "Team2Kills": "5",
            "Team1RiftHeralds": "1",
            "Team2RiftHeralds": "0",
            "Team1VoidGrubs": "3",
            "Team2VoidGrubs": "2",
            "Team1Inhibitors": "1",
            "Team2Inhibitors": "0",
            "N_GameInMatch": "1",
        }

    def test_string_fields_preserved(self):
        result = normalize_row(self._make_row())
        assert result["game_id"] == "LOLTMNT99/12345"
        assert result["team1"] == "Karmine Corp"
        assert result["patch"] == "14.5"

    def test_datetime_parsed(self):
        result = normalize_row(self._make_row())
        assert result["datetime_utc"] == "2026-01-15T18:00:00+00:00"

    def test_gamelength_seconds_computed(self):
        result = normalize_row(self._make_row())
        assert result["gamelength_seconds"] == 1935

    def test_int_fields_cast(self):
        result = normalize_row(self._make_row())
        assert result["team1_gold"] == 58000
        assert result["team1_kills"] == 15
        assert result["n_game_in_match"] == 1

    def test_missing_optional_fields_become_none(self):
        row = {"GameId": "abc"}
        result = normalize_row(row)
        assert result["team1_gold"] is None
        assert result["gamelength_seconds"] is None
        assert result["datetime_utc"] is None


# ---------------------------------------------------------------------------
# transform_rows
# ---------------------------------------------------------------------------


class TestTransformRows:
    def test_returns_one_row_per_input(self):
        rows = [{"GameId": "g1"}, {"GameId": "g2"}]
        result = transform_rows(rows)
        assert len(result) == 2

    def test_empty_input(self):
        assert transform_rows([]) == []


# ---------------------------------------------------------------------------
# get_lfl_overview_pages
# ---------------------------------------------------------------------------


class TestGetLflOverviewPages:
    def test_returns_lfl_pages(self):
        tournaments = [
            {"OverviewPage": "LFL/2026/Spring", "League": "La Ligue Française"},
            {"OverviewPage": "LFL2/2026/Spring", "League": "La Ligue Française Division 2"},
            {"OverviewPage": "LCS/2026/Spring", "League": "LCS"},
        ]
        result = get_lfl_overview_pages(tournaments)
        assert result == {"LFL/2026/Spring", "LFL2/2026/Spring"}

    def test_includes_emea_masters(self):
        tournaments = [
            {"OverviewPage": "LFL/2026/Spring", "League": "La Ligue Française"},
            {
                "OverviewPage": "EMEA Masters/2026 Season/Spring Main Event",
                "League": "EMEA Masters",
            },
            {"OverviewPage": "LCS/2026/Spring", "League": "LCS"},
        ]
        result = get_lfl_overview_pages(tournaments)
        assert result == {"LFL/2026/Spring", "EMEA Masters/2026 Season/Spring Main Event"}

    def test_empty_tournaments_returns_empty_set(self):
        assert get_lfl_overview_pages([]) == set()

    def test_no_target_leagues_returns_empty_set(self):
        tournaments = [{"OverviewPage": "LCS/2026", "League": "LCS"}]
        assert get_lfl_overview_pages(tournaments) == set()


# ---------------------------------------------------------------------------
# filter_lfl_games
# ---------------------------------------------------------------------------


class TestFilterLflGames:
    def test_keeps_only_lfl_games(self):
        rows = [
            {"OverviewPage": "LFL/2026/Spring", "GameId": "g1"},
            {"OverviewPage": "LCS/2026/Spring", "GameId": "g2"},
            {"OverviewPage": "LFL2/2026/Spring", "GameId": "g3"},
        ]
        lfl_pages = {"LFL/2026/Spring", "LFL2/2026/Spring"}
        result = filter_lfl_games(rows, lfl_pages)
        assert len(result) == 2
        assert all(r["OverviewPage"] in lfl_pages for r in result)

    def test_empty_rows_returns_empty(self):
        assert filter_lfl_games([], {"LFL/2026/Spring"}) == []

    def test_empty_lfl_pages_returns_empty(self):
        rows = [{"OverviewPage": "LFL/2026/Spring"}]
        assert filter_lfl_games(rows, set()) == []


# ---------------------------------------------------------------------------
# run_transform (integration with mocked GCS)
# ---------------------------------------------------------------------------

TOURNAMENT_ROW = {"OverviewPage": "LFL/2026/Spring", "League": "La Ligue Française"}

BRONZE_GAME_ROW = {
    "GameId": "LOLTMNT99/12345",
    "MatchId": "LOLTMNT99/M1",
    "OverviewPage": "LFL/2026/Spring",
    "Tournament": "LFL 2026 Spring",
    "Patch": "14.5",
    "DateTime_UTC": "2026-01-15 18:00:00",
    "Team1": "KC",
    "Team2": "VIT",
    "WinTeam": "KC",
    "LossTeam": "VIT",
    "Gamelength": "30:00",
    "Gamelength_Number": "30",
    "Team1Score": "1",
    "Team2Score": "0",
    "Winner": "1",
    "Team1Gold": "55000",
    "Team2Gold": "45000",
    "Team1Kills": "12",
    "Team2Kills": "4",
    "Team1Dragons": "3",
    "Team2Dragons": "0",
    "Team1Barons": "1",
    "Team2Barons": "0",
    "Team1Towers": "9",
    "Team2Towers": "2",
    "Team1RiftHeralds": "1",
    "Team2RiftHeralds": "1",
    "Team1VoidGrubs": "4",
    "Team2VoidGrubs": "2",
    "Team1Inhibitors": "1",
    "Team2Inhibitors": "0",
    "N_GameInMatch": "1",
}

NON_LFL_GAME_ROW = {**BRONZE_GAME_ROW, "OverviewPage": "LCS/2026/Spring", "GameId": "g_lcs"}


def _make_gcs_ctx(download_side_effects: list[str]):
    """Build a GCS context manager that returns different content per call."""
    mock_blob = MagicMock()
    mock_blob.download_as_text.side_effect = download_side_effects
    mock_bucket = MagicMock()
    mock_bucket.blob.return_value = mock_blob
    mock_client = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_client)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    return mock_ctx


class TestRunTransform:
    def test_nominal_case_filters_and_uploads_lfl_games(self):
        tournaments_ndjson = json.dumps(TOURNAMENT_ROW)
        games_ndjson = "\n".join([json.dumps(BRONZE_GAME_ROW), json.dumps(NON_LFL_GAME_ROW)])
        mock_ctx = _make_gcs_ctx([tournaments_ndjson, games_ndjson])

        with (
            patch(PATCH_GCS, return_value=mock_ctx),
            patch(PATCH_SETTINGS) as mock_settings,
            patch(PATCH_DISCORD),
        ):
            mock_settings.gcs_bucket_name = "test-bucket"
            run_transform(date="2026-01-15")

        upload_call = mock_ctx.__enter__.return_value.bucket().blob().upload_from_string
        upload_call.assert_called_once()
        uploaded_content = upload_call.call_args[0][0]
        uploaded_rows = [json.loads(line) for line in uploaded_content.splitlines()]
        assert len(uploaded_rows) == 1
        assert uploaded_rows[0]["game_id"] == "LOLTMNT99/12345"
        assert uploaded_rows[0]["gamelength_seconds"] == 1800

    def test_no_lfl_tournaments_sends_discord_error(self):
        non_lfl_tournament = json.dumps({"OverviewPage": "LCS/2026", "League": "LCS"})
        mock_ctx = _make_gcs_ctx([non_lfl_tournament])

        with (
            patch(PATCH_GCS, return_value=mock_ctx),
            patch(PATCH_SETTINGS) as mock_settings,
            patch(PATCH_DISCORD) as mock_discord,
        ):
            mock_settings.gcs_bucket_name = "test-bucket"
            run_transform(date="2026-01-15")

        mock_discord.assert_called_once()
        assert ":x:" in mock_discord.call_args[0][0]

    def test_no_matching_games_sends_discord_error(self):
        tournaments_ndjson = json.dumps(TOURNAMENT_ROW)
        games_ndjson = json.dumps(NON_LFL_GAME_ROW)
        mock_ctx = _make_gcs_ctx([tournaments_ndjson, games_ndjson])

        with (
            patch(PATCH_GCS, return_value=mock_ctx),
            patch(PATCH_SETTINGS) as mock_settings,
            patch(PATCH_DISCORD) as mock_discord,
        ):
            mock_settings.gcs_bucket_name = "test-bucket"
            run_transform(date="2026-01-15")

        mock_discord.assert_called_once()
        assert ":x:" in mock_discord.call_args[0][0]
