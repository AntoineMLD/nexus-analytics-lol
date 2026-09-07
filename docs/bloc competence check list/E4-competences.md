# Bloc de compétences 2 : Réaliser la collecte, le stockage et la mise à disposition des données d'un projet data

# E4 — Mise en situation (C8, C9, C10, C11, C12)

## Contexte de l'évaluation

E4. Mise en situation (C8, C9, C10, C11, C12)

L'évaluation doit se faire dans un contexte de réalisation d'un service numérique réel ou fictif basé sur l'usage de données, à partir du cadrage pour la réalisation d'un service numérique (spécifications fonctionnelles et techniques par exemple).

Le projet évalué a pour but d'optimiser, d'automatiser, de pérenniser et de mettre à disposition les flux de données et les données, utiles et nécessaires à la réalisation du service numérique, par les équipes techniques (par exemple en analyse statistique, en business intelligence, en machine learning ou encore en intelligence artificielle).

Livrable : rapport professionnel individuel

Évaluation :
- Correction du rapport professionnel
- Soutenance orale individuelle

---

## C8. Automatiser l'extraction de données depuis un service web, une page web (scraping), un fichier de données, une base de données et un système big data en programmant le script adapté afin de pérenniser la collecte des données nécessaires au projet.

### Critères d'évaluation

- [ ] La présentation du projet et de son contexte est complète : acteurs, objectifs fonctionnels et techniques, environnements et contraintes techniques, budget, organisation du travail et planification.
- [ ] Les spécifications techniques précisent : les technologies et outils, les services externes, les exigences de programmation (langages), l'accessibilité (disponibilité, accès).
- [ ] Le périmètre des spécifications techniques est complet : il couvre l'ensemble des moyens techniques à mettre en œuvre pour l'extraction et l'agrégation des données en un jeu de données brutes final.
- [x] Le script d'extraction des données est fonctionnel : toutes les données visées sont effectivement récupérées à l'issue de l'exécution du script.
- [x] Le script comprend un point de lancement, l'initialisation des dépendances et des connexions externes, les règles logiques de traitement, la gestion des erreurs et des exceptions, la fin du traitement et la sauvegarde des résultats.
- [x] Le script d'extraction des données est versionné* et accessible depuis un dépôt Git*.
- [x] L'extraction des données est faite depuis un mix entre au moins les sources suivantes : un service web (API REST), un fichier de données, un scraping, une base de données et un système big data.

> **Preuves** :
> - **API REST 1** : Leaguepedia Cargo API (`ingestion/leaguepedia/ingest.py`) → Bronze → Silver (lfl_matches, lfl_player_stats, lfl_drafts, lfl_players) → Gold (11 modèles dbt). Source principale du projet.
> - **API REST 2** : Riot Games API (`ingestion/riot_api/ingest.py`) → Bronze → Silver (`riot_players.py`) → Gold (`dim_player.puuid` via `stg_riot_players`). PUUIDs des joueurs LFL alimentent la dimension joueur.
> - **Fichier CSV** : Oracle's Elixir via Google Drive API (`ingestion/oracle_elixir/ingest.py`) → Bronze → Silver (`oracle_elixir.py` — filtre LFL, extrait golddiffat15/cspm/dpm) → Gold (`fact_oe_player_game` — métriques avancées). Affiché dans le dashboard Profil Joueur.
> - **Scraping** : Leaguepedia wiki (`ingestion/leaguepedia_wiki/ingest.py`) → Bronze → consommé dans Silver `lfl_players.py` (merge avec Cargo API pour enrichir les SoloqueueIds). Source secondaire intégrée.
> - **Système big data** : GCS + BigQuery. GCS = data lake (Bronze + Silver), BigQuery = data warehouse (Gold, 13 modèles dbt, 2013–2026 soit 12+ ans de données). Oracle's Elixir couvre 2014–2026 (13 années).
> - **Base de données** : BigQuery Gold (dataset `gold_gold`) — requêtes SQL analytiques via dbt et API FastAPI.

---

## C9. Développer des requêtes de type SQL* d'extraction des données depuis un système de gestion de base de données et un système big data en appliquant le langage de requête propre au système afin de préparer la collecte des données nécessaires au projet.

### Critères d'évaluation

- [x] Les requêtes de type SQL pour la collecte de données sont fonctionnelles : les données visées sont effectivement extraites suites à l'exécution des requêtes.
- [x] La documentation des requêtes met en lumières choix de sélections filtrages, conditions, jointures, etc., en fonction des objectifs de collecte.
- [x] La documentation explicite les optimisations appliquées aux requêtes.

> **Preuves** : `dbt/models/` (staging, dimensions, facts) — commentaires SQL détaillés sur SAFE_DIVIDE, LEFT vs INNER JOIN, NULLIF(deaths, 0), COUNTIF, UNION DISTINCT.

---

## C10. Développer des règles d'agrégation de données issues de différentes sources en programmant, sous forme de script, la suppression des entrées corrompues et en programmant l'homogénéisation des formats des données afin de préparer le stockage du jeu de données final.

### Critères d'évaluation

- [x] Le script d'agrégation des données est fonctionnel : les données sont effectivement agrégées, nettoyées et normalisées en un seul jeu de données à l'issue de l'exécution du script.
- [x] Le script d'agrégation des données est versionné et accessible depuis un dépôt Git.
- [x] La documentation du script d'agrégation est complète : dépendances, commandes, les enchaînements logiques de l'algorithme, les choix de nettoyage et d'homogénéisation des formats données.

> **Preuves** : `pipeline/silver_transforms/` — `lfl_matches.py`, `lfl_player_stats.py`, `lfl_players.py` (fusion Cargo + wiki Bronze), `lfl_drafts.py`, `oracle_elixir.py` (filtre LFL/LFL D2, colonnes optionnelles gérées via `_safe_float`), `riot_players.py` (déduplication PUUID). Fonctions `cast_int`, `parse_datetime`, `to_snake_case`, `filter_lfl_rows` (lève `ValueError` sur Bronze corrompu), `parse_euw_accounts` (3 formats MediaWiki), `merge_soloqueue_lookups` (fusion deux sources). Docstrings + exemples sur chaque fonction.

---

## C11. Créer une base de données dans le respect du RGPD en élaborant les modèles conceptuels et physique des modèles de données à partir des données préparées et en programmant leur import afin de stocker le jeu de données du projet.

### Critères d'évaluation

- [x] Les modélisations des données respectent la méthode et le formalisme MERISE.
- [x] Le modèle physique des données est fonctionnel : il est intégré avec succès lors de la création de la base de données, sans erreur.
- [x] La base de données est choisie au regard de la modélisation des données et des contraintes du projet.
- [x] La reproduction des procédures d'installation décrites (base de données et API) a pour résultat un système conforme aux objets techniques attendus.
- [x] Le script d'import fourni est fonctionnel : il permet l'insertion des données dans le système mis en place.
- [x] La documentation technique du script d'import est versionné à la racine du même dépôt Git que celui utilisé pour le script d'import.
- [x] Les documentations techniques des script couvrent les parties suivantes : - les dépendances nécessaires pour la réutilisation des scripts (langages, dépendances externes, etc) - les commandes pour l'exécution des scripts.
- [x] Le registre des traitements de données personnelles intègre l'ensemble des traitements de données personnelles impliqués dans la base de données.
- [x] Les procédures de tri des données personnelles pour la mise en conformité de la base de données avec le RGPD sont rédigées.
- [x] Les procédures de tri détaillent les traitements de conformité (automatisés ou non) à appliquer ainsi que leur fréquence d'exécution.

> **Preuves** :
> - Procédure d'installation : `README.md` — 8 étapes reproductibles (clone + uv sync, .env, gcloud auth, Terraform, dbt debug, run_pipeline, test API, pytest).
> - RGPD fréquences : `docs/RGPD_registre.md` — tableau des 7 fréquences d'exécution (ingestion hebdo, lifecycle automatique 90j/365j, audit IAM trimestriel, revue registre annuelle, demandes droits sous 30j, audit BQ mensuel).

---

## C12. Partager le jeu de données en configurant des interfaces logicielles et en créant des interfaces programmables afin de mettre à disposition le jeu de données pour le développement du projet.

### Critères d'évaluation

- [x] La documentation technique de l'API (REST) couvre tous les points de terminaisons (end points*).
- [x] La documentation technique coure les règles d'authentification et/ou d'autorisation de l'API.
- [x] La documentation technique respecte les standards du modèle choisi (par exemple Open API*).
- [x] L'API REST est fonctionnelle pour l'accès aux données du projet : elle restreint par une autorisation (ou authentification) l'accès aux données,
- [x] L'API REST est fonctionnelle pour la mise à disposition : elle permet la récupération de l'ensemble des données nécessaires au projet.

> **Preuves** : `api/main.py` — 6 endpoints (`/health`, `/players`, `/players/{id}`, `/matches`, `/meta/champion-stats`, `/teams/{team}/draft-history`, `/meta/trends`), auth `X-API-Key` (`api/auth.py`), OpenAPI Swagger auto-généré sur `/docs`, requêtes BigQuery paramétrées (`api/database.py`).
