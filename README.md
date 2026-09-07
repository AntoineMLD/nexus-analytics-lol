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
(données brutes)  (Python transforms)  (bq_loader + dbt)   (/players, /matches)
```

| Couche | Rôle | Technologie | Statut |
|--------|------|-------------|--------|
| Bronze | Données brutes, sans transformation | Google Cloud Storage (NDJSON) | ✅ Implémenté |
| Silver | Nettoyage, typage, filtrage LFL | Python → Google Cloud Storage | ✅ Implémenté |
| Gold | Agrégats métier, modèles dimensionnels | BigQuery + dbt | ✅ Opérationnel |
| API | Exposition des données Gold | FastAPI | ✅ Opérationnel |

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
  loaders/
    bq_loader.py        # GCS Silver → BigQuery raw (CLI, WRITE_TRUNCATE)
  orchestration/        # Orchestration des pipelines (planifié)

dbt/
  dbt_project.yml       # Config dbt (staging=view, gold=table)
  profiles.yml          # Template connexion BigQuery (ADC oauth)
  models/
    staging/            # stg_lfl_matches.sql, stg_lfl_player_stats.sql
    dimensions/         # dim_team.sql, dim_player.sql
    facts/              # fact_player_game.sql (KDA ratio calculé)

api/
  main.py               # App FastAPI — 3 endpoints + /health
  auth.py               # Dépendance X-API-Key
  database.py           # Requêtes BigQuery Gold paramétrées
  models.py             # Schémas Pydantic (PlayerSummary, MatchSummary…)
terraform/
  main.tf               # Provider Google + version
  variables.tf          # project_id, region, bucket_name, seuils lifecycle
  gcs.tf                # Bucket GCS + lifecycle Bronze → Coldline (90j)
  bigquery.tf           # Datasets raw, gold_gold (expiration 24 mois), gold_staging
  iam.tf                # SA nexus-ingestion + SA nexus-api + IAM bindings
  outputs.tf            # Emails SA, noms datasets
tests/
  unit/                 # 129 tests unitaires, offline, sans credentials
docs/
  MAPPING_CERTIFICATION.md  # Mapping complet critères RNCP ↔ code
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

## Installation complète pas-à-pas

### Prérequis

Avant de commencer, vérifier que les outils suivants sont installés :

```bash
python --version       # Python 3.11+
uv --version           # uv (gestionnaire de paquets)
gcloud --version       # Google Cloud SDK
terraform --version    # Terraform (pour l'infrastructure)
```

Si `uv` n'est pas installé :
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.zshrc  # ou ~/.bashrc selon votre shell
```

### Étape 1 — Cloner le dépôt et installer les dépendances

```bash
git clone git@github.com:AntoineMLD/nexus-analytics-lol.git
cd nexus-analytics-lol
uv sync                # installe toutes les dépendances depuis uv.lock
```

### Étape 2 — Configurer les variables d'environnement

Copier `.env.example` en `.env` et renseigner chaque valeur :

```bash
cp .env.example .env
```

```env
GCS_BUCKET_NAME=<nom du bucket GCS — ex: nexus-analytics-bucket>
RIOT_API_KEY=<clé Riot Games API — obtenue sur developer.riotgames.com>
FANDOM_BOT_NAME=<compte@BotName — ex: SpideyBot>
FANDOM_BOT_PASSWORD=<mot de passe bot Fandom>
GCP_PROJECT_ID=<ID du projet GCP — ex: nexus-analytics-prod-498107>
DISCORD_WEBHOOK_URL=<URL webhook Discord — optionnel, pour les alertes>
GOOGLE_DRIVE_API_KEY=<clé API Google Drive — pour Oracle's Elixir>
NEXUS_API_KEY=<clé d'accès à l'API FastAPI — choisir une valeur secrète>
```

### Étape 3 — Authentification GCP

```bash
# Connexion avec votre compte Google
gcloud auth application-default login

# Configurer le projet par défaut
gcloud config set project <GCP_PROJECT_ID>

# Définir le projet de facturation (nécessaire pour GCS + BigQuery)
gcloud auth application-default set-quota-project <GCP_PROJECT_ID>
```

Vérification :
```bash
gcloud auth application-default print-access-token   # doit retourner un token
gsutil ls                                              # doit lister vos buckets
```

### Étape 4 — Provisionner l'infrastructure GCP (Terraform)

> À réaliser une seule fois, ou après chaque modification de `terraform/`.

```bash
cd terraform
terraform init              # télécharger les providers
terraform plan              # vérifier les changements avant application
terraform apply             # créer les ressources GCP (bucket, datasets BQ, IAM)
cd ..
```

Ressources créées :
- Bucket GCS `nexus-analytics-bucket` (région EU, lifecycle Bronze → Coldline 90j)
- Datasets BigQuery `raw`, `gold_gold`, `gold_staging`
- Compte de service `nexus-ingestion` (écriture GCS + BQ raw)
- Compte de service `nexus-api` (lecture BQ Gold uniquement)

### Étape 5 — Configurer dbt

```bash
# Copier le profil de connexion BigQuery
mkdir -p ~/.dbt
cp dbt/profiles.yml ~/.dbt/profiles.yml

# Éditer ~/.dbt/profiles.yml et remplacer GCP_PROJECT_ID par votre projet
```

Vérification :
```bash
cd dbt
dbt debug    # doit afficher "All checks passed!"
cd ..
```

### Étape 6 — Lancer le pipeline complet

```bash
# Ingestion complète + Silver + Gold (première fois)
uv run python -m pipeline.orchestration.run_pipeline

# Ingestion uniquement
uv run python -m pipeline.orchestration.run_pipeline --skip-silver

# Pas d'ingestion (réutilise les Bronze existants)
uv run python -m pipeline.orchestration.run_pipeline --skip-ingest
```

### Étape 7 — Vérifier les données

```bash
# API FastAPI (données Gold)
uv run uvicorn api.main:app --reload

# Accéder aux docs interactives : http://localhost:8000/docs
# Tester un endpoint :
curl -H "X-API-Key: <NEXUS_API_KEY>" http://localhost:8000/health
curl -H "X-API-Key: <NEXUS_API_KEY>" "http://localhost:8000/players?min_games=10"
```

### Étape 8 — Lancer les tests

```bash
uv run pytest tests/ -v   # 261 tests, doit passer à 100% sans credentials GCP
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

## Charger en Gold (BigQuery + dbt)

```bash
# 1. Charger une table Silver dans BigQuery (dataset raw)
uv run python -m pipeline.loaders.bq_loader \
  --source leaguepedia --table lfl_matches --date 2026-06-07

uv run python -m pipeline.loaders.bq_loader \
  --source leaguepedia --table lfl_player_stats --date 2026-07-06

uv run python -m pipeline.loaders.bq_loader \
  --source leaguepedia --table lfl_players --date 2026-06-04

# 2. Copier dbt/profiles.yml dans ~/.dbt/profiles.yml et renseigner GCP_PROJECT_ID
# 3. Depuis le dossier dbt/
cd dbt
dbt run        # Exécuter les modèles staging → dimensions → facts
dbt test       # Lancer les tests not_null, unique, relationships
dbt docs serve # Générer et ouvrir la documentation
```

---

## Lancer l'API

```bash
uv run uvicorn api.main:app --reload
```

Docs interactives disponibles sur `http://localhost:8000/docs`.

Authentification : header `X-API-Key` obligatoire (valeur définie dans `NEXUS_API_KEY`).

```bash
# Exemple
curl -H "X-API-Key: <NEXUS_API_KEY>" http://localhost:8000/players?min_games=20
curl -H "X-API-Key: <NEXUS_API_KEY>" "http://localhost:8000/matches?team=Karmine+Corp"
```

---

## Infrastructure (Terraform)

```bash
cd terraform
terraform init
terraform plan   # aperçu des changements
terraform apply  # appliquer sur GCP
```

Ressources provisionnées : bucket GCS `nexus-analytics-bucket`, datasets BigQuery `raw` / `gold_gold` / `gold_staging`, comptes de service `nexus-ingestion` et `nexus-api` avec IAM minimal.

---

## Tests

```bash
# Suite complète (129 tests, ~70s)
uv run pytest tests/ -v

# Tests d'un module spécifique
uv run pytest tests/test_api.py -v
uv run pytest tests/test_lfl_matches.py -v
```

Les tests unitaires tournent **sans credentials ni accès réseau** — tous les appels GCS et HTTP sont mockés avec `unittest.mock`.

---

## Stack technique

| Domaine | Outil |
|---------|-------|
| Langage | Python 3.11 |
| Gestion des dépendances | uv |
| Stockage (Bronze + Silver) | Google Cloud Storage |
| Entrepôt de données (Gold) | BigQuery |
| Transformations (Gold) | dbt (5 modèles : staging, dim, facts) |
| API | FastAPI (3 endpoints, auth X-API-Key, OpenAPI `/docs`) |
| Infrastructure as Code | Terraform (bucket GCS, datasets BQ, IAM, lifecycle) |
| Config / secrets | pydantic-settings + .env |
| Linting | Ruff |
| Tests | pytest + unittest.mock |
| Notifications | Discord Webhooks |
