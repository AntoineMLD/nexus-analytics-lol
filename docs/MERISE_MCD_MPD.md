# Modélisation MERISE — Nexus Analytics

> Document de modélisation des données pour la couche Gold (BigQuery + dbt).
> Répond aux critères C11 (MERISE) et C13 (modélisation entrepôt) du référentiel RNCP.

---

## 1. Modèle Conceptuel de Données (MCD)

Le MCD décrit les entités du domaine métier et leurs associations,
indépendamment de toute technologie.

### Entités

**JOUEUR**
Représente un joueur professionnel ayant participé à au moins une partie LFL ou EMEA Masters.
Identifié par son nom de page wiki Leaguepedia (`player_link`).

**EQUIPE**
Représente une équipe ayant participé au moins à une partie LFL ou EMEA Masters.
Identifiée par son nom d'équipe (`team_name`).

**PARTIE**
Représente une partie individuelle d'un match LFL ou EMEA Masters (une game dans un BO1/BO3/BO5).
Identifiée par `game_id` (identifiant Leaguepedia unique).

**MATCH**
Représente un match complet (série de parties). Identifié par `match_id`.
Un match contient entre 1 et 5 parties.

**TOURNOI**
Représente une compétition LFL ou EMEA Masters (split, saison). Identifié par `overview_page`
(ex: `LFL/2025 Season/Spring Split`, `EMEA Masters/2025 Season/Spring`).

### Associations

```
JOUEUR ─────────────── PARTICIPE_A ─────────────── PARTIE
  │                    (1,n)  (10,10)                  │
  │                  Un joueur participe à              │
  │                  plusieurs parties ;                │
  │                  une partie a exactement 10 joueurs │
  │                                                     │
EQUIPE ─────────────── AFFRONTE ───────────────── PARTIE
                       (1,n)  (2,2)
                  Une équipe joue plusieurs parties ;
                  une partie oppose exactement 2 équipes

PARTIE ─────────────── APPARTIENT_A ──────────── MATCH
       (1,n)  (1,5)
  Un match contient 1 à 5 parties

MATCH ──────────────── FAIT_PARTIE_DE ─────────── TOURNOI
      (1,n)  (1,n)
  Un tournoi contient plusieurs matchs
```

### Cardinalités résumées

| Association | Entité A | Card. A | Entité B | Card. B |
|-------------|----------|---------|----------|---------|
| PARTICIPE_A | JOUEUR | 1,n | PARTIE | 10,10 |
| AFFRONTE | EQUIPE | 1,n | PARTIE | 2,2 |
| APPARTIENT_A | PARTIE | 1,n | MATCH | 1,5 |
| FAIT_PARTIE_DE | MATCH | 1,n | TOURNOI | 1,n |

---

## 2. Modèle Logique de Données (MLD)

Traduction du MCD en tables relationnelles avant implémentation physique.

```
JOUEUR (player_id PK, player_name, total_games, total_wins, win_rate_pct,
        avg_kills, avg_deaths, avg_assists, avg_cs, avg_damage,
        avg_vision_score, teams_played_for)

EQUIPE (team_name PK, total_games)

MATCH (game_id PK, match_id FK→MATCH_SERIE, overview_page,
       tournament, datetime_utc, team1 FK→EQUIPE, team2 FK→EQUIPE,
       win_team FK→EQUIPE, loss_team FK→EQUIPE,
       gamelength, gamelength_seconds, patch, n_game_in_match,
       team1_gold, team2_gold, team1_kills, team2_kills,
       team1_dragons, team2_dragons, team1_barons, team2_barons,
       team1_towers, team2_towers)

PERFORMANCE_JOUEUR (game_id FK→MATCH, player_link FK→JOUEUR,
                    match_id, overview_page, tournament, datetime_utc,
                    player_name, team FK→EQUIPE, team_vs FK→EQUIPE,
                    champion, role, side, player_win,
                    kills, deaths, assists, gold, cs,
                    damage_to_champions, vision_score, kda_ratio,
                    gamelength_seconds, patch, win_team, loss_team,
                    team1_gold, team2_gold, n_game_in_match)
    PK composite : (game_id, player_link)
```

---

## 3. Modèle Physique de Données (MPD)

Implémentation concrète dans BigQuery (schéma en étoile, couche Gold dbt).

### Schéma en étoile (Star Schema)

```
                    ┌─────────────────┐
                    │   dim_player    │
                    │─────────────────│
                    │ player_id  (PK) │
                    │ player_name     │
                    │ total_games     │
                    │ total_wins      │
                    │ win_rate_pct    │
                    │ avg_kills       │
                    │ avg_deaths      │
                    │ avg_assists     │
                    │ avg_cs          │
                    │ avg_damage      │
                    │ avg_vision_score│
                    │ teams_played_for│
                    └────────┬────────┘
                             │ player_link = player_id
                             │
┌────────────────┐    ┌──────┴──────────────────┐    ┌──────────────────┐
│   dim_team     │    │    fact_player_game      │    │  stg_lfl_matches │
│────────────────│    │─────────────────────────│    │──────────────────│
│ team_name (PK) │    │ game_id     (FK→matches) │    │ game_id     (PK) │
│ total_games    │◄───│ player_link (FK→player)  │    │ match_id         │
└────────────────┘    │ match_id                 │    │ overview_page    │
     team = team_name │ overview_page            │    │ tournament       │
                      │ tournament               │    │ datetime_utc     │
                      │ datetime_utc             │───►│ team1            │
                      │ player_name              │    │ team2            │
                      │ team                     │    │ win_team         │
                      │ team_vs                  │    │ loss_team        │
                      │ champion                 │    │ gamelength       │
                      │ role                     │    │ gamelength_sec   │
                      │ side                     │    │ patch            │
                      │ player_win               │    │ team1_gold       │
                      │ kills                    │    │ team2_gold       │
                      │ deaths                   │    │ team1_kills      │
                      │ assists                  │    │ team2_kills      │
                      │ gold                     │    │ team1_dragons    │
                      │ cs                       │    │ team2_dragons    │
                      │ damage_to_champions      │    │ team1_barons     │
                      │ vision_score             │    │ team2_barons     │
                      │ kda_ratio    (calculé)   │    │ team1_towers     │
                      │ gamelength_seconds       │    │ team2_towers     │
                      │ patch                    │    │ n_game_in_match  │
                      │ win_team                 │    └──────────────────┘
                      │ loss_team                │
                      │ team1_gold               │
                      │ team2_gold               │
                      │ n_game_in_match          │
                      └──────────────────────────┘
```

### Types BigQuery

| Colonne | Type BigQuery | Contrainte |
|---------|--------------|------------|
| `game_id` | STRING | NOT NULL |
| `player_link` | STRING | NOT NULL |
| `datetime_utc` | TIMESTAMP | NULLABLE |
| `kills` / `deaths` / `assists` | INT64 | NULLABLE |
| `gold` / `cs` | INT64 | NULLABLE |
| `damage_to_champions` | INT64 | NULLABLE |
| `vision_score` | INT64 | NULLABLE |
| `kda_ratio` | FLOAT64 | calculé (SAFE_DIVIDE) |
| `player_win` | BOOL | NULLABLE |
| `gamelength_seconds` | INT64 | NULLABLE |
| `team1_gold` / `team2_gold` | INT64 | NULLABLE |

### Nouveaux modèles Gold (ajoutés en Phase 2)

Les modèles suivants ont été ajoutés pour couvrir les analyses méta demandées par Nexus Analytics :

#### `dim_champion` — Dimension champions

| Colonne | Type BigQuery | Description |
|---------|--------------|-------------|
| `champion` | STRING (PK) | Nom du champion |
| `total_games_played` | INT64 | Parties où le champion a été joué |
| `total_picks` | INT64 | Nombre total de sélections |
| `win_rate_pct` | FLOAT64 | Taux de victoire global (0-100) |
| `avg_kills/deaths/assists` | FLOAT64 | Stats moyennes |
| `picks_top/jungle/mid/bot/support` | INT64 | Sélections par rôle |
| `first_played` / `last_played` | TIMESTAMP | Fenêtre temporelle LFL |

#### `dim_patch` — Dimension patches

| Colonne | Type BigQuery | Description |
|---------|--------------|-------------|
| `patch` | STRING (PK) | Version du jeu (ex: `14.5`) |
| `total_games` | INT64 | Parties jouées sur ce patch |
| `patch_start_date` / `patch_end_date` | TIMESTAMP | Fenêtre temporelle |
| `tournaments_count` | INT64 | Nombre de tournois sur ce patch |

#### `fact_draft` — Faits draft (picks et bans)

Source Silver : `pipeline/silver_transforms/lfl_drafts.py` — unpivot de `PicksAndBansS7`
(format large 20 colonnes → format long, une ligne par action).

| Colonne | Type BigQuery | Description |
|---------|--------------|-------------|
| `game_id` | STRING (FK) | Référence vers `stg_lfl_matches` |
| `team_name` | STRING | Équipe concernée |
| `team_side` | INT64 | 1 (bleu) ou 2 (rouge) |
| `action_type` | STRING | `pick` ou `ban` |
| `action_order` | INT64 | Ordre dans la phase (1-5) |
| `champion` | STRING | Champion sélectionné ou banni |
| `team_won` | BOOL | L'équipe a gagné la partie ? |
| `patch` | STRING | Via LEFT JOIN `stg_lfl_matches` |

#### `fact_meta_trend` — Tendances méta par champion et patch

Granularité : (champion, patch, overview_page). Utilisée par l'endpoint `GET /meta/trends`.

| Colonne | Type BigQuery | Description |
|---------|--------------|-------------|
| `champion` | STRING | Nom du champion |
| `patch` | STRING | Version du jeu |
| `overview_page` | STRING | Tournoi / split |
| `picks` | INT64 | Nombre de sélections |
| `wins` | INT64 | Nombre de victoires |
| `pick_rate_pct` | FLOAT64 | % du total de parties du tournoi+patch |
| `win_rate_pct` | FLOAT64 | Taux de victoire sur ce patch |
| `avg_kills/deaths/assists/damage` | FLOAT64 | Stats moyennes |

### Localisation et cycle de vie

| Dataset | Région | Expiration tables |
|---------|--------|------------------|
| `gold_gold` | europe-west1 | 730 jours (24 mois) |
| `gold_staging` | europe-west1 | — (vues, pas de données) |
| `raw` | europe-west1 | — (réingestée régulièrement) |

---

## 4. Justification des choix de modélisation

### Approche bottom-up retenue et justification

L'entrepôt de données a été construit selon une approche **bottom-up** (approche Kimball).

**Définition** : l'approche bottom-up part des besoins d'analyse concrets pour construire les data marts, puis les consolide progressivement en entrepôt global. À l'opposé, l'approche top-down (Inmon) consiste à modéliser l'entrepôt complet en 3NF avant de créer les data marts.

**Justification pour Nexus Analytics :**

| Critère | Bottom-up | Top-down | Choix retenu |
|---------|-----------|----------|-------------|
| Volume de données | Faible (4 535 parties, ~32 700 stats joueurs) | — | Bottom-up adapté aux petits volumes |
| Périmètre | Délimité (LFL + EMEA Masters) | — | Pas de besoin d'intégrer des dizaines de sources hétérogènes |
| Délai | 14 semaines | Projet de 6–18 mois typiquement | Bottom-up livrable en 14 semaines |
| Équipe | 1 data engineer | Nécessite une équipe modélisation dédiée | Solo → bottom-up obligatoire |
| Besoins utilisateurs | Explicitement identifiés en entretien (pick/ban rates, winrates, scouting) | — | Les data marts correspondent directement aux besoins Yasmine |

La modélisation a commencé par les besoins analytiques de l'analyste senior (Yasmine Karim, entretien du 14 mai 2026) et a produit directement les data marts :
- `fact_player_game` → répondre à "stats d'un joueur sur la saison"
- `fact_draft` → répondre à "compositions jouées par une équipe adversaire"
- `fact_meta_trend` → répondre à "pick/ban rates par champion sur les 3 derniers patches"

---

### Pourquoi un schéma en étoile ?

Le schéma en étoile est adapté à ce projet car :
- Les requêtes analytiques portent principalement sur `fact_player_game` (stats par joueur par partie)
- `dim_player` et `dim_team` sont de petites dimensions stables (< 1 000 lignes)
- BigQuery est optimisé pour les jointures en étoile grâce au stockage en colonnes

### SCD Type 1 et SCD Type 2 — stratégie mixte

**SCD Type 1 (écrasement)** est appliqué sur `dim_player`, `dim_team`, `dim_champion`, `dim_patch`.
Ces dimensions sont reconstruites intégralement à chaque run dbt (WRITE_TRUNCATE).
Justification : les statistiques sont des agrégats calculés sur l'historique complet — elles n'ont
pas de "valeur à un instant T" pertinente à conserver.

**SCD Type 2 (historisation)** est appliqué sur `dim_player_current_team` via le snapshot dbt
`snap_player_team` (`dbt/snapshots/snap_player_team.sql`).
Les changements d'équipe d'un joueur sont historisés avec les colonnes `dbt_valid_from` / `dbt_valid_to`.
Justification : l'affiliation d'un joueur à une équipe varie significativement au fil des saisons
(transferts, prêts, montées/descentes D1↔D2). Nexus Analytics a besoin de répondre à "Dans quelle
équipe jouait ce joueur au 1er mars 2025 ?" — ce que SCD Type 1 ne permet pas.

### Pourquoi `SAFE_DIVIDE` pour le KDA ?

`SAFE_DIVIDE(kills + assists, deaths)` renvoie `NULL` si `deaths = 0`
plutôt que de lever une erreur. On utilise `NULLIF(deaths, 0)` pour préserver
la sémantique "0 mort = performance parfaite" en laissant le calcul à NULL
(et non ∞).
