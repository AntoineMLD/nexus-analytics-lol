"""Unit tests for ingestion/leaguepedia/ingest.py.

External calls (Leaguepedia Cargo API, GCS, Discord) are mocked so these tests
run offline without any credentials.
"""

from unittest.mock import MagicMock, patch

from ingestion.leaguepedia.ingest import (
    fetch_all_rows,
    fetch_cargo_page,
    save_to_gcs,
)

PATCH_FETCH_CARGO_PAGE = "ingestion.leaguepedia.ingest.fetch_cargo_page"
PATCH_GCS_CLIENT = "ingestion.leaguepedia.ingest.gcs_client"
PATCH_VERIFY = "ingestion.leaguepedia.ingest.verify_gcs_object_exists"
PATCH_DISCORD = "ingestion.leaguepedia.ingest.send_discord_notification"
PATCH_MAX_PAGE_SIZE = "ingestion.leaguepedia.ingest.MAX_PAGE_SIZE"

SAMPLE_ROWS = [{"field1": "value1"}]


def make_mock_site(query_return_value=None, query_side_effect=None):
    """Build a mock EsportsClient with a controllable cargo_client.query."""
    site = MagicMock()
    if query_side_effect is not None:
        site.cargo_client.query.side_effect = query_side_effect
    else:
        site.cargo_client.query.return_value = query_return_value or []
    return site


class TestFetchCargoPage:
    def test_successful_request_returns_rows(self):
        """Requête réussie → retourne la liste des résultats de l'API Cargo."""
        site = make_mock_site(query_return_value=SAMPLE_ROWS)
        rows = fetch_cargo_page(site, "Table", "field1", 100, 0)
        assert rows == SAMPLE_ROWS

    def test_request_error_returns_empty_list_and_notifies_discord(self):
        """Exception réseau → retourne [] et envoie une notification Discord."""
        site = make_mock_site(query_side_effect=Exception("connection failed"))
        with patch(PATCH_DISCORD) as mock_discord:
            rows = fetch_cargo_page(site, "Table", "field1", 100, 0)
        assert rows == []
        mock_discord.assert_called_once()
        assert ":x:" in mock_discord.call_args[0][0]

    def test_http_status_error_returns_empty_list_and_notifies_discord(self):
        """Erreur HTTP → retourne [] et envoie une notification Discord."""
        site = make_mock_site(query_side_effect=Exception("500 Internal Server Error"))
        with patch(PATCH_DISCORD) as mock_discord:
            rows = fetch_cargo_page(site, "Table", "field1", 100, 0)
        assert rows == []
        mock_discord.assert_called_once()
        assert ":x:" in mock_discord.call_args[0][0]


class TestFetchAllRows:
    def test_first_page_empty_returns_empty_list(self):
        """Première page vide → retourne [] sans rappeler l'API."""
        site = make_mock_site(query_return_value=[])
        with patch(PATCH_FETCH_CARGO_PAGE, return_value=[]) as mock_fetch:
            rows = fetch_all_rows(site, "Table", "field1", limit=10)
        assert rows == []
        mock_fetch.assert_called_once()

    def test_single_page_does_not_call_api_again(self):
        """Une seule page (moins de limit résultats) → l'API n'est appelée qu'une fois."""
        page_rows = [{"id": i} for i in range(3)]  # 3 < limit=5 → dernière page
        with patch(PATCH_FETCH_CARGO_PAGE, return_value=page_rows) as mock_fetch:
            rows = fetch_all_rows(MagicMock(), "Table", "field1", limit=5)
        assert rows == page_rows
        mock_fetch.assert_called_once()

    def test_two_pages_returns_all_rows_aggregated(self):
        """Deux pages → toutes les lignes des deux pages sont agrégées."""
        page1 = [{"id": i} for i in range(5)]  # 5 == limit → page suivante
        page2 = [{"id": i} for i in range(3)]  # 3 < limit → dernière page
        with patch(PATCH_FETCH_CARGO_PAGE, side_effect=[page1, page2]) as mock_fetch:
            rows = fetch_all_rows(MagicMock(), "Table", "field1", limit=5)
        assert len(rows) == 8
        assert mock_fetch.call_count == 2

    def test_reaches_max_page_size_stops_and_returns_collected_rows(self):
        """Atteint MAX_PAGE_SIZE → la boucle s'arrête et retourne les lignes collectées."""
        page_rows = [{"id": 0}]  # 1 row == limit=1 → toujours une page pleine
        with (
            patch(PATCH_FETCH_CARGO_PAGE, return_value=page_rows) as mock_fetch,
            patch(PATCH_MAX_PAGE_SIZE, new=2),
        ):
            rows = fetch_all_rows(MagicMock(), "Table", "field1", limit=1)
        # page=0 → continue, page=1 → continue, page=2 → 2 >= MAX_PAGE_SIZE=2 → break
        assert len(rows) == 3
        assert mock_fetch.call_count == 3


class TestSaveToGcs:
    def test_empty_rows_notifies_discord_and_does_not_upload(self):
        """rows vide → notification Discord :x: envoyée, aucun upload GCS."""
        with (
            patch(PATCH_GCS_CLIENT) as mock_gcs,
            patch(PATCH_DISCORD) as mock_discord,
        ):
            save_to_gcs([], "my-bucket", "test.json")
        mock_gcs.assert_not_called()
        mock_discord.assert_called_once()
        assert ":x:" in mock_discord.call_args[0][0]

    def test_successful_upload_sends_discord_success(self):
        """Upload réussi → notification Discord :white_check_mark: envoyée."""
        rows = [{"field1": "value1"}]
        with (
            patch(PATCH_GCS_CLIENT),
            patch(PATCH_VERIFY, return_value=True),
            patch(PATCH_DISCORD) as mock_discord,
        ):
            save_to_gcs(rows, "my-bucket", "test.json")
        mock_discord.assert_called_once()
        assert ":white_check_mark:" in mock_discord.call_args[0][0]

    def test_gcs_verification_failure_notifies_discord_error(self):
        """verify_gcs_object_exists retourne False → notification Discord :x: envoyée."""
        rows = [{"field1": "value1"}]
        with (
            patch(PATCH_GCS_CLIENT),
            patch(PATCH_VERIFY, return_value=False),
            patch(PATCH_DISCORD) as mock_discord,
        ):
            save_to_gcs(rows, "my-bucket", "test.json")
        mock_discord.assert_called_once()
        assert ":x:" in mock_discord.call_args[0][0]
