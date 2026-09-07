# Bloc de compétences 3 : Élaborer et maintenir un entrepôt de données

# E5 — Mise en situation (C13, C14, C15)

## Contexte de l'évaluation

E5. Mise en situation (C13, C14, C15)

L'évaluation doit se faire dans un contexte de réalisation d'un projet fictif proposé par l'équipe pédagogique ou d'un projet professionnel réalisé en poste. Le projet évalué s'appuie sur le cadre technique de l'organisation et sur le cadre d'exploitation des données.

Le projet a pour but de couvrir toutes les étapes de mise en place d'un entrepôt de données, de sa modélisation à son usage fonctionnel (réponse au besoin d'analyse)

Livrable : rapport professionnel individuel

Évaluation :
- Correction du rapport professionnel
- Soutenance orale individuelle

---

## C13. Modéliser la structure des données d'un entrepôt de données en s'appuyant sur les dimensions* et les faits* afin d'optimiser l'organisation des données pour les requêtes analytiques.

### Critères d'évaluation

- [x] Les données nécessaires aux analyses sont listées.
- [x] La liste des données nécessaires aux analyses est exhaustive.
- [x] Les modélisations logiques et les modélisations physiques sont explicités sans erreur d'interprétation.
- [x] Les modélisations appliquent les pratiques de modélisation d'entrepôt de données : en flocon, en étoile, en constellation.
- [x] L'approche - top-down* ou bottom-up* de création et modélisation de l'entrepôt de données est justifié en fonction des caractéristiques du projet, par exemple : volume de données, fréquences des mise à jour nature(s) des analyses...

> **Preuves** : `docs/MERISE_MCD_MPD.md` — MCD (5 entités : JOUEUR, EQUIPE, PARTIE, MATCH, TOURNOI), MLD (JOUEUR, EQUIPE, MATCH, PERFORMANCE_JOUEUR), MPD star schema avec `fact_player_game`, `fact_draft`, `fact_meta_trend`, `dim_player`, `dim_team`, `dim_champion`, `dim_patch`. Diagramme ASCII complet + table des types BigQuery.
> **Ajout** : `docs/MERISE_MCD_MPD.md` section 4 "Approche bottom-up retenue" — tableau comparatif bottom-up vs top-down avec justification sur 5 critères (volume, périmètre, délai, équipe, besoins utilisateurs).

---

## C14. Créer un entrepôt de données à partir des paramètres du projet, des contraintes techniques et matérielles et de la modélisation de la structure des données afin de soutenir l'analyse de l'activité et l'aide à la décision stratégique de l'organisation.

### Critères d'évaluation

- [x] Les configurations principales appliquées sont explicitées.
- [x] Les accès aux données opérationnelles sources sont correctement configurés.
- [x] Les accès à l'entrepôt de données et/ou datamarts pour les équipes analytiques sont correctement configurés.
- [x] La procédure de test est présentée.
- [x] La procédure de test couvre l'ensemble du spectre technique et fonctionnel de l'entrepôt de données.
- [x] La documentation technique détaille l'architecture technique et couvre la procédure d'installation et de configuration de l'entrepôt de données.
- [x] La documentation respecte une structure permettant d'y rechercher rapidement une information spécifique.
- [ ] La documentation respecte les règles d'accessibilités.
- [x] Un retour d'expérience est fait concernant la pile technique utilisée au regard des besoins d'analyse et du volume de données géré.

> **Preuves** :
> - Configurations : `dbt/dbt_project.yml` (staging=view, dimensions+facts=table, schémas gold/staging), `dbt/profiles.yml`, `terraform/bigquery.tf`.
> - Accès sources : `terraform/iam.tf` — SA `nexus-ingestion` (GCS objectAdmin + BQ dataEditor raw).
> - Accès analytiques : SA `nexus-api` (BQ dataViewer gold uniquement, moindre privilège).
> - Tests : `dbt test` + `dbt/models/*/schema.yml` (not_null, unique, relationships, accepted_values) + 261 tests pytest unitaires.
> - Documentation : `README.md` (architecture + commandes complètes) + `PROGRESS.md` (18 problèmes documentés).
> **Ajouts** :
> - Accessibilité : `docs/ACCESSIBILITE.md` — analyse par livrable + adaptations de poste + plan Phase 2.
> - Retour d'expérience : `PROGRESS.md` section "Retour d'expérience — pile technique" — tableau comparatif BigQuery vs DuckDB vs Snowflake vs Redshift vs PostgreSQL, retex dbt Core, justification divergence Silver DuckDB→Python.

---

## C15. Intégrer les ETL* nécessaires en entrée et en sortie d'un entrepôt de données afin de garantir la qualité et le bon formatage des données en accord avec les modélisations logiques et physiques préalablement établies.

### Critères d'évaluation

- [x] Les formats et le volume des données sont connus et expliqués.
- [x] Les ETL sont alimentés avec les données identifiés.
- [x] Les formats des zones de sortie sont connus et expliqués.
- [x] Les données en sortie respectent le format attendu.
- [x] Les ETL appliquent les traitements nécessaires pour la mise en conformité avec les schémas physiques de données des zones de sortie.
- [x] Les ETL appliquent les traitements de nettoyage des données utiles et nécessaires à la qualité des jeux de données en sortie : unicité des formats et des unités, détection des doublons, etc...,
- [x] Le fonctionnement général et les règles de traitement de chacun des ETL sont clairement explicités, sans ambiguïté.

> **Preuves** :
> - Formats et volumes : PROGRESS.md (3 053 games, 30 530 stats joueurs, 792 joueurs LFL, NDJSON Bronze/Silver, TIMESTAMP/INT64/FLOAT64/BOOL Gold).
> - ETL entrée (Silver → BQ raw) : `pipeline/loaders/bq_loader.py` — `WRITE_TRUNCATE` idempotent, autodetect schema NDJSON.
> - ETL transformation (raw → gold) : `dbt/models/` — 7 modèles (staging CASTs STRING→TIMESTAMP, dimensions agrègent, facts calculent KDA).
> - Nettoyage : `cast_int` (None sur valeur invalide), `parse_datetime` (ISO 8601), `to_snake_case` (uniforme), WRITE_TRUNCATE (pas de doublons), `filter_lfl_rows` (ValueError sur Bronze corrompu).
> - Documentation : docstrings + exemples dans chaque fonction Silver + commentaires SQL dans chaque modèle dbt.
