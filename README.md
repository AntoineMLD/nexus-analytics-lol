# Nexus Analytics

Pipeline de données pour l'analyse des matchs professionnels de League of Legends.

Projet réalisé dans le cadre de la certification **Ingénieur Data (RNCP niveau 7)**.

---

## Objectif

Ingérer, transformer et exposer les données de matchs LoL esports (Oracle's Elixir, Leaguepedia, Riot API) dans une architecture **Medallion** (Bronze / Silver / Gold) hébergée sur Google Cloud Platform.

---

## Architecture

```
Sources externes
  ├── Oracle's Elixir (Google Drive — CSV historiques)
  ├── Leaguepedia (API MediaWiki)
  └── Riot API

        │ ingestion/
        ▼

GCS Bronze  ──►  dbt Silver  ──►  BigQuery Gold  ──►  API FastAPI
```

| Couche | Rôle | Technologie |
|--------|------|-------------|
| Bronze | Données brutes telles que reçues | Google Cloud Storage |
| Silver | Données nettoyées et typées | dbt + BigQuery |
| Gold | Agrégats métier | BigQuery |
| API | Exposition des données | FastAPI |

---

## Structure du projet

```
ingestion/
  oracle_elixir/      # Ingestion CSV depuis Google Drive
  leaguepedia/        # Ingestion depuis l'API Leaguepedia
  riot_api/           # Ingestion depuis l'API Riot
dbt/
  models/             # Transformations Silver
  macros/
  seeds/
pipeline/
  loaders/            # Chargement BigQuery
  orchestration/      # Orchestration des pipelines
  silver_transforms/
api/                  # API FastAPI
terraform/            # Infrastructure GCP as code
tests/
  unit/               # Tests unitaires (offline, sans credentials)
  integration/        # Tests d'intégration
```

---

## Prérequis

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- Compte GCP avec un projet actif

---

## Installation

```bash
git clone git@github.com:AntoineMLD/nexus-analytics-lol.git
cd nexus-analytics-lol
uv sync
```

Créer un fichier `.env` à la racine (voir `.env.example`) :

```env
API_KEY=<clé API Google Drive>
GCS_BUCKET_NAME=<nom du bucket GCS>
DISCORD_WEBHOOK_URL=<webhook Discord pour les notifications>
```

Authentification GCP :

```bash
gcloud auth application-default login
gcloud config set project <PROJECT_ID>
```

---

## Lancer l'ingestion Oracle's Elixir

```bash
# Année courante
uv run python ingestion/oracle_elixir/ingest.py

# Année spécifique
uv run python ingestion/oracle_elixir/ingest.py --year 2024

# Toutes les années (skip les fichiers déjà présents dans GCS)
uv run python ingestion/oracle_elixir/ingest.py --all
```

---

## Tests

```bash
uv run pytest tests/unit/ -v
```

Les tests unitaires tournent sans credentials ni accès réseau (tous les appels externes sont mockés).

---

## Stack technique

| Domaine | Outil |
|---------|-------|
| Langage | Python 3.11 |
| Gestion des dépendances | uv |
| Stockage brut | Google Cloud Storage |
| Entrepôt de données | BigQuery |
| Transformations | dbt |
| API | FastAPI |
| Infrastructure | Terraform |
| Linting | Ruff |
| Tests | pytest + unittest.mock |
| Notifications | Discord Webhooks |
