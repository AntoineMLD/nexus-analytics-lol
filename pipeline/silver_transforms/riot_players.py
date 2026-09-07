"""Silver transform: Riot API Bronze → player PUUID mapping.

Reads:
  - bronze/riot_api/{date}.ndjson  (one row per player account)

Writes:
  - silver/riot_api/riot_players/{date}.json  (one row per player with a valid PUUID)
  (path convention: silver/{source}/{table}/{date}.json — compatible bq_loader)

Each output row:
  {"player_name": "Caliste", "puuid": "abc...xyz"}

Only players with a non-null PUUID are kept.
Players with multiple accounts keep the first valid PUUID found.

Usage:
    uv run python -m pipeline.silver_transforms.riot_players
    uv run python -m pipeline.silver_transforms.riot_players --date 2026-06-05
"""

import argparse
import json
from datetime import UTC, datetime

from ingestion.utils import gcs_client, logger, send_discord_notification, settings


def load_riot_bronze(bucket_name: str, date: str) -> list[dict]:
    """Download and parse the Riot API Bronze NDJSON file from GCS.

    Args:
        bucket_name: GCS bucket name.
        date: Date of the Bronze file (YYYY-MM-DD).
    """
    path = f"bronze/riot_api/{date}.ndjson"
    with gcs_client() as client:
        content = client.bucket(bucket_name).blob(path).download_as_text(encoding="utf-8")
    rows = [json.loads(line) for line in content.splitlines() if line.strip()]
    logger.info("Loaded %d Riot API rows from gs://%s/%s", len(rows), bucket_name, path)
    return rows


def extract_player_puuids(rows: list[dict]) -> list[dict]:
    """Extract unique player → PUUID mappings from Riot API Bronze rows.

    Each Bronze row may represent one account for a player. Multiple rows for
    the same player are possible (multiple accounts). Only rows with a valid
    PUUID are kept. The first valid PUUID per player is used.

    Args:
        rows: Raw Bronze rows, each with 'player', 'account', 'puuid' fields.

    Returns:
        List of dicts with 'player_name' and 'puuid'.
    """
    seen: dict[str, str] = {}
    for row in rows:
        player = row.get("player", "").strip()
        puuid = row.get("puuid")
        if not player or not puuid:
            continue
        if player not in seen:
            seen[player] = puuid
    result = [{"player_name": name, "puuid": puuid} for name, puuid in seen.items()]
    logger.info("Extracted %d unique players with valid PUUIDs.", len(result))
    return result


def save_to_gcs(records: list[dict], bucket_name: str, date: str) -> str:
    """Write player→PUUID records to GCS Silver as NDJSON.

    Path follows the bq_loader convention: silver/{source}/{table}/{date}.json
    → silver/riot_api/riot_players/{date}.json

    Returns the GCS destination path.
    """
    destination = f"silver/riot_api/riot_players/{date}.json"
    content = "\n".join(json.dumps(row) for row in records)
    with gcs_client() as client:
        blob = client.bucket(bucket_name).blob(destination)
        blob.metadata = {
            "source": "riot_api",
            "transform": "riot_players",
            "date": date,
            "record_count": str(len(records)),
        }
        blob.upload_from_string(content, content_type="application/x-ndjson")
    logger.info("Uploaded %d records to gs://%s/%s", len(records), bucket_name, destination)
    return destination


def run_transform(date: str) -> None:
    """Run the Riot API players Silver transform.

    Args:
        date: Date of the Bronze file to read and the Silver file to produce (YYYY-MM-DD).
    """
    bucket = settings.gcs_bucket_name
    logger.info("Starting Riot players Silver transform — date: %s", date)

    rows = load_riot_bronze(bucket, date)
    records = extract_player_puuids(rows)

    if not records:
        msg = f"No valid PUUIDs found in Riot API Bronze ({date})."
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    destination = save_to_gcs(records, bucket, date)
    gcs_uri = f"gs://{bucket}/{destination}"
    msg = (
        f":white_check_mark: Riot players Silver transform\n"
        f"URI: {gcs_uri}\n"
        f"Players with PUUID: {len(records)}"
    )
    logger.info(msg)
    send_discord_notification(msg)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Extract player PUUIDs from Riot API Bronze to Silver."
    )
    parser.add_argument(
        "--date",
        default=datetime.now(UTC).strftime("%Y-%m-%d"),
        help="Date of the Bronze file to read (default: today).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_transform(date=args.date)
