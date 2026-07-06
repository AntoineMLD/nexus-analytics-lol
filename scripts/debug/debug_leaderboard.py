"""Diagnostic: match LFL active players against EUW Master+ leaderboard."""

import json
import time

import httpx

from ingestion.utils import gcs_client, settings

LFL_LEAGUES = {"La Ligue Française", "La Ligue Française Division 2"}
RIOT_BASE = "https://euw1.api.riotgames.com"
HEADERS = {"X-Riot-Token": settings.api_key}


def fetch_tier(queue: str, tier: str) -> list[dict]:
    url = f"{RIOT_BASE}/lol/league-exp/v4/entries/{queue}/{tier}/I"
    r = httpx.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()


# --- Load active LFL 2026 players ---
with gcs_client() as client:
    bucket = client.bucket(settings.gcs_bucket_name)
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

print(f"Joueurs LFL actifs 2026 : {len(active_players)}")

# Normalize names for fuzzy matching
lfl_lower = {p.lower(): p for p in active_players}

# --- Fetch EUW Master+ leaderboard ---
print("Fetching Challenger...")
challenger = fetch_tier("RANKED_SOLO_5x5", "CHALLENGER")
time.sleep(1)
print(f"  {len(challenger)} entries")

print("Fetching Grandmaster...")
grandmaster = fetch_tier("RANKED_SOLO_5x5", "GRANDMASTER")
time.sleep(1)
print(f"  {len(grandmaster)} entries")

print("Fetching Master...")
master = fetch_tier("RANKED_SOLO_5x5", "MASTER")
print(f"  {len(master)} entries")

all_entries = challenger + grandmaster + master
print(f"\nTotal EUW Master+ : {len(all_entries)} joueurs")

# --- Cross-reference ---
leaderboard = {entry["summonerName"].lower(): entry for entry in all_entries}

matched = []
for name_lower, original in lfl_lower.items():
    if name_lower in leaderboard:
        entry = leaderboard[name_lower]
        matched.append(
            {
                "player": original,
                "tier": entry["tier"],
                "rank": entry["rank"],
                "lp": entry["leaguePoints"],
                "wins": entry["wins"],
                "losses": entry["losses"],
                "summonerId": entry["summonerId"],
            }
        )

print(f"\nLFL players matchés dans Master+ : {len(matched)}/{len(active_players)}")
print("\nMatchés :")
for m in sorted(matched, key=lambda x: -x["lp"]):
    print(
        f"  {m['player']:<25} {m['tier']} {m['rank']} {m['lp']} LP  ({m['wins']}W/{m['losses']}L)"
    )
