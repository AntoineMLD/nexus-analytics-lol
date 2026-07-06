# Nexus Analytics

Pipeline de données pour l'analyse des matchs professionnels de League of Legends (LFL).

Projet réalisé dans le cadre de la certification **Ingénieur Data RNCP niveau 7 (BC02)**.

---

## Objectif

Ingérer, transformer et exposer les données de matchs LoL esports (Oracle's Elixir, Leaguepedia, Riot API) dans une architecture **Medallion** (Bronze / Silver / Gold) hébergée sur Google Cloud Platform.

---

## Architecture

```
Sources externes
  ├── Oracle's Elixir    (fichiers CSV — Google Drive)
  ├── Leaguepedia        (API Cargo MediaWiki)
  └── Riot API           (PUUIDs + match IDs joueurs)

        │ ingestion/          (modules Python avec CLI argparse)
        ▼

GCS Bronze   ──►   GCS Silver   ──►   BigQuery Gold   ──►   API FastAPI
(données brutes)  (Python transforms) (dbt — planifié)   (planifiée)
```

| Couche | Rôle | Technologie | Statut |
|--------|------|-------------|--------|
| Bronze | Données brutes, sans transformation | Google Cloud Storage (NDJSON) | ✅ Implémenté |
| Silver | Nettoyage, typage, filtrage LFL | Python → Google Cloud Storage | ✅ Implémenté |
| Gold | Agrégats métier, modèles dimensionnels | BigQuery + dbt | 🔧 En cours |
| API | Exposition des données Silver/Gold | FastAPI | 🔧 Planifiée |

---

## Structure du projet

```
ingestion/
  oracle_elixir/        # CSV historiques depuis Google Drive
  leaguepedia/          # API Cargo Leaguepedia (tournois, matchs, joueurs)
  riot_api/             # PUUIDs et ranked match IDs via Riot API
  utils.py              # GCS client, Discord notifications, Settings (pydantic)

pipeline/
  silver_transforms/    # Transforms Bronze → Silver (Python, CLI argparse)
    lfl_matches.py      # ScoreboardGames → silver/leaguepedia/lfl_matches/
    lfl_player_stats.py # ScoreboardPlayers → silver/leaguepedia/lfl_player_stats/
    lfl_players.py      # Players + TournamentRosters → silver/leaguepedia/lfl_players/
  loaders/              # Chargement BigQuery (en cours)
  orchestration/        # Orchestration des pipelines (en cours)

dbt/
  models/               # Modèles Gold dimensionnels (en cours)

api/                    # API FastAPI (planifiée)
terraform/              # Infrastructure GCP as code (en cours)
tests/
  unit/                 # 129 tests unitaires, offline, sans credentials
scripts/
  debug/                # Scripts d'exploration ad hoc (hors pipeline)
```

---

## Prérequis

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- Compte GCP avec un projet actif et un bucket GCS

---

## Installation

```bash
git clone git@github.com:AntoineMLD/nexus-analytics-lol.git
cd nexus-analytics-lol
uv sync
```

Créer un fichier `.env` à la racine (voir `.env.example` pour la liste complète) :

```env
GCS_BUCKET_NAME=<nom du bucket GCS>
RIOT_API=<clé Riot Games API>
FANDOM_BOT_NAME=<compte@BotName>
FANDOM_BOT_PASSWORD=<mot de passe bot Fandom>
DISCORD_WEBHOOK_URL=<webhook Discord — optionnel>
API_KEY=<clé Google Drive>
```

Authentification GCP :

```bash
gcloud auth application-default login
gcloud config set project <PROJECT_ID>
```

---

## Lancer les ingestions

```bash
# Oracle's Elixir (CSV Google Drive)
uv run python -m ingestion.oracle_elixir.ingest               # année courante
uv run python -m ingestion.oracle_elixir.ingest --year 2024   # année spécifique
uv run python -m ingestion.oracle_elixir.ingest --all         # toutes les années

# Leaguepedia (API Cargo) — tables disponibles :
# Tournaments, TournamentRosters, Players, ScoreboardGames, ScoreboardPlayers
uv run python -m ingestion.leaguepedia.ingest --table Tournaments
uv run python -m ingestion.leaguepedia.ingest --table ScoreboardPlayers

# Riot API (PUUIDs + match IDs)
uv run python -m ingestion.riot_api.ingest
```

---

## Lancer les transforms Silver

```bash
# Matchs LFL (ScoreboardGames Bronze → Silver)
uv run python -m pipeline.silver_transforms.lfl_matches --date 2026-06-07

# Stats joueurs LFL (ScoreboardPlayers Bronze → Silver)
uv run python -m pipeline.silver_transforms.lfl_player_stats \
  --date 2026-07-06 --tournaments-date 2026-06-04

# Joueurs LFL + comptes EUW (Players + TournamentRosters Bronze → Silver)
uv run python -m pipeline.silver_transforms.lfl_players --date 2026-06-04
```

---

## Tests

```bash
# Suite complète (129 tests, ~70s)
uv run pytest tests/unit/ -v

# Tests d'un module spécifique
uv run pytest tests/unit/test_lfl_players.py -v
```

Les tests unitaires tournent **sans credentials ni accès réseau** — tous les appels GCS et HTTP sont mockés avec `unittest.mock`.

---

## Stack technique

| Domaine | Outil |
|---------|-------|
| Langage | Python 3.11 |
| Gestion des dépendances | uv |
| Stockage (Bronze + Silver) | Google Cloud Storage |
| Entrepôt de données (Gold) | BigQuery — en cours |
| Transformations (Gold) | dbt — en cours |
| API | FastAPI — planifiée |
| Infrastructure | Terraform — en cours |
| Config / secrets | pydantic-settings + .env |
| Linting | Ruff |
| Tests | pytest + unittest.mock |
| Notifications | Discord Webhooks |
