"""Diagnostic: fetch raw wiki pages for missing LFL players to find SoloqueueIds."""

import json
import re

from ingestion.leaguepedia.ingest import build_esports_client
from ingestion.utils import gcs_client, settings

LFL_LEAGUES = {"La Ligue Française", "La Ligue Française Division 2"}

with gcs_client() as client:
    bucket = client.bucket(settings.gcs_bucket_name)
    s_lines = (
        bucket.blob("silver/leaguepedia/lfl_players/2026-06-04.json")
        .download_as_text()
        .splitlines()
    )
    t_lines = (
        bucket.blob("bronze/leaguepedia/Tournaments/2026-06-04.json")
        .download_as_text()
        .splitlines()
    )
    r_lines = (
        bucket.blob("bronze/leaguepedia/TournamentRosters/2026-06-04.json")
        .download_as_text()
        .splitlines()
    )

silver = {json.loads(line)["player"]: json.loads(line)["euw_accounts"] for line in s_lines}
tournaments = [json.loads(line) for line in t_lines]
rosters = [json.loads(line) for line in r_lines]

lfl_pages_2026 = {
    t["OverviewPage"]
    for t in tournaments
    if t.get("League") in LFL_LEAGUES and "2026" in t.get("OverviewPage", "")
}

active_players: set[str] = set()
for roster in rosters:
    if roster.get("OverviewPage") not in lfl_pages_2026:
        continue
    for player in (roster.get("RosterLinks") or "").split(";;"):
        player = player.strip()
        if player:
            active_players.add(player)

missing = sorted(p for p in active_players if not silver.get(p))
print(f"Joueurs manquants à tester : {len(missing)}")

site = build_esports_client()

found = 0

# D'abord vérifier sur Caliste (qui a des comptes EUW) pour valider la regex
print("=== Test sur Caliste (joueur connu) ===")
try:
    page = site.client.pages["Caliste"]
    text = page.text()
    print(f"  Page existe: {page.exists}")
    print(f"  Wikitext (400 premiers chars): {repr(text[:400])}")
    ids_match = re.search(r"\|ids\s*=\s*([^\n\|]+)", text)
    print(f"  Regex match: {ids_match}")
except Exception as exc:
    print(f"  Caliste erreur: {exc}")

print("\n=== Joueurs manquants ===")
for player in missing[:10]:
    try:
        page = site.client.pages[player]
        if not page.exists:
            print(f"  {player}: page introuvable")
            continue
        text = page.text()
        if text.lower().startswith("#redirect"):
            print(f"  {player}: redirect → {text[10:60]}")
            continue
        ids_match = re.search(r"\|ids\s*=\s*([^\n\|]+)", text)
        if ids_match:
            raw = ids_match.group(1).strip()
            print(f"  {player}: ids = {repr(raw[:120])}")
            found += 1
        else:
            print(f"  {player}: champ |ids= vide ou absent")
    except Exception as exc:
        print(f"  {player}: erreur — {exc}")

print(f"\nTrouvé dans wikitext : {found}/10")
