# Runbook opérationnel — Nexus Analytics

> Procédures de gestion, monitoring et maintenance du pipeline de données Nexus Analytics.
> Répond aux critères C16 (maintenance entrepôt) et C21 (gestion des accès) du référentiel RNCP.
>
> Dernière mise à jour : 2026-07-09

---

## Sommaire

1. [Surveillance et monitoring](#1-surveillance-et-monitoring)
2. [Pipeline hebdomadaire — procédure normale](#2-pipeline-hebdomadaire--procédure-normale)
3. [Cas d'usage — Oracle's Elixir non disponible le lundi](#3-cas-dusage--oracles-elixir-non-disponible-le-lundi)
4. [Cas d'usage — Lignes en quarantaine](#4-cas-dusage--lignes-en-quarantaine)
5. [Cas d'usage — Nouvelle équipe en LFL (mise à jour dim_team_alias)](#5-cas-dusage--nouvelle-équipe-en-lfl)
6. [Cas d'usage — Nouvelle source de données](#6-cas-dusage--nouvelle-source-de-données)
7. [Gestion des accès IAM — groupes et droits](#7-gestion-des-accès-iam)
8. [Procédure de mise à jour des règles d'accès](#8-procédure-de-mise-à-jour-des-règles-daccès)
9. [Backup et restauration](#9-backup-et-restauration)
10. [Indicateurs de santé du pipeline](#10-indicateurs-de-santé-du-pipeline)

---

## 1. Surveillance et monitoring

### Canaux d'alerte

| Canal | Événements couverts | Responsable |
|-------|--------------------|----|
| **Discord `#pipeline-alerts`** | Succès/échec de chaque étape (ingestion, Silver, BQ load, dbt) | Automatique (webhook) |
| **Discord `#pipeline-alerts`** | Données non disponibles avant 10h00 le lundi | Automatique |
| **Email** | Demandes RGPD (exercice des droits) | Antoine MLD |

### Vérification manuelle de l'état du pipeline

```bash
# Vérifier les derniers fichiers Bronze dans GCS
gsutil ls -l gs://nexus-analytics-bucket/bronze/leaguepedia/ScoreboardGames/ | sort -k2

# Vérifier les derniers fichiers Silver
gsutil ls -l gs://nexus-analytics-bucket/silver/leaguepedia/lfl_matches/ | sort -k2

# Vérifier les logs BigQuery (dernières requêtes)
bq query --use_legacy_sql=false \
  "SELECT creation_time, job_type, state, total_bytes_processed
   FROM region-europe-west1.INFORMATION_SCHEMA.JOBS
   WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
   ORDER BY creation_time DESC LIMIT 20"
```

---

## 2. Pipeline hebdomadaire — procédure normale

### Déclenchement

Le pipeline est actuellement lancé **manuellement** (pas de scheduler configuré). Objectif : chaque dimanche entre 20h00 et 22h00, après publication des résultats des matchs LFL.

### Commande unique

```bash
uv run python -m pipeline.orchestration.run_pipeline
```

Cette commande enchaîne automatiquement :
1. Ingestion Oracle's Elixir (CSV Google Drive)
2. Ingestion Leaguepedia (9 tables Cargo)
3. Ingestion Riot API (PUUIDs)
4. Silver transforms (lfl_matches, lfl_player_stats, lfl_players, lfl_drafts)
5. BigQuery loader (Silver → raw)
6. dbt run + dbt test (raw → Gold)

### Vérification post-run

```bash
# Compter les lignes dans les tables Gold
bq query --use_legacy_sql=false \
  "SELECT 'fact_player_game' AS table, COUNT(*) AS rows FROM gold_gold.fact_player_game
   UNION ALL
   SELECT 'dim_player', COUNT(*) FROM gold_gold.dim_player
   UNION ALL
   SELECT 'fact_meta_trend', COUNT(*) FROM gold_gold.fact_meta_trend"
```

**Résultats attendus (septembre 2026 — LFL + EMEA Masters) :**

| Table | Lignes attendues |
|-------|-----------------|
| `fact_player_game` | ~32 700 |
| `dim_player` | ~939 |
| `fact_meta_trend` | ~7 400 |
| `fact_draft` | ~82 600 |
| `dim_champion` | ~170 |
| `dim_team` | ~194 |

---

## 3. Cas d'usage — Oracle's Elixir non disponible le lundi

**Symptôme** : le CSV Oracle's Elixir de la semaine n'est pas encore publié au moment du run hebdomadaire. Tim Sevenhuysen publie parfois le mardi ou mercredi.

**Procédure** :

1. Vérifier si le CSV est disponible manuellement sur [oracleselixir.com](https://oracleselixir.com).
2. Si non disponible à 10h00 le lundi, une alerte Discord automatique est envoyée.
3. **Option A — Patienter** : relancer l'ingestion Oracle's Elixir seule quand le CSV est publié :
   ```bash
   uv run python -m ingestion.oracle_elixir.ingest --year 2026
   uv run python -m pipeline.orchestration.run_pipeline --skip-ingest
   ```
4. **Option B — Livrer le rapport avec les données S-1** : informer Yasmine Karim que les données de la semaine ne sont pas encore disponibles. Utiliser les données de la semaine précédente en indiquant explicitement la date dans le rapport.

---

## 4. Cas d'usage — Lignes en quarantaine

**Symptôme** : le Silver transform (`lfl_players.py` ou `lfl_player_stats.py`) lève une `ValueError` avec le message "All LFL filter rows removed from input" ou des lignes sont silencieusement exclues.

**Diagnostic** :

```bash
# Inspecter les OverviewPages présents dans le Bronze
uv run python -c "
import json
from ingestion.utils import gcs_client, Settings
s = Settings()
bucket = gcs_client().bucket(s.gcs_bucket_name)
blob = bucket.blob('bronze/leaguepedia/ScoreboardPlayers/2026-06-05.json')
lines = blob.download_as_text().strip().split('\n')
pages = set(json.loads(l)['OverviewPage'] for l in lines[:100] if l)
print(sorted(pages)[:10])
"
```

**Correction** :
- Si les OverviewPages ne sont pas des pages LFL/EMEA (`LFL/...` ou `EMEA Masters/...`), le Bronze est corrompu → relancer l'ingestion :
  ```bash
  uv run python -m ingestion.leaguepedia.ingest --table ScoreboardPlayers
  ```
- Si les lignes sont simplement exclues par le filtre métier, vérifier que la liste des 89 OverviewPages (LFL + EMEA Masters) dans `Tournaments` est bien à jour.

---

## 5. Cas d'usage — Nouvelle équipe en LFL

**Contexte** : à chaque début de saison, des équipes montent ou descendent de LFL. Leur nom peut différer entre Oracle's Elixir et Leaguepedia (ex: "Team BDS Academy" vs "BDSA").

**Procédure** :

1. Identifier le nouveau nom d'équipe dans Oracle's Elixir (colonne `team`) et dans Leaguepedia (champ `Team1`/`Team2` dans `ScoreboardGames`).
2. Ajouter le mapping dans `dbt/seeds/dim_team_alias.csv` :
   ```csv
   oracle_elixir_name,leaguepedia_name,canonical_name
   "BDSA","Team BDS Academy","BDS Academy"
   ```
3. Recharger le seed dbt :
   ```bash
   cd dbt && dbt seed
   ```
4. Relancer la normalisation Silver pour que le nouveau mapping soit appliqué :
   ```bash
   uv run python -m pipeline.orchestration.run_pipeline --skip-ingest
   ```
5. Vérifier qu'aucune ligne avec le nouveau nom n'est en quarantaine.

---

## 6. Cas d'usage — Nouvelle source de données

**Exemples** : ajout d'un scraping de stats EMEA Masters, intégration d'une nouvelle API.

**Procédure** :

1. Créer un module d'ingestion dans `ingestion/<nom_source>/ingest.py` en suivant le pattern des modules existants :
   - Lire depuis `ingestion/utils.py` pour les clients GCS, Discord, Settings
   - Produire du NDJSON dans `bronze/<nom_source>/{date}.ndjson`
   - Gérer les erreurs et envoyer une notification Discord
2. Ajouter les variables d'environnement nécessaires dans `.env` et `.env.example`
3. Évaluer si des données personnelles sont collectées → mettre à jour `docs/RGPD_registre.md` si oui
4. Créer un Silver transform dans `pipeline/silver_transforms/`
5. Ajouter les tests unitaires dans `tests/unit/`
6. Mettre à jour le `PROGRESS.md` et le `README.md`
7. Vérifier la CI (`uv run pytest tests/ && uv run ruff check .`)

---

## 7. Gestion des accès IAM

### Groupes d'accès et droits

> Tous les accès sont attribués à des **comptes de service** (Service Accounts), jamais à des comptes personnels Google. Cela permet de révoquer facilement un accès sans impacter d'autres ressources.

| Compte de service | Email | Rôles | Usage |
|------------------|-------|-------|-------|
| `nexus-ingestion` | `nexus-ingestion@<PROJECT_ID>.iam.gserviceaccount.com` | `roles/storage.objectAdmin` (bucket GCS) + `roles/bigquery.dataEditor` (dataset `raw`) + `roles/bigquery.jobUser` (projet) | Ingestion Bronze → GCS, chargement Silver → BigQuery raw |
| `nexus-api` | `nexus-api@<PROJECT_ID>.iam.gserviceaccount.com` | `roles/bigquery.dataViewer` (datasets `gold_gold`, `gold_staging`) + `roles/bigquery.jobUser` (projet) | API FastAPI — lectures Gold uniquement |

### Principe du moindre privilège

- `nexus-ingestion` ne peut pas lire les datasets Gold (pas de `dataViewer` sur `gold_gold`).
- `nexus-api` ne peut pas écrire dans GCS ni dans BigQuery raw.
- Aucun compte de service n'a de droits d'administration sur le projet GCP.
- Les clés de service account ne sont pas stockées dans Git (`.gitignore` inclut `*.json` credentials).

---

## 8. Procédure de mise à jour des règles d'accès

### Ajouter un analyste en lecture Gold

1. Créer ou identifier le compte Google de l'analyste (`analyst@nexus-analytics.fr`)
2. Attribuer le rôle `bigquery.dataViewer` sur les datasets Gold :
   ```bash
   gcloud projects add-iam-policy-binding <PROJECT_ID> \
     --member="user:analyst@nexus-analytics.fr" \
     --role="roles/bigquery.dataViewer"
   ```
3. Mettre à jour `terraform/iam.tf` pour documenter le changement :
   ```hcl
   # Analyste senior — accès lecture Gold uniquement
   resource "google_bigquery_dataset_iam_member" "analyst_viewer" {
     dataset_id = google_bigquery_dataset.gold_gold.dataset_id
     role       = "roles/bigquery.dataViewer"
     member     = "user:analyst@nexus-analytics.fr"
   }
   ```
4. Appliquer : `cd terraform && terraform apply`
5. Mettre à jour ce fichier `RUNBOOK.md` (section 7) pour documenter le nouvel accès.

### Révoquer un accès

```bash
gcloud projects remove-iam-policy-binding <PROJECT_ID> \
  --member="user:analyst@nexus-analytics.fr" \
  --role="roles/bigquery.dataViewer"
```

Puis supprimer l'entrée correspondante dans `terraform/iam.tf` et appliquer.

### Rotation d'une clé de service account

Les clés de service account ne doivent pas être stockées localement plus de 90 jours.

```bash
# Lister les clés existantes
gcloud iam service-accounts keys list --iam-account=nexus-ingestion@<PROJECT_ID>.iam.gserviceaccount.com

# Supprimer l'ancienne clé
gcloud iam service-accounts keys delete KEY_ID \
  --iam-account=nexus-ingestion@<PROJECT_ID>.iam.gserviceaccount.com

# Créer une nouvelle clé
gcloud iam service-accounts keys create /tmp/nexus-ingestion-key.json \
  --iam-account=nexus-ingestion@<PROJECT_ID>.iam.gserviceaccount.com

# Mettre à jour le fichier .env (ne jamais commiter dans Git)
```

---

## 9. Backup et restauration

### Stratégie de backup actuelle

| Couche | Backup | Rétention |
|--------|--------|-----------|
| Bronze GCS | Pas de backup distinct — les données sont réingérables depuis les sources (Leaguepedia, Oracle's Elixir) | 90 jours Standard + Coldline jusqu'à 365 jours |
| Silver GCS | Pas de backup distinct — régénérable depuis le Bronze | Durée du projet |
| Gold BigQuery | BigQuery snaphots activés par défaut (7 jours rolling) — restauration via `bq cp` | 7 jours |

### Restaurer une table BigQuery depuis un snapshot

```bash
# Restaurer fact_player_game telle qu'elle était il y a 24 heures
bq cp \
  "gold_gold.fact_player_game@-86400000" \
  gold_gold.fact_player_game_backup
```

### Régénérer le Silver depuis le Bronze

Si les fichiers Silver sont corrompus ou supprimés :

```bash
# Identifier la dernière date Bronze disponible
gsutil ls gs://nexus-analytics-bucket/bronze/leaguepedia/Tournaments/ | sort | tail -1

# Relancer les transforms Silver avec cette date
uv run python -m pipeline.orchestration.run_pipeline --skip-ingest --date YYYY-MM-DD
```

---

## 10. Indicateurs de santé du pipeline

### Métriques hebdomadaires

Après chaque run, vérifier les indicateurs suivants via la notification Discord :

| Indicateur | Valeur attendue | Action si hors plage |
|-----------|----------------|---------------------|
| Lignes `ScoreboardGames` Bronze | 3 053 ± 20 | Réingérer si < 3 000 |
| Lignes `ScoreboardPlayers` Bronze | 30 530 ± 200 | Réingérer si < 30 000 |
| Lignes `lfl_matches` Silver | 3 053 ± 20 | Inspecter filter_lfl_rows |
| Lignes `fact_player_game` Gold | ~30 000 | Relancer bq_loader + dbt |
| Tests dbt passés | 100% | Investiguer les tests échoués |
| Timestamp disponibilité données | Avant 10h00 le lundi | Alerte automatique envoyée |

### Requête de monitoring mensuel (volume BigQuery)

```sql
SELECT
  DATE_TRUNC(creation_time, MONTH) AS month,
  COUNT(*) AS total_jobs,
  SUM(total_bytes_processed) / POW(1024, 3) AS total_gb_scanned,
  SUM(total_bytes_billed) / POW(1024, 3) AS total_gb_billed
FROM region-europe-west1.INFORMATION_SCHEMA.JOBS
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 MONTH)
GROUP BY 1
ORDER BY 1 DESC
```

**Seuil d'alerte** : si `total_gb_billed > 800 GB/mois`, les requêtes non optimisées doivent être identifiées et corrigées avant dépassement du tier gratuit (1 TB/mois).
