"""Silver transform: normalize LFL and EMEA Masters draft data from PicksAndBansS7.

Reads:
  - bronze/leaguepedia/Tournaments/{date}.json   (to identify LFL OverviewPages)
  - bronze/leaguepedia/PicksAndBansS7/{date}.json

Writes:
  - silver/leaguepedia/lfl_drafts/{date}.json  (NDJSON, one pick/ban action per line)

The Bronze PicksAndBansS7 table is wide: one row per game with 20 columns for picks
and bans (Team1Ban1..Team1Ban5, Team1Pick1..Team1Pick5, same for Team2).

This transform unpivots to a long format: one row per champion action.
Granularité de la sortie : (game_id, team_side, action_type, action_order)

Example input row:
    {"GameId": "LFL/2024/...", "Team1": "Vitality", "Team1Ban1": "Yone", ...}

Example output rows (one per action):
    {"game_id": "LFL/2024/...", "team_name": "Vitality", "team_side": 1,
     "action_type": "ban", "action_order": 1, "champion": "Yone", ...}

Usage:
    uv run python -m pipeline.silver_transforms.lfl_drafts
    uv run python -m pipeline.silver_transforms.lfl_drafts --date 2026-06-07
"""

import argparse
import json
from datetime import UTC, datetime

from ingestion.utils import gcs_client, logger, send_discord_notification, settings

TARGET_LEAGUES = {
    "La Ligue Française",
    "La Ligue Française Division 2",
    "EMEA Masters",
}

# Ordre des colonnes Bronze pour le dépliage (action_type, action_order, team_side)
_DRAFT_COLUMNS: list[tuple[str, str, int]] = [
    # (bronze_column, action_type, team_side)
    ("Team1Ban1", "ban", 1),
    ("Team1Ban2", "ban", 1),
    ("Team1Ban3", "ban", 1),
    ("Team1Ban4", "ban", 1),
    ("Team1Ban5", "ban", 1),
    ("Team1Pick1", "pick", 1),
    ("Team1Pick2", "pick", 1),
    ("Team1Pick3", "pick", 1),
    ("Team1Pick4", "pick", 1),
    ("Team1Pick5", "pick", 1),
    ("Team2Ban1", "ban", 2),
    ("Team2Ban2", "ban", 2),
    ("Team2Ban3", "ban", 2),
    ("Team2Ban4", "ban", 2),
    ("Team2Ban5", "ban", 2),
    ("Team2Pick1", "pick", 2),
    ("Team2Pick2", "pick", 2),
    ("Team2Pick3", "pick", 2),
    ("Team2Pick4", "pick", 2),
    ("Team2Pick5", "pick", 2),
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
    """Return OverviewPage values for all LFL (D1 + D2) and EMEA Masters tournaments."""
    lfl_pages = {row["OverviewPage"] for row in tournaments if row.get("League") in TARGET_LEAGUES}
    logger.info("Found %d target tournament overview pages.", len(lfl_pages))
    return lfl_pages


def cast_int(value: str | None) -> int | None:
    """Cast a string to int, returning None for missing or non-numeric values."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def unpivot_draft_row(row: dict) -> list[dict]:
    """Unpivot a single wide PicksAndBansS7 row into one dict per champion action.

    Skips actions where the champion field is empty (partial drafts or byes).

    Args:
        row: A single Bronze PicksAndBansS7 row (wide format, up to 20 pick/ban cols).

    Returns:
        A list of dicts, one per non-empty champion action (0 to 20 items).

    Example:
        >>> row = {"GameId": "LFL/2024/g1", "Team1": "Vitality",
        ...        "Team1Ban1": "Yone", "Team1Ban2": "", "Team2": "LDLC OL"}
        >>> actions = unpivot_draft_row(row)
        >>> len(actions)  # only 1 action (Team1Ban1), Team1Ban2 is empty
        1
        >>> actions[0]["champion"]
        'Yone'
    """
    game_id = row.get("GameId")
    match_id = row.get("MatchId")
    overview_page = row.get("OverviewPage")
    team1_name = row.get("Team1")
    team2_name = row.get("Team2")
    winner = cast_int(row.get("Winner"))
    n_game_in_match = cast_int(row.get("N_GameInMatch") or row.get("N GameInMatch"))

    ingested_at = datetime.now(UTC).isoformat()

    ban_counters: dict[int, int] = {1: 0, 2: 0}
    pick_counters: dict[int, int] = {1: 0, 2: 0}

    actions = []
    for col, action_type, team_side in _DRAFT_COLUMNS:
        champion = row.get(col)
        if not champion or champion.strip() == "":
            continue

        counter_map = ban_counters if action_type == "ban" else pick_counters
        counter_map[team_side] += 1
        action_order = counter_map[team_side]

        team_name = team1_name if team_side == 1 else team2_name

        actions.append(
            {
                "game_id": game_id,
                "match_id": match_id,
                "overview_page": overview_page,
                "team_name": team_name,
                "team_side": team_side,
                "action_type": action_type,
                "action_order": action_order,
                "champion": champion.strip(),
                "winner": winner,
                "n_game_in_match": n_game_in_match,
                "ingested_at": ingested_at,
            }
        )

    return actions


def transform_rows(rows: list[dict], lfl_pages: set[str]) -> list[dict]:
    """Filter to LFL games and unpivot all draft rows.

    Args:
        rows: All PicksAndBansS7 Bronze rows.
        lfl_pages: Set of LFL OverviewPage values to keep.

    Returns:
        Flat list of one dict per champion action.
    """
    lfl_rows = [r for r in rows if r.get("OverviewPage") in lfl_pages]
    logger.info("Filtered %d → %d LFL draft rows.", len(rows), len(lfl_rows))

    actions = []
    for row in lfl_rows:
        actions.extend(unpivot_draft_row(row))

    logger.info("Unpivoted to %d draft actions.", len(actions))
    return actions


def find_latest_bronze_date(bucket_name: str, table_name: str) -> str:
    """Find the most recent ingestion date for a Bronze table by listing GCS objects.

    Returns the date string 'YYYY-MM-DD' extracted from the latest file name.
    Raises FileNotFoundError if no file is found.
    """
    prefix = f"bronze/leaguepedia/{table_name}/"
    with gcs_client() as client:
        blobs = list(client.bucket(bucket_name).list_blobs(prefix=prefix))
    if not blobs:
        raise FileNotFoundError(f"No Bronze file found under gs://{bucket_name}/{prefix}")
    latest = max(blobs, key=lambda b: b.name)
    return latest.name.split("/")[-1].replace(".json", "")


def save_to_gcs(actions: list[dict], bucket_name: str, date: str) -> None:
    """Write normalized draft actions to GCS Silver layer as NDJSON."""
    if not actions:
        msg = "No draft actions found in PicksAndBansS7 Bronze — aborting Silver write."
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    path = f"silver/leaguepedia/lfl_drafts/{date}.json"
    ndjson = "\n".join(json.dumps(row, ensure_ascii=False) for row in actions)

    with gcs_client() as client:
        client.bucket(bucket_name).blob(path).upload_from_string(
            ndjson, content_type="application/x-ndjson"
        )

    logger.info("Saved %d draft actions to gs://%s/%s", len(actions), bucket_name, path)
    send_discord_notification(
        f":white_check_mark: Silver lfl_drafts — {len(actions)} actions écrites ({date})"
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Silver transform for LFL draft data.")
    parser.add_argument(
        "--date",
        default=None,
        help=(
            "Date (YYYY-MM-DD) of the Bronze file to process. "
            "Defaults to the latest available date."
        ),
    )
    return parser.parse_args()


def run(date: str | None = None) -> None:
    """Main entry point for the Silver draft transform.

    Args:
        date: Optional Bronze ingestion date. Defaults to the latest available.
    """
    bucket_name = settings.gcs_bucket_name

    if date is None:
        date = find_latest_bronze_date(bucket_name, "PicksAndBansS7")
        logger.info("Using latest Bronze date: %s", date)

    tournaments = load_bronze_table(bucket_name, "Tournaments", date)
    lfl_pages = get_lfl_overview_pages(tournaments)

    drafts = load_bronze_table(bucket_name, "PicksAndBansS7", date)
    actions = transform_rows(drafts, lfl_pages)

    save_to_gcs(actions, bucket_name, date)


if __name__ == "__main__":
    args = parse_args()
    run(date=args.date)
