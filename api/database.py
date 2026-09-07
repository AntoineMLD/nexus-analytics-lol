"""BigQuery query helpers for the Nexus Analytics API.

All queries target the Gold dataset (dbt-materialized tables).
Results are returned as lists of plain dicts for easy Pydantic parsing.

Project and dataset are read from pydantic-settings to avoid hardcoding.
"""

from google.cloud import bigquery

from ingestion.utils import settings

# dbt génère les datasets en préfixant le dataset cible (gold) avec le +schema du modèle.
# Résultat dans BigQuery :
#   - dimensions et facts  → gold_gold
#   - vues staging          → gold_staging
DATASET_GOLD = "gold_gold"
DATASET_STAGING = "gold_staging"


def _client() -> bigquery.Client:
    """Return a BigQuery client for the configured project in europe-west1."""
    return bigquery.Client(project=settings.gcp_project_id, location="europe-west1")


def _table(dataset: str, name: str) -> str:
    """Return the fully-qualified BigQuery table reference."""
    return f"`{settings.gcp_project_id}.{dataset}.{name}`"


def query_players(
    min_games: int = 1,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Fetch player summaries from dim_player, ordered by total_games desc.

    Args:
        min_games: Only return players with at least this many games.
        limit:     Maximum number of rows to return (max 200).
        offset:    Number of rows to skip for pagination.
    """
    sql = f"""
        SELECT
            player_id,
            player_name,
            total_games,
            win_rate_pct,
            avg_kills,
            avg_deaths,
            avg_assists,
            avg_cs
        FROM {_table(DATASET_GOLD, "dim_player")}
        WHERE total_games >= @min_games
        ORDER BY total_games DESC
        LIMIT @limit
        OFFSET @offset
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("min_games", "INT64", min_games),
            bigquery.ScalarQueryParameter("limit", "INT64", min(limit, 200)),
            bigquery.ScalarQueryParameter("offset", "INT64", offset),
        ]
    )
    rows = _client().query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]


def query_champion_stats(
    min_games: int = 1,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Fetch champion stats from dim_champion, ordered by total_games_played desc.

    Args:
        min_games: Only return champions with at least this many games.
        limit:     Maximum rows to return (max 200).
        offset:    Pagination offset.
    """
    sql = f"""
        SELECT
            champion,
            total_games_played,
            total_picks,
            win_rate_pct,
            avg_kills,
            avg_deaths,
            avg_assists,
            picks_top,
            picks_jungle,
            picks_mid,
            picks_bot,
            picks_support
        FROM {_table(DATASET_GOLD, "dim_champion")}
        WHERE total_games_played >= @min_games
        ORDER BY total_games_played DESC
        LIMIT @limit
        OFFSET @offset
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("min_games", "INT64", min_games),
            bigquery.ScalarQueryParameter("limit", "INT64", min(limit, 200)),
            bigquery.ScalarQueryParameter("offset", "INT64", offset),
        ]
    )
    rows = _client().query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]


def query_team_draft_history(
    team: str,
    patch: str | None = None,
    action_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Fetch draft actions for a specific team from fact_draft.

    Args:
        team:        Team name to filter on.
        patch:       Optional patch version filter (exact match).
        action_type: Optional filter: 'pick' or 'ban'.
        limit:       Maximum rows to return (max 200).
        offset:      Pagination offset.
    """
    sql = f"""
        SELECT
            game_id,
            overview_page,
            datetime_utc,
            patch,
            team_side,
            action_type,
            action_order,
            champion,
            team_won
        FROM {_table(DATASET_GOLD, "fact_draft")}
        WHERE team_name = @team
          AND (@patch IS NULL OR patch = @patch)
          AND (@action_type IS NULL OR action_type = @action_type)
        ORDER BY datetime_utc DESC, action_type, action_order
        LIMIT @limit
        OFFSET @offset
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("team", "STRING", team),
            bigquery.ScalarQueryParameter("patch", "STRING", patch),
            bigquery.ScalarQueryParameter("action_type", "STRING", action_type),
            bigquery.ScalarQueryParameter("limit", "INT64", min(limit, 200)),
            bigquery.ScalarQueryParameter("offset", "INT64", offset),
        ]
    )
    rows = _client().query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]


def query_meta_trends(
    patch: str | None = None,
    overview_page: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Fetch champion meta trends from fact_meta_trend, ordered by picks desc.

    Args:
        patch:         Optional patch version filter.
        overview_page: Optional tournament filter (exact match).
        limit:         Maximum rows to return (max 200).
        offset:        Pagination offset.
    """
    sql = f"""
        SELECT
            overview_page,
            patch,
            champion,
            picks,
            wins,
            pick_rate_pct,
            win_rate_pct
        FROM {_table(DATASET_GOLD, "fact_meta_trend")}
        WHERE
            (@patch IS NULL OR patch = @patch)
            AND (@overview_page IS NULL OR overview_page = @overview_page)
        ORDER BY picks DESC
        LIMIT @limit
        OFFSET @offset
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("patch", "STRING", patch),
            bigquery.ScalarQueryParameter("overview_page", "STRING", overview_page),
            bigquery.ScalarQueryParameter("limit", "INT64", min(limit, 200)),
            bigquery.ScalarQueryParameter("offset", "INT64", offset),
        ]
    )
    rows = _client().query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]


def query_player_by_id(player_id: str) -> dict | None:
    """Fetch full stats for a single player from dim_player.

    Returns None if the player does not exist.
    """
    sql = f"""
        SELECT *
        FROM {_table(DATASET_GOLD, "dim_player")}
        WHERE player_id = @player_id
        LIMIT 1
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("player_id", "STRING", player_id),
        ]
    )
    rows = list(_client().query(sql, job_config=job_config).result())
    return dict(rows[0]) if rows else None


def query_matches(
    team: str | None = None,
    season: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Fetch match summaries from stg_lfl_matches with optional filters.

    Args:
        team:   Filter to matches where this team played (team1 or team2).
        season: Filter by overview_page prefix (e.g. 'LFL/2025').
        limit:  Maximum rows to return (max 200).
        offset: Pagination offset.
    """
    sql = f"""
        SELECT
            game_id,
            match_id,
            overview_page,
            datetime_utc,
            team1,
            team2,
            win_team,
            gamelength_seconds,
            patch,
            n_game_in_match
        FROM {_table(DATASET_STAGING, "stg_lfl_matches")}
        WHERE
            (@team IS NULL OR team1 = @team OR team2 = @team)
            AND (@season IS NULL OR STARTS_WITH(overview_page, @season))
        ORDER BY datetime_utc DESC
        LIMIT @limit
        OFFSET @offset
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("team", "STRING", team),
            bigquery.ScalarQueryParameter("season", "STRING", season),
            bigquery.ScalarQueryParameter("limit", "INT64", min(limit, 200)),
            bigquery.ScalarQueryParameter("offset", "INT64", offset),
        ]
    )
    rows = _client().query(sql, job_config=job_config).result()
    return [dict(row) for row in rows]
