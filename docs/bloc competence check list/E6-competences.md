# Bloc de compétences 3 : Élaborer et maintenir un entrepôt de données

# E6 — Étude de cas (C16, C17)

## Contexte de l'évaluation

E6. Etude de cas (C16, C17)

L'évaluation doit se faire dans le cadre d'une situation professionnelle fictive, à partir d'un entrepôt de données en place et d'un besoin d'évolution de celui-ci (technique, évolution dans le schéma des données sources etc.) en environnement de test.

Le projet évalué s'appuie sur le cadre technique de l'organisation et sur le cadre d'exploitation des données.

Lors de cette étude de cas, le candidat ou la candidate rend compte de sa capacité à maintenir un entrepôt de données en conditions opérationnelles, qu'il s'agisse aussi bien d'évolutions techniques que d'évolutions du besoin d'analyse.

Livrable : rapport professionnel individuel

Évaluation :
- Correction du rapport professionnel
- Echanges de questions - réponses individuel

---

## C16. Gérer l'entrepôt de données à l'aide des outils d'administration et de supervision dans le respect du RGPD, afin de garantir les bons accès, l'intégration des évolutions structurelles et son maintien en condition opérationnelle dans le temps.

### Critères d'évaluation

- [x] Une journalisation de l'activité de l'entrepôt de données est mise en place.
- [x] La journalisation catégorise à minima les alertes et les erreurs.
- [x] Un système d'alerte (e-mail, sms, notification...) est mis en place et activé en cas d'erreur notifiée dans les journaux.
- [ ] Les tâches de maintenance sont priorisées selon les objectifs et les exigences de maintenance.
- [ ] Les tâches de maintenance sont assignées entre les membres de l'équipe de maintenance.
- [ ] Les indicateurs de service se base sur les SLA.
- [ ] Le tableau de bord permet de rendre compte de l'ensemble des services.
- [ ] Des tâches planifiées de backup partiel et de backup complet du datawarehouse sont programmées et configurées.
- [ ] Les tâches planifiées produisent les résultats attendus.
- [x] La documentation couvre les principaux cas d'usage de gestion de l'entrepôt : l'intégration de nouvelles sources de données, la création de nouveaux accès à l'entrepôt de données, espace de stockage, datamarts, capacité de calcul...
- [x] La documentation est structurée par cas d'usage et explicite la mise en œuvre des procédures concernées.
- [x] Les nouvelles sources de données sont correctement configurées et ajoutées au processus d'alimentation de l'entrepôt de données.
- [x] Les ETL sont mis correctement à jour en fonction.
- [x] Les nouveaux accès à l'entrepôt de données sont configurés conformément au besoin.
- [x] Le registre des traitements de données personnelles intègre l'ensemble des traitements de données personnelles impliqués dans le projet d'entrepôt de données.
- [x] Les procédures de tri des données personnelles pour la mise en conformité de l'entrepôt de données avec le RGPD sont rédigées.
- [x] Les procédures de tri détaillent les traitements de conformité (automatisés ou non) à appliquer ainsi que leur fréquence d'exécution.

> **Preuves cochées** :
> - Journalisation : `ingestion/utils.py` — `logger.info` / `logger.warning` / `logger.error` sur chaque étape du pipeline.
> - Catégorisation : niveaux INFO (succès), WARNING (retry, skip), ERROR (échec bloquant) + Discord `:white_check_mark:` / `:x:` structuré.
> - Alertes : Discord webhook sur chaque exception (ingestion, silver, bq_loader, orchestration).
> - RGPD : `docs/RGPD_registre.md` — 2 traitements (PUUIDs Riot + Riot IDs wiki), procédure de suppression en 5 étapes.
>
> **Ajouts** :
> - `docs/RUNBOOK.md` — 10 sections structurées par cas d'usage : monitoring, pipeline normal, Oracle's Elixir indispo, quarantaine, nouvelle équipe, nouvelle source, IAM groupes/droits, mise à jour accès, backup, indicateurs santé.
> - `docs/RGPD_registre.md` — tableau des 7 fréquences d'exécution des procédures de tri (lifecycle 90j automatique, audit IAM trimestriel, revue registre annuelle, etc.)
>
> **Manquants résiduels** : SLA formels non définis ; tableau de bord de supervision non implémenté (remplacé par indicateurs Discord + section 10 RUNBOOK).

---

## C17. Implémenter des variations dans les dimensions de l'entrepôt de données en appliquant la méthode adaptée en fonction du type de changement demandé afin d'historiser les évolutions de l'activité de l'organisation et maintenir ainsi une bonne capacité d'analyse.

### Critères d'évaluation

- [x] La modélisation des variations intègre pleinement les changements dans les données sources.
- [x] La modélisation des variations permet d'historiser les changements dans les données sources.
- [x] Les variations sont intégrées à l'entrepôt de données.
- [x] L'intégration des variations respecte la modélisation initiale.
- [x] Les ETL sont mis à jour en fonction des besoins liés aux variations.
- [x] La documentation est à jour, avec les variations.

> **Implémentation SCD Type 2 — historisation des changements d'équipe joueur** :
>
> **Modèle source** : `dbt/models/dimensions/dim_player_current_team.sql`
> - Une ligne par joueur LFL (player_id unique).
> - Expose : `current_team`, `last_game_date`, `total_games_in_team`, `all_teams_played`.
> - Calcule l'équipe la plus récente via `ROW_NUMBER() OVER (PARTITION BY player_link ORDER BY MAX(datetime_utc) DESC)`.
>
> **Snapshot SCD2** : `dbt/snapshots/snap_player_team.sql`
> - Stratégie `check` sur `current_team` : détecte chaque changement d'équipe.
> - À chaque `dbt snapshot`, si un joueur change d'équipe :
>   - L'ancienne ligne reçoit `dbt_valid_to = NOW()` (fermée).
>   - Une nouvelle ligne est insérée avec `dbt_valid_to = NULL` (active).
> - Colonnes dbt ajoutées : `dbt_scd_id`, `dbt_updated_at`, `dbt_valid_from`, `dbt_valid_to`.
>
> **Cas d'usage** : "Dans quelle équipe jouait Caliste au 1er mars 2025 ?"
> ```sql
> SELECT player_name, current_team, dbt_valid_from, dbt_valid_to
> FROM gold_gold.snap_player_team
> WHERE player_id = 'Player:Caliste'
>   AND dbt_valid_from <= '2025-03-01'
>   AND (dbt_valid_to > '2025-03-01' OR dbt_valid_to IS NULL)
> ```
>
> **Cohérence avec le schéma** : SCD1 conservé pour les dimensions agrégées (`dim_player`, `dim_champion`) — les stats de carrière s'écrasent à chaque run. SCD2 appliqué uniquement sur la dimension qui varie de manière significative (affiliation équipe), conformément à la règle "appliquer la méthode adaptée en fonction du type de changement".
>
> **Fréquence recommandée** : `dbt snapshot` hebdomadaire, après `dbt run`.
>
> **Fichiers** : `dbt/snapshots/snap_player_team.sql`, `dbt/models/dimensions/dim_player_current_team.sql`, `dbt/models/dimensions/schema.yml`, `dbt/dbt_project.yml`.
