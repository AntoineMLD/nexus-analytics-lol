"""Ingestion script for Leaguepedia Cargo API data.

Fetches rows from 9 Cargo tables using an authenticated EsportsClient (mwrogue)
and uploads each table as NDJSON to GCS Bronze layer.
GCS destination pattern: bronze/leaguepedia/{TableName}/{YYYY-MM-DD}.json

Usage:
    uv run python -m ingestion.leaguepedia.ingest              # all tables
    uv run python -m ingestion.leaguepedia.ingest --table ScoreboardGames
"""

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime

from mwcleric.auth_credentials import AuthCredentials
from mwrogue.esports_client import EsportsClient

from ingestion.leaguepedia.config import MAX_PAGE_SIZE, TABLE_CONFIGS
from ingestion.utils import (
    gcs_client,
    logger,
    send_discord_notification,
    settings,
    verify_gcs_object_exists,
)


def build_esports_client() -> EsportsClient:
    """Build an authenticated EsportsClient using Fandom bot credentials from settings."""
    credentials = AuthCredentials(
        username=settings.spideybot_fandom_name,
        password=settings.spideybot_fandom_password,
    )
    return EsportsClient("lol", credentials=credentials)


def fetch_cargo_page(
    site: EsportsClient,
    tables: str,
    fields: str,
    limit: int,
    offset: int,
    where: str = "",
) -> list[dict]:
    """Fetch a single page of results from the Leaguepedia Cargo API.

    Returns the list of row dicts, or [] on any error.
    """
    base_delay = 1
    multiplier = 2
    max_delay = 60
    max_retries = 6

    for attempt in range(max_retries + 1):
        try:
            return site.cargo_client.query(
                tables=tables,
                fields=fields,
                limit=limit,
                offset=offset,
                where=where,
            )
        except Exception as exc:
            is_ratelimited = "ratelimited" in str(exc).lower()
            if is_ratelimited and attempt < max_retries:
                wait = min(base_delay * (multiplier**attempt), max_delay)
                logger.warning(
                    "Rate limited — retrying in %ds (attempt %d/%d)...",
                    wait,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait)
                continue
            msg = f"Failed to fetch Cargo page (table={tables}, offset={offset}): {exc}"
            logger.error(msg)
            send_discord_notification(f":x: {msg}")
            return []

    return []


def fetch_all_rows(
    site: EsportsClient, tables: str, fields: str, limit: int, where: str = ""
) -> list[dict]:
    """Fetch all rows from a Cargo table by paginating until the last page.

    Stops early if the number of pages reaches MAX_PAGE_SIZE to avoid infinite loops.
    """
    all_rows = []
    offset = 0
    page = 0

    while True:
        rows = fetch_cargo_page(site, tables, fields, limit, offset, where)
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < limit:
            break
        if page >= MAX_PAGE_SIZE:
            logger.warning("Reached maximum number of pages (%d), stopping.", MAX_PAGE_SIZE)
            break
        offset += limit
        page += 1

    return all_rows


def save_to_gcs(rows: list[dict], bucket_name: str, file_name: str) -> None:
    """Serialize rows to NDJSON and upload to GCS Bronze layer.

    Sends a Discord notification on success or failure.
    The GCS destination is: bronze/leaguepedia/{file_name}
    """
    if not rows:
        msg = f"No rows to save: {file_name}"
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    content = "\n".join(json.dumps(dict(row)) for row in rows)
    destination = f"bronze/leaguepedia/{file_name}"
    metadata = {
        "source": "leaguepedia",
        "ingestion_date": datetime.now(UTC).isoformat(),
        "row_count": str(len(rows)),
        "size_bytes": str(len(content)),
        "md5": hashlib.md5(content.encode()).hexdigest(),
    }

    with gcs_client() as client:
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination)
        blob.metadata = metadata
        blob.upload_from_string(content, content_type="application/json")

    logger.info("Uploaded to gs://%s/%s", bucket_name, destination)

    if not verify_gcs_object_exists(bucket_name, destination):
        msg = f"GCS verification failed: object not found at gs://{bucket_name}/{destination}"
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    gcs_uri = f"gs://{bucket_name}/{destination}"
    msg = (
        f":white_check_mark: Ingestion success — {file_name}\n"
        f"URI: {gcs_uri}\n"
        f"Rows: {len(rows)} | Size: {len(content)} bytes | MD5: {metadata['md5']}"
    )
    logger.info(msg)
    send_discord_notification(msg)


def run_ingestion(table_names: list[str] | None = None) -> None:
    """Run ingestion for the given tables, or all configured tables if none specified.

    Creates a single authenticated EsportsClient shared across all tables.
    GCS destination: bronze/leaguepedia/{TableName}/{YYYY-MM-DD}.json

    Args:
        table_names: List of table names to ingest. Defaults to all tables in TABLE_CONFIGS.
    """
    site = build_esports_client()
    targets = table_names or list(TABLE_CONFIGS.keys())
    date_today = datetime.now(UTC).strftime("%Y-%m-%d")

    for table_name in targets:
        config = TABLE_CONFIGS[table_name]
        logger.info("Starting ingestion for table: %s", table_name)

        rows = fetch_all_rows(
            site=site,
            tables=table_name,
            fields=config["fields"],
            limit=config["limit"],
        )

        file_name = f"{table_name}/{date_today}.json"
        save_to_gcs(rows, settings.gcs_bucket_name, file_name)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Ingest Leaguepedia Cargo tables to GCS.")
    parser.add_argument(
        "--table",
        choices=list(TABLE_CONFIGS.keys()),
        default=None,
        help="Table to ingest (default: all tables).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_ingestion(table_names=[args.table] if args.table else None)
