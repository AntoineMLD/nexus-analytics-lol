"""BigQuery query helpers for the Nexus Analytics API.

All queries target the Gold dataset (dbt-materialized tables).
Results are returned as lists of plain dicts for easy Pydantic parsing.

Project and dataset are read from pydantic-settings to avoid hardcoding.
"""

from google.cloud import bigquery

from ingestion.utils import settings

# Gold dataset name (dbt target schema)
GOLD_DATASET = "gold"


def _client() -> bigquery.Client:
    """Return a BigQuery client for the configured project."""
    return bigquery.Client(project=settings.gcp_project_id)


def _table(name: str) -> str:
    """Return the fully-qualified BigQuery table reference."""
    return f"`{settings.gcp_project_id}.{GOLD_DATASET}.{name}`"


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
        FROM {_table('dim_player')}
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


def query_player_by_id(player_id: str) -> dict | None:
    """Fetch full stats for a single player from dim_player.

    Returns None if the player does not exist.
    """
    sql = f"""
        SELECT *
        FROM {_table('dim_player')}
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
        FROM {_table('stg_lfl_matches')}
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
