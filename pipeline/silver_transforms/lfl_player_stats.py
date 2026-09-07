"""Silver transform: normalize LFL player-level game stats from ScoreboardPlayers.

Reads:
  - bronze/leaguepedia/Tournaments/{date}.json   (to identify LFL OverviewPages)
  - bronze/leaguepedia/ScoreboardPlayers/{date}.json

Writes:
  - silver/leaguepedia/lfl_player_stats/{date}.json  (NDJSON, one player-game per line)

Each output row contains cleaned, typed fields:
  - numeric stats cast to int (None when missing)
  - player_win normalized to boolean
  - datetime_utc parsed to ISO 8601 string
  - GameId and MatchId kept as strings (foreign keys to lfl_matches)

Usage:
    uv run python -m pipeline.silver_transforms.lfl_player_stats
    uv run python -m pipeline.silver_transforms.lfl_player_stats --date 2026-06-07
"""

import argparse
import json
import re
from datetime import UTC, datetime

from ingestion.utils import gcs_client, logger, send_discord_notification, settings

LFL_LEAGUES = {"La Ligue Française", "La Ligue Française Division 2"}


def to_snake_case(name: str) -> str:
    """Convert a CamelCase or mixed field name to snake_case.

    Examples:
        >>> to_snake_case("DamageToChampions")
        'damage_to_champions'
        >>> to_snake_case("VisionScore")
        'vision_score'
        >>> to_snake_case("CS")
        'cs'
    """
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    return re.sub(r"_+", "_", s).lower()


INT_FIELDS = ["Kills", "Deaths", "Assists", "Gold", "CS", "DamageToChampions", "VisionScore"]


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
    """Return OverviewPage values for all LFL (D1 + D2) tournaments."""
    lfl_pages = {row["OverviewPage"] for row in tournaments if row.get("League") in LFL_LEAGUES}
    logger.info("Found %d LFL tournament overview pages.", len(lfl_pages))
    return lfl_pages


def filter_lfl_rows(rows: list[dict], lfl_pages: set[str]) -> list[dict]:
    """Keep only rows whose OverviewPage belongs to an LFL tournament.

    Raises ValueError if the input is non-empty but the filter returns 0 rows.
    This guards against corrupted Bronze files (e.g. a global unfiltered ingestion
    that has no LFL data), preventing a silent empty Silver write.
    """
    filtered = [row for row in rows if row.get("OverviewPage") in lfl_pages]
    logger.info("Filtered %d → %d LFL player-game rows.", len(rows), len(filtered))

    if rows and not filtered:
        # Show a sample of OverviewPage values to help diagnose the root cause
        sample_pages = list({r.get("OverviewPage") for r in rows[:20] if r.get("OverviewPage")})[:5]
        raise ValueError(
            f"Bronze ScoreboardPlayers has {len(rows)} rows but 0 match LFL OverviewPages. "
            f"This file was likely ingested without the 'WHERE OverviewPage LIKE LFL/%' filter. "
            f"Sample OverviewPage values found: {sample_pages}. "
            f"Re-ingest ScoreboardPlayers with: "
            f"uv run python -m ingestion.leaguepedia.ingest --table ScoreboardPlayers"
        )

    return filtered


def parse_datetime(value: str | None) -> str | None:
    """Parse Leaguepedia datetime string to ISO 8601 UTC.

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


def parse_player_win(value: str | None) -> bool | None:
    """Convert 'Yes'/'No' string to boolean.

    Returns None if value is missing or unexpected.

    Examples:
        >>> parse_player_win("Yes")
        True
        >>> parse_player_win("No")
        False
    """
    if value == "Yes":
        return True
    if value == "No":
        return False
    return None


def normalize_row(row: dict) -> dict:
    """Apply all type casts to a single ScoreboardPlayers row."""
    normalized = {
        "game_id": row.get("GameId"),
        "match_id": row.get("MatchId"),
        "overview_page": row.get("OverviewPage"),
        "tournament": row.get("Tournament"),
        # Cargo API returns "DateTime UTC" with a space, not an underscore.
        "datetime_utc": parse_datetime(row.get("DateTime UTC") or row.get("DateTime_UTC")),
        "team": row.get("Team"),
        "team_vs": row.get("TeamVs"),
        "player_link": row.get("Link"),
        "player_name": row.get("Name"),
        "champion": row.get("Champion"),
        "role": row.get("Role"),
        "side": row.get("Side"),
        "player_win": parse_player_win(row.get("PlayerWin")),
    }
    for field in INT_FIELDS:
        normalized[to_snake_case(field)] = cast_int(row.get(field))

    return normalized


def transform_rows(rows: list[dict]) -> list[dict]:
    """Normalize all ScoreboardPlayers Bronze rows."""
    return [normalize_row(row) for row in rows]


def save_to_gcs(player_stats: list[dict], bucket_name: str, date: str) -> None:
    """Write normalized player stats to GCS Silver layer as NDJSON."""
    if not player_stats:
        msg = "No player stats found in ScoreboardPlayers Bronze — aborting Silver write."
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    destination = f"silver/leaguepedia/lfl_player_stats/{date}.json"
    content = "\n".join(json.dumps(row) for row in player_stats)

    with gcs_client() as client:
        blob = client.bucket(bucket_name).blob(destination)
        blob.metadata = {
            "source": "leaguepedia",
            "transform": "lfl_player_stats",
            "date": date,
            "row_count": str(len(player_stats)),
        }
        blob.upload_from_string(content, content_type="application/json")

    gcs_uri = f"gs://{bucket_name}/{destination}"
    msg = (
        f":white_check_mark: Silver transform success — lfl_player_stats\n"
        f"URI: {gcs_uri}\n"
        f"Rows: {len(player_stats)}"
    )
    logger.info(msg)
    send_discord_notification(msg)


def run_transform(date: str, tournaments_date: str | None = None) -> None:
    """Orchestrate the lfl_player_stats Silver transform for a given ingestion date.

    Loads Tournaments Bronze first to identify LFL OverviewPages, then filters
    ScoreboardPlayers Bronze down to LFL player-game rows only.

    Args:
        date: Ingestion date of the ScoreboardPlayers Bronze file (format: YYYY-MM-DD).
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

    all_rows = load_bronze_table(bucket, "ScoreboardPlayers", date)
    try:
        lfl_rows = filter_lfl_rows(all_rows, lfl_pages)
    except ValueError as exc:
        msg = str(exc)
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    player_stats = transform_rows(lfl_rows)
    save_to_gcs(player_stats, bucket, date)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Normalize ScoreboardPlayers Bronze to Silver lfl_player_stats."
    )
    parser.add_argument(
        "--date",
        default=datetime.now(UTC).strftime("%Y-%m-%d"),
        help="Ingestion date of the ScoreboardPlayers Bronze file (default: today).",
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
