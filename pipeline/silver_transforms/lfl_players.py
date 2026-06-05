"""Silver transform: extract the list of unique LFL players from Bronze data.

Reads:
  - bronze/leaguepedia/Tournaments/{date}.json
  - bronze/leaguepedia/TournamentRosters/{date}.json

Writes:
  - silver/leaguepedia/lfl_players/{date}.json  (one player name per line, NDJSON)

Usage:
    uv run python -m pipeline.silver_transforms.lfl_players
    uv run python -m pipeline.silver_transforms.lfl_players --date 2026-06-04
"""

import argparse
import json
from datetime import UTC, datetime

from ingestion.utils import gcs_client, logger, send_discord_notification, settings

LFL_LEAGUES = {"La Ligue Française", "La Ligue Française Division 2"}
ROSTER_LINK_DELIMITER = ";;"


def load_bronze_table(bucket_name: str, table_name: str, date: str) -> list[dict]:
    """Download and parse a Bronze NDJSON file from GCS.

    Each line in the file is a JSON object representing one row.
    """
    path = f"bronze/leaguepedia/{table_name}/{date}.json"
    with gcs_client() as client:
        blob = client.bucket(bucket_name).blob(path)
        content = blob.download_as_text(encoding="utf-8")
    rows = [json.loads(line) for line in content.splitlines() if line.strip()]
    logger.info("Loaded %d rows from gs://%s/%s", len(rows), bucket_name, path)
    return rows


def filter_lfl_tournaments(tournaments: list[dict]) -> set[str]:
    """Return the OverviewPage values for all LFL tournaments."""
    lfl_pages = {row["OverviewPage"] for row in tournaments if row.get("League") in LFL_LEAGUES}
    logger.info("Found %d LFL tournament pages.", len(lfl_pages))
    return lfl_pages


def extract_players_from_rosters(rosters: list[dict], lfl_pages: set[str]) -> list[str]:
    """Parse RosterLinks for LFL tournaments and return a deduplicated player list.

    RosterLinks is a ';;'-delimited string of player wiki names per roster row.
    """
    players: set[str] = set()
    for row in rosters:
        if row.get("OverviewPage") not in lfl_pages:
            continue
        roster_links = row.get("RosterLinks") or ""
        for player in roster_links.split(ROSTER_LINK_DELIMITER):
            player = player.strip()
            if player:
                players.add(player)
    logger.info("Found %d unique LFL players.", len(players))
    return sorted(players)


def save_players_to_gcs(players: list[str], bucket_name: str, date: str) -> None:
    """Write the player list to GCS Silver layer as NDJSON (one name per line)."""
    if not players:
        msg = "No LFL players found — aborting Silver write."
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    destination = f"silver/leaguepedia/lfl_players/{date}.json"
    content = "\n".join(json.dumps({"player": p}) for p in players)

    with gcs_client() as client:
        blob = client.bucket(bucket_name).blob(destination)
        blob.metadata = {
            "source": "leaguepedia",
            "transform": "lfl_players",
            "date": date,
            "player_count": str(len(players)),
        }
        blob.upload_from_string(content, content_type="application/json")

    gcs_uri = f"gs://{bucket_name}/{destination}"
    msg = (
        f":white_check_mark: Silver transform success — lfl_players\n"
        f"URI: {gcs_uri}\n"
        f"Players: {len(players)}"
    )
    logger.info(msg)
    send_discord_notification(msg)


def run_transform(date: str) -> None:
    """Orchestrate the full LFL players Silver transform for a given date.

    Args:
        date: The ingestion date to read from Bronze (format: YYYY-MM-DD).
    """
    bucket = settings.gcs_bucket_name

    tournaments = load_bronze_table(bucket, "Tournaments", date)
    rosters = load_bronze_table(bucket, "TournamentRosters", date)

    lfl_pages = filter_lfl_tournaments(tournaments)
    if not lfl_pages:
        msg = f"No LFL tournaments found in Tournaments Bronze ({date})."
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    players = extract_players_from_rosters(rosters, lfl_pages)
    save_players_to_gcs(players, bucket, date)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Extract unique LFL players from Bronze to Silver."
    )
    parser.add_argument(
        "--date",
        default=datetime.now(UTC).strftime("%Y-%m-%d"),
        help="Ingestion date to read from Bronze (default: today).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_transform(date=args.date)
