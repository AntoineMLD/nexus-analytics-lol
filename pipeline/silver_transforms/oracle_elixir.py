"""Silver transform: Oracle's Elixir CSV → LFL player-game stats.

Reads:
  - bronze/oracle_elixir/{year}/{file}.csv  (CSV, one row per player per game)

Writes:
  - silver/oracle_elixir/oracle_elixir/{date}.json  (NDJSON, one row per player-game)
  (path convention: silver/{source}/{table}/{date}.json — compatible bq_loader)

Each output row contains the player-level advanced metrics not available in
Leaguepedia ScoreboardPlayers: gold/CS/XP diff at 15 min, CS per minute, DPM.

Oracle's Elixir CSV has two row types per game:
  - Player rows  : position in {top, jng, mid, bot, sup}
  - Team rows    : position == 'team'  (aggregated team stats — excluded here)

Only LFL and LFL Division 2 rows are kept (league filter).

Some columns (diff metrics) only appear from ~2021 onwards. Missing columns
produce null values rather than errors.

Usage:
    uv run python -m pipeline.silver_transforms.oracle_elixir
    uv run python -m pipeline.silver_transforms.oracle_elixir --year 2024
    uv run python -m pipeline.silver_transforms.oracle_elixir --all-years
"""

import argparse
import csv
import io
import json
from datetime import UTC, datetime

from ingestion.utils import gcs_client, logger, send_discord_notification, settings

TARGET_LEAGUES = {"LFL", "LFL D2"}
PLAYER_POSITIONS = {"top", "jng", "mid", "bot", "sup"}

# Columns that may be absent in older OE files (pre-2021)
OPTIONAL_FLOAT_COLUMNS = {
    "golddiffat15",
    "csdiffat15",
    "xpdiffat15",
    "golddiffat10",
    "csdiffat10",
    "xpdiffat10",
    "dpm",
    "cspm",
    "damagetochampions",
    "visionscore",
    "gamelength",
}


def _safe_float(value: str | None) -> float | None:
    """Convert a string to float, returning None for empty or non-numeric values."""
    if value is None or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _safe_int(value: str | None) -> int | None:
    """Convert a string to int, returning None for empty or non-numeric values."""
    if value is None or value.strip() == "":
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def list_bronze_oe_years(bucket_name: str) -> list[int]:
    """List all years available in bronze/oracle_elixir/ in GCS.

    Returns a sorted list of years (e.g. [2019, 2020, 2021, ...]).
    """
    prefix = "bronze/oracle_elixir/"
    with gcs_client() as client:
        blobs = list(client.bucket(bucket_name).list_blobs(prefix=prefix))
    years = set()
    for blob in blobs:
        parts = blob.name.split("/")
        if len(parts) >= 3 and parts[2].isdigit():
            years.add(int(parts[2]))
    return sorted(years)


def load_oe_csv_from_gcs(bucket_name: str, year: int) -> bytes | None:
    """Download the Oracle's Elixir CSV for a given year from GCS Bronze.

    Returns the raw CSV bytes, or None if no file is found for that year.
    """
    prefix = f"bronze/oracle_elixir/{year}/"
    with gcs_client() as client:
        blobs = list(client.bucket(bucket_name).list_blobs(prefix=prefix))
    if not blobs:
        logger.warning("No Oracle's Elixir CSV found in GCS for year %d.", year)
        return None
    # Take the first (and typically only) file for this year
    blob_name = blobs[0].name
    with gcs_client() as client:
        content = client.bucket(bucket_name).blob(blob_name).download_as_bytes()
    logger.info("Downloaded %d bytes from gs://%s/%s", len(content), bucket_name, blob_name)
    return content


def parse_oe_csv(content: bytes) -> list[dict]:
    """Parse Oracle's Elixir CSV bytes into a list of raw row dicts.

    Returns all rows without filtering (filtering is done in filter_lfl_rows).
    """
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def filter_lfl_rows(rows: list[dict]) -> list[dict]:
    """Keep only LFL player rows (exclude team summary rows and other leagues).

    Filters:
      - league must be in TARGET_LEAGUES (case-insensitive)
      - position must be a player position (not 'team')
    """
    filtered = []
    for row in rows:
        if row.get("league", "").strip().upper() not in {lg.upper() for lg in TARGET_LEAGUES}:
            continue
        if row.get("position", "").strip().lower() not in PLAYER_POSITIONS:
            continue
        filtered.append(row)
    logger.info("Filtered %d LFL player rows (from %d total rows).", len(filtered), len(rows))
    return filtered


def build_silver_row(row: dict) -> dict:
    """Convert a raw OE CSV row to a clean Silver record.

    Renames columns to snake_case, casts types, and handles missing optional fields.
    """
    return {
        "game_id": row.get("gameid", "").strip() or None,
        "league": row.get("league", "").strip() or None,
        "year": _safe_int(row.get("year")),
        "split": row.get("split", "").strip() or None,
        "date": row.get("date", "").strip() or None,
        "patch": row.get("patch", "").strip() or None,
        "side": row.get("side", "").strip() or None,
        "position": row.get("position", "").strip() or None,
        "player_name": row.get("playername", "").strip() or None,
        "team_name": row.get("teamname", "").strip() or None,
        "champion": row.get("champion", "").strip() or None,
        "result": _safe_int(row.get("result")),
        "kills": _safe_int(row.get("kills")),
        "deaths": _safe_int(row.get("deaths")),
        "assists": _safe_int(row.get("assists")),
        # Timeline diff metrics — may be absent in older files
        "gold_diff_at_15": _safe_float(row.get("golddiffat15")),
        "cs_diff_at_15": _safe_float(row.get("csdiffat15")),
        "xp_diff_at_15": _safe_float(row.get("xpdiffat15")),
        "gold_diff_at_10": _safe_float(row.get("golddiffat10")),
        "cs_diff_at_10": _safe_float(row.get("csdiffat10")),
        # Per-minute metrics
        "cs_per_min": _safe_float(row.get("cspm")),
        "damage_per_min": _safe_float(row.get("dpm")),
        # Totals
        "damage_to_champions": _safe_float(row.get("damagetochampions")),
        "vision_score": _safe_float(row.get("visionscore")),
        "game_length_s": _safe_float(row.get("gamelength")),
    }


def save_to_gcs(records: list[dict], bucket_name: str, date: str) -> str:
    """Write Silver OE records to GCS as NDJSON.

    Path follows the bq_loader convention: silver/{source}/{table}/{date}.json
    → silver/oracle_elixir/oracle_elixir/{date}.json

    Returns the GCS destination path.
    """
    destination = f"silver/oracle_elixir/oracle_elixir/{date}.json"
    content = "\n".join(json.dumps(row, ensure_ascii=False) for row in records)
    with gcs_client() as client:
        blob = client.bucket(bucket_name).blob(destination)
        blob.metadata = {
            "source": "oracle_elixir",
            "transform": "oracle_elixir",
            "date": date,
            "record_count": str(len(records)),
        }
        blob.upload_from_string(content, content_type="application/x-ndjson")
    logger.info("Uploaded %d records to gs://%s/%s", len(records), bucket_name, destination)
    return destination


def run_transform(year: int, date: str) -> None:
    """Run the Oracle's Elixir Silver transform for a given year.

    Args:
        year: The year to process (e.g. 2024).
        date: Output Silver file date (YYYY-MM-DD).
    """
    bucket = settings.gcs_bucket_name
    logger.info("Starting Oracle's Elixir Silver transform — year %d", year)

    content = load_oe_csv_from_gcs(bucket, year)
    if content is None:
        msg = f"Oracle's Elixir Bronze not found for year {year} — run ingestion first."
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    rows = parse_oe_csv(content)
    lfl_rows = filter_lfl_rows(rows)

    if not lfl_rows:
        msg = (
            f"No LFL rows found in Oracle's Elixir {year}. "
            f"Check TARGET_LEAGUES: {TARGET_LEAGUES}"
        )
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    records = [build_silver_row(row) for row in lfl_rows]
    destination = save_to_gcs(records, bucket, date)

    gcs_uri = f"gs://{bucket}/{destination}"
    msg = (
        f":white_check_mark: Oracle's Elixir Silver transform — year {year}\n"
        f"URI: {gcs_uri}\n"
        f"LFL player-game rows: {len(records)}"
    )
    logger.info(msg)
    send_discord_notification(msg)


def run_all_years(date: str) -> None:
    """Run the Silver transform for all years available in Bronze GCS.

    Produces a single merged NDJSON file combining all years.

    Args:
        date: Output Silver file date (YYYY-MM-DD).
    """
    bucket = settings.gcs_bucket_name
    years = list_bronze_oe_years(bucket)
    if not years:
        msg = "No Oracle's Elixir Bronze files found in GCS — run ingestion first."
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    logger.info("Found %d years in Bronze: %s", len(years), years)
    all_records: list[dict] = []

    for year in years:
        content = load_oe_csv_from_gcs(bucket, year)
        if content is None:
            continue
        rows = parse_oe_csv(content)
        lfl_rows = filter_lfl_rows(rows)
        records = [build_silver_row(row) for row in lfl_rows]
        logger.info("Year %d: %d LFL player-game rows", year, len(records))
        all_records.extend(records)

    if not all_records:
        msg = "No LFL rows found across all Oracle's Elixir years."
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    destination = save_to_gcs(all_records, bucket, date)
    gcs_uri = f"gs://{bucket}/{destination}"
    msg = (
        f":white_check_mark: Oracle's Elixir Silver — all years ({years[0]}–{years[-1]})\n"
        f"URI: {gcs_uri}\n"
        f"Total LFL player-game rows: {len(all_records)}"
    )
    logger.info(msg)
    send_discord_notification(msg)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Transform Oracle's Elixir Bronze CSV to LFL Silver NDJSON."
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Year to process (default: current year). Ignored if --all-years is set.",
    )
    parser.add_argument(
        "--all-years",
        action="store_true",
        help="Process all years available in Bronze GCS (produces one merged Silver file).",
    )
    parser.add_argument(
        "--date",
        default=datetime.now(UTC).strftime("%Y-%m-%d"),
        help="Output Silver file date (default: today).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.all_years:
        run_all_years(date=args.date)
    else:
        year = args.year or datetime.now(UTC).year
        run_transform(year=year, date=args.date)
