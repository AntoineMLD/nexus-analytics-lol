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
bronze/oracle_elixir/{year}/{filename}.csv         ← CSV brut Oracle's Elixir
bronze/leaguepedia/{TableName}/{YYYY-MM-DD}.json   ← NDJSON brut Leaguepedia
bronze/riot_api/matches/{YYYY-MM-DD}.ndjson        ← historique ranked joueurs EUW (à venir)
silver/leaguepedia/lfl_players/{YYYY-MM-DD}.json   ← joueurs LFL + comptes EUW
```

---

## Bronze Oracle's Elixir ✅

13 fichiers CSV ingérés (2014–2026) dans `bronze/oracle_elixir/`.

**Commande :**
```bash
uv run python ingestion/oracle_elixir/ingest.py --all
uv run python ingestion/oracle_elixir/ingest.py --year 2026  # réingestion année courante
```

---

## Tables Bronze Leaguepedia (9 tables)

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

## Décision Riot API — 7 juin 2026

**Option leaderboard (Master+) abandonnée** — trop coûteux en appels pour un gain incertain.

**Décision finale** : travailler avec les **194 joueurs EUW** identifiés via `SoloqueueIds`.

**Prochain module** : `ingestion/riot_api/ingest.py`
- Lit le Silver `lfl_players`
- Prend les 194 joueurs avec compte EUW
- `GET /riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}` → récupère les PUUIDs
- `GET /lol/match/v5/matches/by-puuid/{puuid}/ids` → historique ranked
- Stockage Bronze : `bronze/riot_api/matches/{YYYY-MM-DD}.ndjson`

---

## Prochaines étapes

1. **`ingestion/riot_api/ingest.py`** — PUUIDs + historique ranked 194 joueurs EUW
2. **Normalisation Silver** — Oracle's Elixir + Leaguepedia
3. **Terraform** — infrastructure GCP as code
4. **dbt Gold** — `fact_match`, `fact_player_game`, `dim_player`, `dim_team`, `dim_tournament`
5. **FastAPI**
6. **Rapport BC02**

---

## Commandes utiles

```bash
# Ingestion Oracle's Elixir
uv run python ingestion/oracle_elixir/ingest.py --all
uv run python ingestion/oracle_elixir/ingest.py --year 2026

# Ingestion Leaguepedia complète
uv run python -m ingestion.leaguepedia.ingest

# Ingestion Leaguepedia table spécifique
uv run python -m ingestion.leaguepedia.ingest --table Players

# Silver transform lfl_players
uv run python -m pipeline.silver_transforms.lfl_players --date 2026-06-04 --players-date 2026-06-05

# Tests
uv run pytest tests/ -v

# Lint + format
uv run ruff check . && uv run ruff format .
```
