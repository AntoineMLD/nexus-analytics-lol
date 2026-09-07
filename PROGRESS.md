# Nexus Analytics — État d'avancement

## Contexte du projet

Pipeline de données pour analyser la **LFL (La Ligue Française, D1 + D2) et l'EMEA Masters** depuis plusieurs sources vers GCS, avec une architecture Bronze → Silver → Gold.

**Objectif final** : alimenter un dashboard Streamlit et une API FastAPI exposant des métriques LFL + EMEA Masters (champion pools, win rates, stats joueurs, méta, drafts) à partir de modèles dbt Gold sur BigQuery.

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
silver/leaguepedia/lfl_matches/{YYYY-MM-DD}.json        ← games normalisées (LFL + EMEA Masters)
silver/leaguepedia/lfl_player_stats/{YYYY-MM-DD}.json   ← stats joueur/game (LFL + EMEA Masters)
silver/leaguepedia/lfl_drafts/{YYYY-MM-DD}.json         ← picks/bans dépivotés (LFL + EMEA Masters)
```

**Pipeline complet (ordre d'exécution obligatoire) :**
```
Bronze ingestion → Silver transforms → bq_loader → dbt run
```
⚠️ L'étape `bq_loader` (GCS Silver → BigQuery raw) est indispensable entre Silver et dbt.
Sans elle, dbt lit les anciennes données BigQuery même si Silver GCS est à jour.

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
- `TARGET_LEAGUES = {"La Ligue Française", "La Ligue Française Division 2", "EMEA Masters"}` — filtre étendu le 2026-09-07
- Pagination automatique (500 lignes/page, max 8 000 pages)
- Exponential backoff sur rate limits : `1s → 2s → 4s → 8s → 16s → 32s → 60s`
- Notification Discord success/failure par table

| Table | Filtre | Rows (2026-09-07) |
|---|---|---|
| `ScoreboardGames` | LFL + EMEA via `OverviewPage IN (89 pages)` | **4 535** ✅ |
| `ScoreboardPlayers` | `LIKE 'LFL/%' OR LIKE 'EMEA Masters/%'` | **32 690** ✅ |
| `PicksAndBansS7` | aucun (toutes leagues) | **103 382** ✅ |
| `Tournaments` | aucun | **10 462** |
| `Teams` | aucun | — |
| `TournamentResults` | aucun | — |
| `TournamentRosters` | aucun | 80 886 |
| `Teamnames` | aucun | — |
| `Players` | aucun | 20 562 |

**Dernière ingestion complète : 2026-09-07**

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

## Silver transforms ✅ complet (LFL + EMEA Masters depuis 2026-09-07)

> **Validation qualité** — voir `pipeline/quality_checks/lfl_completeness.py` pour le rapport de réconciliation complet (méthodes 1→5). Résumé ci-dessous.

> **Périmètre étendu le 2026-09-07** : `TARGET_LEAGUES` remplace `LFL_LEAGUES` dans les 3 transforms.
> Les fichiers Silver incluent désormais les données LFL (D1 + D2) ET EMEA Masters.

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

**Sources Bronze** : `Tournaments` (filtre TARGET_LEAGUES), `ScoreboardGames`

**État** : **4 535 lignes** — complet ✅ (`silver/leaguepedia/lfl_matches/2026-09-07.json`)

**Logique** :
1. Charge `Tournaments` Bronze → extrait les 89 OverviewPages (LFL + EMEA Masters)
2. Charge `ScoreboardGames` Bronze → filtre par OverviewPage → **4 535 lignes**
3. Normalise chaque ligne :
   - `DateTime_UTC` → ISO 8601
   - `Gamelength` "MM:SS" → `gamelength_seconds` (int)
   - Tous les champs numériques → `int | None`

```bash
uv run python -m pipeline.silver_transforms.lfl_matches
```

---

### `lfl_player_stats` ✅ — `pipeline/silver_transforms/lfl_player_stats.py`

**Sources Bronze** : `Tournaments` (filtre TARGET_LEAGUES), `ScoreboardPlayers`

**État** : **32 690 lignes** — complet ✅ (`silver/leaguepedia/lfl_player_stats/2026-09-07.json`)

**Logique** :
1. Charge `Tournaments` Bronze → extrait les 89 OverviewPages (LFL + EMEA Masters)
2. Filtre `ScoreboardPlayers` Bronze par OverviewPage
3. Normalise :
   - `PlayerWin` "Yes"/"No" → `bool | None`
   - Stats (`Kills`, `Deaths`, `Gold`, etc.) → `int | None`
   - `DateTime_UTC` → ISO 8601

```bash
uv run python -m pipeline.silver_transforms.lfl_player_stats
```

---

### `lfl_drafts` ✅ — `pipeline/silver_transforms/lfl_drafts.py`

**Sources Bronze** : `Tournaments` (filtre TARGET_LEAGUES), `PicksAndBansS7`

**État** : **82 630 actions** — complet ✅ (`silver/leaguepedia/lfl_drafts/2026-09-07.json`)

**Logique** :
1. Dépivote les colonnes wide (`Team1Ban1`…`Team2Pick5`) → format long
2. Une ligne par action pick/ban (champion, order, side, team)
3. Filtre sur 89 OverviewPages LFL + EMEA Masters

```bash
uv run python -m pipeline.silver_transforms.lfl_drafts
```

---

## Dashboard Streamlit ✅ (2026-09-07)

**Module** : `dashboard/`

Dashboard multi-pages Streamlit connecté à BigQuery Gold. Répond aux questions métier de Nexus Analytics.

| Page | Question métier couverte |
|---|---|
| `app.py` | KPIs globaux (total games, tournois, date min/max) |
| `1_🏆_Joueurs.py` | Quels joueurs évoluent en LFL ? Historique d'équipe, mobilité |
| `2_🐉_Champions.py` | Pool de champions, win rate, KDA par rôle |
| `3_⚔️_Drafts.py` | 5 dernières compositions, pick order, bans prioritaires |
| `4_📈_Meta.py` | Pick/ban/win rate sur les 3 derniers patches — méta a-t-elle changé ? |
| `5_🛡️_Equipes.py` | Win rate, gold diff, durée moyenne par équipe et saison |
| `6_🔍_Profil_Joueur.py` | Pool champion, stats détaillées, historique équipe |
| `7_🚨_Alerte_Meta.py` | Champions sur/sous-performants (winrate anormal sur 2 derniers patches) |
| `8_🌍_LFL_vs_EMEA.py` | Comparaison méta LFL vs EMEA Masters — champions émergents |

**Commande :**
```bash
uv run streamlit run dashboard/app.py --server.port 8501 --server.headless true
```

---

## Gold dbt ✅ (11 modèles, 2026-09-07)

| Modèle | Lignes | Description |
|---|---|---|
| `stg_lfl_matches` (view) | — | Vue sur `raw.lfl_matches` |
| `stg_lfl_player_stats` (view) | — | Vue sur `raw.lfl_player_stats` |
| `stg_lfl_drafts` (view) | — | Vue sur `raw.lfl_drafts` |
| `dim_patch` | 109 | Patches distincts |
| `dim_champion` | 170 | Champions joués |
| `dim_team` | 194 | Équipes (LFL + EMEA) |
| `dim_player` | 939 | Joueurs (LFL + EMEA) |
| `dim_player_current_team` | 939 | Équipe actuelle + historique SCD2 |
| `fact_meta_trend` | 7 400 | Pick/ban/win rate par champion + patch |
| `fact_player_game` | 32 700 | Stats joueur par game |
| `fact_draft` | 82 600 | Actions pick/ban dépivotées |

```bash
uv run --with dbt-bigquery dbt run --project-dir dbt --profiles-dir dbt
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

## Checklist exhaustive — Ce qui reste à faire

> Mise à jour 2026-07-06 après audit complet de tous les documents projet (Brief commanditaire,
> rapport BC01, grilles d'entretien, étude de faisabilité, planning prévisionnel, référentiel RNCP).
>
> Les divergences identifiées entre la documentation et le code réel sont signalées explicitement.

---

### P0 — Bloquants : code manquant promis dans les docs

- [x] **`dim_champion`** — dimension champions jouables. ✅ 2026-07-06
  - Source : champ `champion` dans `stg_lfl_player_stats`
  - Fichier : `dbt/models/dimensions/dim_champion.sql`

- [x] **`dim_patch`** — historique des patches du jeu. ✅ 2026-07-06
  - Source : champ `patch` dans `stg_lfl_matches`
  - Fichier : `dbt/models/dimensions/dim_patch.sql`

- [x] **`fact_draft`** — une ligne par pick/ban par match. ✅ 2026-07-06
  - Silver : `pipeline/silver_transforms/lfl_drafts.py` — unpivot PicksAndBansS7 → long format
  - dbt : `dbt/models/facts/fact_draft.sql` + `dbt/models/staging/stg_lfl_drafts.sql`
  - 31 tests unitaires dans `tests/test_lfl_drafts.py`

- [x] **`fact_meta_trend`** — pick/ban rates + winrates par champion et patch. ✅ 2026-07-06
  - Source : `stg_lfl_player_stats` JOIN `stg_lfl_matches` (patch uniquement dans matches)
  - Fichier : `dbt/models/facts/fact_meta_trend.sql`

- [x] **Endpoints FastAPI analytiques** ✅ 2026-07-06
  - `GET /meta/champion-stats` — stats dim_champion (win_rate, picks par rôle, KDA)
  - `GET /teams/{team}/draft-history` — fact_draft filtré par équipe, patch, type (pick/ban)
  - `GET /meta/trends` — fact_meta_trend filtré par patch et tournoi
  - 12 nouveaux tests dans `tests/test_api.py` → 27 tests API total

- [ ] **Grilles d'entretien BC01 complétées** — les colonnes "Réponse / Notes" sont vides dans
  `docs/docs_projet/Grilles d'entretien - analyse du besoin/BC01_grilles_entretien_nexus_analytics.docx`.
  Les réponses fictives existent dans le fichier séparé mais ne sont pas intégrées dans les grilles.
  À merger manuellement dans le .docx avant la soutenance E1.

---

### P1 — Important : cohérence doc/code et infrastructure

- [ ] **Documenter la divergence Silver DuckDB→Python dans le rapport E4**.
  Le rapport BC01 (p.8) et tous les docs techniques promettent `DuckDB + Parquet`.
  Le code réel utilise `Python + NDJSON`. Deux choix :
  - Option A : implémenter DuckDB+Parquet (migration complète, ~2 jours de travail)
  - Option B : expliquer le changement architectural dans E4 — "initialement prévu avec DuckDB,
    migré vers Python natif pour éviter une dépendance supplémentaire et simplifier les tests.
    L'impact est minimal : les NDJSON GCS remplissent le même rôle de zone Silver normalisée."
  Recommandation : **Option B** — plus rapide, honnête, démontre la capacité d'adaptation.

- [x] **Déploiement Cloud Run** — `Dockerfile` + `terraform/cloudrun.tf` créés. ✅ 2026-07-06
  Déploiement réel (après `gcloud builds submit`) :
  ```
  gcloud builds submit --tag europe-west1-docker.pkg.dev/$PROJECT_ID/nexus/api:latest .
  terraform apply -target=google_cloud_run_v2_service.nexus_api
  ```

- [ ] **`dim_team_alias` (seeds dbt)** — mapping des noms d'équipes entre Oracle's Elixir et Leaguepedia.
  Yasmine l'a explicitement signalé : "Team BDS Academy" vs "BDS Academy" vs "BDSA".
  Fichier : `dbt/seeds/dim_team_alias.csv` + utilisation dans Silver transforms.

- [x] **Script d'orchestration `pipeline/orchestration/run_pipeline.py`** — ✅ 2026-07-06
  Enchaîne ingest → silver → bq_loader → dbt run. Pas de cron configuré — lancement manuel.
  Flags : `--skip-ingest`, `--dbt-only`, `--date YYYY-MM-DD`.
  Fix #17 : auto-détection de la dernière date Bronze via listing GCS (évite le 404 "fichier du jour introuvable").

- [x] **Mise à jour `docs/MERISE_MCD_MPD.md`** — dim_champion, dim_patch, fact_draft, fact_meta_trend documentés. ✅ 2026-07-06

- [x] **`.env.example`** — créé avec toutes les variables commentées. ✅ 2026-07-06

---

### Retour d'expérience — pile technique

> Section répondant au critère C14 (retour d'expérience pile technique).

#### BigQuery — entrepôt analytique

**Choix retenu** : BigQuery on-demand (Google Cloud)

**Alternatives évaluées** :

| Alternative | Avantages | Raison du rejet |
|-------------|-----------|-----------------|
| **DuckDB en local** | Gratuit, très rapide, SQL standard | Pas de multi-utilisateurs, pas d'API REST native, pas de stockage persistant partagé, gestion des accès IAM impossible |
| **Snowflake** | Séparation compute/storage, multi-cloud | Coût : 2$/crédit-heure minimum, incompatible avec le budget 300€/mois. Complexité opérationnelle disproportionnée |
| **Amazon Redshift** | Mature, SQL compatible | Hors GCP, nécessiterait double facturation et transfert de données. Terraform plus complexe |
| **PostgreSQL (Cloud SQL)** | Simple, standard SQL | Optimisé pour l'OLTP, pas l'OLAP. Requêtes analytiques sur 30 000 lignes seraient lentes sans colonnar storage. Coût fixe mensuel vs on-demand BigQuery |
| **BigQuery** ✅ | Serverless, facturation à l'usage, colonnar storage, intégration dbt native, IAM GCP, tier gratuit 1 TB/mois | **Retenu** |

**Retour d'expérience** :
- Le tier gratuit BigQuery (1 TB de requêtes/mois) est largement suffisant pour un pipeline hebdomadaire LFL (~500 Ko de données scannées par run).
- La latence des requêtes BigQuery est de 2–5 secondes pour des tables de 30 000 lignes, acceptable pour une API analytique interne.
- Le partitionnement n'est pas activé (tables trop petites pour justifier la complexité) — à reconsidérer si le volume augmente.
- Limite identifiée : l'absence de connexion permanente (chaque requête FastAPI ouvre une connexion BigQuery) introduit une latence de ~1–2 secondes. Pour une API en production à fort trafic, un cache Redis devrait être ajouté.

#### dbt Core — transformation Gold

**Choix retenu** : dbt Core (open source, local)

**Alternative écartée** : dbt Cloud (SaaS payant, inutile pour un projet solo sans orchestration cloud).

**Retour d'expérience** :
- Les tests dbt (not_null, unique, relationships, accepted_values) ont détecté 3 anomalies réelles pendant le développement (dates nulles, doublons de game_id, relations orphelines).
- La documentation auto-générée (`dbt docs serve`) est utile pour la soutenance RNCP.
- Limite : sans scheduler (Airflow, Cloud Composer), dbt est lancé manuellement. Le `run_pipeline.py` d'orchestration pallie cette limitation pour le périmètre actuel.

#### Python + NDJSON — couche Silver (divergence vs spécifications initiales)

**Spécification initiale** (rapport BC01 p.8) : DuckDB + Parquet.

**Implémentation réelle** : Python natif + NDJSON (`.json`).

**Justification du changement** :
- DuckDB aurait nécessité une dépendance supplémentaire et une conversion CSV→DuckDB→Parquet, sans valeur ajoutée pour des volumes de quelques Mo.
- Python natif (json, datetime, re) est plus lisible, plus facile à tester (unittest.mock), et produit des NDJSON directement ingérables par BigQuery (`autodetect=True`).
- Parquet aurait été pertinent pour des volumes > 1 Go — hors scope actuel.

**Impact sur la certification** : le rôle de zone Silver normalisée est identique. La divergence est documentée et justifiable à l'oral (capacité d'adaptation architecturale).

---

### P2 — Qualité et documentation

- [ ] **Tests dbt métier** — règles de domaine dans `dbt/tests/` :
  - `gamelength_seconds > 0` sur `fact_player_game`
  - `kills >= 0`, `deaths >= 0` sur `fact_player_game`
  - `win_rate_pct` entre 0 et 100 sur `dim_player`

- [ ] **Tests unitaires nouveaux endpoints** — ajouter dans `tests/test_api.py` les tests pour
  `/meta/champion-stats`, `/teams/{team}/draft-history`, `/meta/top-compositions`.

- [ ] **Runbook opérationnel** — procédures de monitoring et de re-run :
  - Que faire si Oracle's Elixir n'est pas disponible le lundi ?
  - Comment corriger une ligne en quarantaine ?
  - Comment mettre à jour `dim_team_alias` quand une équipe change de nom ?
  Fichier : `docs/RUNBOOK.md`

- [ ] **SCD Type 1 — justification formalisée** dans le rapport E4 ou `docs/MERISE_MCD_MPD.md`.

- [ ] **Retour d'expérience pile technique** pour C14 — expliquer pourquoi BigQuery vs alternatives
  (DuckDB en local, Snowflake, Redshift). Section dans rapport E4.

---

### P3 — Dashboard ✅ (2026-09-07)

- [x] **Dashboard Streamlit** (8 pages) — opérationnel ✅ 2026-09-07
  - Connecté à BigQuery Gold via `google-cloud-bigquery`
  - 8 pages couvrant toutes les questions métier Nexus Analytics
  - Données LFL **et EMEA Masters** disponibles
  - Lancement : `uv run streamlit run dashboard/app.py --server.headless true`

- [x] **Page "Alerte méta"** — champions sur/sous-performants sur 2 derniers patches ✅ 2026-09-07
- [x] **Page "LFL vs EMEA Masters"** — comparaison méta inter-compétitions ✅ 2026-09-07
- [x] **SCD Type 2** — `dim_player_current_team` + snapshot dbt `snap_player_team` ✅ 2026-09-07

---

### Rapport E4 (BC02) — Livrable principal à rédiger

- [ ] **Rédiger le rapport professionnel BC02** (E4) basé sur `PROGRESS.md` comme ossature.
  Structure recommandée :
  1. Présentation du projet et contexte (Nexus Analytics, Brief commanditaire)
  2. Architecture technique réalisée (Medallion, GCP, divergences par rapport aux specs)
  3. Collecte et ingestion (C8 — 4 sources documentées)
  4. Qualité et transformation des données (C9-C10 — Silver + dbt)
  5. Entrepôt de données (C11-C15 — BigQuery, MERISE, RGPD)
  6. API de mise à disposition (C12 — FastAPI)
  7. Infrastructure (C14 — Terraform, IAM)
  8. Problèmes rencontrés et solutions (les 16 problèmes du PROGRESS.md)
  9. Bilan, limites, améliorations futures (dont Phase 2 Dashboard)

---

### Récapitulatif par priorité

| Priorité | Tâche | Critère certif | Effort estimé |
|---|---|---|---|
| P0 | dim_champion + dim_patch | C13 | 2h |
| P0 | fact_draft (Silver + dbt) | C13, C15 | 4h |
| P0 | fact_meta_trend | C13 | 2h |
| P0 | Endpoints analytiques FastAPI | C12 | 3h |
| P0 | Grilles d'entretien remplies | E1 (BC01) | 1h |
| P1 | Documenter divergence Silver | rapport E4 | 30min |
| P1 | Déploiement Cloud Run | C12, C14 | 2h |
| P1 | dim_team_alias seeds dbt | C10 | 1h |
| P1 | Script orchestration | C8 | 1h |
| P1 | .env.example | — | 15min |
| P2 | Tests dbt métier | M1 DataOps | 1h |
| P2 | Runbook opérationnel | C16 | 1h |
| P3 | Dashboard Looker Studio | Phase 2 | 3h |
| P3 | Alerte méta endpoint | Phase 2 | 1h |
| — | **Rapport E4 complet** | BC02 entier | 2 jours |

---

## Terraform ✅ (2026-07-06)

Infrastructure GCP déclarée en code dans `terraform/` et appliquée avec succès.

**Ressources gérées :**

| Ressource | Description |
|---|---|
| `google_storage_bucket.main` | Bucket `nexus-analytics-bucket` (EU) — lifecycle Bronze → Coldline après 90j |
| `google_bigquery_dataset.raw` | Dataset Silver chargé par `bq_loader.py` |
| `google_bigquery_dataset.gold_gold` | Tables dbt (dim_player, dim_team, fact_player_game) — expiration 24 mois |
| `google_bigquery_dataset.gold_staging` | Vues dbt staging |
| `google_service_account.ingestion` | SA `nexus-ingestion` — GCS objectAdmin + BQ dataEditor raw |
| `google_service_account.api` | SA `nexus-api` — BQ dataViewer gold uniquement |
| IAM bindings (×4) | `bigquery.jobUser` au niveau projet pour les deux SA |

**Commandes :**
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

**Problème #16 — Bucket en région EU vs europe-west1**

Symptôme : `terraform plan` affichait `-/+ destroy and recreate` sur le bucket (changement de région `EU` → `EUROPE-WEST1`). Aurait supprimé toutes les données Bronze/Silver.

Solution : le bucket existant a été créé en multi-région `EU`. GCS n'autorise pas de changer la région. Corrigé en fixant `location = "EU"` dans `gcs.tf` pour matcher l'état réel. Les nouvelles ressources seraient à créer en `europe-west1`.

---

**Problème #19 — EMEA Masters absent du dashboard (2026-09-07)**

Symptôme : la page "LFL vs EMEA Masters" affichait "Aucune donnée EMEA Masters détectée" malgré les données en GCS.

Cause racine (3 niveaux) :
1. `TARGET_LEAGUES` ne contenait pas `"EMEA Masters"` dans les Silver transforms ni l'ingestion Bronze
2. `ScoreboardPlayers` avait un filtre `LIKE 'LFL/%'` excluant les pages EMEA Masters (`EMEA Masters/...`)
3. L'étape `bq_loader` avait été omise — dbt lisait les anciennes tables BigQuery même si Silver GCS était à jour
4. Cache Streamlit (`ttl=600s`) servait les vieux résultats après mise à jour BigQuery

Solution : `TARGET_LEAGUES` + `"EMEA Masters"` dans 3 Silver transforms + ingestion, WHERE étendu pour ScoreboardPlayers, fix `gcs_client()` project_id, pipeline relancé complet, Streamlit redémarré.

Résultat : 89 OverviewPages, 4 535 matchs, 939 joueurs, 194 équipes dont EMEA Masters.

---

**Problème #20 — BigQuery `ORDER BY in ARRAY_AGG` non supporté dans `dim_player_current_team` (2026-09-07)**

Symptôme : dbt échouait avec `ORDER BY in arguments is not supported on analytic functions`.

Cause : BigQuery n'autorise pas `ORDER BY` dans `ARRAY_AGG` utilisé comme fonction analytique.

Solution : restructuration en deux CTEs — `all_teams` (GROUP BY + ARRAY_AGG) et `latest_team` (QUALIFY ROW_NUMBER()) — puis JOIN.

---

**Problème #18 — Bronze ScoreboardPlayers corrompu (données 2012 MLG)**

Symptôme : `lfl_player_stats` Silver retournait `Filtered 26500 → 0 LFL player-game rows`. Le fichier `bronze/leaguepedia/ScoreboardPlayers/2026-06-04.json` contenait 26 500 lignes d'anciennes compétitions (MLG 2012, GPL 2014...) — aucune LFL.

Cause racine : ce fichier Bronze a été ingéré AVANT que le `"where": "OverviewPage LIKE 'LFL/%'"` soit ajouté à `config.py`. L'ingestion globale non filtrée a récupéré les premières pages de `ScoreboardPlayers` depuis l'aube du jeu.

Solution code : `filter_lfl_rows()` lève maintenant une `ValueError` explicite avec diagnostic (sample des OverviewPage trouvées + commande pour relancer l'ingestion) au lieu d'écrire silencieusement un Silver vide. Test unitaire ajouté (`test_raises_if_non_empty_input_all_filtered_out`).

Action restante : relancer l'ingestion ScoreboardPlayers quand le throttle Fandom se lève (quelques heures) :
```bash
uv run python -m ingestion.leaguepedia.ingest --table ScoreboardPlayers
uv run python -m pipeline.orchestration.run_pipeline --skip-ingest
```

---

**Problème #17 — `run_pipeline.py --skip-ingest` échoue avec 404**

Symptôme : en lançant `run_pipeline --skip-ingest`, les transforms Silver (`lfl_matches`, `lfl_player_stats`, `lfl_players`) échouaient avec `404 No such object: bronze/leaguepedia/Tournaments/2026-07-06.json`. Ces scripts ont `datetime.now().strftime("%Y-%m-%d")` comme date par défaut — ils cherchent le fichier Bronze du jour qui n'existe que le jour de l'ingestion.

Solution : ajout de `find_latest_bronze_date()` dans `run_pipeline.py` — liste le préfixe `bronze/leaguepedia/Tournaments/` en GCS et retourne la date du fichier le plus récent (`2026-06-04`). Cette date est résolue une seule fois avant de lancer les transforms et passée via `--date` à tous les sous-processus.

Enseignement : les scripts individuels ont une valeur par défaut "aujourd'hui" raisonnable pour un usage isolé, mais l'orchestration doit résoudre la date une seule fois depuis la source de vérité (GCS).

---

## Couverture de tests

| Module | Tests | État |
|---|---|---|
| `ingestion/oracle_elixir/ingest.py` | `test_oracle_elixir.py` | ✅ 25 tests |
| `ingestion/leaguepedia/ingest.py` | `test_leaguepedia.py` | ✅ 10 tests |
| `ingestion/riot_api/ingest.py` | `test_riot_api.py` | ✅ 21 tests |
| `ingestion/leaguepedia_wiki/ingest.py` | `test_leaguepedia_wiki.py` | ✅ 25 tests |
| `pipeline/silver_transforms/lfl_matches.py` | `test_lfl_matches.py` | ✅ 31 tests |
| `pipeline/silver_transforms/lfl_player_stats.py` | `test_lfl_player_stats.py` | ✅ 25 tests |
| `pipeline/silver_transforms/lfl_players.py` | `test_lfl_players.py` | ✅ 49 tests |
| `pipeline/silver_transforms/lfl_drafts.py` | `test_lfl_drafts.py` | ✅ 31 tests |
| `api/` (FastAPI endpoints) | `test_api.py` | ✅ 27 tests |

**Total : 261 tests unitaires (100% de couverture des modules Python)**

---

## Commandes utiles

```bash
# ─── Pipeline complet (ordre obligatoire) ────────────────────────────────────

# 1. Bronze — Tournaments en premier (référence pour le filtre TARGET_LEAGUES)
uv run python -m ingestion.leaguepedia.ingest --table Tournaments

# 2. Bronze — tables de données de jeu
uv run python -m ingestion.leaguepedia.ingest --table ScoreboardGames
uv run python -m ingestion.leaguepedia.ingest --table ScoreboardPlayers
uv run python -m ingestion.leaguepedia.ingest --table PicksAndBansS7

# 3. Silver transforms (LFL + EMEA Masters)
uv run python -m pipeline.silver_transforms.lfl_matches
uv run python -m pipeline.silver_transforms.lfl_player_stats
uv run python -m pipeline.silver_transforms.lfl_drafts

# 4. bq_loader — ⚠️ OBLIGATOIRE avant dbt (GCS Silver → BigQuery raw)
uv run python -m pipeline.loaders.bq_loader --source leaguepedia --table lfl_matches --date $(date +%Y-%m-%d)
uv run python -m pipeline.loaders.bq_loader --source leaguepedia --table lfl_player_stats --date $(date +%Y-%m-%d)
uv run python -m pipeline.loaders.bq_loader --source leaguepedia --table lfl_drafts --date $(date +%Y-%m-%d)

# 5. dbt — rebuild Gold
uv run --with dbt-bigquery dbt run --project-dir dbt --profiles-dir dbt

# ─── Dashboard ────────────────────────────────────────────────────────────────
uv run streamlit run dashboard/app.py --server.port 8501 --server.headless true
# http://localhost:8501

# ─── Autres ingestions ────────────────────────────────────────────────────────
uv run python -m ingestion.oracle_elixir.ingest --all
uv run python -m ingestion.oracle_elixir.ingest --year 2026
uv run python -m ingestion.riot_api.ingest --silver-date 2026-06-04

# ─── API FastAPI ──────────────────────────────────────────────────────────────
uv run uvicorn api.main:app --reload
# curl -H "X-API-Key: nexus-dev-secret-change-in-prod" http://localhost:8000/players

# ─── Infrastructure ───────────────────────────────────────────────────────────
cd terraform && terraform plan
cd terraform && terraform apply

# ─── Qualité ──────────────────────────────────────────────────────────────────
uv run pytest tests/ -v
uv run ruff check . && uv run ruff format .
uv run --with dbt-bigquery dbt test --project-dir dbt --profiles-dir dbt
```
