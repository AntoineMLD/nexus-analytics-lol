# Mapping certification RNCP Data Engineer — Nexus Analytics

> Document généré le 2026-07-06 à partir de :
> - `cm.pdf` : cours "Gestion de projet & ingénierie data" (76 pages, BC01)
> - `referentiel projet/Referentiel Activites Competences et evaluation - RNCP Data Engineer.cleaned.md`
> - Audit complet du code Nexus Analytics (branche `feature/silver-leaguepedia`)

---

## Lecture rapide — tableau de bord

| Bloc | Évaluation | Statut global | Commentaire |
|------|-----------|---------------|-------------|
| **BC01** C1-C7 — Piloter un projet data | E1, E2, E3 | ✅ **Terminé** | Documents produits et livrés |
| **BC02** C8-C12 — Collecte, stockage, mise à disposition | E4 | 🟢 **Solide (~90%)** | 4 sources réelles en Gold (Leaguepedia, OE, Riot, Wiki), FastAPI ✅, dashboard ✅, MERISE ✅ |
| **BC03** C13-C17 — Entrepôt de données | E5, E6 | 🟡 **Partiel (~75%)** | dbt 13 modèles ✅, SCD2 ✅, fact_oe_player_game ✅, dim_player.puuid ✅ |
| **BC04** C18-C21 — Data lake | E7 | 🟡 **Partiel (~65%)** | GCS Medallion ✅, catalogue ✅ `DATA_CATALOG.md`, streaming absent |

---

## Partie 1 — Lecture du `cm.pdf` (BC01) : correspondances avec Nexus Analytics

Le `cm.pdf` est le cours BC01 (gestion de projet). BC01 est déjà validé. Cependant, plusieurs
concepts du cours se retrouvent **dans le code ou la documentation** du projet technique
et peuvent être valorisés devant le jury lors de l'oral BC02.

### M1 — DataOps & Qualité

| Concept du cours | Ce qu'on a dans Nexus Analytics | Statut |
|-----------------|--------------------------------|--------|
| CI/CD data : lint + tests + déploiement | GitHub Actions : `ruff check`, `ruff format`, `pytest tests/` à chaque push | ✅ Présent |
| Tests structurels dbt : `not_null`, `unique`, `relationships`, `accepted_values` | `dbt/models/staging/schema.yml`, `dimensions/schema.yml`, `facts/schema.yml` | ✅ Présent |
| Tests métier (règles domaine) | Absent — pas de test "gamelength_seconds > 0" ou "kills >= 0" dans dbt | ❌ Manquant |
| Observabilité : fraîcheur, volume | Discord notifications à chaque run (✅ partiel) — pas de check de fraîcheur automatique | 🟡 Partiel |
| Observabilité : distribution, schéma, lignée | Absent — pas de Soda, Elementary ni Monte Carlo | ❌ Manquant |
| Data contract formel | Absent — les métadonnées GCS (blob.metadata) sont un proxy très léger | ❌ Manquant |
| Versioning de schéma (Flyway/Liquibase) | Absent — les schémas BQ sont écrasés à chaque load (WRITE_TRUNCATE) | ❌ Manquant (acceptable) |

**À valoriser à l'oral :** "Notre CI/CD vérifie lint + format + 129 tests à chaque commit.
Les tests dbt couvrent not_null, unique, relationships et accepted_values sur les 5 modèles Gold."

### M2 — Analyse du besoin

> BC01 déjà livré. Les documents E1 (grilles entretien), E2 (rapport professionnel), E3
> (lancement) couvrent entièrement ce module.

Ce qui est **aussi visible dans le code** :
- `PROGRESS.md` : journal de 13 problèmes rencontrés/résolus = proxy d'une note de cadrage technique
- `README.md` : cartographie des flux (diagramme ASCII) = proxy d'une cartographie des flux M2

### M3 — Planification

> BC01 déjà livré (E3 : feuille de route, planning).

Absence dans le code : pas de WBS, RICE, story map formels. Acceptable car BC01 couvert.

### M4 — Management

| Concept | Ce qu'on a | Statut |
|---------|-----------|--------|
| ADR (Architecture Decision Records) | `PROGRESS.md` sections "Problème X → Solution Y" = ADR informels | 🟡 Partiel |
| Runbook | Absent — pas de procédure de re-run documentée | ❌ Manquant |
| README comme doc de référence | `README.md` honnête et à jour | ✅ Présent |
| KPIs pipeline | Logs Discord (row_count, statut) = KPIs très basiques | 🟡 Partiel |
| Rapport de sprint | Absent | ❌ Non applicable (solo) |

### M5 — Veille technique

Le dossier `docs/docs_projet/Veille innoreader/` contient une synthèse de veille.
- Critères de fiabilité (auteur identifié, date récente, confirmable) : à vérifier dans ce document
- Outil d'agrégation (Inoreader) : ✅ mentionné

---

## Partie 2 — BC02 : Collecte, stockage, mise à disposition (E4)

BC02 est l'évaluation centrale du projet Nexus Analytics. Livrable : **rapport professionnel E4**.

### C8 — Automatiser l'extraction depuis plusieurs sources

**Exigence clé :** "L'extraction est faite depuis un mix entre au moins : API REST, fichier, scraping, BDD, big data."

| Source requise | Ce qu'on a | Fichier | Statut | Alimente Gold |
|---------------|-----------|---------|--------|---------------|
| API REST (service web) | Leaguepedia Cargo API (mwrogue) | `ingestion/leaguepedia/ingest.py` | ✅ | `fact_player_game`, `fact_meta_trend`, `fact_draft` |
| API REST (service web) | Riot Games API (PUUIDs) | `ingestion/riot_api/ingest.py` | ✅ | `dim_player.puuid` via `stg_riot_players` |
| Fichier de données | Oracle's Elixir CSV (Google Drive) | `ingestion/oracle_elixir/ingest.py` | ✅ | `fact_oe_player_game` (golddiffat15, cspm, dpm) |
| Scraping web | Leaguepedia wiki (SoloqueueIds) | `ingestion/leaguepedia_wiki/ingest.py` | ✅ | `lfl_players` Silver → `dim_player` (merge avec Cargo) |
| Base de données SQL | BigQuery Gold (analytique) | `dbt/models/` | ✅ | Entrepôt analytique — requêtes via API + dashboard |
| Système big data | GCS + BigQuery, 2013–2026 (13 ans, 12+ sources) | — | ✅ | Data lake multi-années |

**Verdict C8 :** 6/6 sources couvertes. Chaque source alimente réellement le Gold analytique — aucune n'est uniquement en Bronze.

**Autres critères C8 vérifiés :**
- ✅ Point de lancement (`if __name__ == "__main__"` + `parse_args()`)
- ✅ Initialisation des connexions (GCS, API clients)
- ✅ Gestion des erreurs et exceptions (retry, Discord, try/except)
- ✅ Sauvegarde des résultats (GCS Bronze NDJSON)
- ✅ Versionné et accessible sur dépôt Git

### C9 — Requêtes SQL d'extraction depuis BDD et big data

**Exigence clé :** requêtes SQL fonctionnelles + documentées, depuis une BDD et/ou big data.

| Élément | Ce qu'on a | Fichier | Statut |
|---------|-----------|---------|--------|
| Requêtes SQL sur BigQuery (staging) | `stg_lfl_matches.sql`, `stg_lfl_player_stats.sql` | `dbt/models/staging/` | ✅ |
| Requêtes SQL analytiques (dimensions, faits) | `dim_team.sql`, `dim_player.sql`, `fact_player_game.sql` | `dbt/models/` | ✅ |
| Documentation des requêtes | Commentaires SQL dans les fichiers + `schema.yml` | `dbt/models/*/schema.yml` | 🟡 Partiel |
| Optimisations explicitées | Absent — pas de commentaires sur les choix de filtre/jointure | ❌ |
| Connexion programmatique BDD source | `bq_loader.py` se connecte à BigQuery via SDK | `pipeline/loaders/bq_loader.py` | ✅ |

**À faire :** ajouter dans les fichiers SQL des commentaires expliquant les choix
(pourquoi LEFT JOIN et pas INNER, pourquoi SAFE_DIVIDE, etc.).

### C10 — Règles d'agrégation, suppression des entrées corrompues, homogénéisation

**Exigence clé :** script d'agrégation fonctionnel, versionné, documenté.

| Élément | Ce qu'on a | Fichier | Statut |
|---------|-----------|---------|--------|
| Parsing / nettoyage | `cast_int`, `parse_datetime`, `parse_gamelength_seconds`, `to_snake_case` | `lfl_matches.py`, `lfl_player_stats.py` | ✅ |
| Suppression entrées corrompues | Retour `None` sur valeurs invalides, pas de suppression de ligne | 🟡 Partiel |
| Homogénéisation formats | datetime → ISO 8601, int fields typés, snake_case uniforme | ✅ |
| Déduplication | Idempotency GCS (WRITE_TRUNCATE sur BQ, écrasement Silver) | ✅ |
| Script versionné Git | ✅ | — | ✅ |
| Documentation du script | Docstrings présentes, exemples dans les fonctions | ✅ |
| Tests du script | 56 tests (lfl_matches + lfl_player_stats), 30 tests (lfl_players) | `tests/unit/` | ✅ |

**Point faible :** les lignes "corrompues" (valeur None) ne sont pas supprimées, elles
sont gardées avec des `None`. Le rapport doit justifier ce choix : "on préfère conserver
les lignes partielles pour traçabilité et les filtrer en aval si besoin."

### C11 — Créer une base de données dans le respect du RGPD, modèles MERISE, import

**Exigence clé :** MCD/MPD MERISE + base de données + registre RGPD + procédures de tri.

| Élément | Ce qu'on a | Fichier | Statut |
|---------|-----------|---------|--------|
| Base de données créée | BigQuery datasets `raw` + `gold` | `pipeline/loaders/bq_loader.py` | ✅ |
| Script d'import fonctionnel | `bq_loader.py` : GCS Silver → BQ | `pipeline/loaders/bq_loader.py` | ✅ |
| Documentation du script | Docstring + usage CLI | ✅ | ✅ |
| Versionné Git | ✅ | — | ✅ |
| **Modèle Conceptuel (MCD) MERISE** | **ABSENT** | — | ❌ **Bloquant** |
| **Modèle Physique (MPD) MERISE** | **ABSENT** | — | ❌ **Bloquant** |
| **Registre des traitements RGPD** | Absent — PUUIDs identifiés dans `.cursorrules` art. 6.1.f mais pas formalisés | ❌ **Bloquant** |
| Procédures de tri données personnelles | Absent | ❌ |

**Note RGPD pour Nexus Analytics :** les PUUIDs Riot sont des pseudonymes (pas de nom
réel). Ils tombent sous le RGPD car ils peuvent ré-identifier une personne avec croisement.
Le registre doit documenter : finalité (analyse statistique), base légale (6.1.f intérêt légitime),
durée de conservation, procédure de suppression sur demande.

### C12 — Partager les données via API REST avec authentification

**Exigence clé :** API REST fonctionnelle, auth, documentation OpenAPI.

| Élément | Ce qu'on a | Fichier | Statut |
|---------|-----------|---------|--------|
| Framework FastAPI | Dépendance présente dans `pyproject.toml` | `api/__init__.py` (vide) | 🔴 Stub vide |
| Endpoints implémentés | **0 endpoint** | — | ❌ **Bloquant** |
| Authentification (X-API-Key ou JWT) | Absent | — | ❌ |
| Documentation OpenAPI auto-générée | Absent | — | ❌ |
| Documentation technique des endpoints | Absent | — | ❌ |

**C12 est le point le plus critique** : rien n'est implémenté. FastAPI est installé mais
le fichier `api/__init__.py` est vide.

---

## Partie 3 — BC03 : Entrepôt de données (E5, E6)

BC03 est couvert partiellement par notre Gold (BigQuery + dbt). Il est évalué séparément
(E5 = mise en situation, E6 = étude de cas maintien).

### C13 — Modéliser la structure de l'entrepôt (dimensions, faits)

| Élément | Ce qu'on a | Statut |
|---------|-----------|--------|
| Tables de faits | `fact_player_game.sql` (1 ligne/joueur/partie) | ✅ |
| Tables de dimensions | `dim_team.sql`, `dim_player.sql` | ✅ |
| Vues staging | `stg_lfl_matches.sql`, `stg_lfl_player_stats.sql` | ✅ |
| Schéma en étoile (star schema) | Oui : fact_player_game ← dim_player, dim_team | ✅ |
| Schéma en flocon / constellation | Non — une seule table de faits pour l'instant | 🟡 |
| Modélisation logique (MLD) documentée | Absent — aucun schéma ERD/MERISE | ❌ |
| Justification top-down vs bottom-up | Absent | ❌ |

### C14 — Créer l'entrepôt de données

| Élément | Ce qu'on a | Statut |
|---------|-----------|--------|
| Entrepôt créé (BigQuery) | Datasets `raw` + `gold` via bq_loader + dbt | ✅ |
| Configuration des accès | Absent — IAM BigQuery non configuré | ❌ |
| Documentation architecture DWH | Absent — README ne détaille pas BigQuery | 🟡 Partiel |
| Procédure d'installation documentée | `dbt/profiles.yml` comme template | 🟡 Partiel |
| Tests de bon fonctionnement | Tests dbt dans `schema.yml` | ✅ |
| Retour d'expérience sur la pile technique | Absent | ❌ |

### C15 — Intégrer les ETL en entrée et sortie

| Élément | Ce qu'on a | Statut |
|---------|-----------|--------|
| ETL en entrée (Silver → BQ raw) | `bq_loader.py` (WRITE_TRUNCATE, NDJSON) | ✅ |
| ETL de transformation (raw → gold) | dbt (5 modèles SQL) | ✅ |
| Formats et volumes connus | Absent — pas de doc sur le volume des tables | ❌ |
| Règles de nettoyage explicitées | `cast_int`, `parse_datetime` documentés dans Silver | ✅ |
| Unicité des formats en sortie | snake_case uniforme, datetime ISO 8601 | ✅ |

### C16 — Gérer l'entrepôt (administration, supervision, RGPD)

| Élément | Ce qu'on a | Statut |
|---------|-----------|--------|
| Journalisation (logs) | Logs Python (ingestion.utils.logger) + Discord | 🟡 Partiel |
| Alertes sur erreur | Discord notifications (`:x:` sur exception) | ✅ |
| Tableau de bord KPIs | Absent | ❌ |
| Backup planifié | Absent | ❌ |
| Registre RGPD DWH | Absent | ❌ |

### C17 — Variations de dimensions (SCD - Slowly Changing Dimensions)

| Élément | Ce qu'on a | Statut |
|---------|-----------|--------|
| SCD Type 1 (écrasement) | WRITE_TRUNCATE sur bq_loader | ✅ |
| SCD Type 2 (historisation) | `dim_player_current_team.sql` + snapshot dbt `snap_player_team` (valid_from/valid_to) | ✅ 2026-09-07 |
| Documentation des choix SCD | `docs/MERISE_MCD_MPD.md` section SCD | ✅ |

---

## Partie 4 — BC04 : Data lake (E7) — analyse rapide

BC04 couvre la collecte massive avec data lake. Notre GCS Bronze + Silver = data lake de fait,
mais non formalisé comme tel.

| Compétence | Ce qu'on a | Statut |
|-----------|-----------|--------|
| C18 — Architecture data lake | GCS Bronze (raw) + Silver (transformed) = data lake Medallion | ✅ Documenté (`docs/ARCHITECTURE.md`) |
| C19 — Intégrer composants (batch, streaming, catalogue) | Batch ✅ / Catalogue ✅ `docs/DATA_CATALOG.md` / Streaming ❌ | 🟡 |
| C20 — Gérer le catalogue et cycle de vie | `docs/DATA_CATALOG.md` (489 lignes) + lifecycle GCS Terraform (Bronze 90j → Coldline) + BQ expiration 24 mois | ✅ 2026-09-07 |
| C21 — Gouvernance : droits, accès | IAM Terraform (SA nexus-ingestion + nexus-api, moindre privilège) | 🟡 Partiel |

> BC04 n'est probablement pas dans le périmètre immédiat de soutenance. À traiter après BC02/BC03.

---

## Résumé des manquants par priorité

> Mise à jour : 2026-09-07 — dashboard ✅, SCD2 ✅, EMEA Masters ✅, bq_loader documenté ✅

### 🔴 Bloquants résolus ✅

| # | Élément | Critère | Statut |
|---|---------|---------|--------|
| 1 | **Module scraping** `ingestion/leaguepedia_wiki/ingest.py` | C8 | ✅ |
| 2 | **FastAPI** endpoints + auth X-API-Key + OpenAPI | C12 | ✅ |
| 3 | **MCD/MPD MERISE** `docs/MERISE_MCD_MPD.md` | C11, C13 | ✅ |
| 4 | **Registre RGPD** `docs/RGPD_registre.md` | C11, C16 | ✅ |

### 🟡 Restants importants

| # | Manque | Critère | Effort estimé |
|---|--------|---------|---------------|
| 5 | **Terraform** lifecycle Bronze → Coldline 90j | C14, C19 | 1h |
| 6 | **Commentaires SQL** dans les modèles dbt (choix de jointure, SAFE_DIVIDE) | C9 | 1h |
| 7 | **Tests métier dbt** : `gamelength_seconds > 0`, `kills >= 0` | M1 DataOps | 2h |
| 8 | **Runbook opérationnel** `docs/RUNBOOK.md` | C16 | 1h |

### ✅ Points forts à valoriser à l'oral

| Point fort | Où le montrer |
|-----------|---------------|
| 263 tests unitaires offline (100% mockés) | `tests/` — lancer `pytest` en live |
| Architecture Medallion LFL + EMEA Masters | README + PROGRESS.md — 20 problèmes documentés |
| Dashboard Streamlit 8 pages connecté à BigQuery | `dashboard/` — démo live |
| SCD Type 2 sur historique équipe joueur | `dbt/models/dimensions/dim_player_current_team.sql` |
| CI/CD : lint + format + tests à chaque commit | `.github/workflows/ci.yml` |
| pydantic-settings : zéro secret commité | `ingestion/utils.py` Settings |
| Bug join_on mwcleric : investigation code source lib | PROGRESS.md problème #1 |
| dbt : 11 modèles + schema.yml tests + star schema | `dbt/models/` |

---

## Plan d'action recommandé

```
Semaine 1 (cette semaine)
  ├── [4h] Scraping module → ingestion/leaguepedia_wiki/ingest.py
  ├── [6h] FastAPI → api/main.py avec 3 endpoints + X-API-Key
  └── [3h] MERISE MCD/MPD → docs/merise/

Semaine 2
  ├── [4h] Terraform main.tf complet (bucket + BQ + IAM + lifecycle)
  ├── [2h] Registre RGPD → docs/rgpd/registre_traitements.md
  └── [2h] Commentaires SQL dbt + tests métier

Semaine 3
  ├── Rapport professionnel E4 (utiliser PROGRESS.md comme base)
  └── Préparation orale : scénario de démonstration live du pipeline
```

---

## Annexe — Fichiers existants pertinents par critère

```
C8  (extraction)     ingestion/oracle_elixir/ingest.py
                     ingestion/leaguepedia/ingest.py
                     ingestion/riot_api/ingest.py
                     [MANQUANT] ingestion/leaguepedia_wiki/ingest.py

C9  (SQL)            dbt/models/staging/stg_lfl_matches.sql
                     dbt/models/staging/stg_lfl_player_stats.sql
                     dbt/models/dimensions/dim_team.sql
                     dbt/models/dimensions/dim_player.sql
                     dbt/models/facts/fact_player_game.sql

C10 (agrégation)     pipeline/silver_transforms/lfl_matches.py
                     pipeline/silver_transforms/lfl_player_stats.py
                     pipeline/silver_transforms/lfl_players.py

C11 (BDD + RGPD)     pipeline/loaders/bq_loader.py
                     [MANQUANT] docs/merise/mcd.md
                     [MANQUANT] docs/rgpd/registre_traitements.md

C12 (API)            [MANQUANT] api/main.py

C13 (modélisation)   dbt/models/dimensions/
                     dbt/models/facts/
                     [MANQUANT] docs/merise/mpd.md

C14 (DWH)            dbt/dbt_project.yml
                     dbt/profiles.yml
                     pipeline/loaders/bq_loader.py

C15 (ETL)            pipeline/loaders/bq_loader.py (Bronze → raw BQ)
                     dbt/models/ (raw → gold)

C16 (gestion DWH)    ingestion/utils.py (Discord alerts)
                     [MANQUANT] terraform/main.tf complet

C17 (SCD)            Défendable en SCD Type 1 par défaut
                     [MANQUANT] justification dans rapport
```
