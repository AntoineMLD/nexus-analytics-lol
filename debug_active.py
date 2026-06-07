"""Diagnostic: EUW coverage for active LFL players in 2026."""

import json

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

# LFL tournament pages from 2026 only
lfl_pages_2026 = {
    t["OverviewPage"]
    for t in tournaments
    if t.get("League") in LFL_LEAGUES and "2026" in t.get("OverviewPage", "")
}
print(f"Tournois LFL 2026 : {len(lfl_pages_2026)}")
print(sorted(lfl_pages_2026)[:10])

# Players from those rosters
active_players: set[str] = set()
for roster in rosters:
    if roster.get("OverviewPage") not in lfl_pages_2026:
        continue
    for player in (roster.get("RosterLinks") or "").split(";;"):
        player = player.strip()
        if player:
            active_players.add(player)

with_euw = [p for p in active_players if silver.get(p)]
without_euw = sorted(p for p in active_players if not silver.get(p))

print(f"\nJoueurs LFL actifs (saison 2026) : {len(active_players)}")
print(
    f"Avec comptes EUW                 : {len(with_euw)} ({100 * len(with_euw) // max(len(active_players), 1)}%)"
)
print(f"Sans comptes EUW                 : {len(without_euw)}")
print(f"\nPremiers manquants : {without_euw[:20]}")
