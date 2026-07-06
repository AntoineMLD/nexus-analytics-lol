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
import sys
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

LFL_LEAGUES = {"La Ligue Française", "La Ligue Française Division 2"}


def load_lfl_overview_pages(bucket_name: str) -> set[str]:
    """Load the most recent Tournaments Bronze file from GCS and return LFL OverviewPage values.

    Lists all files under bronze/leaguepedia/Tournaments/ and picks the latest one.
    Used to build a WHERE clause for tables that need LFL-only ingestion
    (ScoreboardGames, ScoreboardPlayers) without relying on a Cargo table join.

    The mwcleric Cargo join is silently ignored by the MediaWiki API because
    it expects the parameter 'join on' (with space) but receives 'join_on'.
    """
    prefix = "bronze/leaguepedia/Tournaments/"
    with gcs_client() as client:
        blobs = list(client.bucket(bucket_name).list_blobs(prefix=prefix))

    if not blobs:
        logger.warning("No Tournaments Bronze file found under gs://%s/%s.", bucket_name, prefix)
        return set()

    latest_blob = max(blobs, key=lambda b: b.name)
    logger.info("Using Tournaments Bronze file: gs://%s/%s", bucket_name, latest_blob.name)

    with gcs_client() as client:
        content = (
            client.bucket(bucket_name).blob(latest_blob.name).download_as_text(encoding="utf-8")
        )

    rows = [json.loads(line) for line in content.splitlines() if line.strip()]
    lfl_pages = {row["OverviewPage"] for row in rows if row.get("League") in LFL_LEAGUES}
    logger.info("Loaded %d LFL OverviewPages from Tournaments Bronze.", len(lfl_pages))
    return lfl_pages


def build_overview_page_filter(pages: set[str]) -> str:
    """Build a Cargo WHERE clause filtering by OverviewPage IN (...).

    Escapes single quotes in page names and sorts for deterministic output.

    Example:
        {"LFL/2026/Spring", "LFL/2025/Summer"} →
        "OverviewPage IN ('LFL/2025/Summer','LFL/2026/Spring')"
    """
    escaped = sorted("'" + p.replace("'", "\\'") + "'" for p in pages)
    return f"OverviewPage IN ({','.join(escaped)})"


def build_esports_client() -> EsportsClient:
    """Build an authenticated EsportsClient using Fandom bot credentials from settings."""
    credentials = AuthCredentials(
        username=settings.fandom_bot_name,
        password=settings.fandom_bot_password,
    )
    return EsportsClient("lol", credentials=credentials)


def fetch_cargo_page(
    site: EsportsClient,
    tables: str,
    fields: str,
    limit: int,
    offset: int,
    where: str = "",
    join_on: str = "",
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
                join_on=join_on,
            )
        except Exception as exc:
            exc_str = str(exc).lower()
            is_retriable = (
                "ratelimited" in exc_str or "timeout" in exc_str or "connection" in exc_str
            )
            if is_retriable and attempt < max_retries:
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


SLEEP_BETWEEN_PAGES = 2.0


def fetch_all_rows(
    site: EsportsClient,
    tables: str,
    fields: str,
    limit: int,
    where: str = "",
    join_on: str = "",
) -> list[dict]:
    """Fetch all rows from a Cargo table by paginating until the last page.

    Sleeps between pages to stay within Leaguepedia rate limits.
    Stops early if the number of pages reaches MAX_PAGE_SIZE to avoid infinite loops.
    """
    all_rows = []
    offset = 0
    page = 0

    while True:
        rows = fetch_cargo_page(site, tables, fields, limit, offset, where, join_on)
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
        time.sleep(SLEEP_BETWEEN_PAGES)

    return all_rows


def fetch_lfl_filtered_table(
    site: EsportsClient,
    tables: str,
    fields: str,
    lfl_pages: set[str],
    order_by: str,
) -> list[dict]:
    """Fetch all rows for an LFL-filtered table using mwcleric's auto_continue.

    Instead of our own pagination loop (which triggers rate limits with many
    small requests), this delegates pagination to mwcleric's built-in
    auto_continue mechanism. mwcleric uses limit='max' server-side (up to 5000
    rows per HTTP request) and handles offset increments internally — resulting
    in far fewer API calls than our manual 500-row pages.

    The order_by parameter ensures stable pagination (without ORDER BY, Cargo
    can return duplicate or missing rows when paginating).

    Args:
        site: Authenticated EsportsClient.
        tables: Cargo table name(s).
        fields: Comma-separated field list.
        lfl_pages: Set of LFL tournament OverviewPage values for the WHERE clause.
        order_by: Field to sort by for stable pagination (e.g. 'DateTime_UTC').
    """
    where = build_overview_page_filter(lfl_pages)
    logger.info(
        "Fetching %s with auto_continue (WHERE covers %d LFL pages, order_by=%s)...",
        tables,
        len(lfl_pages),
        order_by,
    )
    try:
        rows = site.cargo_client.query(
            tables=tables,
            fields=fields,
            where=where,
            order_by=order_by,
            # No limit → mwcleric sets auto_continue=True and limit='max'
        )
        logger.info("Fetched %d rows from %s.", len(rows), tables)
        return list(rows)
    except Exception as exc:
        msg = f"Failed to fetch {tables} with auto_continue: {exc}"
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return []


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


def run_ingestion(table_names: list[str] | None = None) -> bool:
    """Run ingestion for the given tables, or all configured tables if none specified.

    Creates a single authenticated EsportsClient shared across all tables.
    GCS destination: bronze/leaguepedia/{TableName}/{YYYY-MM-DD}.json

    For tables marked with 'lfl_filter: True', the WHERE clause is built from
    LFL OverviewPages loaded from the Tournaments Bronze file. This avoids the
    broken Cargo table join (mwcleric sends 'join_on' but the API expects 'join on').

    Returns True if all tables fetched at least one row, False if any table failed.

    Args:
        table_names: List of table names to ingest. Defaults to all tables in TABLE_CONFIGS.
    """
    site = build_esports_client()
    targets = table_names or list(TABLE_CONFIGS.keys())
    date_today = datetime.now(UTC).strftime("%Y-%m-%d")
    all_success = True

    needs_lfl_filter = any(TABLE_CONFIGS[t].get("lfl_filter") for t in targets)
    lfl_pages: set[str] = set()
    if needs_lfl_filter:
        lfl_pages = load_lfl_overview_pages(settings.gcs_bucket_name)
        if not lfl_pages:
            logger.error(
                "LFL filter requested but no LFL OverviewPages found. "
                "Ingest Tournaments first, or check Bronze date."
            )

    for table_name in targets:
        config = TABLE_CONFIGS[table_name]
        logger.info("Starting ingestion for table: %s", table_name)

        if config.get("lfl_filter"):
            if not lfl_pages:
                logger.error("Skipping %s — no LFL OverviewPages available.", table_name)
                all_success = False
                continue
            rows = fetch_lfl_filtered_table(
                site=site,
                tables=config.get("tables", table_name),
                fields=config["fields"],
                lfl_pages=lfl_pages,
                order_by=config.get("order_by", "DateTime_UTC"),
            )
        else:
            rows = fetch_all_rows(
                site=site,
                tables=config.get("tables", table_name),
                fields=config["fields"],
                limit=config["limit"],
            )

        min_rows = config.get("min_rows", 1)
        if len(rows) < min_rows:
            logger.error(
                "Table %s incomplete: got %d rows, expected at least %d.",
                table_name,
                len(rows),
                min_rows,
            )
            all_success = False

        file_name = f"{table_name}/{date_today}.json"
        save_to_gcs(rows, settings.gcs_bucket_name, file_name)

    return all_success


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
    success = run_ingestion(table_names=[args.table] if args.table else None)
    sys.exit(0 if success else 1)
