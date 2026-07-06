"""Pydantic response schemas for the Nexus Analytics API.

Each class maps directly to a BigQuery Gold table column set.
Optional fields cover columns that can legitimately be NULL in BigQuery
(e.g. damage_to_champions not tracked before 2021).
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PlayerSummary(BaseModel):
    """Condensed player stats — used in list responses."""

    player_id: str = Field(description="Identifiant wiki unique du joueur.")
    player_name: str = Field(description="Pseudo affiché du joueur.")
    total_games: int = Field(description="Nombre de parties jouées en LFL.")
    win_rate_pct: float | None = Field(description="Taux de victoire en % (0-100).")
    avg_kills: float | None = Field(description="Moyenne de kills par partie.")
    avg_deaths: float | None = Field(description="Moyenne de morts par partie.")
    avg_assists: float | None = Field(description="Moyenne d'assists par partie.")
    avg_cs: float | None = Field(description="Moyenne de CS par partie.")


class PlayerDetail(PlayerSummary):
    """Full player stats including damage and vision — used in /players/{id}."""

    teams_played_for: int | None = Field(description="Nombre d'équipes distinctes.")
    avg_damage: float | None = Field(description="Moyenne de dégâts aux champions par partie.")
    avg_vision_score: float | None = Field(description="Moyenne de vision score par partie.")
    total_wins: int | None = Field(description="Nombre total de victoires.")


class MatchSummary(BaseModel):
    """Match-level data — one row per game."""

    game_id: str = Field(description="Identifiant unique de la partie.")
    match_id: str = Field(description="Identifiant du match (série BO1/BO3/BO5).")
    overview_page: str = Field(description="Tournoi LFL (ex: LFL/2025 Season/Spring Split).")
    datetime_utc: datetime | None = Field(description="Date et heure de la partie (UTC).")
    team1: str = Field(description="Équipe côté bleu.")
    team2: str = Field(description="Équipe côté rouge.")
    win_team: str = Field(description="Équipe gagnante.")
    gamelength_seconds: int | None = Field(description="Durée de la partie en secondes.")
    patch: str | None = Field(description="Version du jeu.")
    n_game_in_match: int | None = Field(description="Numéro de la partie dans le match.")
