# Bloc de compétences 4 : Mettre en œuvre une architecture de données évolutive

# E7 — Mise en situation (C18, C19, C20, C21)

## Contexte de l'évaluation

E7. Mise en situation (C18, C19, C20, C21)

L'évaluation doit se faire dans un contexte de réalisation d'un projet fictif proposé par l'équipe pédagogique ou d'un projet professionnel réalisé en poste.

Le projet évalué a pour but de mettre en œuvre une architecture de données technique afin de rendre disponibles les données pour les besoins d'analyse d'une organisation.

Cette architecture de données reprend les éléments abordés dans les blocs de compétences précédents, dans le but de construire une architecture cible évolutive, compatible avec des besoins d'une organisation en croissance.

Livrable : rapport professionnel individuel

Évaluation :
- Correction du rapport professionnel
- Soutenance orale individuelle

---

## C18. Concevoir l'architecture du datalake* en s'appuyant sur les critères de choix des outils et la cohérence avec le système d'information de l'organisation afin de répondre aux besoins de stockage, de performance et d'évolutivité des données.

### Critères d'évaluation

- [ ] Les propositions techniques sont cohérentes avec le cadre d'exploitation et les contraintes de l'organisation.
- [ ] Le schéma d'architecture tient compte des contraintes de volume, de vitesse et/ou de variété des données.
- [ ] Le schéma d'architecture est lisible et utilise un formalisme approprié.
- [ ] Plusieurs catalogues de données sont proposés et comparés au regard des contraintes de l'organisation.
- [ ] L'outil de catalogue de données sélectionné répond aux contraintes d'exploitabilité et de gouvernance des données de l'organisation.

> **Note** : le projet utilise effectivement un datalake GCS (Bronze/Silver/Gold, architecture Medallion) mais cette architecture n'est pas formellement documentée dans le contexte C18. `README.md` contient un diagramme ASCII de l'architecture technique mais sans formalisme (C4, UML ou autre standard reconnu). Aucun catalogue de données n'est proposé ni comparé.
> À produire : schéma d'architecture formel (draw.io / Mermaid) + comparatif d'outils de catalogue (ex: DataHub vs Dataplex vs OpenMetadata).

---

## C19. Installer et configurer un datalake en intégrant les outils de stockage (système de fichier distribué ou objet) et les outils batch et de temps réel adaptés ainsi qu'un catalogue de données afin de disposer du système de stockage adapté aux différents formats de données.

### Critères d'évaluation

- [x] L'ensemble des éléments de documentation nécessaires à la mise en œuvre de la procédure d'installation sont présentés.
- [x] La procédure d'installation se déroule sans erreur dans un environnement de test.
- [x] Le système de stockage est installé et fonctionnel en environnement de test.
- [ ] Les outils batch et temps réel sont fonctionnels et connectés au système de stockage.
- [ ] Le catalogue est connecté au système de stockage.
- [x] La documentation couvre la procédure d'installation et de configuration du système de stockage, des outils batch et de l'outil de catalogue.

> **Preuves cochées** :
> - GCS bucket `nexus-analytics-prod-498107-raw` opérationnel — Bronze, Silver, Gold layers actifs. Lifecycle Terraform configuré (Coldline à 90j, suppression à 365j).
>
> **Ajouts** :
> - `README.md` — 8 étapes d'installation complètes et reproductibles (prérequis, clone+sync, .env, gcloud auth, Terraform, dbt debug, run_pipeline, tests).
> - `docs/ARCHITECTURE.md` — documentation complète du datalake avec schéma Mermaid (vue d'ensemble, vue applicative, vue infrastructure, vue opérationnelle).
>
> **Manquants résiduels** : traitement temps réel absent (Pub/Sub, Dataflow, Kafka) — justifié par l'architecture batch (données hebdomadaires) dans `docs/ARCHITECTURE.md` section 5 ; catalogue de données non implémenté (glossaire dbt + `docs/GLOSSAIRE_METIER.md` en remplacement).

---

## C20. Alimenter le datalake en programmant les scripts d'alimentation du datalake à partir des sources de données identifiées dans le projet afin de disposer des données dans le système de stockage.

### Critères d'évaluation

- [x] Les choix des méthodes d'alimentation sont justifiés et appropriés à chaque source de données.
- [x] Les scripts d'alimentation s'exécutent sans erreur.
- [x] Les données sont importées correctement dans le système de stockage.
- [ ] Les métadonnées sont intégrées dans le catalogue.
- [x] Les procédures de suppression sont conformes aux contraintes d'accès (notamment réglementaires) et aux contraintes opérationnelles.
- [x] Le monitorage permet le suivi des conditions matérielles et applicatives.
- [x] Le monitorage génère une alerte lors d'une rupture de service.
- [x] Le registre des traitements de données personnelles intègre l'ensemble des traitements de données personnelles impliqués dans le projet d'entrepôt de données.
- [x] Les procédures de tri des données personnelles pour la mise en conformité de l'entrepôt de données avec le RGPD sont rédigées.
- [x] Les procédures de tri détaillent les traitements de conformité (automatisés ou non) à appliquer ainsi que leur fréquence d'exécution.

> **Preuves cochées** :
> - Méthodes justifiées : `README.md` + `PROGRESS.md` — Cargo API pour Leaguepedia (mwrogue, bot auth), CSV Drive pour Oracle's Elixir, Riot REST API pour PUUIDs, scraping MediaWiki pour Riot IDs wiki.
> - Scripts fonctionnels : 4 modules `ingestion/` actifs, testés, versionés. Exponential backoff, retry automatique.
> - Import GCS : Bronze NDJSON date-partitionné (`bronze/leaguepedia/{table}/{date}.json`).
> - Suppression : Terraform lifecycle (Coldline 90j → suppression 365j) + RGPD procédure de suppression manuelle en 5 étapes.
> - Monitorage : `ingestion/utils.py` `logger` + Discord webhook sur chaque étape.
> - RGPD fréquences : `docs/RGPD_registre.md` — tableau 7 fréquences d'exécution (lifecycle automatique 90j/365j, audit IAM trimestriel, revue registre annuelle, demandes droits sous 30j, audit BQ mensuel).
>
> **Manquant résiduel** : catalogue de données non implémenté → pas de métadonnées intégrées dans un outil type Dataplex.

---

## C21. Sécuriser les accès au datalake en configurant les droits d'accès et les autorisations en accord avec les règles d'accès aux données de l'organisation afin de garantir un accès maîtrisé et de protéger l'accès aux données personnelles.

### Critères d'évaluation

- [x] Les droits sont appliqués à des groupes et non à des individus dès que possible.
- [x] Les accès fournis répondent aux besoins des groupes concernés.
- [x] Les accès fournis sont limités aux ressources nécessaires aux usages des groupes concernés (notion de moindre privilège).
- [x] Les accès fournis sont conformes à la réglementation (RGPD).
- [x] La documentation couvre les groupes d'accès et les droits associés ainsi que les procédures de mise à jour des règles.

> **Preuves cochées** :
> - SA `nexus-ingestion@` : `roles/storage.objectAdmin` (GCS bucket) + `roles/bigquery.dataEditor` (dataset raw uniquement).
> - SA `nexus-api@` : `roles/bigquery.dataViewer` (datasets gold uniquement) — accès read-only, moindre privilège.
> - Droits sur Service Accounts (groupes fonctionnels), non sur comptes personnels Google.
> - RGPD conforme : moindre privilège + pas de données personnelles accessibles par `nexus-api`.
> - Code source : `terraform/iam.tf`.
> - `docs/RUNBOOK.md` section 7 (tableau groupes/droits) + section 8 (procédures : ajout analyste, révocation, rotation clé SA).
