"""Silver transform: extract LFL players and their EUW Soloqueue IDs.

Reads (primary):
  - bronze/leaguepedia/Tournaments/{date}.json
  - bronze/leaguepedia/TournamentRosters/{date}.json
  - bronze/leaguepedia/Players/{date}.json          ← SoloqueueIds field

Reads (secondary — wiki scraping, enriches accounts not found in Cargo API):
  - bronze/leaguepedia_wiki/player_ids/{latest}.json  ← riot_ids from wiki pages

Writes:
  - silver/leaguepedia/lfl_players/{date}.json  (NDJSON, one player per line)

Each output row:
  {"player": "Caliste", "euw_accounts": ["KC NEXT ADKING#EUW", "I NEED SOLOQ#EUW"]}

Usage:
    uv run python -m pipeline.silver_transforms.lfl_players
    uv run python -m pipeline.silver_transforms.lfl_players --date 2026-06-05
"""

import argparse
import json
import re
from datetime import UTC, datetime

from ingestion.utils import gcs_client, logger, send_discord_notification, settings

LFL_LEAGUES = {"La Ligue Française", "La Ligue Française Division 2"}
ROSTER_LINK_DELIMITER = ";;"


def load_bronze_table(bucket_name: str, table_name: str, date: str) -> list[dict]:
    """Download and parse a Bronze NDJSON file from GCS."""
    path = f"bronze/leaguepedia/{table_name}/{date}.json"
    with gcs_client() as client:
        blob = client.bucket(bucket_name).blob(path)
        content = blob.download_as_text(encoding="utf-8")
    rows = [json.loads(line) for line in content.splitlines() if line.strip()]
    logger.info("Loaded %d rows from gs://%s/%s", len(rows), bucket_name, path)
    return rows


def filter_lfl_tournaments(tournaments: list[dict]) -> set[str]:
    """Return the OverviewPage values for all LFL (D1 + D2) tournaments."""
    lfl_pages = {row["OverviewPage"] for row in tournaments if row.get("League") in LFL_LEAGUES}
    logger.info("Found %d LFL tournament pages.", len(lfl_pages))
    return lfl_pages


def extract_players_from_rosters(rosters: list[dict], lfl_pages: set[str]) -> list[str]:
    """Return a deduplicated sorted list of LFL player wiki names from TournamentRosters.

    RosterLinks is a ';;'-delimited string of player wiki page names.
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


_REGION_WITH_COLON = re.compile(r"\b[A-Z]{2,}\s*:", re.MULTILINE)
_SERVER_SUFFIX = re.compile(r"\s*\([A-Z]{2,}\)\s*$")


def strip_wiki_markup(text: str) -> str:
    """Remove MediaWiki markup, converting <br> to newlines.

    Handles bold/italic markers ('''text''') and <br> tags.
    Each <br> becomes a newline so that accounts on separate lines stay separate.
    """
    text = re.sub(r"'{2,3}", "", text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    return text


def _split_accounts(section: str) -> list[str]:
    """Split a region section into individual account names.

    Handles both comma-separated and newline-separated lists.
    Strips server suffixes like '(EUW)' at the end of a name.
    """
    accounts = []
    for raw in re.split(r"[\n,]", section):
        name = _SERVER_SUFFIX.sub("", raw).strip()
        if len(name) > 1:
            accounts.append(name)
    return accounts


def parse_euw_accounts(soloqueue_text: str) -> list[str]:
    """Extract EUW account names from a SoloqueueIds field.

    The field can contain MediaWiki markup and three different formats:

    1. Riot ID with region markers:
       '''EUW:''' KC NEXT ADKING#EUW <br> I NEED SOLOQ#EUW <br> '''KR:''' KC Caliste#0001
       → ['KC NEXT ADKING#EUW', 'I NEED SOLOQ#EUW']

    2. Old summoner names with region markers:
       '''EUW:''' AbbedaggÆ <br> Mein Königreich <br> '''KR:''' 아베다게
       → ['AbbedaggÆ', 'Mein Königreich']

    3. No region markers (assumed EUW):
       Acidy          → ['Acidy']
       Achuu (EUW)    → ['Achuu']
       name1, name2   → ['name1', 'name2']
    """
    if not soloqueue_text:
        return []

    clean = strip_wiki_markup(soloqueue_text)

    if re.search(r"\bEUW\s*:", clean):
        euw_match = re.search(r"EUW\s*:(.*?)(?:\b[A-Z]{2,}\s*:|$)", clean, re.DOTALL)
        if not euw_match:
            return []
        return _split_accounts(euw_match.group(1))

    if _REGION_WITH_COLON.search(clean):
        return []

    return _split_accounts(clean)


def build_soloqueue_lookup(players_bronze: list[dict]) -> dict[str, list[str]]:
    """Build a mapping from player OverviewPage → list of EUW accounts.

    Uses OverviewPage as key because RosterLinks contains wiki page names.
    """
    lookup: dict[str, list[str]] = {}
    for row in players_bronze:
        overview_page = row.get("OverviewPage", "").strip()
        if not overview_page:
            continue
        euw_accounts = parse_euw_accounts(row.get("SoloqueueIds") or "")
        lookup[overview_page] = euw_accounts
    return lookup


def load_wiki_bronze(bucket_name: str) -> dict[str, list[str]]:
    """Load the most recent wiki scraping Bronze file and return a player→ids mapping.

    The wiki Bronze file contains riot_ids scraped from Leaguepedia player pages.
    This is a secondary source: it enriches players not found in the Cargo API.

    Returns an empty dict if no wiki Bronze file exists (non-blocking).
    """
    prefix = "bronze/leaguepedia_wiki/player_ids/"
    try:
        with gcs_client() as client:
            blobs = sorted(
                client.bucket(bucket_name).list_blobs(prefix=prefix),
                key=lambda b: b.name,
            )
        if not blobs:
            logger.info("No wiki Bronze file found — skipping secondary enrichment.")
            return {}
        latest_blob = blobs[-1]
        with gcs_client() as client:
            content = client.bucket(bucket_name).blob(latest_blob.name).download_as_text()
        rows = [json.loads(line) for line in content.splitlines() if line.strip()]
        lookup = {
            row["player"]: row.get("riot_ids", [])
            for row in rows
            if row.get("player") and row.get("riot_ids")
        }
        logger.info(
            "Loaded wiki Bronze from gs://%s/%s — %d players with ids.",
            bucket_name,
            latest_blob.name,
            len(lookup),
        )
        return lookup
    except Exception as exc:
        logger.warning("Could not load wiki Bronze (non-blocking): %s", exc)
        return {}


def merge_soloqueue_lookups(
    cargo_lookup: dict[str, list[str]],
    wiki_lookup: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Merge Cargo API and wiki lookups, with wiki IDs taking priority.

    For each player:
    - If wiki has IDs: use wiki IDs (more up-to-date format: gameName#tagLine)
    - If only Cargo has IDs: use Cargo IDs
    - If neither: empty list

    Args:
        cargo_lookup: player OverviewPage → EUW accounts (from Cargo API)
        wiki_lookup: player name → riot IDs (from wiki scraping)
    """
    merged: dict[str, list[str]] = {}
    all_players = set(cargo_lookup.keys()) | set(wiki_lookup.keys())
    for player in all_players:
        wiki_ids = wiki_lookup.get(player, [])
        cargo_ids = cargo_lookup.get(player, [])
        merged[player] = wiki_ids if wiki_ids else cargo_ids
    wiki_enriched = sum(1 for p in cargo_lookup if wiki_lookup.get(p) and not cargo_lookup.get(p))
    logger.info(
        "Merged lookups: %d players total, %d enriched by wiki (had no Cargo IDs).",
        len(merged),
        wiki_enriched,
    )
    return merged


def enrich_players(player_names: list[str], soloqueue_lookup: dict[str, list[str]]) -> list[dict]:
    """Combine player names with their EUW accounts.

    Players without EUW accounts are kept (euw_accounts=[]) for completeness.
    """
    return [
        {"player": name, "euw_accounts": soloqueue_lookup.get(name, [])} for name in player_names
    ]


def save_to_gcs(players: list[dict], bucket_name: str, date: str) -> None:
    """Write the enriched player list to GCS Silver layer as NDJSON."""
    if not players:
        msg = "No LFL players found — aborting Silver write."
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    destination = f"silver/leaguepedia/lfl_players/{date}.json"
    content = "\n".join(json.dumps(row) for row in players)

    with_accounts = sum(1 for p in players if p["euw_accounts"])

    with gcs_client() as client:
        blob = client.bucket(bucket_name).blob(destination)
        blob.metadata = {
            "source": "leaguepedia",
            "transform": "lfl_players",
            "date": date,
            "player_count": str(len(players)),
            "with_euw_accounts": str(with_accounts),
        }
        blob.upload_from_string(content, content_type="application/json")

    gcs_uri = f"gs://{bucket_name}/{destination}"
    msg = (
        f":white_check_mark: Silver transform success — lfl_players\n"
        f"URI: {gcs_uri}\n"
        f"Players: {len(players)} | With EUW accounts: {with_accounts}"
    )
    logger.info(msg)
    send_discord_notification(msg)


def run_transform(
    date: str,
    players_date: str | None = None,
    rosters_date: str | None = None,
) -> None:
    """Orchestrate the LFL players Silver transform for a given date.

    Args:
        date: Ingestion date for Tournaments (format: YYYY-MM-DD).
        players_date: Ingestion date for Players table (defaults to date).
        rosters_date: Ingestion date for TournamentRosters (defaults to date).
    """
    bucket = settings.gcs_bucket_name
    effective_players_date = players_date or date
    effective_rosters_date = rosters_date or date

    tournaments = load_bronze_table(bucket, "Tournaments", date)
    rosters = load_bronze_table(bucket, "TournamentRosters", effective_rosters_date)
    players_bronze = load_bronze_table(bucket, "Players", effective_players_date)

    lfl_pages = filter_lfl_tournaments(tournaments)
    if not lfl_pages:
        msg = f"No LFL tournaments found in Tournaments Bronze ({date})."
        logger.error(msg)
        send_discord_notification(f":x: {msg}")
        return

    player_names = extract_players_from_rosters(rosters, lfl_pages)
    cargo_lookup = build_soloqueue_lookup(players_bronze)
    wiki_lookup = load_wiki_bronze(bucket)
    soloqueue_lookup = merge_soloqueue_lookups(cargo_lookup, wiki_lookup)
    enriched = enrich_players(player_names, soloqueue_lookup)

    save_to_gcs(enriched, bucket, date)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Extract LFL players and EUW Soloqueue IDs from Bronze to Silver."
    )
    parser.add_argument(
        "--date",
        default=datetime.now(UTC).strftime("%Y-%m-%d"),
        help="Ingestion date for Tournaments and TournamentRosters (default: today).",
    )
    parser.add_argument(
        "--players-date",
        default=None,
        help="Ingestion date for Players table (default: same as --date).",
    )
    parser.add_argument(
        "--rosters-date",
        default=None,
        help="Ingestion date for TournamentRosters (default: same as --date).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_transform(
        date=args.date,
        players_date=args.players_date,
        rosters_date=args.rosters_date,
    )
