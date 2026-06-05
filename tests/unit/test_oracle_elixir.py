"""Unit tests for ingestion/oracle_elixir/ingest.py.

External calls (Drive API, GCS, Discord) are mocked so these tests
run offline without any credentials.
"""

import csv
import io
from unittest.mock import patch

from ingestion.oracle_elixir.ingest import (
    EXPECTED_COLUMNS,
    MIN_ROW_COUNT,
    build_file_name,
    build_gcs_destination,
    run_ingestion,
    validate_csv_content,
)

# Helpers


def make_csv_bytes(columns: list[str], row_count: int) -> bytes:
    """Build a minimal CSV in memory with the given columns and number of rows."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for i in range(row_count):
        writer.writerow({col: f"value_{i}" for col in columns})
    return buffer.getvalue().encode("utf-8")


VALID_COLUMNS = list(EXPECTED_COLUMNS) + ["extra_column"]
VALID_CSV = make_csv_bytes(VALID_COLUMNS, MIN_ROW_COUNT + 10)


# validate_csv_content


class TestValidateCsvContent:
    def test_valid_csv_returns_true_and_row_count(self):
        is_valid, error, row_count = validate_csv_content(
            VALID_CSV, EXPECTED_COLUMNS, MIN_ROW_COUNT
        )
        assert is_valid is True
        assert error == ""
        assert row_count == MIN_ROW_COUNT + 10

    def test_empty_content_returns_false(self):
        is_valid, error, row_count = validate_csv_content(b"", EXPECTED_COLUMNS, MIN_ROW_COUNT)
        assert is_valid is False
        assert "empty" in error.lower()
        assert row_count == 0

    def test_missing_column_returns_false(self):
        columns_without_one = VALID_COLUMNS[1:]  # drop first expected column
        csv_bytes = make_csv_bytes(columns_without_one, MIN_ROW_COUNT + 10)
        is_valid, error, row_count = validate_csv_content(
            csv_bytes, EXPECTED_COLUMNS, MIN_ROW_COUNT
        )
        assert is_valid is False
        assert "Missing" in error
        assert row_count == 0

    def test_too_few_rows_returns_false(self):
        csv_bytes = make_csv_bytes(VALID_COLUMNS, MIN_ROW_COUNT - 1)
        is_valid, error, row_count = validate_csv_content(
            csv_bytes, EXPECTED_COLUMNS, MIN_ROW_COUNT
        )
        assert is_valid is False
        assert "Too few rows" in error
        assert row_count == MIN_ROW_COUNT - 1


# run_ingestion — all external calls are mocked

# Base patch targets used in every run_ingestion test.
PATCH_BUILD = "ingestion.oracle_elixir.ingest.build"
PATCH_VERIFY = "ingestion.oracle_elixir.ingest.verify_gcs_object_exists"
PATCH_FIND = "ingestion.oracle_elixir.ingest.find_file_in_drive"
PATCH_DOWNLOAD = "ingestion.oracle_elixir.ingest.download_file_content"
PATCH_UPLOAD = "ingestion.oracle_elixir.ingest.upload_to_gcs_bronze"
PATCH_DISCORD = "ingestion.oracle_elixir.ingest.send_discord_notification"
PATCH_YEAR = "ingestion.oracle_elixir.ingest.get_current_year"


class TestRunIngestion:
    def test_historical_year_already_in_gcs_is_skipped(self):
        """A historical year already present in GCS must not trigger a download."""
        with (
            patch(PATCH_BUILD),
            patch(PATCH_YEAR, return_value=2026),
            patch(PATCH_VERIFY, return_value=True),
            patch(PATCH_FIND) as mock_find,
            patch(PATCH_DOWNLOAD) as mock_download,
            patch(PATCH_UPLOAD) as mock_upload,
            patch(PATCH_DISCORD),
        ):
            run_ingestion(year=2024)
            mock_find.assert_not_called()
            mock_download.assert_not_called()
            mock_upload.assert_not_called()

    def test_current_year_in_gcs_is_not_skipped(self):
        """The current year must always be re-ingested even if already in GCS."""
        with (
            patch(PATCH_BUILD),
            patch(PATCH_YEAR, return_value=2026),
            patch(PATCH_VERIFY, side_effect=[True, True]),  # exists before AND after
            patch(PATCH_FIND, return_value={"id": "file123", "name": "2026_...csv"}),
            patch(PATCH_DOWNLOAD, return_value=VALID_CSV),
            patch(PATCH_UPLOAD),
            patch(PATCH_DISCORD),
        ):
            run_ingestion(year=2026)

    def test_file_not_found_in_drive_notifies_discord(self):
        """If the file is missing in Drive, a Discord error notification must be sent."""
        with (
            patch(PATCH_BUILD),
            patch(PATCH_YEAR, return_value=2026),
            patch(PATCH_VERIFY, return_value=False),
            patch(PATCH_FIND, return_value=None),
            patch(PATCH_UPLOAD) as mock_upload,
            patch(PATCH_DISCORD) as mock_discord,
        ):
            run_ingestion(year=2026)
            mock_upload.assert_not_called()
            mock_discord.assert_called_once()
            assert ":x:" in mock_discord.call_args[0][0]

    def test_validation_failure_notifies_discord(self):
        """If the CSV content is invalid, a Discord error notification must be sent."""
        invalid_csv = b""  # empty → validation fails
        with (
            patch(PATCH_BUILD),
            patch(PATCH_YEAR, return_value=2026),
            patch(PATCH_VERIFY, return_value=False),
            patch(PATCH_FIND, return_value={"id": "file123", "name": "2026_...csv"}),
            patch(PATCH_DOWNLOAD, return_value=invalid_csv),
            patch(PATCH_UPLOAD) as mock_upload,
            patch(PATCH_DISCORD) as mock_discord,
        ):
            run_ingestion(year=2026)
            mock_upload.assert_not_called()
            mock_discord.assert_called_once()

    def test_gcs_verification_failure_after_upload_notifies_discord(self):
        """If GCS object is missing after upload, a Discord error notification must be sent."""
        with (
            patch(PATCH_BUILD),
            patch(PATCH_YEAR, return_value=2026),
            # First call: pre-upload check (not historical, so skipped anyway)
            # Second call: post-upload verification → object not found
            patch(PATCH_VERIFY, side_effect=[False, False]),
            patch(PATCH_FIND, return_value={"id": "file123", "name": "2026_...csv"}),
            patch(PATCH_DOWNLOAD, return_value=VALID_CSV),
            patch(PATCH_UPLOAD),
            patch(PATCH_DISCORD) as mock_discord,
        ):
            run_ingestion(year=2026)
            mock_discord.assert_called_once()
            assert ":x:" in mock_discord.call_args[0][0]

    def test_nominal_case_uploads_and_notifies_success(self):
        """Full happy path: file found, valid, uploaded, verified — success notification sent."""
        with (
            patch(PATCH_BUILD),
            patch(PATCH_YEAR, return_value=2026),
            patch(
                PATCH_VERIFY, return_value=True
            ),  # called once: post-upload check (pre-check skipped because is_historical=False)
            patch(PATCH_FIND, return_value={"id": "file123", "name": "2026_...csv"}),
            patch(PATCH_DOWNLOAD, return_value=VALID_CSV),
            patch(PATCH_UPLOAD) as mock_upload,
            patch(PATCH_DISCORD) as mock_discord,
        ):
            run_ingestion(year=2026)
            mock_upload.assert_called_once()
            mock_discord.assert_called_once()
            assert ":white_check_mark:" in mock_discord.call_args[0][0]


# build_file_name / build_gcs_destination


class TestHelpers:
    def test_build_file_name(self):
        assert build_file_name(2024) == "2024_LoL_esports_match_data_from_OraclesElixir.csv"

    def test_build_gcs_destination(self):
        name = build_file_name(2024)
        dest = build_gcs_destination(2024, name)
        assert (
            dest == "bronze/oracle_elixir/2024/2024_LoL_esports_match_data_from_OraclesElixir.csv"
        )
