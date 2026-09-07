# Catalogue de données — Nexus Analytics

> **Périmètre** : données LFL (La Ligue Française D1 + D2) et EMEA Masters, saisons 2013–2026.
>
> **Mise à jour** : 2026-09-07
>
> **Propriétaire** : Nexus Analytics — projet RNCP37638 Expert infrastructures data
>
> **Critères RNCP couverts** : C19 (intégration catalogue), C20 (cycle de vie), C11 (RGPD)

---

## Sommaire

1. [Architecture et flux de données](#1-architecture-et-flux-de-données)
2. [Couche Bronze — GCS](#2-couche-bronze--gcs)
3. [Couche Silver — GCS](#3-couche-silver--gcs)
4. [Couche Gold — BigQuery](#4-couche-gold--bigquery)
5. [Classification RGPD](#5-classification-rgpd)
6. [Cycle de vie et rétention](#6-cycle-de-vie-et-rétention)
7. [Lignée des données](#7-lignée-des-données)

---

## 1. Architecture et flux de données

```
Sources externes
  ├── Leaguepedia Cargo API    → bronze/leaguepedia/{Table}/{date}.json
  ├── Oracle's Elixir (CSV)    → bronze/oracle_elixir/{year}/{file}.csv
  └── Riot Games API           → bronze/riot_api/{date}.ndjson

        │ ingestion/ (Python, argparse CLI)
        ▼

GCS Bronze (données brutes, NDJSON / CSV)
        │ pipeline/silver_transforms/ (Python)
        ▼

GCS Silver (données normalisées, NDJSON)
        │ pipeline/loaders/bq_loader.py (WRITE_TRUNCATE)
        ▼

BigQuery raw (tables sources pour dbt)
        │ dbt run (SQL)
        ▼

BigQuery gold_gold (modèles dimensionnels)
        │
        ├── API FastAPI (/players, /matches, /stats)
        └── Dashboard Streamlit (8 pages)
```

| Couche | Stockage | Format | Rôle |
|--------|----------|--------|------|
| Bronze | GCS `nexus-analytics-bucket` | NDJSON / CSV | Données brutes — jamais modifiées |
| Silver | GCS `nexus-analytics-bucket` | NDJSON | Données normalisées, filtrées LFL + EMEA |
| Gold (raw) | BigQuery dataset `raw` | Tables BQ | Copie Silver pour dbt |
| Gold (gold) | BigQuery dataset `gold_gold` | Tables BQ | Modèles dimensionnels analytiques |

---

## 2. Couche Bronze — GCS

### 2.1 Leaguepedia — `ScoreboardGames`

**Chemin GCS** : `bronze/leaguepedia/ScoreboardGames/{YYYY-MM-DD}.json`
**Format** : NDJSON — une ligne JSON par partie
**Source** : Leaguepedia Cargo API, table `ScoreboardGames`
**Filtre d'ingestion** : `OverviewPage IN (89 pages LFL + EMEA Masters)`
**Fréquence de mise à jour** : à chaque nouveau split LFL / EMEA Masters
**Volume** : ~4 535 lignes (LFL 2013–2026 + EMEA Masters)

| Champ | Type | Description |
|-------|------|-------------|
| `GameId` | string | Identifiant unique de la partie (ex: `LFL 2024 Spring_1_1`) |
| `MatchId` | string | Identifiant du match (série de parties) |
| `DateTime UTC` | string | Date et heure UTC de la partie |
| `Team1` | string | Nom de l'équipe côté bleu |
| `Team2` | string | Nom de l'équipe côté rouge |
| `WinTeam` | string | Nom de l'équipe gagnante |
| `Patch` | string | Version du patch (ex: `14.5`) |
| `Gamelength` | string | Durée en format `MM:SS` |
| `OverviewPage` | string | Page wiki du tournoi (ex: `LFL/2024 Season/Spring`) |
| `ingested_at` | string | Timestamp d'ingestion ISO 8601 |
| `source` | string | Toujours `"leaguepedia"` |
| `schema_version` | string | Version du schéma d'ingestion |

---

### 2.2 Leaguepedia — `ScoreboardPlayers`

**Chemin GCS** : `bronze/leaguepedia/ScoreboardPlayers/{YYYY-MM-DD}.json`
**Format** : NDJSON
**Source** : Leaguepedia Cargo API, table `ScoreboardPlayers`
**Filtre d'ingestion** : `OverviewPage LIKE 'LFL/%' OR OverviewPage LIKE 'EMEA Masters/%'`
**Volume** : ~32 690 lignes (10 joueurs × 4 535 parties)

| Champ | Type | Description |
|-------|------|-------------|
| `GameId` | string | Référence à `ScoreboardGames.GameId` |
| `Link` | string | Nom wiki du joueur (clé joueur) |
| `Team` | string | Équipe du joueur dans cette partie |
| `Champion` | string | Champion joué |
| `Role` | string | Rôle : `Top`, `Jungle`, `Mid`, `Bot`, `Support` |
| `Kills` | string | Nombre de kills (numérique en string) |
| `Deaths` | string | Nombre de deaths |
| `Assists` | string | Nombre d'assists |
| `Gold` | string | Or total gagné |
| `PlayerWin` | string | `"Yes"` ou `"No"` |
| `DateTime UTC` | string | Date et heure de la partie |
| `OverviewPage` | string | Tournoi/split |

---

### 2.3 Leaguepedia — `PicksAndBansS7`

**Chemin GCS** : `bronze/leaguepedia/PicksAndBansS7/{YYYY-MM-DD}.json`
**Format** : NDJSON — format wide (une colonne par pick/ban)
**Source** : Leaguepedia Cargo API, table `PicksAndBansS7`
**Filtre** : aucun au Bronze (toutes leagues), filtrage par OverviewPage au Silver
**Volume** : ~103 382 lignes (global, non filtré LFL)

| Champ | Type | Description |
|-------|------|-------------|
| `GameId` | string | Référence à `ScoreboardGames.GameId` |
| `OverviewPage` | string | Tournoi/split |
| `Team1Ban1` … `Team1Ban5` | string | Bans de l'équipe 1 (ordre chronologique) |
| `Team2Ban1` … `Team2Ban5` | string | Bans de l'équipe 2 |
| `Team1Pick1` … `Team1Pick5` | string | Picks de l'équipe 1 |
| `Team2Pick1` … `Team2Pick5` | string | Picks de l'équipe 2 |

---

### 2.4 Leaguepedia — `Tournaments`

**Chemin GCS** : `bronze/leaguepedia/Tournaments/{YYYY-MM-DD}.json`
**Format** : NDJSON
**Volume** : ~10 462 lignes (toutes compétitions mondiales)
**Rôle** : table de référence — les Silver transforms filtrent par `League IN (TARGET_LEAGUES)` pour extraire les OverviewPages LFL + EMEA Masters.

| Champ | Type | Description |
|-------|------|-------------|
| `OverviewPage` | string | Identifiant wiki du tournoi (clé de jointure) |
| `Name` | string | Nom complet du tournoi |
| `League` | string | Nom de la ligue (ex: `La Ligue Française`) |
| `DateStart` | string | Date de début |
| `Date` | string | Date de fin |

---

### 2.5 Oracle's Elixir — CSV historiques

**Chemin GCS** : `bronze/oracle_elixir/{year}/{filename}.csv`
**Format** : CSV avec en-tête
**Source** : [Oracle's Elixir](https://oracleselixir.com/) — Google Drive partagé
**Couverture** : 2014–2026 (13 fichiers)
**Lignes** : ~500 000+ (données mondiales, non filtrées LFL)

> **Usage** : validation croisée (méthode 5 du quality check `lfl_completeness.py`). Non chargé en Gold.

---

### 2.6 Riot API — PUUIDs et match IDs

**Chemin GCS** : `bronze/riot_api/{YYYY-MM-DD}.ndjson`
**Format** : NDJSON
**Source** : `GET /riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}` + `GET /lol/match/v5/matches/by-puuid/{puuid}/ids`

| Champ | Type | RGPD | Description |
|-------|------|------|-------------|
| `player` | string | Public | Nom wiki du joueur |
| `account` | string | Public | Riot ID (pseudonyme public) |
| `puuid` | string | **Pseudonyme** | PUUID Riot — identifiant technique unique |
| `ranked_match_ids` | array | Non personnel | IDs des 100 dernières ranked solo |

---

## 3. Couche Silver — GCS

### 3.1 `lfl_matches`

**Chemin GCS** : `silver/leaguepedia/lfl_matches/{YYYY-MM-DD}.json`
**Source Bronze** : `Tournaments` + `ScoreboardGames`
**Script** : `pipeline/silver_transforms/lfl_matches.py`
**Périmètre** : LFL D1 + D2 + EMEA Masters, 2013–2026
**Volume** : ~4 535 lignes

| Champ | Type Python | Description |
|-------|-------------|-------------|
| `game_id` | `str` | Identifiant unique de la partie (clé primaire) |
| `match_id` | `str` | Identifiant du match |
| `datetime_utc` | `str \| None` | Date ISO 8601 (ex: `2024-02-03T14:00:00`) |
| `team1` | `str` | Équipe côté bleu |
| `team2` | `str` | Équipe côté rouge |
| `win_team` | `str` | Équipe gagnante |
| `patch` | `str \| None` | Version du patch (ex: `14.5`) |
| `gamelength_seconds` | `int \| None` | Durée en secondes |
| `overview_page` | `str` | Tournoi/split wiki |

---

### 3.2 `lfl_player_stats`

**Chemin GCS** : `silver/leaguepedia/lfl_player_stats/{YYYY-MM-DD}.json`
**Source Bronze** : `Tournaments` + `ScoreboardPlayers`
**Script** : `pipeline/silver_transforms/lfl_player_stats.py`
**Volume** : ~32 690 lignes

| Champ | Type Python | Description |
|-------|-------------|-------------|
| `game_id` | `str` | Clé étrangère → `lfl_matches.game_id` |
| `player_link` | `str` | Nom wiki du joueur (clé joueur) |
| `team` | `str` | Équipe du joueur dans cette partie |
| `champion` | `str` | Champion joué |
| `role` | `str` | Rôle (`Top`, `Jungle`, `Mid`, `Bot`, `Support`) |
| `kills` | `int \| None` | Kills |
| `deaths` | `int \| None` | Deaths |
| `assists` | `int \| None` | Assists |
| `gold` | `int \| None` | Or total gagné |
| `player_win` | `bool \| None` | `True` si victoire |
| `datetime_utc` | `str \| None` | Date ISO 8601 |
| `overview_page` | `str` | Tournoi/split wiki |

---

### 3.3 `lfl_drafts`

**Chemin GCS** : `silver/leaguepedia/lfl_drafts/{YYYY-MM-DD}.json`
**Source Bronze** : `Tournaments` + `PicksAndBansS7`
**Script** : `pipeline/silver_transforms/lfl_drafts.py`
**Volume** : ~82 630 lignes (format dépivotté — une ligne par action)

| Champ | Type Python | Description |
|-------|-------------|-------------|
| `game_id` | `str` | Clé étrangère → `lfl_matches.game_id` |
| `champion` | `str` | Champion sélectionné ou banni |
| `action_type` | `str` | `"pick"` ou `"ban"` |
| `team_side` | `int` | `1` = côté bleu, `2` = côté rouge |
| `pick_order` | `int` | Ordre de l'action dans le draft (1–20) |
| `overview_page` | `str` | Tournoi/split wiki |

---

### 3.4 `lfl_players`

**Chemin GCS** : `silver/leaguepedia/lfl_players/{YYYY-MM-DD}.json`
**Source Bronze** : `Tournaments` + `TournamentRosters` + `Players`
**Script** : `pipeline/silver_transforms/lfl_players.py`
**Volume** : 792 joueurs historiques (2013–2026)

| Champ | Type Python | RGPD | Description |
|-------|-------------|------|-------------|
| `player_link` | `str` | Public | Nom wiki du joueur (clé primaire) |
| `player_name` | `str` | Public | Pseudonyme professionnel public |
| `soloqueue_ids_raw` | `str \| None` | Public | Contenu brut du champ `SoloqueueIds` wiki |
| `euw_accounts` | `list[str]` | **Pseudonyme** | Comptes EUW identifiés (Riot IDs ou summoner names) |

> **Note RGPD** : `euw_accounts` contient des pseudonymes publics de joueurs professionnels.
> Traitement licite sous RGPD art. 6.1.f (intérêt légitime — analyse statistique LFL).

---

## 4. Couche Gold — BigQuery

**Dataset** : `{GCP_PROJECT_ID}.gold_gold`
**Outil** : dbt Core — modèles SQL versionnés dans `dbt/models/`
**Tests** : `not_null`, `unique`, `relationships`, `accepted_values` sur toutes les colonnes clés

### 4.1 Vues staging (dataset `gold_gold`)

| Modèle | Type | Description |
|--------|------|-------------|
| `stg_lfl_matches` | VIEW | Vue sur `raw.lfl_matches` — sélection colonnes + cast datetime |
| `stg_lfl_player_stats` | VIEW | Vue sur `raw.lfl_player_stats` — une ligne/joueur/partie |
| `stg_lfl_drafts` | VIEW | Vue sur `raw.lfl_drafts` — une ligne/action pick-ban |

---

### 4.2 `dim_team`

**Grain** : une ligne par équipe
**Volume** : ~194 équipes (LFL + EMEA Masters)

| Colonne | Type BQ | Description |
|---------|---------|-------------|
| `team_name` | STRING | Nom de l'équipe — clé primaire |
| `total_games` | INT64 | Nombre total de parties jouées |
| `first_game_date` | DATE | Date de la première partie connue |
| `last_game_date` | DATE | Date de la dernière partie connue |

---

### 4.3 `dim_player`

**Grain** : un joueur unique — statistiques agrégées toutes saisons
**Volume** : ~939 joueurs (LFL + EMEA Masters)

| Colonne | Type BQ | Description |
|---------|---------|-------------|
| `player_id` | STRING | `player_link` wiki — clé primaire |
| `player_name` | STRING | Pseudonyme du joueur |
| `total_games` | INT64 | Nombre total de parties jouées |
| `win_rate_pct` | FLOAT64 | Taux de victoire (0–100) |
| `avg_kills` | FLOAT64 | Moyenne kills |
| `avg_deaths` | FLOAT64 | Moyenne deaths |
| `avg_assists` | FLOAT64 | Moyenne assists |
| `most_played_champion` | STRING | Champion le plus joué |
| `most_played_role` | STRING | Rôle le plus joué |

---

### 4.4 `dim_champion`

**Grain** : un champion unique — statistiques agrégées toutes saisons
**Volume** : ~170 champions

| Colonne | Type BQ | Description |
|---------|---------|-------------|
| `champion` | STRING | Nom du champion — clé primaire |
| `total_games_played` | INT64 | Nombre de parties jouées |
| `win_rate_pct` | FLOAT64 | Taux de victoire global (0–100) |
| `avg_kills` | FLOAT64 | Moyenne kills |
| `avg_deaths` | FLOAT64 | Moyenne deaths |
| `avg_assists` | FLOAT64 | Moyenne assists |

---

### 4.5 `dim_patch`

**Grain** : une version de patch
**Volume** : ~109 patches

| Colonne | Type BQ | Description |
|---------|---------|-------------|
| `patch` | STRING | Version (ex: `14.5`) — clé primaire |
| `total_games` | INT64 | Nombre de parties jouées sur ce patch |
| `first_game_date` | DATE | Première partie sur ce patch |
| `last_game_date` | DATE | Dernière partie sur ce patch |

---

### 4.6 `dim_player_current_team` — SCD Type 2

**Grain** : un joueur — équipe actuelle + historique
**Volume** : ~939 joueurs
**Mécanisme** : snapshot dbt `snap_player_team` (colonnes `dbt_valid_from` / `dbt_valid_to`)

| Colonne | Type BQ | Description |
|---------|---------|-------------|
| `player_id` | STRING | `player_link` wiki — clé primaire |
| `player_name` | STRING | Pseudonyme du joueur |
| `current_team` | STRING | Équipe la plus récente |
| `last_game_date` | DATE | Date de la dernière partie dans cette équipe |
| `total_games_in_team` | INT64 | Parties jouées dans l'équipe actuelle |
| `all_teams_played` | ARRAY\<STRING\> | Toutes les équipes jouées (historique complet) |

---

### 4.7 `fact_player_game`

**Grain** : une ligne par joueur par partie
**Volume** : ~32 700 lignes
**Clés étrangères** : `game_id` → `stg_lfl_matches`, `player_link` → `dim_player`

| Colonne | Type BQ | Description |
|---------|---------|-------------|
| `game_id` | STRING | Identifiant de la partie |
| `player_link` | STRING | Identifiant wiki du joueur |
| `team` | STRING | Équipe du joueur |
| `champion` | STRING | Champion joué |
| `role` | STRING | Rôle (`Top`, `Jungle`, `Mid`, `Bot`, `Support`) |
| `kills` | INT64 | Kills |
| `deaths` | INT64 | Deaths |
| `assists` | INT64 | Assists |
| `gold` | INT64 | Or total |
| `player_win` | BOOL | `true` si victoire |
| `kda_ratio` | FLOAT64 | (kills + assists) / max(deaths, 1) |
| `gamelength_seconds` | INT64 | Durée de la partie en secondes |
| `patch` | STRING | Version du patch |
| `datetime_utc` | TIMESTAMP | Date et heure de la partie |
| `overview_page` | STRING | Tournoi/split |

---

### 4.8 `fact_meta_trend`

**Grain** : (champion, patch, overview_page)
**Volume** : ~7 400 lignes
**Usage** : pages Méta, Alerte Méta, LFL vs EMEA Masters du dashboard

| Colonne | Type BQ | Description |
|---------|---------|-------------|
| `champion` | STRING | Nom du champion |
| `patch` | STRING | Version du patch |
| `overview_page` | STRING | Tournoi/split |
| `pick_count` | INT64 | Nombre de fois sélectionné |
| `ban_count` | INT64 | Nombre de fois banni |
| `win_count` | INT64 | Nombre de victoires avec ce champion |
| `total_games` | INT64 | Parties totales sur ce patch + tournoi |
| `pick_rate_pct` | FLOAT64 | pick_count / total_games × 100 |
| `ban_rate_pct` | FLOAT64 | ban_count / total_games × 100 |
| `win_rate_pct` | FLOAT64 | win_count / pick_count × 100 (SAFE_DIVIDE) |

---

### 4.9 `fact_draft`

**Grain** : une action (pick ou ban) par partie
**Volume** : ~82 600 lignes
**Usage** : page Drafts du dashboard

| Colonne | Type BQ | Description |
|---------|---------|-------------|
| `game_id` | STRING | Identifiant de la partie |
| `champion` | STRING | Champion sélectionné ou banni |
| `action_type` | STRING | `"pick"` ou `"ban"` |
| `team_side` | INT64 | `1` = bleu, `2` = rouge |
| `pick_order` | INT64 | Ordre de l'action dans le draft (1–20) |
| `overview_page` | STRING | Tournoi/split |

---

## 5. Classification RGPD

> Référence complète : `docs/RGPD_registre.md`

| Donnée | Catégorie | Pseudonymisée | Base légale | Durée conservation |
|--------|-----------|---------------|-------------|-------------------|
| `player_name` (pseudo pro) | Donnée publique | N/A | Art. 6.1.f | 24 mois Gold |
| `player_link` (nom wiki) | Donnée publique | N/A | Art. 6.1.f | 24 mois Gold |
| `euw_accounts` (Riot ID) | Pseudonyme | Oui | Art. 6.1.f | Silver uniquement |
| `puuid` (PUUID Riot) | Pseudonyme technique | Oui | Art. 6.1.f | Bronze 90j Coldline |
| `ranked_match_ids` | Non personnel | N/A | — | Bronze 90j Coldline |

**Droits des personnes** : suppression sur demande via retrait du `player_link` dans Silver `lfl_players` et re-run dbt. Délai : 72h maximum.

**Responsable du traitement** : Nexus Analytics (projet de certification).

---

## 6. Cycle de vie et rétention

| Couche | Stockage | Classe initiale | Transition | Suppression |
|--------|----------|-----------------|------------|-------------|
| Bronze GCS | `nexus-analytics-bucket` | Standard | → Coldline après 90j (Terraform lifecycle) | Manuelle |
| Silver GCS | `nexus-analytics-bucket` | Standard | Pas de transition | Manuelle |
| Gold BigQuery | `gold_gold` | — | — | Expiration 24 mois (Terraform) |
| Gold BigQuery | `raw` | — | — | Expiration 24 mois (Terraform) |

**Idempotence** : chaque re-run `bq_loader` utilise `WRITE_TRUNCATE` — les tables BigQuery sont entièrement remplacées.

**Versioning** : les fichiers GCS sont nommés par date d'ingestion (`{YYYY-MM-DD}.json`). Les versions précédentes restent accessibles dans GCS tant qu'elles n'ont pas expiré.

---

## 7. Lignée des données

```
Leaguepedia Cargo API
  ├── Tournaments          →  Bronze  →  (référence OverviewPages LFL + EMEA)
  ├── ScoreboardGames      →  Bronze  →  Silver lfl_matches      →  raw.lfl_matches
  │                                           │                       → stg_lfl_matches
  │                                           │                       → fact_player_game
  │                                           └──────────────────────→ fact_meta_trend
  ├── ScoreboardPlayers    →  Bronze  →  Silver lfl_player_stats  →  raw.lfl_player_stats
  │                                           │                       → stg_lfl_player_stats
  │                                           └──────────────────────→ fact_player_game
  │                                                                   → dim_player
  │                                                                   → dim_player_current_team
  ├── PicksAndBansS7       →  Bronze  →  Silver lfl_drafts        →  raw.lfl_drafts
  │                                           │                       → stg_lfl_drafts
  │                                           └──────────────────────→ fact_draft
  ├── TournamentRosters    →  Bronze  →  Silver lfl_players       →  raw.lfl_players
  └── Players              →  Bronze  ┘

Oracle's Elixir (CSV)
  └── bronze/oracle_elixir/{year}/  →  (validation croisée uniquement, non chargé en Gold)

Riot Games API
  └── PUUIDs + match IDs  →  Bronze riot_api/  →  (non chargé en Gold — recherche future)
```

**Modèles dérivés** :
- `dim_team` ← `stg_lfl_matches` (toutes les équipes distinctes)
- `dim_champion` ← `stg_lfl_player_stats` (tous les champions distincts)
- `dim_patch` ← `stg_lfl_matches` (tous les patches distincts)
- `fact_meta_trend` ← `stg_lfl_player_stats` JOIN `stg_lfl_matches` (patch uniquement dans matches)
- `snap_player_team` ← `dim_player_current_team` (snapshot SCD Type 2 — historique des équipes)
