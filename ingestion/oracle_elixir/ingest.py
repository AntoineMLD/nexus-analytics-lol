"""Ingestion script for Oracle's Elixir LoL esports match data.

Downloads the target year's CSV from Google Drive and uploads it to GCS Bronze layer.

Usage:
    uv run python ingestion/oracle_elixir/ingest.py           # current year
    uv run python ingestion/oracle_elixir/ingest.py --year 2024
"""

import argparse
import csv
import hashlib
import io
from datetime import UTC, datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from ingestion.utils import (
    gcs_client,
    logger,
    send_discord_notification,
    settings,
    verify_gcs_object_exists,
)

from .config import DRIVE_FOLDER_ID, EXPECTED_COLUMNS, MIN_ROW_COUNT


def get_current_year() -> int:
    """Return the current UTC year, evaluated at call time."""
    return datetime.now(UTC).year


def build_file_name(year: int) -> str:
    """Return the expected Drive file name for a given year."""
    return f"{year}_LoL_esports_match_data_from_OraclesElixir.csv"


def build_gcs_destination(year: int, file_name: str) -> str:
    """Return the GCS Bronze destination path for a given year."""
    return f"bronze/oracle_elixir/{year}/{file_name}"


def find_file_in_drive(service, folder_id: str, file_name: str) -> dict | None:
    """Search for a file by name inside a specific Google Drive folder.

    Returns the file metadata dict with keys (id, name), or None if not found.
    """
    query = f"'{folder_id}' in parents and name = '{file_name}' and trashed = false"
    response = service.files().list(q=query, fields="files(id, name)", pageSize=10).execute()
    files = response.get("files", [])
    return files[0] if files else None


def download_file_content(service, file_id: str) -> bytes:
    """Download the binary content of a Drive file by its ID.

    Uses chunked download to handle large files (100 MB+).
    """
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def validate_csv_content(
    content: bytes, expected_columns: set, min_rows: int
) -> tuple[bool, str, int]:
    """Validate that the CSV content is usable.

    Checks:
    - File is not empty
    - All expected columns are present
    - Number of data rows meets the minimum threshold

    Returns (is_valid, error_message, row_count).
    """
    if not content:
        return False, "File is empty.", 0

    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))

    headers = set(reader.fieldnames or [])
    missing_columns = expected_columns - headers
    if missing_columns:
        return False, f"Missing expected columns: {missing_columns}", 0

    row_count = sum(1 for _ in reader)
    if row_count < min_rows:
        return False, f"Too few rows: {row_count} (minimum {min_rows}).", row_count

    return True, "", row_count


def compute_metadata(content: bytes, year: int, row_count: int) -> dict:
    """Generate traceability metadata for the ingested file."""
    return {
        "source": "oracle_elixir",
        "year": str(year),
        "ingestion_date": datetime.now(UTC).isoformat(),
        "size_bytes": str(len(content)),
        "row_count": str(row_count),
        "md5": hashlib.md5(content).hexdigest(),
    }


def upload_to_gcs_bronze(
    bucket_name: str, destination: str, content: bytes, metadata: dict
) -> None:
    """Upload bytes content to GCS Bronze layer with traceability metadata."""
    with gcs_client() as client:
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination)
        blob.metadata = metadata
        blob.upload_from_string(content, content_type="text/csv")
    logger.info("Uploaded to gs://%s/%s", bucket_name, destination)


def run_ingestion(year: int | None = None) -> None:
    """Orchestrate the full ingestion pipeline for the target year.

    Args:
        year: The year to ingest. Defaults to the current UTC year.
    """
    current_year = get_current_year()
    if year is None:
        year = current_year

    file_name = build_file_name(year)
    gcs_destination = build_gcs_destination(year, file_name)

    logger.info("Starting ingestion for year %s", year)

    try:
        service = build("drive", "v3", developerKey=settings.api_key)
    except HttpError as exc:
        msg = f"Failed to connect to Drive API: {exc}"
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    # Historical years (< current year) are immutable: skip if already in GCS.
    # Current year is updated weekly by the source, so always re-ingest.
    is_historical = year < current_year
    if is_historical and verify_gcs_object_exists(settings.gcs_bucket_name, gcs_destination):
        logger.info(
            "Historical year already in GCS, skipping: gs://%s/%s",
            settings.gcs_bucket_name,
            gcs_destination,
        )
        return

    # Find the target year's file in the Drive folder
    file_meta = find_file_in_drive(service, DRIVE_FOLDER_ID, file_name)
    if not file_meta:
        msg = f"File not found in Drive: {file_name}"
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return
    logger.info("Found file: %s (id=%s)", file_meta["name"], file_meta["id"])

    # Download the raw file content
    logger.info("Downloading %s...", file_name)
    content = download_file_content(service, file_meta["id"])
    logger.info("Downloaded %d bytes", len(content))

    # Validate the content
    is_valid, error, row_count = validate_csv_content(content, EXPECTED_COLUMNS, MIN_ROW_COUNT)
    if not is_valid:
        msg = f"Validation failed for {file_name}: {error}"
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return
    logger.info("Validation passed — %d rows.", row_count)

    # Generate traceability metadata
    metadata = compute_metadata(content, year, row_count)
    logger.info("Metadata: %s", metadata)

    # Upload to GCS Bronze
    upload_to_gcs_bronze(settings.gcs_bucket_name, gcs_destination, content, metadata)

    # Verify the upload
    if not verify_gcs_object_exists(settings.gcs_bucket_name, gcs_destination):
        msg = f"GCS verification failed: object not found at gs://{settings.gcs_bucket_name}/{gcs_destination}"
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    # Success
    gcs_uri = f"gs://{settings.gcs_bucket_name}/{gcs_destination}"
    msg = (
        f":white_check_mark: Ingestion success — {file_name}\n"
        f"URI: {gcs_uri}\n"
        f"Rows: {row_count} | Size: {metadata['size_bytes']} bytes | MD5: {metadata['md5']}"
    )
    logger.info(msg)
    send_discord_notification(msg)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Ingest Oracle's Elixir match data to GCS.")
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Year to ingest (default: current UTC year).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Ingest all available years (2014 to current). Already loaded years are skipped.",
    )
    return parser.parse_args()


FIRST_AVAILABLE_YEAR = 2014


if __name__ == "__main__":
    args = parse_args()
    if args.all:
        for y in range(FIRST_AVAILABLE_YEAR, get_current_year() + 1):
            run_ingestion(year=y)
    else:
        run_ingestion(year=args.year)
