"""Riot API ingestion: fetch PUUIDs and ranked match IDs for LFL players.

Reads:
  - silver/leaguepedia/lfl_players/{date}.json  (NDJSON)

Writes:
  - bronze/riot_api/{date}.ndjson  (one line per account, NDJSON)

Each output row:
  {
    "player": "Caliste",
    "account": "KC NEXT ADKING#EUW",
    "puuid": "abc...xyz",           # null if account not found
    "ranked_match_ids": ["EUW1_123", ...]
  }

Only accounts with a valid Riot ID format (gameName#tagLine) are processed.
Old summoner name format (no #) is skipped — Riot removed the resolution endpoint
after the migration to Riot IDs in November 2023.

Usage:
    uv run python -m ingestion.riot_api.ingest
    uv run python -m ingestion.riot_api.ingest --silver-date 2026-06-05
"""

import argparse
import json
import time
from datetime import UTC, datetime

import httpx

from ingestion.utils import gcs_client, logger, send_discord_notification, settings

from .config import MATCH_IDS_PER_PLAYER, RANKED_SOLO_QUEUE, RIOT_API_BASE, SLEEP_BETWEEN_CALLS


def load_silver_lfl_players(bucket_name: str, date: str) -> list[dict]:
    """Download and parse the Silver lfl_players NDJSON file from GCS."""
    path = f"silver/leaguepedia/lfl_players/{date}.json"
    with gcs_client() as client:
        blob = client.bucket(bucket_name).blob(path)
        content = blob.download_as_text(encoding="utf-8")
    rows = [json.loads(line) for line in content.splitlines() if line.strip()]
    logger.info("Loaded %d players from gs://%s/%s", len(rows), bucket_name, path)
    return rows


def upload_ndjson_to_gcs(bucket_name: str, destination: str, records: list[dict]) -> None:
    """Write a list of dicts as NDJSON to GCS Bronze."""
    content = "\n".join(json.dumps(row) for row in records)
    with gcs_client() as client:
        blob = client.bucket(bucket_name).blob(destination)
        blob.metadata = {
            "source": "riot_api",
            "ingestion_date": datetime.now(UTC).isoformat(),
            "record_count": str(len(records)),
        }
        blob.upload_from_string(content, content_type="application/x-ndjson")
    logger.info("Uploaded %d records to gs://%s/%s", len(records), bucket_name, destination)


# Riot ID validation and parsing


def is_riot_id(account: str) -> bool:
    """Return True if the account string is in gameName#tagLine format.

    Examples:
        "KC NEXT ADKING#EUW"  → True
        "banger5"             → False (old summoner name)
        "Achuu (EUW)"         → False (no # separator)
    """
    parts = account.split("#")
    return len(parts) == 2 and bool(parts[0].strip()) and bool(parts[1].strip())


def parse_riot_id(account: str) -> tuple[str, str]:
    """Split a valid Riot ID into (game_name, tag_line).

    Assumes is_riot_id(account) is True.

    Examples:
        "KC NEXT ADKING#EUW"  → ("KC NEXT ADKING", "EUW")
        "G2 Hans Sama#12838"  → ("G2 Hans Sama", "12838")
    """
    game_name, tag_line = account.split("#", maxsplit=1)
    return game_name.strip(), tag_line.strip()


# Riot API calls


def _headers(api_key: str) -> dict:
    """Return the authentication headers required by the Riot API."""
    return {"X-Riot-Token": api_key}


def fetch_puuid(game_name: str, tag_line: str, api_key: str) -> str | None:
    """Fetch the PUUID for a Riot ID from the Account API.

    Returns the PUUID string (78 characters), or None if not found or on error.

    Endpoint: GET /riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}
    """
    url = f"{RIOT_API_BASE}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    try:
        response = httpx.get(url, headers=_headers(api_key), timeout=10)
        if response.status_code == 404:
            logger.warning("Account not found: %s#%s", game_name, tag_line)
            return None
        response.raise_for_status()
        return response.json()["puuid"]
    except httpx.HTTPError as exc:
        logger.warning("HTTP error fetching PUUID for %s#%s: %s", game_name, tag_line, exc)
        return None


def fetch_ranked_match_ids(
    puuid: str, api_key: str, count: int = MATCH_IDS_PER_PLAYER
) -> list[str]:
    """Fetch the most recent ranked solo match IDs for a given PUUID.

    Returns a list of match ID strings, or an empty list on error.

    Endpoint: GET /lol/match/v5/matches/by-puuid/{puuid}/ids
    Params: queue=420 (Ranked Solo/Duo), type=ranked, count=0-100
    Note: queue and type filters are mutually inclusive — both must be set together.
    """
    url = f"{RIOT_API_BASE}/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {"queue": RANKED_SOLO_QUEUE, "type": "ranked", "count": count}
    try:
        response = httpx.get(url, headers=_headers(api_key), params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        logger.warning("HTTP error fetching match IDs for puuid %s...: %s", puuid[:12], exc)
        return []


# Orchestration


def run_ingestion(silver_date: str) -> None:
    """Fetch PUUIDs and ranked match IDs for all LFL players with valid Riot IDs.

    Args:
        silver_date: Date of the Silver lfl_players file to read (YYYY-MM-DD).
    """
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    bucket = settings.gcs_bucket_name
    api_key = settings.riot_api

    logger.info("Starting Riot API ingestion — silver date: %s", silver_date)

    players = load_silver_lfl_players(bucket, silver_date)

    # Collect all (player, account) pairs with a valid Riot ID format
    valid_accounts: list[tuple[str, str]] = []
    skipped = 0
    for row in players:
        for account in row.get("euw_accounts", []):
            if is_riot_id(account):
                valid_accounts.append((row["player"], account))
            else:
                skipped += 1

    logger.info(
        "Accounts to process: %d — skipped old-format accounts: %d",
        len(valid_accounts),
        skipped,
    )

    if not valid_accounts:
        msg = "No valid Riot IDs found in Silver lfl_players — aborting."
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    results = []
    total = len(valid_accounts)

    for i, (player, account) in enumerate(valid_accounts, start=1):
        game_name, tag_line = parse_riot_id(account)
        logger.info("[%d/%d] %s — %s#%s", i, total, player, game_name, tag_line)

        puuid = fetch_puuid(game_name, tag_line, api_key)
        time.sleep(SLEEP_BETWEEN_CALLS)

        match_ids = []
        if puuid is not None:
            match_ids = fetch_ranked_match_ids(puuid, api_key)
            time.sleep(SLEEP_BETWEEN_CALLS)
            logger.info("  → %d ranked match IDs", len(match_ids))
        else:
            logger.info("  → PUUID not found, skipping match IDs fetch")

        results.append(
            {
                "player": player,
                "account": account,
                "puuid": puuid,
                "ranked_match_ids": match_ids,
            }
        )

    destination = f"bronze/riot_api/{today}.ndjson"
    upload_ndjson_to_gcs(bucket, destination, results)

    found = sum(1 for r in results if r["puuid"] is not None)
    gcs_uri = f"gs://{bucket}/{destination}"
    msg = (
        f":white_check_mark: Riot API ingestion complete\n"
        f"URI: {gcs_uri}\n"
        f"Accounts processed: {total} | PUUIDs found: {found} | Not found: {total - found}"
    )
    logger.info(msg)
    send_discord_notification(msg)


# CLI


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch Riot PUUIDs and ranked match IDs for LFL players with EUW accounts."
    )
    parser.add_argument(
        "--silver-date",
        default=datetime.now(UTC).strftime("%Y-%m-%d"),
        help="Date of the Silver lfl_players file to read (default: today).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_ingestion(silver_date=args.silver_date)
