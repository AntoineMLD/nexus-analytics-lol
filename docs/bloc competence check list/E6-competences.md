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

- [ ] La modélisation des variations intègre pleinement les changements dans les données sources.
- [ ] La modélisation des variations permet d'historiser les changements dans les données sources.
- [ ] Les variations sont intégrées à l'entrepôt de données.
- [ ] L'intégration des variations respecte la modélisation initiale.
- [ ] Les ETL sont mis à jour en fonction des besoins liés aux variations.
- [ ] La documentation est à jour, avec les variations.

> **Note** : le projet applique implicitement SCD Type 1 (WRITE_TRUNCATE sur bq_loader — écrasement sans historisation). Aucun SCD Type 2 ni Type 3 n'est implémenté. Le choix SCD1 est justifié dans `docs/MERISE_MCD_MPD.md` (section 4 "Pourquoi SCD Type 1") mais aucune variation dimensionnelle n'est formellement modélisée ni intégrée.
> À documenter et défendre à l'oral : "SCD Type 1 choisi car les statistiques agrégées remplacent systématiquement les précédentes ; l'historique joueur par partie est préservé dans `fact_player_game` via la colonne `team`."
