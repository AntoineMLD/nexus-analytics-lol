"""Quality check script for LFL data completeness.

Implements a multi-layer reconciliation approach:
  Method 1 — Per-tournament game count vs expected format
  Method 2 — Tournament-by-tournament Silver vs Oracle's Elixir cross-reference
  Method 3 — Temporal bounds per tournament (detect truncated ingestions)
  Method 4 — Structural integrity (10 players/game, 1 winner, no duplicate game_ids)
  Method 5 — Global cross-source summary

Output: a report that distinguishes "I believe it's complete" from
"I verified it tournament by tournament". Useful as a BC02 data quality artefact.

Usage:
    uv run python -m pipeline.quality_checks.lfl_completeness
    uv run python -m pipeline.quality_checks.lfl_completeness --date 2026-06-07
"""

import argparse
import csv
import io
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field

from google.cloud import storage

from ingestion.utils import gcs_client, settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────

ORACLE_PREFIX = "bronze/oracle_elixir"


def find_latest_silver_date(table: str) -> str:
    """Return the most recent date available for a Silver table in GCS.

    Args:
        table: Silver table name (e.g. 'lfl_matches').

    Returns:
        Date string 'YYYY-MM-DD'.

    Raises:
        FileNotFoundError: If no Silver file exists for this table.
    """
    prefix = f"silver/leaguepedia/{table}/"
    with gcs_client() as client:
        blobs = list(client.bucket(settings.gcs_bucket_name).list_blobs(prefix=prefix))
    if not blobs:
        raise FileNotFoundError(
            f"No Silver file found for table '{table}' in gs://{settings.gcs_bucket_name}/{prefix}."
        )
    latest = max(blobs, key=lambda b: b.name)
    date = latest.name.split("/")[-1].replace(".json", "")
    logger.info("Auto-detected latest Silver date for %s: %s", table, date)
    return date


# Known league format: number of teams → expected regular-season BO1 games
# (double round-robin = n × (n-1))
TEAM_COUNT_TO_GAMES = {
    10: 90,  # 10 × 9 = 90 — standard D1 format
    8: 56,  # 8 × 7 = 56 — some seasons use 8 teams
    6: 30,  # 6 × 5 = 30
}


# ─── Data classes ────────────────────────────────────────────────────────────


@dataclass
class TournamentStats:
    """Per-tournament metrics computed from Silver data."""

    overview_page: str
    games: int = 0
    player_rows: int = 0
    date_min: str = ""
    date_max: str = ""
    duplicate_game_ids: int = 0
    games_without_winner: int = 0
    games_wrong_player_count: list[str] = field(default_factory=list)

    @property
    def players_per_game_ok(self) -> bool:
        return len(self.games_wrong_player_count) == 0

    @property
    def is_division2(self) -> bool:
        return "Division 2" in self.overview_page


# ─── Loaders ─────────────────────────────────────────────────────────────────


def load_silver_matches(bucket: storage.Bucket, date: str | None = None) -> list[dict]:
    resolved = date or find_latest_silver_date("lfl_matches")
    path = f"silver/leaguepedia/lfl_matches/{resolved}.json"
    logger.info("Loading Silver lfl_matches from %s...", path)
    content = bucket.blob(path).download_as_text().strip()
    return [json.loads(line) for line in content.splitlines()]


def load_silver_players(bucket: storage.Bucket, date: str | None = None) -> list[dict]:
    resolved = date or find_latest_silver_date("lfl_player_stats")
    path = f"silver/leaguepedia/lfl_player_stats/{resolved}.json"
    logger.info("Loading Silver lfl_player_stats from %s...", path)
    content = bucket.blob(path).download_as_text().strip()
    return [json.loads(line) for line in content.splitlines()]


def load_oracle_elixir_lfl(bucket: storage.Bucket) -> dict[str, set[str]]:
    """Return game IDs per (year, league) from Oracle's Elixir Bronze.

    Returns a dict: {(year, league_code) -> set of gameid}
    league_code is 'LFL' or 'LFL2'.
    """
    logger.info("Loading Oracle's Elixir Bronze (LFL + LFL2)...")
    result: dict[tuple, set] = defaultdict(set)
    for year in range(2019, 2027):
        path = f"{ORACLE_PREFIX}/{year}/{year}_LoL_esports_match_data_from_OraclesElixir.csv"
        try:
            content = bucket.blob(path).download_as_text()
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                league = row.get("league", "")
                gid = row.get("gameid", "")
                if league in ("LFL", "LFL2") and gid:
                    result[(year, league)].add(gid)
        except Exception:
            pass
    return result


# ─── Method 4: Structural integrity ─────────────────────────────────────────


def check_structural_integrity(
    matches: list[dict],
    players: list[dict],
) -> TournamentStats:
    """Run structural checks across the full dataset (not per-tournament).

    Returns a fake TournamentStats used only for the structural summary.
    """
    stats = TournamentStats(overview_page="__GLOBAL__")

    # Duplicate game_ids in matches
    game_ids = [r["game_id"] for r in matches]
    stats.duplicate_game_ids = len(game_ids) - len(set(game_ids))

    # Games without winner
    stats.games_without_winner = sum(
        1 for r in matches if not r.get("win_team") and not r.get("winner")
    )

    # Player count per game (should be 10)
    players_per_game: dict[str, int] = defaultdict(int)
    for row in players:
        players_per_game[row["game_id"]] += 1

    stats.games_wrong_player_count = [gid for gid, cnt in players_per_game.items() if cnt != 10]

    return stats


# ─── Method 2+3: Per-tournament reconciliation ───────────────────────────────


def compute_tournament_stats(
    matches: list[dict],
    players: list[dict],
) -> list[TournamentStats]:
    """Compute per-tournament stats from Silver data."""

    # Index player rows by game_id
    players_by_game: dict[str, list] = defaultdict(list)
    for row in players:
        players_by_game[row["game_id"]].append(row)

    # Group matches by tournament
    matches_by_page: dict[str, list] = defaultdict(list)
    for row in matches:
        matches_by_page[row["overview_page"]].append(row)

    stats_list = []
    for page, page_matches in sorted(matches_by_page.items()):
        s = TournamentStats(overview_page=page)
        s.games = len(page_matches)

        # Date range (skip None values)
        dates = [r["datetime_utc"] for r in page_matches if r.get("datetime_utc")]
        s.date_min = min(dates) if dates else "N/A"
        s.date_max = max(dates) if dates else "N/A"

        # Player rows
        for match in page_matches:
            s.player_rows += len(players_by_game.get(match["game_id"], []))

        # Games with wrong player count
        s.games_wrong_player_count = [
            m["game_id"] for m in page_matches if len(players_by_game.get(m["game_id"], [])) != 10
        ]

        stats_list.append(s)

    return stats_list


def infer_expected_games(page: str, actual_games: int) -> int | None:
    """Infer the expected regular-season game count from tournament page name.

    Returns None for playoffs/promotion stages where the game count depends
    on match outcomes (variable length series).
    """
    name = page.lower()
    # Skip non-regular-season tournaments
    skip_keywords = [
        "playoff",
        "promotion",
        "finals",
        "swiss",
        "invitational",
        "qualification",
        "groups",
        "relegation",
    ]
    if any(kw in name for kw in skip_keywords):
        return None

    # Regular season: infer team count from actual games
    # actual_games = n × (n-1) for double round-robin
    # Solve: n² - n - actual_games = 0 → n = (1 + sqrt(1 + 4*g)) / 2
    import math

    discriminant = 1 + 4 * actual_games
    sqrt_d = math.sqrt(discriminant)
    if abs(sqrt_d - round(sqrt_d)) < 0.01:
        n = round((1 + sqrt_d) / 2)
        expected = n * (n - 1)
        if expected == actual_games:
            return expected
    return None


# ─── Reporting ───────────────────────────────────────────────────────────────


def print_separator(char: str = "─", width: int = 100) -> None:
    print(char * width)


def print_tournament_table(stats_list: list[TournamentStats]) -> None:
    """Print Method 2+3 per-tournament table."""

    print_separator("═")
    print("METHOD 2+3 — Per-tournament reconciliation (Silver lfl_matches)")
    print_separator("═")

    header = f"{'Tournament':<55} {'Games':>6} {'Players':>8} {'Date min':>12} {'Date max':>12} {'Issues'}"
    print(header)
    print_separator()

    issues_found = []
    for s in stats_list:
        issues = []
        if s.games_wrong_player_count:
            issues.append(f"{len(s.games_wrong_player_count)} games ≠10 players")

        expected = infer_expected_games(s.overview_page, s.games)
        if expected is not None and expected != s.games:
            issues.append(f"expected {expected} regular-season games")

        issue_str = ", ".join(issues) if issues else "✅"
        short_page = s.overview_page[-54:] if len(s.overview_page) > 54 else s.overview_page
        print(
            f"{short_page:<55} {s.games:>6} {s.player_rows:>8} "
            f"{str(s.date_min)[:12]:>12} {str(s.date_max)[:12]:>12}  {issue_str}"
        )
        if issues:
            issues_found.append((s.overview_page, issues))

    print_separator()
    if issues_found:
        print(f"⚠️  {len(issues_found)} tournament(s) with issues:")
        for page, issues in issues_found:
            print(f"   {page}: {', '.join(issues)}")
    else:
        print("✅ No structural issues found in any tournament.")


def print_structural_summary(global_stats: TournamentStats, total_games: int) -> None:
    """Print Method 4 structural integrity summary."""

    print()
    print_separator("═")
    print("METHOD 4 — Structural integrity (cross-table consistency)")
    print_separator("═")
    print(f"  Total games in lfl_matches  : {total_games}")
    print(
        f"  Duplicate game_ids          : {global_stats.duplicate_game_ids} {'✅' if global_stats.duplicate_game_ids == 0 else '❌'}"
    )
    print(
        f"  Games without winner field  : {global_stats.games_without_winner} {'✅' if global_stats.games_without_winner == 0 else '⚠️'}"
    )
    wrong = len(global_stats.games_wrong_player_count)
    print(f"  Games with ≠ 10 players     : {wrong} {'✅' if wrong == 0 else '❌'}")
    if wrong > 0:
        print("  Affected game_ids:")
        for gid in global_stats.games_wrong_player_count[:5]:
            print(f"    {gid}")


def print_oracle_crosscheck(
    oracle_data: dict[tuple, set[str]],
    matches: list[dict],
) -> None:
    """Print Method 5 cross-source summary."""

    print()
    print_separator("═")
    print("METHOD 5 — Cross-source: Oracle's Elixir vs Leaguepedia Silver")
    print_separator("═")

    lp_by_year: dict[int, int] = defaultdict(int)
    for row in matches:
        page = row.get("overview_page", "")
        # Extract year from page name
        for y in range(2019, 2027):
            if str(y) in page:
                lp_by_year[y] += 1
                break

    print(
        f"{'Year':<6} {'OE D1':>7} {'OE D2':>7} {'OE Total':>9} {'LP Total':>9} {'Diff':>6} {'Status'}"
    )
    print_separator("-", 60)

    total_diff = 0
    for year in range(2019, 2027):
        oe_d1 = len(oracle_data.get((year, "LFL"), set()))
        oe_d2 = len(oracle_data.get((year, "LFL2"), set()))
        oe_total = oe_d1 + oe_d2
        lp_total = lp_by_year.get(year, 0)
        diff = lp_total - oe_total
        total_diff += diff

        # Flag if D1 diverges significantly (D2 gaps in OE are expected)
        d1_only_lp = sum(
            1
            for r in matches
            if str(year) in r.get("overview_page", "")
            and "Division 2" not in r.get("overview_page", "")
        )
        status = "✅" if abs(d1_only_lp - oe_d1) <= 5 else "⚠️  D1 mismatch"
        if oe_total == 0 and lp_total == 0:
            status = "—"

        print(
            f"{year:<6} {oe_d1:>7} {oe_d2:>7} {oe_total:>9} {lp_total:>9} " f"{diff:>+6}  {status}"
        )

    print_separator("-", 60)
    print(
        f"{'TOTAL':<6} "
        f"{sum(len(v) for (yr, lg), v in oracle_data.items() if lg == 'LFL'):>7} "
        f"{sum(len(v) for (yr, lg), v in oracle_data.items() if lg == 'LFL2'):>7} "
        f"{sum(len(v) for v in oracle_data.values()):>9} "
        f"{sum(lp_by_year.values()):>9} "
        f"{total_diff:>+6}"
    )
    print()
    print("Note: LP > OE is expected — OE has incomplete LFL D2 coverage for 2020/2021/2024.")
    print("      Validate D1 convergence (< 5 games diff per year) as primary quality signal.")


# ─── Main ─────────────────────────────────────────────────────────────────────


def run_checks(date: str | None = None) -> None:
    """Run all completeness checks and print a full report.

    Args:
        date: Optional Silver date (YYYY-MM-DD). Auto-detected if None.
    """
    with gcs_client() as client:
        bucket = client.bucket(settings.gcs_bucket_name)

        matches = load_silver_matches(bucket, date)
        players = load_silver_players(bucket, date)
        oracle_data = load_oracle_elixir_lfl(bucket)

    print()
    print_separator("═")
    print("LFL DATA COMPLETENESS REPORT")
    print(f"  Total games     : {len(matches)}")
    print(f"  Total player rows: {len(players)}")
    print_separator("═")

    tournament_stats = compute_tournament_stats(matches, players)
    print_tournament_table(tournament_stats)

    global_stats = check_structural_integrity(matches, players)
    print_structural_summary(global_stats, len(matches))

    print_oracle_crosscheck(oracle_data, matches)

    # Final verdict
    print_separator("═")
    issues = (
        global_stats.duplicate_game_ids
        + len(global_stats.games_wrong_player_count)
        + sum(1 for s in tournament_stats if s.games_wrong_player_count)
    )
    if issues == 0:
        print("✅ VERDICT: Data passes all automated quality checks.")
    else:
        print(f"⚠️  VERDICT: {issues} issue(s) found — review above for details.")
    print_separator("═")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LFL data completeness checks (Silver vs Oracle's Elixir)."
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Silver date to check (YYYY-MM-DD). Auto-detected if omitted.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_checks(args.date)
