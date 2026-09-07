"""Unit tests for pipeline/silver_transforms/lfl_player_stats.py."""

import json
from unittest.mock import MagicMock, patch

from pipeline.silver_transforms.lfl_player_stats import (
    cast_int,
    filter_lfl_rows,
    get_lfl_overview_pages,
    normalize_row,
    parse_datetime,
    parse_player_win,
    run_transform,
    transform_rows,
)

PATCH_GCS = "pipeline.silver_transforms.lfl_player_stats.gcs_client"
PATCH_SETTINGS = "pipeline.silver_transforms.lfl_player_stats.settings"
PATCH_DISCORD = "pipeline.silver_transforms.lfl_player_stats.send_discord_notification"


# ---------------------------------------------------------------------------
# parse_player_win
# ---------------------------------------------------------------------------


class TestParsePlayerWin:
    def test_yes_returns_true(self):
        assert parse_player_win("Yes") is True

    def test_no_returns_false(self):
        assert parse_player_win("No") is False

    def test_none_returns_none(self):
        assert parse_player_win(None) is None

    def test_unexpected_value_returns_none(self):
        assert parse_player_win("maybe") is None


# ---------------------------------------------------------------------------
# parse_datetime
# ---------------------------------------------------------------------------


class TestParseDatetime:
    def test_standard_format(self):
        result = parse_datetime("2026-01-15 18:00:00")
        assert result == "2026-01-15T18:00:00+00:00"

    def test_none_returns_none(self):
        assert parse_datetime(None) is None

    def test_malformed_returns_none(self):
        assert parse_datetime("not-a-date") is None


# ---------------------------------------------------------------------------
# cast_int
# ---------------------------------------------------------------------------


class TestCastInt:
    def test_valid_string(self):
        assert cast_int("10") == 10

    def test_none_returns_none(self):
        assert cast_int(None) is None

    def test_empty_string_returns_none(self):
        assert cast_int("") is None


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
            "DateTime_UTC": "2026-01-15 18:00:00",
            "Team": "Karmine Corp",
            "TeamVs": "Team Vitality",
            "Link": "Caliste",
            "Name": "Caliste",
            "Champion": "Azir",
            "Role": "Mid",
            "Side": "Blue",
            "PlayerWin": "Yes",
            "Kills": "5",
            "Deaths": "1",
            "Assists": "8",
            "Gold": "14500",
            "CS": "280",
            "DamageToChampions": "25000",
            "VisionScore": "30",
        }

    def test_string_fields_preserved(self):
        result = normalize_row(self._make_row())
        assert result["champion"] == "Azir"
        assert result["role"] == "Mid"
        assert result["side"] == "Blue"

    def test_player_win_is_boolean(self):
        result = normalize_row(self._make_row())
        assert result["player_win"] is True

    def test_player_loss_is_false(self):
        row = self._make_row()
        row["PlayerWin"] = "No"
        result = normalize_row(row)
        assert result["player_win"] is False

    def test_numeric_fields_cast(self):
        result = normalize_row(self._make_row())
        assert result["kills"] == 5
        assert result["deaths"] == 1
        assert result["gold"] == 14500
        assert result["cs"] == 280

    def test_datetime_parsed(self):
        result = normalize_row(self._make_row())
        assert result["datetime_utc"] == "2026-01-15T18:00:00+00:00"

    def test_missing_fields_become_none(self):
        result = normalize_row({"GameId": "abc"})
        assert result["kills"] is None
        assert result["player_win"] is None
        assert result["champion"] is None


# ---------------------------------------------------------------------------
# transform_rows
# ---------------------------------------------------------------------------


class TestTransformRows:
    def test_returns_one_row_per_input(self):
        rows = [{"GameId": "g1"}, {"GameId": "g2"}]
        assert len(transform_rows(rows)) == 2

    def test_empty_input(self):
        assert transform_rows([]) == []


# ---------------------------------------------------------------------------
# get_lfl_overview_pages
# ---------------------------------------------------------------------------


class TestGetLflOverviewPages:
    def test_returns_only_lfl_pages(self):
        tournaments = [
            {"OverviewPage": "LFL/2026/Spring", "League": "La Ligue Française"},
            {"OverviewPage": "LFL2/2026/Spring", "League": "La Ligue Française Division 2"},
            {"OverviewPage": "LCS/2026/Spring", "League": "LCS"},
        ]
        result = get_lfl_overview_pages(tournaments)
        assert result == {"LFL/2026/Spring", "LFL2/2026/Spring"}

    def test_empty_tournaments_returns_empty_set(self):
        assert get_lfl_overview_pages([]) == set()


# ---------------------------------------------------------------------------
# filter_lfl_rows
# ---------------------------------------------------------------------------


class TestFilterLflRows:
    def test_keeps_only_lfl_rows(self):
        rows = [
            {"OverviewPage": "LFL/2026/Spring", "GameId": "g1"},
            {"OverviewPage": "LCS/2026/Spring", "GameId": "g2"},
        ]
        result = filter_lfl_rows(rows, {"LFL/2026/Spring"})
        assert len(result) == 1
        assert result[0]["GameId"] == "g1"

    def test_empty_rows_returns_empty(self):
        assert filter_lfl_rows([], {"LFL/2026/Spring"}) == []

    def test_raises_if_non_empty_input_all_filtered_out(self):
        """Bronze file ingested without LFL WHERE clause — must raise instead of silent empty write."""
        corrupted_rows = [
            {"OverviewPage": "2012 MLG Pro Circuit/Fall/Championship", "GameId": "g1"},
            {"OverviewPage": "2014 GPL Spring", "GameId": "g2"},
        ]
        import pytest

        with pytest.raises(ValueError, match="Re-ingest ScoreboardPlayers"):
            filter_lfl_rows(corrupted_rows, {"LFL/2026/Spring"})


# ---------------------------------------------------------------------------
# run_transform (integration with mocked GCS)
# ---------------------------------------------------------------------------

TOURNAMENT_ROW = {"OverviewPage": "LFL/2026/Spring", "League": "La Ligue Française"}

BRONZE_PLAYER_ROW = {
    "GameId": "LOLTMNT99/12345",
    "MatchId": "LOLTMNT99/M1",
    "OverviewPage": "LFL/2026/Spring",
    "Tournament": "LFL 2026 Spring",
    "DateTime_UTC": "2026-01-15 18:00:00",
    "Team": "KC",
    "TeamVs": "VIT",
    "Link": "Caliste",
    "Name": "Caliste",
    "Champion": "Azir",
    "Role": "Mid",
    "Side": "Blue",
    "PlayerWin": "Yes",
    "Kills": "5",
    "Deaths": "1",
    "Assists": "8",
    "Gold": "14500",
    "CS": "280",
    "DamageToChampions": "25000",
    "VisionScore": "30",
}

NON_LFL_PLAYER_ROW = {**BRONZE_PLAYER_ROW, "OverviewPage": "LCS/2026/Spring"}


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
    def test_nominal_case_filters_and_uploads_lfl_rows(self):
        tournaments_ndjson = json.dumps(TOURNAMENT_ROW)
        players_ndjson = "\n".join([json.dumps(BRONZE_PLAYER_ROW), json.dumps(NON_LFL_PLAYER_ROW)])
        mock_ctx = _make_gcs_ctx([tournaments_ndjson, players_ndjson])

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
        assert uploaded_rows[0]["champion"] == "Azir"
        assert uploaded_rows[0]["kills"] == 5
        assert uploaded_rows[0]["player_win"] is True

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

    def test_no_matching_rows_sends_discord_error(self):
        tournaments_ndjson = json.dumps(TOURNAMENT_ROW)
        players_ndjson = json.dumps(NON_LFL_PLAYER_ROW)
        mock_ctx = _make_gcs_ctx([tournaments_ndjson, players_ndjson])

        with (
            patch(PATCH_GCS, return_value=mock_ctx),
            patch(PATCH_SETTINGS) as mock_settings,
            patch(PATCH_DISCORD) as mock_discord,
        ):
            mock_settings.gcs_bucket_name = "test-bucket"
            run_transform(date="2026-01-15")

        mock_discord.assert_called_once()
        assert ":x:" in mock_discord.call_args[0][0]
