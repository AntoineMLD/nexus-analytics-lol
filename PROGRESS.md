# Nexus Analytics — État d'avancement

## Contexte du projet

Pipeline de données pour analyser la **LFL (La Ligue Française, D1 + D2)** depuis plusieurs sources vers GCS, avec une architecture Bronze → Silver → Gold.

**Objectif final** : alimenter une API FastAPI exposant des métriques LFL (champion pools, win rates, stats joueurs) à partir de modèles dbt Gold sur BigQuery.

---

## Stack technique

- **Python** géré avec `uv`
- **GCS** comme data lake (bucket `nexus-analytics-bucket`)
- **BigQuery** comme data warehouse (à venir)
- **Leaguepedia Cargo API** via `mwrogue` + `mwcleric` (credentials bot dans `.env`)
- **Google Drive API** via `googleapiclient` (clé API dans `.env`)
- **Riot API** via `httpx` (clé API dans `.env`)
- **GCP auth** : `gcloud auth application-default login` + quota project configuré
- **CI** : GitHub Actions — `ruff` (lint + format) + `pytest` à chaque PR
- **Pre-commit** : `ruff` auto-appliqué au commit

---

## Architecture GCS (Medallion)

```
bronze/oracle_elixir/{year}/{filename}.csv              ← CSV brut Oracle's Elixir
bronze/leaguepedia/{TableName}/{YYYY-MM-DD}.json        ← NDJSON brut Leaguepedia (9 tables)
bronze/riot_api/{YYYY-MM-DD}.ndjson                    ← PUUIDs + match IDs ranked EUW
silver/leaguepedia/lfl_players/{YYYY-MM-DD}.json        ← joueurs LFL + comptes EUW
silver/leaguepedia/lfl_matches/{YYYY-MM-DD}.json        ← games normalisées (ScoreboardGames)
silver/leaguepedia/lfl_player_stats/{YYYY-MM-DD}.json   ← stats joueur/game (ScoreboardPlayers)
```

---

## Bronze Oracle's Elixir ✅

13 fichiers CSV ingérés (2014–2026) dans `bronze/oracle_elixir/`.

**Module** : `ingestion/oracle_elixir/ingest.py`

**Logique** :
- Authentification Google Drive via clé API (`developerKey`)
- Recherche du fichier par nom dans le dossier partagé via `files().list()`
- Téléchargement via `files().get_media()`
- Validation : colonnes attendues présentes + minimum 1 000 lignes
- Idempotence : skip si l'année historique est déjà en GCS, toujours réingère l'année courante
- Notification Discord success/failure

**Commande :**
```bash
uv run python -m ingestion.oracle_elixir.ingest --all   # toutes les années
uv run python -m ingestion.oracle_elixir.ingest --year 2026  # réingestion année courante
```

---

## Bronze Leaguepedia (9 tables) ✅

**Module** : `ingestion/leaguepedia/ingest.py`

**Logique** :
- Authentification via bot Fandom (`mwrogue.EsportsClient`)
- Pagination automatique (500 lignes/page, max 8 000 pages)
- Exponential backoff sur rate limits : `1s → 2s → 4s → 8s → 16s → 32s → 60s`
- Notification Discord success/failure par table

| Table | Filtre | Rows |
|---|---|---|
| `ScoreboardGames` | LFL D1 + D2 via `OverviewPage IN (...)` | **3 053** ✅ |
| `ScoreboardPlayers` | `OverviewPage LIKE 'LFL/%'` | **30 530** ✅ |
| `PicksAndBansS7` | aucun | — |
| `Tournaments` | aucun | 10 288 |
| `Teams` | aucun | — |
| `TournamentResults` | aucun | — |
| `TournamentRosters` | aucun | 80 886 |
| `Teamnames` | aucun | — |
| `Players` | aucun | 20 562 |

**Dates d'ingestion actuelles :**
- La plupart : `2026-06-04`
- `Players` : `2026-06-05`
- `ScoreboardGames` : `2026-06-07` → **3 053 rows** ✅
- `ScoreboardPlayers` : `2026-06-05` → **30 530 rows** ✅ (voir problème n°14)

**Commande :**
```bash
uv run python -m ingestion.leaguepedia.ingest             # toutes les tables
uv run python -m ingestion.leaguepedia.ingest --table ScoreboardGames
```

---

## Bronze Riot API ✅

**Module** : `ingestion/riot_api/ingest.py`

**Logique** :
- Lit le Silver `lfl_players` pour trouver les joueurs avec compte EUW (format `name#tag`)
- `GET /riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}` → PUUID
- `GET /lol/match/v5/matches/by-puuid/{puuid}/ids` → 100 dernières parties ranked solo (`queue=420`)
- Rate limiting : `time.sleep(1.2)` entre chaque appel
- Stockage : une ligne NDJSON par compte `{"player", "account", "puuid", "ranked_match_ids"}`
- Résultat : 17/22 comptes Riot ID valides résolus

**Commande :**
```bash
uv run python -m ingestion.riot_api.ingest --silver-date 2026-06-04
```

---

## Silver transforms ✅ complet

> **Validation qualité** — voir `pipeline/quality_checks/lfl_completeness.py` pour le rapport de réconciliation complet (méthodes 1→5). Résumé ci-dessous.

### `lfl_players` — `pipeline/silver_transforms/lfl_players.py`

**Sources Bronze** : `Tournaments`, `TournamentRosters`, `Players`

**Logique** :
- Filtre les tournois LFL (D1 + D2) depuis `Tournaments`
- Extrait les noms wiki des joueurs depuis `TournamentRosters` (délimiteur `;;`)
- Parse le champ `SoloqueueIds` (markup MediaWiki) pour extraire les comptes EUW
- Gère 3 formats : Riot ID `name#EUW`, ancien summoner name, sans marqueur région

**Résultat :**
- 792 joueurs LFL (historique 2013–2026)
- 194 avec comptes EUW identifiés (24%)

```bash
uv run python -m pipeline.silver_transforms.lfl_players --date 2026-06-04 --players-date 2026-06-05
```

---

### `lfl_matches` ✅ — `pipeline/silver_transforms/lfl_matches.py`

**Sources Bronze** : `Tournaments` (filtre LFL), `ScoreboardGames`

**État** : **3 053 lignes** — complet ✅ (`silver/leaguepedia/lfl_matches/2026-06-07.json`)

**Logique** :
1. Charge `Tournaments` Bronze → extrait les 71 OverviewPages LFL
2. Charge `ScoreboardGames` Bronze → filtre par OverviewPage → **3 053 lignes LFL**
3. Normalise chaque ligne :
   - `DateTime_UTC` → ISO 8601
   - `Gamelength` "MM:SS" → `gamelength_seconds` (int)
   - Tous les champs numériques → `int | None`

> **Note** : `--tournaments-date` est nécessaire si Tournaments et ScoreboardGames ont des dates d'ingestion différentes.

```bash
uv run python -m pipeline.silver_transforms.lfl_matches \
  --date 2026-06-07 \
  --tournaments-date 2026-06-04
```

---

### `lfl_player_stats` ✅ — `pipeline/silver_transforms/lfl_player_stats.py`

**Sources Bronze** : `Tournaments` (filtre LFL), `ScoreboardPlayers`

**État** : **30 530 lignes** — complet ✅ (`silver/leaguepedia/lfl_player_stats/2026-06-05.json`)

**Logique** :
1. Charge `Tournaments` Bronze → extrait les 71 OverviewPages LFL
2. Filtre `ScoreboardPlayers` Bronze par OverviewPage → LFL uniquement
3. Normalise :
   - `PlayerWin` "Yes"/"No" → `bool | None`
   - Stats (`Kills`, `Deaths`, `Gold`, etc.) → `int | None`
   - `DateTime_UTC` → ISO 8601

```bash
uv run python -m pipeline.silver_transforms.lfl_player_stats \
  --date <date-reingestion-ScoreboardPlayers> \
  --tournaments-date 2026-06-04
```

---

## Problèmes rencontrés et résolus

### 1. Bug Cargo API — filtre LFL ignoré silencieusement

**Date** : 7 juin 2026

**Symptôme** : Le Bronze `ScoreboardGames` contenait **130 984 lignes** au lieu des ~3 053 attendus pour la LFL. En inspectant les données, on trouvait `GPL 2014`, `Worlds 2014`, `Demacia Cup 2015`... soit la totalité des compétitions LoL mondiales.

**Investigation** :
- Le code passait `join_on="SG.OverviewPage=T.OverviewPage"` à `mwcleric.cargo_client.query()`
- En inspectant la source de `mwcleric`, le paramètre est stocké dans un dict avec la clé `join_on` (underscore)
- `mwclient.api()` envoie ce dict tel quel en tant que paramètres HTTP
- **Le Cargo API MediaWiki attend le paramètre `join on` (avec un espace), pas `join_on` (underscore)**
- `join_on` est donc un paramètre HTTP inconnu de l'API → silencieusement ignoré
- Sans le JOIN, le WHERE `T.League='La Ligue Française'` référençait un alias `T` inexistant → aussi ignoré
- Résultat : tous les 130 984 ScoreboardGames globaux retournés sans filtrage

**Solution** :
- **Bronze** : suppression du join dans `TABLE_CONFIGS`. Ajout du flag `lfl_filter: True`. Nouvelle fonction `load_lfl_overview_pages()` qui charge le fichier Tournaments Bronze le plus récent depuis GCS et retourne les 71 OverviewPages LFL. Fonction `build_overview_page_filter()` qui construit le WHERE `OverviewPage IN ('page1', 'page2', ...)` — requête simple, pas de join.
- **Silver** : les transforms `lfl_matches.py` et `lfl_player_stats.py` chargent aussi `Tournaments` Bronze pour post-filtrer, ce qui garantit le filtrage même si le Bronze est re-ingéré sans filtre à l'avenir.
- **Résultat** : réingestion ScoreboardGames → 3 053 lignes ✅

**Leçon architecturale** : le filtrage métier (LFL only) appartient à la couche Silver, pas uniquement au Bronze. Le Bronze devrait idéalement contenir les données brutes globales. Le filtre au niveau Bronze est une optimisation de coût (moins de données stockées), mais ne doit jamais être le seul point de filtrage.

---

### 2. ScoreboardPlayers Bronze — données incohérentes

**Date** : 7 juin 2026

**Symptôme** : `ScoreboardPlayers/2026-06-04.json` contenait 26 500 lignes mais **0 ligne LFL** après filtrage par OverviewPage. En inspectant : seulement 60 OverviewPages uniques, toutes non-LFL (`2012 MLG Pro Circuit`, `2014 GPL Spring`, `2021 Season World Championship`...).

**Cause** : même bug que pour ScoreboardGames (join ignoré), mais le WHERE mal formé a produit un résultat partiel cohérent avec une requête sans filtre sur un sous-ensemble de la table (probablement un comportement de fallback de l'API Cargo qui a retourné les données d'une autre façon).

**Solution** : réingestion de `ScoreboardPlayers` avec le nouveau mécanisme `OverviewPage IN (...)`. L'ingestion a été interrompue par un rate limit Leaguepedia lors de la première tentative — réessayer après cooldown de 5 minutes.

---

### 3. Variables globales calculées à l'import

**Date** : session précédente

**Symptôme** : `CURRENT_YEAR`, `EXPECTED_FILE_NAME`, `GCS_DESTINATION_PATH` dans Oracle's Elixir étaient calculés au moment de l'import du module. Si le script tournait à 23h58 le 31 décembre, les valeurs seraient figées pour l'ancienne année même si l'upload se terminait après minuit.

**Solution** : transformé en fonctions `get_current_year()` appelées au moment de l'exécution dans `run_ingestion()`. La valeur de `year` est fixée une seule fois en début de fonction pour éviter un edge case similaire si deux appels `get_current_year()` tombaient de part et d'autre de minuit.

---

### 4. Validation des variables d'environnement

**Date** : session précédente

**Symptôme** : pattern `os.environ.get("KEY") or (_ for _ in ()).throw(KeyError(...))` — un hack illisible qui abusait des expressions génériques pour lever une exception.

**Solution** : migration vers `pydantic-settings` (`BaseSettings`). Les variables requises sont déclarées comme attributs de classe sans valeur par défaut. Pydantic lève une `ValidationError` explicite au démarrage si une variable est manquante. Les variables optionnelles ont une valeur par défaut (`discord_webhook_url: str = ""`).

---

### 5. Bucket GCS avec nom invalide

**Date** : session précédente

**Symptôme** : `google.cloud.storage.exceptions.BadRequest: Invalid bucket name: 'nexus-analytics-bucket@nexus-analytics-prod-498107.iam.gserviceaccount.com'`

**Cause** : le fichier `.env` avait une ligne mal formatée. La valeur de `GCS_BUCKET_NAME` était suivie immédiatement (sans saut de ligne) par la ligne du service account, ce qui a concatené les deux valeurs.

**Solution** : correction du `.env` pour isoler chaque variable sur sa propre ligne.

---

### 6. GCS — Permission 403 `storage.objects.create`

**Date** : session précédente

**Symptôme** : `google.api_core.exceptions.Forbidden: 403 ... does not have storage.objects.create access`

**Cause** : le service account utilisé n'avait pas les droits d'écriture sur le bucket GCS.

**Solution** : attribution du rôle `Storage Object Admin` au service account via la console GCP IAM.

---

### 7. CI — `uv sync --frozen` échoue car `uv.lock` absent

**Date** : session précédente

**Symptôme** : `error: Unable to find lockfile at 'uv.lock', but '--frozen' was provided.`

**Cause** : `uv.lock` était listé dans `.gitignore` et n'était donc pas commité.

**Solution** : retrait de `uv.lock` du `.gitignore`. Le lock file doit être commité pour que le CI puisse reproduire l'environnement de manière déterministe avec `uv sync --frozen`.

---

### 8. `pytest` — `ModuleNotFoundError: No module named 'ingestion'`

**Date** : session précédente

**Symptôme** : les tests unitaires échouaient avec une erreur d'import même si le module existait.

**Cause** : pytest ne connaissait pas la racine du projet comme chemin Python.

**Solution** : ajout dans `pyproject.toml` :
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

---

### 9. GCS auth — `UserWarning: quota project` + erreur 403 `storage.objects.get`

**Date** : lors de l'exécution du module Riot API

**Symptôme** : `UserWarning: Your application has authenticated using end user credentials from Google Cloud SDK without a quota project` suivi d'une erreur 403.

**Solution** :
```bash
gcloud auth application-default set-quota-project nexus-analytics-prod-498107
```

---

### 10. Silver `lfl_player_stats` — données ScoreboardPlayers non filtrées

**Date** : 7 juin 2026

**Symptôme** : `lfl_player_stats` Silver donnait 26 500 lignes (cohérent avec le Bronze ScoreboardPlayers existant) mais après inspection, ces lignes appartenaient à des tournois non-LFL — le filtrage Silver renvoyait **0 ligne LFL**.

**Cause** : le Bronze `ScoreboardPlayers/2026-06-04.json` était lui-même corrompu (voir problème n°2).

**Solution partielle** : réingestion en cours, mais limitée par le rate limit Leaguepedia (voir problème n°13). Bronze `ScoreboardPlayers/2026-06-07.json` contient **16 000 lignes LFL** (53% du total attendu ~30 000). Réingestion complète prévue le lendemain après reset du cooldown.

---

### 13. Rate limit Leaguepedia — ScoreboardPlayers ingestion répétée

**Date** : 7 juin 2026

**Symptôme** : chaque tentative de réingestion de ScoreboardPlayers déclenchait immédiatement un rate limit Leaguepedia (`429 ratelimited`), même après plusieurs minutes de pause et malgré diverses optimisations du code.

**Séquence des tentatives :**

1. **Tentative 1** — WHERE avec 71 OverviewPages, pagination manuelle 500/page, sans sleep entre pages → rate limit à offset=2500 (5 pages) → **2 500 lignes**

2. **Tentative 2** — ajout de `SLEEP_BETWEEN_PAGES=1.5s` → rate limit à offset=16000 (32 pages) → **16 000 lignes**

3. **Tentative 3** — batches de 15 OverviewPages au lieu de 71 → inspection du code mwcleric révèle que sans `ORDER BY`, la pagination Cargo est instable (doublons) : 415 lignes uniques sur ~4000 retournées → identifié comme bug pagination + rate limit persistant

4. **Tentative 4** — `auto_continue=True` (mwcleric gère la pagination avec `limit=max`) + `order_by=DateTime_UTC` → rate limit dès la première requête : le quota global IP/compte est épuisé pour la journée

**Diagnostic final** : le quota journalier de l'API lol.fandom.com était saturé après ~15 tentatives successives sur ScoreboardGames et ScoreboardPlayers. C'est un cooldown global côté serveur, indépendant des optimisations code.

**Leçons :**

- **ORDER BY est obligatoire** pour toute pagination Cargo : sans lui, OFFSET peut retourner des lignes déjà vues ou en sauter d'autres (comportement non déterministe de la DB sans tri explicite)
- **`auto_continue=True` de mwcleric** est le mécanisme correct pour la pagination Leaguepedia : il utilise `limit=max` côté serveur (beaucoup moins de requêtes que notre boucle manuelle de 500/page)
- **Planifier les réingestions** en dehors des heures de développement actif pour ne pas épuiser le quota

**Solution finale retenue** : filtre `WHERE OverviewPage LIKE 'LFL/%'` — une seule condition LIKE qui couvre LFL D1 et Division 2, sans JOIN ni liste IN, sans déclencher de rate limit agressif. La clé `where` du `TABLE_CONFIGS` est transmise à `fetch_all_rows()` via `run_ingestion()`.

**Données de référence correctes** : `ScoreboardPlayers/2026-06-05.json` (30 530 lignes, 71/71 tournois) était déjà complet depuis le 5 juin. L'audit GCS du 6 juillet a révélé que les fichiers des tentatives ultérieures étaient soit corrompus (2026-06-04 : données MLG 2012), soit incomplets (2026-06-07 : 16 000 lignes). Ces fichiers ont été supprimés de GCS.

---

### 14. Champ `DateTime UTC` — espace vs underscore

**Date** : 6 juillet 2026

**Symptôme** : les Silver transforms `lfl_matches` et `lfl_player_stats` produisaient `datetime_utc: null` pour toutes les lignes. Le quality check `lfl_completeness.py` affichait `N/A` dans les colonnes Date min/max.

**Cause** : le Cargo API Leaguepedia retourne le champ sous la clé `"DateTime UTC"` (avec un espace), mais les transforms appelaient `row.get("DateTime_UTC")` (avec underscore). Résultat : la date était silencieusement ignorée.

**Solution** : `row.get("DateTime UTC") or row.get("DateTime_UTC")` — supporte les deux formats pour la robustesse.

---

### 15. Validation exhaustivité des données — démarche qualité

**Date** : 6 juillet 2026

**Contexte** : après plusieurs réingestions, doute légitime sur la complétude des données LFL. Un audit GCS puis une réconciliation multi-sources ont été réalisés.

**Script** : `pipeline/quality_checks/lfl_completeness.py` — 5 méthodes de vérification :
1. Cohérence du format de ligue (round-robin attendu vs obtenu)
2. Réconciliation tournoi par tournoi (71 pages × game count + date min/max)
3. Bornes temporelles par tournoi
4. Intégrité structurelle (0 duplicate game_id, 0 game sans vainqueur, 0 game ≠ 10 joueurs)
5. Croisement Oracle's Elixir par année

**Résultats** :
- Méthodes 2+3+4 : 71/71 ✅, 0 anomalie structurelle ✅
- Méthode 5 — convergence D1 : 2019=0, 2022=0, 2023=1, 2025=5 games d'écart ✅
- Écart résiduel 2021 D1 : OE=240 vs LP=222 (18 games). Oracle's Elixir pourrait comptabiliser certains matchs de qualification ou un format de bracket différent. Non bloquant : toutes les pages du Tournaments Bronze sont présentes avec des counts cohérents avec le format double round-robin.
- LP total > OE total (+350 games) s'explique par la couverture LFL D2 absente d'Oracle's Elixir en 2020 et partielle en 2021/2024.

---

### 11. Parsing SoloqueueIds — markup MediaWiki

**Date** : session précédente

**Symptôme** : le champ `SoloqueueIds` de Leaguepedia contient du markup MediaWiki mixte (`'''EUW:''' name#EUW <br> name2#EUW`) avec trois formats coexistants différents.

**Solution** : fonction `strip_wiki_markup()` (supprime `'''`, convertit `<br>` → `\n`) + `parse_euw_accounts()` qui gère les trois cas :
1. Riot ID avec marqueur région : `EUW: name#tag` → extraire la section EUW uniquement
2. Ancien summoner name avec marqueur : `EUW: AbbedaggÆ` → idem, garder même si pas de `#`
3. Sans marqueur région : tout le champ est EUW

---

### 12. Riot API — PUUID introuvable pour comptes anciens

**Date** : session précédente

**Symptôme** : sur 194 comptes EUW identifiés, 172 étaient des anciens summoner names (sans `#tag`) incompatibles avec l'endpoint `account-v1`.

**Solution** : filtre `is_riot_id()` qui sélectionne uniquement les comptes au format `name#tag` avant les appels API. Résultat : 22 comptes valides, 17 PUUIDs résolus avec succès.

---

## Décision Riot API — stratégie

**Option leaderboard (Master+) abandonnée** — trop coûteux en appels API (pages de leaderboard entières) pour un gain incertain (les joueurs LFL ne sont pas tous Master+).

**Stratégie retenue** : les 194 comptes EUW identifiés dans `lfl_players`, dont 22 au format Riot ID `name#tag`. Les 172 anciens summoner names sont exclus faute d'API compatible.

---

## Prochaines étapes

1. **BigQuery loader** — charger les Silver dans BQ (`pipeline/loaders/bq_loader.py`) :
   - `lfl_matches/2026-06-07.json` → table `raw.lfl_matches`
   - `lfl_player_stats/2026-06-05.json` → table `raw.lfl_player_stats`
   - `lfl_players/2026-06-04.json` → table `raw.lfl_players`
2. **dbt Gold** ✅ — `fact_player_game`, `dim_player`, `dim_team` opérationnels dans BigQuery
3. **FastAPI** ✅ — 3 endpoints (`/players`, `/players/{id}`, `/matches`), auth X-API-Key, OpenAPI `/docs`
4. **Terraform** — BQ dataset, GCS bucket, IAM, lifecycle Bronze 90j (prochaine étape)
5. **Rapport BC02**

---

## Couverture de tests

| Module | Tests | État |
|---|---|---|
| `ingestion/oracle_elixir/ingest.py` | `test_oracle_elixir.py` | ✅ 25 tests |
| `ingestion/leaguepedia/ingest.py` | `test_leaguepedia.py` | ✅ 10 tests |
| `ingestion/riot_api/ingest.py` | `test_riot_api.py` | ✅ 21 tests |
| `pipeline/silver_transforms/lfl_matches.py` | `test_lfl_matches.py` | ✅ 31 tests |
| `pipeline/silver_transforms/lfl_player_stats.py` | `test_lfl_player_stats.py` | ✅ 25 tests |
| `pipeline/silver_transforms/lfl_players.py` | — | ❌ non couvert |
| `api/` (FastAPI endpoints) | `test_api.py` | ✅ 15 tests |

**Total : 129 tests unitaires**

---

## Commandes utiles

```bash
# Ingestion Oracle's Elixir
uv run python -m ingestion.oracle_elixir.ingest --all
uv run python -m ingestion.oracle_elixir.ingest --year 2026

# Ingestion Leaguepedia (toutes tables — Tournaments en premier pour le filtre LFL)
uv run python -m ingestion.leaguepedia.ingest
uv run python -m ingestion.leaguepedia.ingest --table ScoreboardGames
uv run python -m ingestion.leaguepedia.ingest --table ScoreboardPlayers

# Ingestion Riot API
uv run python -m ingestion.riot_api.ingest --silver-date 2026-06-04

# Silver transforms
uv run python -m pipeline.silver_transforms.lfl_players --date 2026-06-04 --players-date 2026-06-05

# lfl_matches : --tournaments-date = date d'ingestion de Tournaments (peut différer de --date)
uv run python -m pipeline.silver_transforms.lfl_matches \
  --date 2026-06-07 \
  --tournaments-date 2026-06-04

# lfl_player_stats : ⚠️ réingérer ScoreboardPlayers d'abord, puis lancer avec la bonne date
uv run python -m pipeline.silver_transforms.lfl_player_stats \
  --date <date-reingestion> \
  --tournaments-date 2026-06-04

# API FastAPI
uv run uvicorn api.main:app --reload
# Docs interactives : http://localhost:8000/docs
# Exemple curl :
# curl -H "X-API-Key: nexus-dev-secret-change-in-prod" http://localhost:8000/players

# Tests
uv run pytest tests/ -v

# Lint + format
uv run ruff check . && uv run ruff format .
```
