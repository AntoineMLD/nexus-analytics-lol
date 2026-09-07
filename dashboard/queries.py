"""BigQuery queries pour le dashboard Streamlit Nexus Analytics.

Retourne des DataFrames pandas, mis en cache via @st.cache_data
pour éviter les requêtes répétées pendant la session.

Les requêtes ciblent les tables Gold matérialisées par dbt.
"""

import pandas as pd
import streamlit as st
from google.cloud import bigquery

GCP_PROJECT = None  # chargé depuis st.secrets ou variable d'env au runtime
DATASET_GOLD = "gold_gold"
DATASET_STAGING = "gold_staging"


def _client() -> bigquery.Client:
    """Retourne un client BigQuery (ADC ou Service Account selon l'env)."""
    import os

    project = os.environ.get("GCP_PROJECT_ID", "")
    return bigquery.Client(project=project, location="europe-west1")


def _table(dataset: str, name: str) -> str:
    import os

    project = os.environ.get("GCP_PROJECT_ID", "")
    return f"`{project}.{dataset}.{name}`"


@st.cache_data(ttl=600, show_spinner=False)
def fetch_seasons() -> list[str]:
    """Liste des saisons/tournois distincts depuis stg_lfl_matches."""
    sql = f"""
        SELECT DISTINCT REGEXP_EXTRACT(overview_page, r'^[^/]+/[^/]+') AS season
        FROM {_table(DATASET_STAGING, "stg_lfl_matches")}
        WHERE overview_page IS NOT NULL
        ORDER BY season DESC
        LIMIT 40
    """
    rows = _client().query(sql).to_dataframe()
    return [r for r in rows["season"].tolist() if r]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_players(min_games: int = 5, season: str | None = None) -> pd.DataFrame:
    """Joueurs LFL avec stats agrégées et équipe actuelle — filtrables par saison."""
    if season:
        sql = f"""
            SELECT
                ps.player_link                                                          AS player_id,
                ps.player_name,
                t.current_team,
                COUNT(DISTINCT ps.game_id)                                              AS total_games,
                ROUND(COUNTIF(ps.player_win) * 100.0 / COUNT(*), 1)                    AS win_rate_pct,
                ROUND(AVG(ps.kills), 2)                                                 AS avg_kills,
                ROUND(AVG(ps.deaths), 2)                                                AS avg_deaths,
                ROUND(AVG(ps.assists), 2)                                               AS avg_assists,
                ROUND(AVG(ps.cs), 2)                                                    AS avg_cs,
                ROUND(SAFE_DIVIDE(AVG(ps.kills) + AVG(ps.assists),
                                  GREATEST(AVG(ps.deaths), 1)), 2)                     AS kda
            FROM {_table(DATASET_STAGING, "stg_lfl_player_stats")} ps
            JOIN {_table(DATASET_STAGING, "stg_lfl_matches")} m
              ON ps.game_id = m.game_id
            LEFT JOIN {_table(DATASET_GOLD, "dim_player_current_team")} t
              ON ps.player_link = t.player_id
            WHERE STARTS_WITH(m.overview_page, '{season}')
            GROUP BY ps.player_link, ps.player_name, t.current_team
            HAVING COUNT(DISTINCT ps.game_id) >= {min_games}
            ORDER BY total_games DESC
            LIMIT 200
        """
    else:
        sql = f"""
            SELECT
                p.player_id,
                p.player_name,
                t.current_team,
                p.total_games,
                p.win_rate_pct,
                p.avg_kills,
                p.avg_deaths,
                p.avg_assists,
                p.avg_cs,
                ROUND(SAFE_DIVIDE(p.avg_kills + p.avg_assists, GREATEST(p.avg_deaths, 1)), 2) AS kda
            FROM {_table(DATASET_GOLD, "dim_player")} p
            LEFT JOIN {_table(DATASET_GOLD, "dim_player_current_team")} t
              ON p.player_id = t.player_id
            WHERE p.total_games >= {min_games}
            ORDER BY p.total_games DESC
            LIMIT 200
        """
    return _client().query(sql).to_dataframe()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_champions(min_games: int = 3, season: str | None = None) -> pd.DataFrame:
    """Champions avec pick rates et win rates — filtrables par saison."""
    if season:
        sql = f"""
            SELECT
                ps.champion,
                COUNT(*)                                                AS total_games_played,
                ROUND(COUNTIF(ps.player_win) * 100.0 / COUNT(*), 1)    AS win_rate_pct,
                ROUND(AVG(ps.kills), 2)                                 AS avg_kills,
                ROUND(AVG(ps.deaths), 2)                                AS avg_deaths,
                ROUND(AVG(ps.assists), 2)                               AS avg_assists,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)      AS pick_rate_pct
            FROM {_table(DATASET_STAGING, "stg_lfl_player_stats")} ps
            JOIN {_table(DATASET_STAGING, "stg_lfl_matches")} m
              ON ps.game_id = m.game_id
            WHERE STARTS_WITH(m.overview_page, '{season}')
            GROUP BY ps.champion
            HAVING COUNT(*) >= {min_games}
            ORDER BY total_games_played DESC
            LIMIT 100
        """
    else:
        sql = f"""
            SELECT
                champion,
                total_games_played,
                win_rate_pct,
                avg_kills,
                avg_deaths,
                avg_assists,
                picks_top,
                picks_jungle,
                picks_mid,
                picks_bot,
                picks_support,
                ROUND(total_games_played * 100.0 / SUM(total_games_played) OVER (), 2) AS pick_rate_pct
            FROM {_table(DATASET_GOLD, "dim_champion")}
            WHERE total_games_played >= {min_games}
            ORDER BY total_games_played DESC
            LIMIT 100
        """
    return _client().query(sql).to_dataframe()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_player_champion_pool(player_name: str) -> pd.DataFrame:
    """Pool de champions d'un joueur — picks, winrate, rôle principal."""
    sql = f"""
        SELECT
            ps.champion,
            COUNT(*)                                                AS games,
            ROUND(COUNTIF(ps.player_win) * 100.0 / COUNT(*), 1)    AS win_rate_pct,
            ps.role,
            ROUND(AVG(ps.kills), 2)                                 AS avg_kills,
            ROUND(AVG(ps.deaths), 2)                                AS avg_deaths,
            ROUND(AVG(ps.assists), 2)                               AS avg_assists
        FROM {_table(DATASET_STAGING, "stg_lfl_player_stats")} ps
        WHERE ps.player_name = '{player_name}'
        GROUP BY ps.champion, ps.role
        ORDER BY games DESC
        LIMIT 30
    """
    return _client().query(sql).to_dataframe()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_player_names() -> list[str]:
    """Liste des noms de joueurs pour les sélecteurs."""
    sql = f"""
        SELECT DISTINCT player_name
        FROM {_table(DATASET_GOLD, "dim_player")}
        ORDER BY player_name
    """
    rows = _client().query(sql).to_dataframe()
    return rows["player_name"].tolist()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_player_stats_by_name(player_name: str) -> dict | None:
    """Stats complètes d'un joueur par nom, avec équipe actuelle et historique."""
    sql = f"""
        SELECT
            p.*,
            ROUND(SAFE_DIVIDE(p.avg_kills + p.avg_assists, GREATEST(p.avg_deaths, 1)), 2) AS kda,
            t.current_team,
            t.last_game_date,
            t.total_games_in_team,
            t.all_teams_played
        FROM {_table(DATASET_GOLD, "dim_player")} p
        LEFT JOIN {_table(DATASET_GOLD, "dim_player_current_team")} t
          ON p.player_id = t.player_id
        WHERE p.player_name = '{player_name}'
        LIMIT 1
    """
    rows = _client().query(sql).to_dataframe()
    return rows.iloc[0].to_dict() if not rows.empty else None


@st.cache_data(ttl=600, show_spinner=False)
def fetch_player_current_team(player_name: str) -> str | None:
    """Équipe actuelle d'un joueur (accès rapide)."""
    sql = f"""
        SELECT t.current_team
        FROM {_table(DATASET_GOLD, "dim_player")} p
        JOIN {_table(DATASET_GOLD, "dim_player_current_team")} t
          ON p.player_id = t.player_id
        WHERE p.player_name = '{player_name}'
        LIMIT 1
    """
    rows = _client().query(sql).to_dataframe()
    return rows.iloc[0]["current_team"] if not rows.empty else None


@st.cache_data(ttl=600, show_spinner=False)
def fetch_meta_by_patch(patch: str | None = None) -> pd.DataFrame:
    """Tendances méta par patch — pick rate et win rate par champion."""
    where = f"WHERE patch = '{patch}'" if patch else ""
    sql = f"""
        SELECT
            patch,
            champion,
            picks,
            wins,
            pick_rate_pct,
            win_rate_pct
        FROM {_table(DATASET_GOLD, "fact_meta_trend")}
        {where}
        ORDER BY picks DESC
        LIMIT 100
    """
    return _client().query(sql).to_dataframe()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_patches() -> list[str]:
    """Liste des patches disponibles dans fact_meta_trend."""
    sql = f"""
        SELECT DISTINCT patch
        FROM {_table(DATASET_GOLD, "fact_meta_trend")}
        WHERE patch IS NOT NULL
        ORDER BY patch DESC
    """
    rows = _client().query(sql).to_dataframe()
    return rows["patch"].tolist()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_teams() -> list[str]:
    """Liste des équipes LFL présentes dans dim_team."""
    sql = f"""
        SELECT team_name
        FROM {_table(DATASET_GOLD, "dim_team")}
        ORDER BY team_name
    """
    rows = _client().query(sql).to_dataframe()
    return rows["team_name"].tolist()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_team_draft(team: str, action_type: str | None = None) -> pd.DataFrame:
    """Historique de draft d'une équipe (picks et/ou bans)."""
    action_filter = f"AND action_type = '{action_type}'" if action_type else ""
    sql = f"""
        SELECT
            datetime_utc,
            patch,
            action_type,
            champion,
            action_order,
            team_side,
            team_won
        FROM {_table(DATASET_GOLD, "fact_draft")}
        WHERE team_name = '{team}'
        {action_filter}
        ORDER BY datetime_utc DESC
        LIMIT 500
    """
    return _client().query(sql).to_dataframe()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_kpi_summary() -> dict:
    """KPIs globaux pour la page d'accueil."""
    sql = f"""
        SELECT
            COUNT(DISTINCT game_id)     AS total_games,
            COUNT(DISTINCT overview_page) AS total_tournaments,
            MIN(CAST(datetime_utc AS DATE)) AS date_min,
            MAX(CAST(datetime_utc AS DATE)) AS date_max
        FROM {_table(DATASET_STAGING, "stg_lfl_matches")}
    """
    row = list(_client().query(sql).result())[0]

    sql2 = f"SELECT COUNT(DISTINCT player_id) AS total_players FROM {_table(DATASET_GOLD, 'dim_player')}"
    row2 = list(_client().query(sql2).result())[0]

    sql3 = f"SELECT COUNT(DISTINCT patch) AS total_patches FROM {_table(DATASET_GOLD, 'dim_patch')}"
    row3 = list(_client().query(sql3).result())[0]

    return {
        "total_games": row["total_games"],
        "total_tournaments": row["total_tournaments"],
        "total_players": row2["total_players"],
        "total_patches": row3["total_patches"],
        "date_min": str(row["date_min"]),
        "date_max": str(row["date_max"]),
    }
