"""Unit tests for ingestion/riot_api/ingest.py.

External calls (Riot API, GCS, Discord) are mocked so these tests
run offline without any credentials or network access.
"""

from unittest.mock import MagicMock, patch

from ingestion.riot_api.ingest import (
    fetch_puuid,
    fetch_ranked_match_ids,
    is_riot_id,
    parse_riot_id,
    run_ingestion,
)

# Patch targets

PATCH_LOAD_SILVER = "ingestion.riot_api.ingest.load_silver_lfl_players"
PATCH_UPLOAD = "ingestion.riot_api.ingest.upload_ndjson_to_gcs"
PATCH_DISCORD = "ingestion.riot_api.ingest.send_discord_notification"
PATCH_SLEEP = "ingestion.riot_api.ingest.time.sleep"
PATCH_HTTPX_GET = "ingestion.riot_api.ingest.httpx.get"

# is_riot_id


class TestIsRiotId:
    def test_valid_riot_id_with_euw_tag(self):
        assert is_riot_id("KC NEXT ADKING#EUW") is True

    def test_valid_riot_id_with_numeric_tag(self):
        assert is_riot_id("G2 Hans Sama#12838") is True

    def test_valid_riot_id_with_custom_tag(self):
        assert is_riot_id("monk mentality#kboom") is True

    def test_old_summoner_name_no_hash(self):
        assert is_riot_id("banger5") is False

    def test_old_summoner_name_with_server_suffix(self):
        assert is_riot_id("Achuu (EUW)") is False

    def test_empty_string(self):
        assert is_riot_id("") is False

    def test_hash_only_no_tag(self):
        assert is_riot_id("name#") is False

    def test_hash_only_no_name(self):
        assert is_riot_id("#EUW") is False


# parse_riot_id


class TestParseRiotId:
    def test_simple_tag(self):
        assert parse_riot_id("KC NEXT ADKING#EUW") == ("KC NEXT ADKING", "EUW")

    def test_numeric_tag(self):
        assert parse_riot_id("G2 Hans Sama#12838") == ("G2 Hans Sama", "12838")

    def test_hash_in_game_name_is_not_split(self):
        # rsplit with maxsplit=1 would keep # in name — but we use split with maxsplit=1
        # "Awful Things #Koala" → game_name="Awful Things ", tag_line="Koala"
        game_name, tag_line = parse_riot_id("Awful Things #Koala")
        assert tag_line == "Koala"
        assert "Awful Things" in game_name

    def test_strips_whitespace(self):
        game_name, tag_line = parse_riot_id("  Name  # TAG  ")
        assert game_name == "Name"
        assert tag_line == "TAG"


# fetch_puuid


class TestFetchPuuid:
    def test_returns_puuid_on_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "puuid": "abc123xyz",
            "gameName": "Test",
            "tagLine": "EUW",
        }

        with patch(PATCH_HTTPX_GET, return_value=mock_response):
            result = fetch_puuid("Test", "EUW", "fake-api-key")

        assert result == "abc123xyz"

    def test_returns_none_on_404(self):
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch(PATCH_HTTPX_GET, return_value=mock_response):
            result = fetch_puuid("Unknown", "EUW", "fake-api-key")

        assert result is None

    def test_returns_none_on_http_error(self):
        import httpx as _httpx

        with patch(PATCH_HTTPX_GET, side_effect=_httpx.RequestError("connection refused")):
            result = fetch_puuid("Test", "EUW", "fake-api-key")

        assert result is None


# fetch_ranked_match_ids


class TestFetchRankedMatchIds:
    def test_returns_match_ids_on_success(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ["EUW1_111", "EUW1_222", "EUW1_333"]

        with patch(PATCH_HTTPX_GET, return_value=mock_response):
            result = fetch_ranked_match_ids("puuid_abc", "fake-api-key")

        assert result == ["EUW1_111", "EUW1_222", "EUW1_333"]

    def test_returns_empty_list_on_http_error(self):
        import httpx as _httpx

        with patch(PATCH_HTTPX_GET, side_effect=_httpx.RequestError("timeout")):
            result = fetch_ranked_match_ids("puuid_abc", "fake-api-key")

        assert result == []


# run_ingestion


SILVER_DATA = [
    {"player": "Caliste", "euw_accounts": ["KC NEXT ADKING#EUW", "I NEED SOLOQ#EUW"]},
    {"player": "Agresivoo", "euw_accounts": ["banger5", "agrsv"]},  # old format, skipped
    {"player": "Hans Sama", "euw_accounts": ["G2 Hans Sama#12838"]},
]


class TestRunIngestion:
    def test_nominal_case_processes_valid_riot_ids_only(self):
        """Only accounts with #tag format should be fetched — old names are skipped."""
        with (
            patch(PATCH_LOAD_SILVER, return_value=SILVER_DATA),
            patch("ingestion.riot_api.ingest.fetch_puuid", return_value="puuid_abc") as mock_puuid,
            patch("ingestion.riot_api.ingest.fetch_ranked_match_ids", return_value=["EUW1_1"]),
            patch(PATCH_UPLOAD) as mock_upload,
            patch(PATCH_DISCORD),
            patch(PATCH_SLEEP),
        ):
            run_ingestion(silver_date="2026-06-05")

        # 3 valid Riot IDs (2 for Caliste, 1 for Hans Sama), 0 for Agresivoo
        assert mock_puuid.call_count == 3
        mock_upload.assert_called_once()
        records = mock_upload.call_args[0][2]
        assert len(records) == 3

    def test_no_valid_riot_ids_notifies_discord_and_aborts(self):
        """If no account has a valid Riot ID format, Discord is notified and nothing is uploaded."""
        old_format_only = [
            {"player": "Agresivoo", "euw_accounts": ["banger5", "agrsv"]},
        ]
        with (
            patch(PATCH_LOAD_SILVER, return_value=old_format_only),
            patch(PATCH_UPLOAD) as mock_upload,
            patch(PATCH_DISCORD) as mock_discord,
            patch(PATCH_SLEEP),
        ):
            run_ingestion(silver_date="2026-06-05")

        mock_upload.assert_not_called()
        mock_discord.assert_called_once()
        assert ":x:" in mock_discord.call_args[0][0]

    def test_account_not_found_stores_null_puuid(self):
        """If PUUID fetch returns None, the record is stored with puuid=null and no match IDs."""
        with (
            patch(
                PATCH_LOAD_SILVER,
                return_value=[{"player": "Caliste", "euw_accounts": ["KC NEXT ADKING#EUW"]}],
            ),
            patch("ingestion.riot_api.ingest.fetch_puuid", return_value=None),
            patch("ingestion.riot_api.ingest.fetch_ranked_match_ids") as mock_matches,
            patch(PATCH_UPLOAD) as mock_upload,
            patch(PATCH_DISCORD),
            patch(PATCH_SLEEP),
        ):
            run_ingestion(silver_date="2026-06-05")

        mock_matches.assert_not_called()
        records = mock_upload.call_args[0][2]
        assert records[0]["puuid"] is None
        assert records[0]["ranked_match_ids"] == []

    def test_success_notification_contains_counts(self):
        """Discord success notification must include account counts."""
        with (
            patch(PATCH_LOAD_SILVER, return_value=SILVER_DATA),
            patch("ingestion.riot_api.ingest.fetch_puuid", return_value="puuid_abc"),
            patch("ingestion.riot_api.ingest.fetch_ranked_match_ids", return_value=[]),
            patch(PATCH_UPLOAD),
            patch(PATCH_DISCORD) as mock_discord,
            patch(PATCH_SLEEP),
        ):
            run_ingestion(silver_date="2026-06-05")

        message = mock_discord.call_args[0][0]
        assert ":white_check_mark:" in message
        assert "3" in message  # 3 accounts processed
