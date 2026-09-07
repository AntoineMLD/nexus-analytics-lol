# Architecture technique — Nexus Analytics

> Schéma formel d'architecture du datalake Nexus Analytics.
> Répond au critère C18 (conception architecture datalake) du référentiel RNCP.
>
> Dernière mise à jour : 2026-07-09

---

## 1. Vue d'ensemble — Architecture Medallion (datalake 3 couches)

```mermaid
graph LR
    subgraph Sources["Sources de données externes"]
        OE["Oracle's Elixir<br/>(CSV Google Drive)<br/>Fichiers ~5 Mo/semaine"]
        LP["Leaguepedia<br/>(API Cargo MediaWiki)<br/>~1 Mo/jour JSON"]
        RA["Riot Games API<br/>(ranked + account)<br/>~500 Ko/jour JSON"]
        WK["Leaguepedia Wiki<br/>(scraping pages joueurs)<br/>HTML → Riot IDs"]
    end

    subgraph Bronze["☁️ GCS Bronze — Données brutes"]
        B1["bronze/oracle_elixir/{year}/"]
        B2["bronze/leaguepedia/{table}/{date}.json"]
        B3["bronze/riot_api/{date}.ndjson"]
        B4["bronze/leaguepedia_wiki/player_ids/{date}.ndjson"]
    end

    subgraph Silver["☁️ GCS Silver — Données normalisées"]
        S1["silver/lfl_matches/{date}.json<br/>3 053 parties LFL"]
        S2["silver/lfl_player_stats/{date}.json<br/>30 530 stats joueurs"]
        S3["silver/lfl_players/{date}.json<br/>792 joueurs, 194 comptes EUW"]
        S4["silver/lfl_drafts/{date}.json<br/>Picks/bans unpivotés"]
    end

    subgraph Gold["BigQuery Gold — Entrepôt analytique"]
        subgraph Staging["gold_staging (vues)"]
            SG1["stg_lfl_matches"]
            SG2["stg_lfl_player_stats"]
            SG3["stg_lfl_drafts"]
        end
        subgraph Dims["gold_gold (tables)"]
            D1["dim_player"]
            D2["dim_team"]
            D3["dim_champion"]
            D4["dim_patch"]
        end
        subgraph Facts["gold_gold (tables)"]
            F1["fact_player_game"]
            F2["fact_draft"]
            F3["fact_meta_trend"]
        end
    end

    subgraph API["API FastAPI — Exposition"]
        EP1["/players"]
        EP2["/matches"]
        EP3["/meta/champion-stats"]
        EP4["/teams/{team}/draft-history"]
        EP5["/meta/trends"]
    end

    OE --> B1
    LP --> B2
    RA --> B3
    WK --> B4

    B1 --> S1
    B1 --> S2
    B2 --> S1
    B2 --> S2
    B2 --> S3
    B2 --> S4
    B3 --> S3
    B4 --> S3

    S1 --> SG1
    S2 --> SG2
    S4 --> SG3

    SG1 --> D2
    SG1 --> D4
    SG2 --> D1
    SG2 --> D3
    SG1 --> F1
    SG2 --> F1
    SG3 --> F2
    SG1 --> F2
    SG2 --> F3
    SG1 --> F3

    F1 --> EP1
    F1 --> EP2
    D3 --> EP3
    F2 --> EP4
    F3 --> EP5
```

---

## 2. Vue applicative — Matrice des flux

| Flux | Source | Destination | Fréquence | Volume estimé | Format | Déclencheur |
|------|--------|-------------|-----------|--------------|--------|------------|
| Ingestion Oracle's Elixir | oracleselixir.com (Google Drive) | GCS Bronze | Hebdomadaire | ~5 Mo/CSV | CSV | Manuel (dim. 20h00) |
| Ingestion Leaguepedia | lol.fandom.com API Cargo | GCS Bronze | Hebdomadaire | ~1 Mo/table/jour | NDJSON | Manuel (dim. 20h00) |
| Ingestion Riot API | developer.riotgames.com | GCS Bronze | Hebdomadaire | ~500 Ko/jour | NDJSON | Après Silver lfl_players |
| Ingestion wiki scraping | lol.fandom.com pages | GCS Bronze | Mensuel | ~200 Ko | NDJSON | Manuel |
| Normalisation Silver | GCS Bronze | GCS Silver | Hebdomadaire | ~2 Mo/Parquet | NDJSON | Après ingestion |
| Chargement Silver→Gold | GCS Silver | BigQuery raw | Hebdomadaire | ~1 Mo/semaine | BQ tables | Après normalisation Silver |
| Transformation dbt | BigQuery raw | BigQuery Gold | Hebdomadaire | ~500 Ko nouvelles lignes | BQ views/tables | Après chargement Silver→Gold |
| Requêtes analytiques | BigQuery Gold | API FastAPI → Analyste | À la demande | < 1 Go scanné/req | JSON/HTTP | Appel HTTP analyste |
| Alertes pipeline | GitHub Actions / Python | Discord webhook | Sur erreur | Minimal | Text | Échec job ou données non disponibles avant 10h lundi |

---

## 3. Vue infrastructure — Représentation GCP

```mermaid
graph TB
    subgraph GCP["Google Cloud Platform (europe-west1)"]
        subgraph IAM["IAM — Comptes de service"]
            SA1["nexus-ingestion SA<br/>Storage objectAdmin<br/>BQ dataEditor (raw)"]
            SA2["nexus-api SA<br/>BQ dataViewer (gold uniquement)"]
        end

        subgraph Storage["Google Cloud Storage"]
            GCS["Bucket nexus-analytics-bucket<br/>Bronze: Standard (90j) → Coldline<br/>Silver: Standard (durée projet)<br/>Région: EU multi-région"]
        end

        subgraph BQ["BigQuery"]
            BQR["Dataset raw<br/>(Silver NDJSON chargé)"]
            BQG["Dataset gold_gold<br/>(dim + facts, expiration 730j)"]
            BQS["Dataset gold_staging<br/>(vues staging)"]
        end

        subgraph Compute["Compute"]
            CR["Cloud Run<br/>API FastAPI<br/>(serverless, tier gratuit)"]
        end
    end

    subgraph Local["Environnement local / CI"]
        PY["Python scripts<br/>(ingestion + silver)"]
        DBT["dbt Core<br/>(transformation Gold)"]
        TF["Terraform<br/>(Infrastructure as Code)"]
        GHA["GitHub Actions<br/>(CI: lint + tests)"]
    end

    SA1 --> GCS
    SA1 --> BQR
    SA2 --> BQG
    SA2 --> BQS
    PY --> GCS
    GCS --> DBT
    DBT --> BQG
    BQG --> CR
    TF --> GCP
    GHA --> PY
```

---

## 4. Vue opérationnelle — Pipeline hebdomadaire

```mermaid
sequenceDiagram
    participant Dim as Dimanche soir 20h00
    participant OE as Oracle's Elixir
    participant LP as Leaguepedia
    participant RA as Riot API
    participant Bronze as GCS Bronze
    participant Silver as GCS Silver
    participant BQ as BigQuery
    participant Discord as Discord #alerts

    Dim->>OE: GET CSV 2026
    OE-->>Bronze: bronze/oracle_elixir/2026/
    Discord-->>Discord: ✅ Oracle's Elixir ingéré (N lignes)

    Dim->>LP: Cargo API × 9 tables
    LP-->>Bronze: bronze/leaguepedia/{table}/{date}.json
    Discord-->>Discord: ✅ Leaguepedia ingéré (9 tables)

    Bronze->>Silver: lfl_matches (3053 lignes)
    Bronze->>Silver: lfl_player_stats (30530 lignes)
    Bronze->>Silver: lfl_players (792 joueurs)
    Bronze->>Silver: lfl_drafts
    Discord-->>Discord: ✅ Silver transforms complets

    Silver->>BQ: bq_loader (WRITE_TRUNCATE)
    BQ->>BQ: dbt run (staging → dims → facts)
    BQ->>BQ: dbt test (not_null, unique, relationships)
    Discord-->>Discord: ✅ Gold disponible — lundi avant 8h00

    opt Riot API (si nouveaux Riot IDs disponibles)
        Silver->>RA: lfl_players Silver → PUUIDs
        RA-->>Bronze: bronze/riot_api/{date}.ndjson
    end
```

---

## 5. Justification des choix techniques

### Pourquoi GCS comme couche Bronze/Silver ?

GCS est le stockage objet natif GCP, avec intégration directe BigQuery (`load_table_from_uri`). Le stockage objet est adapté à des fichiers NDJSON non structurés de quelques Mo. La facturation est à l'usage (~0,10€/mois pour 5 Go). Terraform permet de gérer les lifecycle policies (transition Coldline) comme code versionné.

### Pourquoi le pattern Medallion ?

La séparation Bronze/Silver/Gold garantit la traçabilité complète (chaque donnée Gold est retrouvable jusqu'à son fichier Bronze source). En cas d'erreur dans la normalisation Silver, on peut recalculer sans réingérer depuis les APIs externes. Ce pattern est devenu un standard de l'industrie du datalake (Databricks Medallion Architecture, Delta Lake).

### Pourquoi pas de streaming ?

Les données LFL sont publiées après chaque journée de compétition. Il n'existe pas de besoin temps réel chez Nexus Analytics. Un pipeline batch hebdomadaire consomme plusieurs ordres de grandeur d'énergie de moins qu'un pipeline streaming pour le même résultat analytique (choix éco-responsable conforme au RGESN 2024).

### Pourquoi pas un catalogue de données outillé ?

Trois outils ont été évalués avant de choisir l'approche catalogue retenue.

#### Comparatif outils catalogue

| Critère | Google Cloud Dataplex | OpenMetadata | dbt docs + DATA_CATALOG.md *(retenu)* |
|---------|----------------------|--------------|---------------------------------------|
| **Intégration GCS + BigQuery** | Native — scan automatique des assets GCS et BQ | Via connecteurs configurables (non natif) | dbt couvre BigQuery Gold ; DATA_CATALOG.md couvre GCS Bronze/Silver |
| **Lineage automatique** | Oui — détecte les dépendances entre ressources GCP | Oui — lineage multi-sources | Oui dans dbt (`dbt docs serve` génère le DAG) ; lineage GCS → BQ documenté manuellement dans DATA_CATALOG.md |
| **Installation** | Managed GCP — activable en 5 min via Terraform | Self-hosted — Docker/Kubernetes requis | Aucune infrastructure supplémentaire — dbt déjà en place |
| **Coût mensuel** | ~15–50€/mois selon volume scanné (pricing à l'asset) | 0€ (open source) + coût infra serveur (~20€/mois min) | 0€ — dbt Core gratuit, DATA_CATALOG.md statique |
| **Gouvernance / RGPD** | Tags de sensibilité GCP (PII tagging), DLP intégré | Politiques de données, classification custom | Classification manuelle dans DATA_CATALOG.md (tableau RGPD par colonne) |
| **Adapté projet mono-équipe** | Surdimensionné — conçu pour des dizaines de datasets | Surdimensionné — conçu pour des équipes data | Adapté — un fichier markdown + `dbt docs serve` |
| **Courbe d'apprentissage** | Faible (interface GCP) | Élevée (configuration API, connecteurs, auth) | Nulle — déjà maîtrisé |
| **Mise à jour catalogue** | Automatique (scan planifié) | Semi-automatique (connecteurs) | Manuelle (DATA_CATALOG.md) + automatique pour Gold (dbt docs) |

#### Décision et justification

**Outil retenu : `dbt docs` (Gold) + `docs/DATA_CATALOG.md` (Bronze/Silver)**

Raisons :

1. **Volume et périmètre** : 4 sources, 11 modèles dbt, 1 équipe. Google Dataplex et OpenMetadata sont conçus pour des centaines de datasets et des équipes multi-profils — leur coût opérationnel (humain et financier) dépasse la valeur apportée.

2. **Coût** : le budget Nexus Analytics est de 8€/mois réel vs 300€ alloué. Ajouter Dataplex ajouterait 15–50€/mois pour un gain marginal sur ce périmètre.

3. **Intégration dbt** : `dbt docs serve` génère automatiquement un catalogue interactif de la couche Gold (schémas, descriptions, tests, DAG de lignée) depuis les fichiers `schema.yml` déjà écrits. Ce catalogue est fonctionnel sans configuration supplémentaire.

4. **Couverture Bronze/Silver** : `docs/DATA_CATALOG.md` documente statiquement les 6 sources Bronze et 4 tables Silver avec schéma, volume, classification RGPD et lignée. Mise à jour manuelle à chaque ajout de source.

5. **Évolutivité** : si le projet s'étend à de nouvelles équipes ou à 50+ tables, **Google Cloud Dataplex** serait l'outil recommandé — intégration GCS/BigQuery native, PII tagging automatique, lifecycle management. La migration serait facilitée par la structure déjà en place (metadata GCS, schema.yml dbt).

#### Commande pour générer le catalogue Gold interactif

```bash
cd dbt
uv run --with dbt-bigquery dbt docs generate --project-dir . --profiles-dir .
uv run --with dbt-bigquery dbt docs serve --project-dir . --profiles-dir .
# http://localhost:8080 — DAG interactif + schémas + descriptions + tests
```
