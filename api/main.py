"""Nexus Analytics REST API.

Exposes LFL player and match statistics from the BigQuery Gold layer.

Usage (local):
    uvicorn api.main:app --reload

Authentication:
    All endpoints require the header:
        X-API-Key: <value of NEXUS_API_KEY in .env>

OpenAPI docs:
    http://localhost:8000/docs    (Swagger UI)
    http://localhost:8000/redoc   (ReDoc)
"""

from fastapi import FastAPI, HTTPException, Query, Security, status

from api.auth import verify_api_key
from api.database import query_matches, query_player_by_id, query_players
from api.models import MatchSummary, PlayerDetail, PlayerSummary

app = FastAPI(
    title="Nexus Analytics API",
    description=(
        "API de statistiques LFL (La Ligue Française) — League of Legends.\n\n"
        "Données issues de Leaguepedia et Oracle's Elixir, "
        "traitées via un pipeline Medallion (Bronze → Silver → Gold / BigQuery).\n\n"
        "**Authentification** : header `X-API-Key` obligatoire sur tous les endpoints."
    ),
    version="1.0.0",
    contact={"name": "Nexus Analytics", "url": "https://github.com/nexus-analytics"},
)


@app.get(
    "/health",
    summary="Health check",
    tags=["Système"],
    include_in_schema=True,
)
def health_check() -> dict:
    """Retourne le statut de l'API. Aucune authentification requise."""
    return {"status": "ok", "version": "1.0.0"}


@app.get(
    "/players",
    response_model=list[PlayerSummary],
    summary="Liste des joueurs LFL",
    tags=["Joueurs"],
)
def list_players(
    min_games: int = Query(default=1, ge=1, description="Nombre minimum de parties jouées."),
    limit: int = Query(default=50, ge=1, le=200, description="Nombre de résultats (max 200)."),
    offset: int = Query(default=0, ge=0, description="Décalage pour la pagination."),
    _key: str = Security(verify_api_key),
) -> list[PlayerSummary]:
    """Retourne les joueurs LFL classés par nombre de parties décroissant.

    Filtrable par `min_games` pour n'inclure que les joueurs réguliers.
    Paginable via `limit` et `offset`.

    Exemple :
        GET /players?min_games=20&limit=10
    """
    rows = query_players(min_games=min_games, limit=limit, offset=offset)
    return [PlayerSummary(**row) for row in rows]


@app.get(
    "/players/{player_id}",
    response_model=PlayerDetail,
    summary="Stats détaillées d'un joueur",
    tags=["Joueurs"],
)
def get_player(
    player_id: str,
    _key: str = Security(verify_api_key),
) -> PlayerDetail:
    """Retourne l'ensemble des statistiques de carrière LFL d'un joueur.

    `player_id` est l'identifiant wiki du joueur (ex: `Player:Rekkles`).
    Utiliser l'endpoint `/players` pour obtenir les identifiants disponibles.
    """
    row = query_player_by_id(player_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player '{player_id}' not found.",
        )
    return PlayerDetail(**row)


@app.get(
    "/matches",
    response_model=list[MatchSummary],
    summary="Liste des parties LFL",
    tags=["Parties"],
)
def list_matches(
    team: str | None = Query(
        default=None,
        description="Filtrer les parties d'une équipe (ex: `Karmine Corp`).",
    ),
    season: str | None = Query(
        default=None,
        description="Filtrer par préfixe de saison (ex: `LFL/2025`).",
    ),
    limit: int = Query(default=50, ge=1, le=200, description="Nombre de résultats (max 200)."),
    offset: int = Query(default=0, ge=0, description="Décalage pour la pagination."),
    _key: str = Security(verify_api_key),
) -> list[MatchSummary]:
    """Retourne les parties LFL triées par date décroissante.

    Filtres cumulables :
    - `team` : uniquement les parties de cette équipe
    - `season` : uniquement les parties de cette saison (ex: `LFL/2024`)

    Exemple :
        GET /matches?team=Karmine+Corp&season=LFL/2025&limit=20
    """
    rows = query_matches(team=team, season=season, limit=limit, offset=offset)
    return [MatchSummary(**row) for row in rows]
