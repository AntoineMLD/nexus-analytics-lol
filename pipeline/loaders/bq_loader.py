"""Loader: push GCS Silver NDJSON into BigQuery raw dataset.

Reads from GCS:
  gs://{bucket}/silver/{source}/{table}/{date}.json

Writes to BigQuery:
  {project}.{dataset}.{table}   (WRITE_TRUNCATE — idempotent)

The BigQuery table schema is auto-detected from the NDJSON. Running the loader
twice with the same arguments overwrites the previous content (no duplicates).

Usage:
    uv run python -m pipeline.loaders.bq_loader \\
        --source leaguepedia --table lfl_matches --date 2026-06-07

    uv run python -m pipeline.loaders.bq_loader \\
        --source leaguepedia --table lfl_player_stats --date 2026-07-06

    uv run python -m pipeline.loaders.bq_loader \\
        --source oracle_elixir --table matches --date 2026-06-01
"""

import argparse
from datetime import UTC, datetime

from google.cloud import bigquery

from ingestion.utils import logger, send_discord_notification, settings


def build_gcs_uri(bucket: str, source: str, table: str, date: str) -> str:
    """Return the GCS URI for a Silver NDJSON file.

    Examples:
        >>> build_gcs_uri("my-bucket", "leaguepedia", "lfl_matches", "2026-06-07")
        'gs://my-bucket/silver/leaguepedia/lfl_matches/2026-06-07.json'
    """
    return f"gs://{bucket}/silver/{source}/{table}/{date}.json"


def load_to_bigquery(
    gcs_uri: str,
    project: str,
    dataset: str,
    table: str,
) -> int:
    """Load a GCS NDJSON file into a BigQuery table.

    Uses WRITE_TRUNCATE for idempotency: running twice with the same parameters
    overwrites the previous content without creating duplicates.

    Returns the number of rows loaded.
    """
    client = bigquery.Client(project=project)
    destination = f"{project}.{dataset}.{table}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    logger.info("Loading %s → %s", gcs_uri, destination)
    load_job = client.load_table_from_uri(gcs_uri, destination, job_config=job_config)
    load_job.result()

    table_ref = client.get_table(destination)
    return table_ref.num_rows


def run_loader(source: str, table: str, date: str) -> None:
    """Orchestrate the GCS Silver → BigQuery load for a given table and date.

    Args:
        source: Silver source folder (e.g. 'leaguepedia', 'oracle_elixir').
        table:  Table name matching the Silver file (e.g. 'lfl_matches').
        date:   File date in YYYY-MM-DD format.
    """
    bucket = settings.gcs_bucket_name
    project = settings.gcp_project_id
    dataset = settings.bq_dataset_raw

    if not project:
        msg = "GCP_PROJECT_ID is not set — cannot load to BigQuery."
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    gcs_uri = build_gcs_uri(bucket, source, table, date)
    bq_table = f"{project}.{dataset}.{table}"

    try:
        row_count = load_to_bigquery(gcs_uri, project, dataset, table)
    except Exception as exc:
        msg = f"BigQuery load failed for {gcs_uri}: {exc}"
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        raise

    msg = (
        f":white_check_mark: BigQuery load success\n"
        f"Source: {gcs_uri}\n"
        f"Destination: {bq_table}\n"
        f"Rows: {row_count:,}"
    )
    logger.info(msg)
    send_discord_notification(msg)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Load a GCS Silver NDJSON file into a BigQuery raw table."
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Silver source folder (e.g. leaguepedia, oracle_elixir, riot_api).",
    )
    parser.add_argument(
        "--table",
        required=True,
        help="Table name matching the Silver filename (e.g. lfl_matches).",
    )
    parser.add_argument(
        "--date",
        default=datetime.now(UTC).strftime("%Y-%m-%d"),
        help="File date in YYYY-MM-DD format (default: today).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_loader(source=args.source, table=args.table, date=args.date)
