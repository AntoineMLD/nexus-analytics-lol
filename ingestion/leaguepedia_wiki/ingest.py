"""Scraping des pages wiki Leaguepedia pour récupérer les SoloqueueIds des joueurs LFL.

Lit la liste des joueurs depuis Silver lfl_players, puis scrape chaque page wiki
pour extraire le champ `|ids=` (comptes SoloQueue Riot des joueurs).

Sauvegarde les résultats bruts dans GCS Bronze :
    bronze/leaguepedia_wiki/player_ids/{YYYY-MM-DD}.json

Chaque ligne NDJSON contient :
    {
        "player": "Caliste",
        "riot_ids": ["Caliste#EUW"],
        "source": "leaguepedia_wiki",
        "ingested_at": "2026-07-06T14:00:00Z",
        "schema_version": "1",
        "md5": "<md5 du champ riot_ids sérialisé>"
    }

Usage :
    uv run python -m ingestion.leaguepedia_wiki.ingest
    uv run python -m ingestion.leaguepedia_wiki.ingest --silver-date 2026-06-04
    uv run python -m ingestion.leaguepedia_wiki.ingest --limit 20
"""

import argparse
import hashlib
import json
import re
import time
from datetime import UTC, datetime

from ingestion.leaguepedia.ingest import build_esports_client
from ingestion.utils import (
    gcs_client,
    logger,
    send_discord_notification,
    settings,
    verify_gcs_object_exists,
)

# Regex qui capture tout ce qui suit "|ids =" jusqu'à la prochaine pipe, accolade ou fin de ligne.
_IDS_PATTERN = re.compile(r"\|ids\s*=\s*([^\n\|{}]+)")

# Délai minimum entre deux requêtes wiki (règle anti-ban cursorrules).
_REQUEST_DELAY_SECONDS = 2

GCS_PREFIX = "bronze/leaguepedia_wiki/player_ids"


def load_player_names_from_silver(silver_date: str) -> list[str]:
    """Return all player names present in Silver lfl_players for the given date.

    Reads the NDJSON Silver file and extracts the `player` field from each row.

    Args:
        silver_date: Date string (YYYY-MM-DD) of the Silver lfl_players file.
    """
    path = f"silver/leaguepedia/lfl_players/{silver_date}.json"
    with gcs_client() as client:
        text = client.bucket(settings.gcs_bucket_name).blob(path).download_as_text()
    players = [json.loads(line)["player"] for line in text.splitlines() if line.strip()]
    logger.info("Loaded %d player names from Silver (%s).", len(players), path)
    return players


def find_latest_silver_date() -> str:
    """Return the date of the most recent Silver lfl_players file in GCS.

    Raises:
        RuntimeError: If no Silver lfl_players file exists.
    """
    prefix = "silver/leaguepedia/lfl_players/"
    with gcs_client() as client:
        blobs = list(client.bucket(settings.gcs_bucket_name).list_blobs(prefix=prefix))
    if not blobs:
        raise RuntimeError(
            f"No Silver lfl_players file found under gs://{settings.gcs_bucket_name}/{prefix}"
        )
    latest = sorted(blobs, key=lambda b: b.name)[-1]
    # Extract date from path: silver/leaguepedia/lfl_players/YYYY-MM-DD.json
    return latest.name.split("/")[-1].replace(".json", "")


def extract_riot_ids(wikitext: str) -> list[str]:
    """Parse the `|ids=` field from a Leaguepedia wiki page wikitext.

    The field may contain comma-separated or semicolon-separated account names.
    Strips whitespace and filters empty strings.

    Args:
        wikitext: Raw wikitext content of a Leaguepedia player page.

    Returns:
        List of account name strings found in `|ids=`. Empty list if not found.

    Example:
        >>> extract_riot_ids("{{Infobox|ids=Caliste#EUW, CalysteOP#EUW}}")
        ['Caliste#EUW', 'CalysteOP#EUW']
    """
    match = _IDS_PATTERN.search(wikitext)
    if not match:
        return []
    raw = match.group(1).strip()
    parts = re.split(r"[,;]+", raw)
    return [p.strip() for p in parts if p.strip()]


def fetch_player_wiki_data(site, player_name: str) -> dict:
    """Fetch and parse a single player's wiki page.

    Returns a dict with `player`, `riot_ids`, and `page_exists` fields.
    On any exception, logs the error and returns an empty riot_ids list.

    Args:
        site: Authenticated EsportsClient instance.
        player_name: Wiki page name of the player (e.g. "Caliste").
    """
    try:
        page = site.client.pages[player_name]
        if not page.exists:
            logger.debug("Wiki page not found for player: %s", player_name)
            return {"player": player_name, "riot_ids": [], "page_exists": False}

        text = page.text()

        if text.lower().startswith("#redirect"):
            logger.debug("Wiki page is a redirect for player: %s", player_name)
            return {"player": player_name, "riot_ids": [], "page_exists": True}

        riot_ids = extract_riot_ids(text)
        return {"player": player_name, "riot_ids": riot_ids, "page_exists": True}

    except Exception as exc:
        logger.error("Error fetching wiki page for %s: %s", player_name, exc)
        return {"player": player_name, "riot_ids": [], "page_exists": False}


def build_bronze_row(player_data: dict, ingested_at: str) -> dict:
    """Add Bronze metadata fields to a scraped player row.

    Adds: source, ingested_at, schema_version, md5.

    Args:
        player_data: Dict from fetch_player_wiki_data.
        ingested_at: ISO 8601 timestamp string.
    """
    payload = json.dumps(player_data["riot_ids"], sort_keys=True)
    return {
        "player": player_data["player"],
        "riot_ids": player_data["riot_ids"],
        "page_exists": player_data["page_exists"],
        "source": "leaguepedia_wiki",
        "ingested_at": ingested_at,
        "schema_version": "1",
        "md5": hashlib.md5(payload.encode()).hexdigest(),
    }


def save_to_bronze(rows: list[dict], date: str) -> str:
    """Upload scraped rows as NDJSON to GCS Bronze.

    Args:
        rows: List of Bronze row dicts.
        date: Date string (YYYY-MM-DD) used as filename.

    Returns:
        GCS destination path.
    """
    destination = f"{GCS_PREFIX}/{date}.json"
    ndjson = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    with gcs_client() as client:
        bucket = client.bucket(settings.gcs_bucket_name)
        bucket.blob(destination).upload_from_string(ndjson, content_type="application/ndjson")
    logger.info("Uploaded %d rows to gs://%s/%s", len(rows), settings.gcs_bucket_name, destination)
    return destination


def run_scraping(date: str, silver_date: str, limit: int | None = None) -> None:
    """Main scraping pipeline: Silver lfl_players → wiki pages → GCS Bronze.

    1. Loads player names from Silver lfl_players.
    2. For each player, fetches the wiki page and extracts SoloqueueIds.
    3. Saves all results to GCS Bronze.

    Args:
        date: Output Bronze file date (YYYY-MM-DD).
        silver_date: Date of the Silver lfl_players file to use as input.
        limit: Optional max number of players to scrape (for dev/testing).
    """
    destination = f"{GCS_PREFIX}/{date}.json"
    if verify_gcs_object_exists(settings.gcs_bucket_name, destination):
        logger.info("Bronze file already exists at %s — skipping.", destination)
        return

    players = load_player_names_from_silver(silver_date)
    if limit:
        players = players[:limit]
        logger.info("Limiting scraping to %d players.", limit)

    site = build_esports_client()
    ingested_at = datetime.now(UTC).isoformat()
    rows: list[dict] = []
    found_ids = 0

    for i, player_name in enumerate(players, start=1):
        logger.info("[%d/%d] Scraping wiki page: %s", i, len(players), player_name)
        data = fetch_player_wiki_data(site, player_name)
        row = build_bronze_row(data, ingested_at)
        rows.append(row)
        if row["riot_ids"]:
            found_ids += 1
        time.sleep(_REQUEST_DELAY_SECONDS)

    save_to_bronze(rows, date)

    summary = (
        f"✅ Wiki scraping terminé — {len(players)} joueurs traités, "
        f"{found_ids} avec SoloqueueIds trouvés."
    )
    logger.info(summary)
    send_discord_notification(summary)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the wiki scraping pipeline."""
    parser = argparse.ArgumentParser(
        description="Scrape les pages wiki Leaguepedia pour extraire les SoloqueueIds LFL."
    )
    parser.add_argument(
        "--date",
        default=datetime.now(UTC).strftime("%Y-%m-%d"),
        help="Date du fichier Bronze de sortie (défaut : aujourd'hui).",
    )
    parser.add_argument(
        "--silver-date",
        dest="silver_date",
        default=None,
        help="Date du fichier Silver lfl_players à utiliser (défaut : plus récent).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limite le nombre de joueurs scrapés (pour les tests).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    silver_date = args.silver_date or find_latest_silver_date()
    run_scraping(date=args.date, silver_date=silver_date, limit=args.limit)
