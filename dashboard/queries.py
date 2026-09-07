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
def fetch_players(min_games: int = 5) -> pd.DataFrame:
    """Joueurs LFL avec stats agrégées — min_games filtre les remplaçants."""
    sql = f"""
        SELECT
            player_name,
            total_games,
            win_rate_pct,
            avg_kills,
            avg_deaths,
            avg_assists,
            avg_cs,
            ROUND(SAFE_DIVIDE(avg_kills + avg_assists, GREATEST(avg_deaths, 1)), 2) AS kda
        FROM {_table(DATASET_GOLD, "dim_player")}
        WHERE total_games >= {min_games}
        ORDER BY total_games DESC
        LIMIT 200
    """
    return _client().query(sql).to_dataframe()


@st.cache_data(ttl=600, show_spinner=False)
def fetch_champions(min_games: int = 3) -> pd.DataFrame:
    """Champions avec pick rates et win rates agrégés."""
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
