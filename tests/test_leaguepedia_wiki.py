"""Tests for ingestion/leaguepedia_wiki/ingest.py.

All GCS and wiki network calls are mocked.
"""

from unittest.mock import MagicMock, patch

import pytest

from ingestion.leaguepedia_wiki.ingest import (
    build_bronze_row,
    extract_riot_ids,
    fetch_player_wiki_data,
    find_latest_silver_date,
    load_player_names_from_silver,
    run_scraping,
    save_to_bronze,
)

# ─── extract_riot_ids ─────────────────────────────────────────────────────────


class TestExtractRiotIds:
    def test_single_id_no_hash(self):
        wikitext = "{{Infobox Player|ids=Caliste}}"
        assert extract_riot_ids(wikitext) == ["Caliste"]

    def test_single_riot_id_with_hash(self):
        wikitext = "{{Infobox|ids=Caliste#EUW}}"
        assert extract_riot_ids(wikitext) == ["Caliste#EUW"]

    def test_multiple_ids_comma_separated(self):
        wikitext = "|ids=Caliste#EUW, CalysteOP#EUW"
        assert extract_riot_ids(wikitext) == ["Caliste#EUW", "CalysteOP#EUW"]

    def test_multiple_ids_semicolon_separated(self):
        wikitext = "|ids=Player1#EUW;Player2#EUW"
        assert extract_riot_ids(wikitext) == ["Player1#EUW", "Player2#EUW"]

    def test_ids_field_absent(self):
        wikitext = "{{Infobox Player|name=Caliste|team=KC}}"
        assert extract_riot_ids(wikitext) == []

    def test_ids_field_empty(self):
        wikitext = "|ids=   "
        assert extract_riot_ids(wikitext) == []

    def test_strips_whitespace(self):
        wikitext = "|ids=  Caliste#EUW  ,  Other#EUW  "
        result = extract_riot_ids(wikitext)
        assert result == ["Caliste#EUW", "Other#EUW"]

    def test_ids_stops_at_next_pipe(self):
        wikitext = "|ids=Caliste#EUW|team=KarmineKorp"
        assert extract_riot_ids(wikitext) == ["Caliste#EUW"]

    def test_ids_stops_at_newline(self):
        wikitext = "|ids=Caliste#EUW\n|team=KC"
        assert extract_riot_ids(wikitext) == ["Caliste#EUW"]


# ─── fetch_player_wiki_data ───────────────────────────────────────────────────


class TestFetchPlayerWikiData:
    def _make_site(self, wikitext: str, page_exists: bool = True) -> MagicMock:
        page = MagicMock()
        page.exists = page_exists
        page.text.return_value = wikitext
        site = MagicMock()
        site.client.pages.__getitem__ = MagicMock(return_value=page)
        return site

    def test_returns_riot_ids_when_page_exists(self):
        site = self._make_site("|ids=Caliste#EUW")
        result = fetch_player_wiki_data(site, "Caliste")
        assert result["player"] == "Caliste"
        assert result["riot_ids"] == ["Caliste#EUW"]
        assert result["page_exists"] is True

    def test_returns_empty_when_page_not_found(self):
        site = self._make_site("", page_exists=False)
        result = fetch_player_wiki_data(site, "Unknown")
        assert result["riot_ids"] == []
        assert result["page_exists"] is False

    def test_returns_empty_on_redirect(self):
        site = self._make_site("#REDIRECT [[Some Page]]")
        result = fetch_player_wiki_data(site, "OldName")
        assert result["riot_ids"] == []
        assert result["page_exists"] is True

    def test_returns_empty_when_ids_field_absent(self):
        site = self._make_site("{{Infobox Player|name=Unknown|team=BDS}}")
        result = fetch_player_wiki_data(site, "Unknown")
        assert result["riot_ids"] == []

    def test_handles_exception_gracefully(self):
        site = MagicMock()
        site.client.pages.__getitem__.side_effect = Exception("Network error")
        result = fetch_player_wiki_data(site, "Caliste")
        assert result["player"] == "Caliste"
        assert result["riot_ids"] == []
        assert result["page_exists"] is False


# ─── build_bronze_row ─────────────────────────────────────────────────────────


class TestBuildBronzeRow:
    def test_adds_required_metadata_fields(self):
        player_data = {"player": "Caliste", "riot_ids": ["Caliste#EUW"], "page_exists": True}
        row = build_bronze_row(player_data, "2026-07-06T14:00:00+00:00")
        assert row["source"] == "leaguepedia_wiki"
        assert row["schema_version"] == "1"
        assert row["ingested_at"] == "2026-07-06T14:00:00+00:00"
        assert "md5" in row
        assert len(row["md5"]) == 32

    def test_md5_is_deterministic(self):
        player_data = {"player": "Caliste", "riot_ids": ["Caliste#EUW"], "page_exists": True}
        row1 = build_bronze_row(player_data, "2026-07-06T14:00:00")
        row2 = build_bronze_row(player_data, "2026-07-06T14:00:00")
        assert row1["md5"] == row2["md5"]

    def test_empty_riot_ids_produces_md5(self):
        player_data = {"player": "Unknown", "riot_ids": [], "page_exists": False}
        row = build_bronze_row(player_data, "2026-07-06T14:00:00")
        assert row["md5"] is not None


# ─── load_player_names_from_silver ────────────────────────────────────────────


class TestLoadPlayerNamesFromSilver:
    def test_returns_player_names(self):
        ndjson = (
            '{"player": "Caliste", "euw_accounts": []}\n{"player": "Saken", "euw_accounts": []}'
        )
        mock_blob = MagicMock()
        mock_blob.download_as_text.return_value = ndjson
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        with patch("ingestion.leaguepedia_wiki.ingest.gcs_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            result = load_player_names_from_silver("2026-06-04")

        assert result == ["Caliste", "Saken"]

    def test_skips_empty_lines(self):
        ndjson = '{"player": "Caliste", "euw_accounts": []}\n\n'
        mock_blob = MagicMock()
        mock_blob.download_as_text.return_value = ndjson
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        with patch("ingestion.leaguepedia_wiki.ingest.gcs_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            result = load_player_names_from_silver("2026-06-04")

        assert result == ["Caliste"]


# ─── find_latest_silver_date ──────────────────────────────────────────────────


class TestFindLatestSilverDate:
    def test_returns_most_recent_date(self):
        blob_a = MagicMock()
        blob_a.name = "silver/leaguepedia/lfl_players/2026-06-01.json"
        blob_b = MagicMock()
        blob_b.name = "silver/leaguepedia/lfl_players/2026-06-04.json"
        mock_client = MagicMock()
        mock_client.bucket.return_value.list_blobs.return_value = [blob_a, blob_b]

        with patch("ingestion.leaguepedia_wiki.ingest.gcs_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            result = find_latest_silver_date()

        assert result == "2026-06-04"

    def test_raises_if_no_file_found(self):
        mock_client = MagicMock()
        mock_client.bucket.return_value.list_blobs.return_value = []

        with patch("ingestion.leaguepedia_wiki.ingest.gcs_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            with pytest.raises(RuntimeError):
                find_latest_silver_date()


# ─── save_to_bronze ───────────────────────────────────────────────────────────


class TestSaveToBronze:
    def test_uploads_ndjson_to_correct_path(self):
        rows = [{"player": "Caliste", "riot_ids": ["Caliste#EUW"]}]
        mock_blob = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = MagicMock()
        mock_client.bucket.return_value = mock_bucket

        with patch("ingestion.leaguepedia_wiki.ingest.gcs_client") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=mock_client)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)
            path = save_to_bronze(rows, "2026-07-06")

        assert path == "bronze/leaguepedia_wiki/player_ids/2026-07-06.json"
        mock_bucket.blob.assert_called_once_with(
            "bronze/leaguepedia_wiki/player_ids/2026-07-06.json"
        )
        mock_blob.upload_from_string.assert_called_once()


# ─── run_scraping (integration) ───────────────────────────────────────────────


class TestRunScraping:
    def test_skips_if_bronze_already_exists(self):
        with patch("ingestion.leaguepedia_wiki.ingest.verify_gcs_object_exists", return_value=True):
            with patch(
                "ingestion.leaguepedia_wiki.ingest.load_player_names_from_silver"
            ) as mock_load:
                run_scraping("2026-07-06", "2026-06-04")
        mock_load.assert_not_called()

    def test_scrapes_all_players_with_delay(self):
        with (
            patch("ingestion.leaguepedia_wiki.ingest.verify_gcs_object_exists", return_value=False),
            patch(
                "ingestion.leaguepedia_wiki.ingest.load_player_names_from_silver",
                return_value=["Caliste", "Saken"],
            ),
            patch("ingestion.leaguepedia_wiki.ingest.build_esports_client") as mock_build,
            patch("ingestion.leaguepedia_wiki.ingest.save_to_bronze") as mock_save,
            patch("ingestion.leaguepedia_wiki.ingest.send_discord_notification"),
            patch("ingestion.leaguepedia_wiki.ingest.time.sleep") as mock_sleep,
        ):
            page = MagicMock()
            page.exists = True
            page.text.return_value = "|ids=Player#EUW"
            mock_build.return_value.client.pages.__getitem__ = MagicMock(return_value=page)

            run_scraping("2026-07-06", "2026-06-04")

        # 2 players → 2 sleeps
        assert mock_sleep.call_count == 2
        mock_sleep.assert_called_with(2)
        mock_save.assert_called_once()
        saved_rows = mock_save.call_args[0][0]
        assert len(saved_rows) == 2

    def test_limit_restricts_player_count(self):
        with (
            patch("ingestion.leaguepedia_wiki.ingest.verify_gcs_object_exists", return_value=False),
            patch(
                "ingestion.leaguepedia_wiki.ingest.load_player_names_from_silver",
                return_value=["P1", "P2", "P3", "P4", "P5"],
            ),
            patch("ingestion.leaguepedia_wiki.ingest.build_esports_client") as mock_build,
            patch("ingestion.leaguepedia_wiki.ingest.save_to_bronze") as mock_save,
            patch("ingestion.leaguepedia_wiki.ingest.send_discord_notification"),
            patch("ingestion.leaguepedia_wiki.ingest.time.sleep"),
        ):
            page = MagicMock()
            page.exists = True
            page.text.return_value = ""
            mock_build.return_value.client.pages.__getitem__ = MagicMock(return_value=page)

            run_scraping("2026-07-06", "2026-06-04", limit=2)

        saved_rows = mock_save.call_args[0][0]
        assert len(saved_rows) == 2
