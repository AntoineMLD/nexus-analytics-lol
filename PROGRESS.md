# Nexus Analytics — État d'avancement

## Contexte du projet

Pipeline de données pour analyser la **LFL (La Ligue Française, D1 + D2)** depuis Leaguepedia vers GCS, avec une architecture Bronze → Silver → Gold.

---

## Stack technique

- **Python** géré avec `uv`
- **GCS** comme data lake (voir `.env` pour les détails de configuration)
- **Leaguepedia Cargo API** via `mwrogue` (credentials bot dans `.env`)
- **GCP auth** : compte configuré via `gcloud auth application-default login`
- **CI** : GitHub Actions avec `ruff` + `pytest`

---

## Architecture GCS

```
bronze/leaguepedia/{TableName}/{YYYY-MM-DD}.json   ← NDJSON brut Leaguepedia
silver/leaguepedia/lfl_players/{YYYY-MM-DD}.json   ← joueurs LFL + comptes EUW
```

---

## Tables Bronze ingérées (9 tables)

| Table | Filtre | Rows approx. |
|---|---|---|
| `ScoreboardGames` | LFL D1 + D2 uniquement | ~3 053 games |
| `ScoreboardPlayers` | LFL D1 + D2 uniquement | à réingérer (voir problèmes) |
| `PicksAndBansS7` | toutes | — |
| `Tournaments` | toutes | 10 288 |
| `Teams` | toutes | — |
| `TournamentResults` | toutes | — |
| `TournamentRosters` | toutes | 80 886 |
| `Teamnames` | toutes | — |
| `Players` | toutes | 20 562 |

**Dates d'ingestion actuelles :**
- La plupart : `2026-06-04`
- `Players` (avec `SoloqueueIds`) : `2026-06-05`

---

## Silver transforms réalisés

### `lfl_players` — `pipeline/silver_transforms/lfl_players.py`

Extrait les joueurs LFL actifs et leurs comptes EUW soloqueue depuis les bronzes.

**Commande :**
```bash
uv run python -m pipeline.silver_transforms.lfl_players --date 2026-06-04 --players-date 2026-06-05
```

**Résultat actuel :**
- Joueurs LFL uniques (historique) : **792**
- Avec comptes EUW : **194** (24%)
- Joueurs actifs saison 2026 : **172**
- Actifs 2026 avec comptes EUW : **36 (20%)**

---

## Problèmes rencontrés et résolus

### Migration WSL → Linux natif
- Suppression du `.venv`, réinstallation avec `uv sync`
- PATH `uv` manquant → ajout dans `.zshrc` (chemin snap : `/home/scott/snap/code/244/.local/bin`)

### GCP auth
- Erreur 403 `serviceusage.services.use` → `gcloud auth application-default set-quota-project nexus-analytics-prod-498107`

### API Leaguepedia — rate limits
- Implémenté exponential backoff : `base_delay=1s, ×2, max=60s`
- Sleep 2s entre chaque table, 1s entre pages

### Champs Cargo invalides (MWException)
- Certains champs n'existaient pas → récupéré les vrais noms depuis `Special:CargoTables`
- Le champ `Teams` dans `Tournaments` conflictait avec le nom d'une table → supprimé

### SoloqueueIds — parsing Wikitext
- Le champ contient du markup MediaWiki : `'''EUW:''' name#EUW <br> name2#EUW`
- **Fix** : `strip_wiki_markup()` convertit `<br>` → `\n` et supprime `'''`
- Trois formats coexistent :
  1. Riot ID : `KC NEXT ADKING#EUW` (nouveau format avec `#tag`)
  2. Ancien summoner name : `AbbedaggÆ`, `banger5` (sans `#`)
  3. Sans marqueur région : `Acidy`, `Achuu (EUW)` (tout le champ = EUW)
- **Fix** : `parse_euw_accounts()` gère les 3 cas + split par `\n` et `,`

### CI GitHub Actions
- `uv.lock` et `.python-version` exclus du gitignore → maintenant trackés
- Variables d'env manquantes dans le job `test` → ajoutées comme env dummy
- `ruff format` automatiquement appliqué avant commit (pre-commit hook)

---

## En cours — Trouver les comptes EUW des 136 joueurs manquants

### Piste 1 — Wikitext (testée, abandonnée)
Fetch des pages wiki brutes via `mwrogue` → le champ `|ids=` est vide/absent pour ces joueurs. La donnée n'existe pas sur Leaguepedia.

### Piste 2 — Riot API `league-exp-v4` (en cours)
Script : `debug_leaderboard.py`

Fetch tous les joueurs EUW Master+ (~1500) et croise avec les noms LFL 2026.

**Hypothèse** : beaucoup de pros LFL jouent sous leur pseudo comme nom de compte → match par `summonerName.lower()`.

**Non encore exécuté sur le PC fixe.**

```bash
uv run python debug_leaderboard.py
```

### Piste 3 — Riot ID guess `playerName#EUW`
Si la piste 2 est insuffisante, tenter `GET /riot/account/v1/accounts/by-riot-id/{name}/EUW` pour chaque joueur manquant.

### Alternative — Abandonner soloqueue, focus data officielle
`ScoreboardPlayers` donne déjà stats complètes de chaque game LFL officielle (KDA, gold, CS, damage, vision, champion, side). Suffisant pour champion pool analysis, win rates, patch trends, etc. **La soloqueue est un bonus, pas un prérequis.**

---

## Prochaines étapes possibles

1. **Tester `debug_leaderboard.py`** → mesurer taux de match LFL dans Master+
2. **Réingérer `ScoreboardGames`** → le fichier Bronze contient des données 2012 (avant filtre LFL) → à relancer
3. **Gold transforms** sur `ScoreboardGames` + `ScoreboardPlayers` :
   - `fact_match` : stats par match d'équipe
   - `fact_player_game` : stats individuelles par game
   - `dim_player`, `dim_team`, `dim_tournament`
4. **Décider** : enrichissement soloqueue via Riot API ou focus analytics officielle LFL

---

## Commandes utiles

```bash
# Ingestion complète
uv run python -m ingestion.leaguepedia.ingest

# Ingestion table spécifique
uv run python -m ingestion.leaguepedia.ingest --table Players

# Silver transform lfl_players
uv run python -m pipeline.silver_transforms.lfl_players --date 2026-06-04 --players-date 2026-06-05

# Tests
uv run pytest tests/ -v

# Lint + format
uv run ruff check . && uv run ruff format .
```
