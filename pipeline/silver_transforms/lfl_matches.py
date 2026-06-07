"""Silver transform: normalize LFL match-level data from ScoreboardGames.

Reads:
  - bronze/leaguepedia/Tournaments/{date}.json   (to identify LFL OverviewPages)
  - bronze/leaguepedia/ScoreboardGames/{date}.json

Writes:
  - silver/leaguepedia/lfl_matches/{date}.json  (NDJSON, one game per line)

The Bronze ScoreboardGames file contains global data (all leagues). This transform
filters to LFL (D1 + D2) games only using the Tournaments Bronze table, then
normalizes all fields.

Each output row contains cleaned, typed fields:
  - datetime_utc parsed to ISO 8601 string
  - numeric fields cast to int (None when missing)
  - gamelength_seconds computed from "MM:SS" string
  - GameId and MatchId kept as strings (primary keys)

Usage:
    uv run python -m pipeline.silver_transforms.lfl_matches
    uv run python -m pipeline.silver_transforms.lfl_matches --date 2026-06-07
"""

import argparse
import json
from datetime import UTC, datetime

from ingestion.utils import gcs_client, logger, send_discord_notification, settings

LFL_LEAGUES = {"La Ligue Française", "La Ligue Française Division 2"}

INT_FIELDS = [
    "Team1Score",
    "Team2Score",
    "Winner",
    "Team1Dragons",
    "Team2Dragons",
    "Team1Barons",
    "Team2Barons",
    "Team1Towers",
    "Team2Towers",
    "Team1Gold",
    "Team2Gold",
    "Team1Kills",
    "Team2Kills",
    "Team1RiftHeralds",
    "Team2RiftHeralds",
    "Team1VoidGrubs",
    "Team2VoidGrubs",
    "Team1Inhibitors",
    "Team2Inhibitors",
    "N_GameInMatch",
]


def load_bronze_table(bucket_name: str, table_name: str, date: str) -> list[dict]:
    """Download and parse a Bronze NDJSON table from GCS."""
    path = f"bronze/leaguepedia/{table_name}/{date}.json"
    with gcs_client() as client:
        blob = client.bucket(bucket_name).blob(path)
        content = blob.download_as_text(encoding="utf-8")
    rows = [json.loads(line) for line in content.splitlines() if line.strip()]
    logger.info("Loaded %d rows from gs://%s/%s", len(rows), bucket_name, path)
    return rows


def get_lfl_overview_pages(tournaments: list[dict]) -> set[str]:
    """Return OverviewPage values for all LFL (D1 + D2) tournaments.

    Bronze ScoreboardGames contains global data. This set is used to filter
    down to LFL games only in the Silver layer.
    """
    lfl_pages = {row["OverviewPage"] for row in tournaments if row.get("League") in LFL_LEAGUES}
    logger.info("Found %d LFL tournament overview pages.", len(lfl_pages))
    return lfl_pages


def filter_lfl_games(rows: list[dict], lfl_pages: set[str]) -> list[dict]:
    """Keep only games whose OverviewPage belongs to an LFL tournament."""
    filtered = [row for row in rows if row.get("OverviewPage") in lfl_pages]
    logger.info("Filtered %d → %d LFL games.", len(rows), len(filtered))
    return filtered


def parse_gamelength_seconds(gamelength: str | None) -> int | None:
    """Convert 'MM:SS' string to total seconds.

    Returns None if the value is missing or malformed.

    Examples:
        >>> parse_gamelength_seconds("32:15")
        1935
        >>> parse_gamelength_seconds(None)
        None
    """
    if not gamelength or ":" not in gamelength:
        return None
    try:
        minutes, seconds = gamelength.split(":", 1)
        return int(minutes) * 60 + int(seconds)
    except ValueError:
        return None


def parse_datetime(value: str | None) -> str | None:
    """Parse Leaguepedia datetime string to ISO 8601 UTC.

    The source format is 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD HH:MM:SS+00:00'.
    Returns None if missing or unparseable.

    Examples:
        >>> parse_datetime("2026-01-15 18:00:00")
        '2026-01-15T18:00:00+00:00'
    """
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S+00:00"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=UTC).isoformat()
        except ValueError:
            continue
    return None


def cast_int(value: str | None) -> int | None:
    """Cast a string to int, returning None for missing or non-numeric values."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def normalize_row(row: dict) -> dict:
    """Apply all type casts and derived fields to a single ScoreboardGames row.

    Preserves all original string fields; adds gamelength_seconds.
    """
    normalized = {
        "game_id": row.get("GameId"),
        "match_id": row.get("MatchId"),
        "overview_page": row.get("OverviewPage"),
        "tournament": row.get("Tournament"),
        "patch": row.get("Patch"),
        "datetime_utc": parse_datetime(row.get("DateTime_UTC")),
        "team1": row.get("Team1"),
        "team2": row.get("Team2"),
        "win_team": row.get("WinTeam"),
        "loss_team": row.get("LossTeam"),
        "gamelength": row.get("Gamelength"),
        "gamelength_seconds": parse_gamelength_seconds(row.get("Gamelength")),
    }
    for field in INT_FIELDS:
        snake_key = field[0].lower() + field[1:]
        normalized[snake_key] = cast_int(row.get(field))

    return normalized


def transform_rows(rows: list[dict]) -> list[dict]:
    """Normalize all ScoreboardGames Bronze rows."""
    return [normalize_row(row) for row in rows]


def save_to_gcs(matches: list[dict], bucket_name: str, date: str) -> None:
    """Write normalized matches to GCS Silver layer as NDJSON."""
    if not matches:
        msg = "No matches found in ScoreboardGames Bronze — aborting Silver write."
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    destination = f"silver/leaguepedia/lfl_matches/{date}.json"
    content = "\n".join(json.dumps(row) for row in matches)

    with gcs_client() as client:
        blob = client.bucket(bucket_name).blob(destination)
        blob.metadata = {
            "source": "leaguepedia",
            "transform": "lfl_matches",
            "date": date,
            "row_count": str(len(matches)),
        }
        blob.upload_from_string(content, content_type="application/json")

    gcs_uri = f"gs://{bucket_name}/{destination}"
    msg = (
        f":white_check_mark: Silver transform success — lfl_matches\n"
        f"URI: {gcs_uri}\n"
        f"Games: {len(matches)}"
    )
    logger.info(msg)
    send_discord_notification(msg)


def run_transform(date: str, tournaments_date: str | None = None) -> None:
    """Orchestrate the lfl_matches Silver transform for a given ingestion date.

    Loads Tournaments Bronze first to identify LFL OverviewPages, then filters
    ScoreboardGames Bronze (which contains global data) down to LFL games only.

    Args:
        date: Ingestion date of the ScoreboardGames Bronze file (format: YYYY-MM-DD).
        tournaments_date: Ingestion date of the Tournaments Bronze file.
                          Defaults to date when not provided.
    """
    bucket = settings.gcs_bucket_name
    effective_tournaments_date = tournaments_date or date
    tournaments = load_bronze_table(bucket, "Tournaments", effective_tournaments_date)
    lfl_pages = get_lfl_overview_pages(tournaments)

    if not lfl_pages:
        msg = (
            f"No LFL tournaments found in Tournaments Bronze "
            f"({effective_tournaments_date}) — aborting."
        )
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    all_games = load_bronze_table(bucket, "ScoreboardGames", date)
    lfl_games = filter_lfl_games(all_games, lfl_pages)
    matches = transform_rows(lfl_games)
    save_to_gcs(matches, bucket, date)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Normalize ScoreboardGames Bronze to Silver lfl_matches."
    )
    parser.add_argument(
        "--date",
        default=datetime.now(UTC).strftime("%Y-%m-%d"),
        help="Ingestion date of the ScoreboardGames Bronze file (default: today).",
    )
    parser.add_argument(
        "--tournaments-date",
        default=None,
        help="Ingestion date of the Tournaments Bronze file (default: same as --date).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_transform(date=args.date, tournaments_date=args.tournaments_date)
