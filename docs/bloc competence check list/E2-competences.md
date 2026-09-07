# Bloc de compétences 1 : Piloter la conduite d'un projet data

# E2 — Mise en situation (C1, C2, C3, C4, C6)

## Contexte de l'évaluation

E2. Mise en situation (C1, C2, C3, C4, C6)

L'évaluation doit se faire dans un contexte de projet data réel ou fictif d'une organisation et des éléments de preuves de la réalisation du projet.

La mise en situation a pour but de confronter le ou la candidat/e à un besoin data rencontré par une organisation à laquelle il ou elle devra répondre dans son intégralité. Selon la situation choisie, cette évaluation pourra intégrer les éléments d'infrastructure technique associés (fusion alors avec E6) ou se limiter à la dimension de pilotage du projet.

Livrable : rapport professionnel individuel

Évaluation :
- Correction du rapport professionnel
- Soutenance orale individuelle

---

## C2. Cartographier les données disponibles en référençant les usages, les sources, les métadonnées et les données, afin de valider les hypothèses techniques du projet data

### Critères d'évaluation

- [x] La topographie des données est complète, respectant la structuration suivante en quatre parties :
  - La sémantique : les métadonnées des données et les objets métier propres à l'organisation dans un glossaire métier.
  - Les modèles de données : la façon dont les données sont modélisées et stockées dans les différents systèmes (structurées, semi structurées ou non structurées).
  - les traitements et les flux de données : les informations importantes sur les méthodes de transformation, de manipulation et de traitement des données à travers les différents SI de l'organisation.
  - la mise à disposition, les accès et les conditions d'utilisation des données.

> **Preuves** :
> - Sémantique/glossaire : `docs/GLOSSAIRE_METIER.md` — 40+ termes définis (champion, patch, méta, KDA, pick rate, OverviewPage, PUUID, Riot ID, Medallion, ETL, SCD, idempotence, etc.)
> - Modèles de données : `docs/ARCHITECTURE.md` section 2 (matrice des flux avec formats) + `docs/MERISE_MCD_MPD.md` section 3 (types BigQuery)
> - Traitements et flux : `docs/ARCHITECTURE.md` sections 2 (matrice des flux) et 4 (vue opérationnelle)
> - Mise à disposition/accès/conditions : `BC01_grilles_entretien` synthèse (cartographie sources), `docs/RGPD_registre.md` (licences CC BY-SA, Riot Developer Policy), `docs/RUNBOOK.md` section 7 (groupes IAM)

---

## C3. Concevoir un cadre technique d'exploitation des données en analysant les contraintes techniques, de moyens et la cartographie des données afin de définir une réponse adaptée aux ressources mobilisables dans le respect du RGPD et d'une démarche éco-responsable.

### Critères d'évaluation

- [x] L'étude technique d'architecture couvre les parties suivantes :
  - L'analyse fonctionnelle : Que fait le système décrit ? Quelles sont les contraintes métiers qui auront un impact sur l'architecture ?
  - Les besoins non-fonctionnels (outils et contraintes techniques)
  - La représentation fonctionnelle
  - La représentation applicative
  - La représentation d'infrastructure
  - La représentation opérationnelle
  - Les décisions d'architecture : documentation des choix techniques effectués
  - Les processus de mise en conformité RGPD (registre des données personnelles, traitements des tris et suppression, etc.)
  - La stratégie d'éco-responsabilité selon le référentiel général d'éco-conception des services numériques du gouvernemen
  - Les risques et les coûts
- [x] Les choix techniques d'architecture prennent en compte et respectent les objectifs du projet data les moyens mobilisables.
- [x] L'accessibilité des livrables du projet est anticipé et des solutions d'adaptation de poste de travail sont proposées quand cela est nécessaire.
- [x] La représentation applicative contient une matrice des flux.
- [x] La matrice des flux permet la qualification des flux de données concernées par le projet.
- [x] Les choix dans l'étude technique d'architecture s'appuient sur les ressources techniques et matériels du SI directement mobilisables pour le projet.
- [x] Le choix des éventuels prestataires techniques intègre le paramètre d'adoption d'une démarche d'éco-responsabilité chez le ou les prestataires.
- [x] Le choix des outils et services techniques concourent au respect de la stratégie d'éco-conception du projet
- [x] L'étude techniques d'architectures définit et illustre les processus nécessaires à implémenter lors de la réalisation du projet pour la conformité avec le RGPD
- [x] Les processus de conformité définis par l'étude technique d'architecture sont conformes au RGPD

> **Preuves** :
> - Analyse fonctionnelle : section 1 (contexte, enjeux) + section 2 (périmètre inclus/exclu) ✅
> - Besoins non-fonctionnels : budget 300€/mois, disponibilité lundi 8h, usage interne non-commercial ✅
> - Représentation fonctionnelle + applicative : section 4.2 matrice des flux (7 flux, source/dest/fréquence/volume/format/déclencheur) ✅
> - Représentation d'infrastructure : description textuelle Bronze/Silver/Gold + Terraform, sans diagramme formel (C4/UML absent)
> - Représentation opérationnelle : planning S1–S14 section 4.6 ✅
> - Décisions d'architecture : section 4.1 justifie chaque choix (DuckDB, BigQuery on-demand, dbt Core, Cloud Run, Terraform) ✅
> - RGPD : section 4.4 (minimisation, localisation EU, durée conservation, moindre privilège, INFORMATION_SCHEMA.JOBS) ✅
> - Éco-responsabilité : section 4.5 (RGESN 2024, serverless, batch vs streaming, Parquet, eu-west1 >90% renouvelable, open source) ✅
> - Risques et coûts : section 4.6 (5 risques avec proba/impact/mitigation, tableau coûts 8€/mois) ✅
> - Prestataire éco : GCP europe-west1 >90% énergie renouvelable explicitement cité (cloud.google.com/sustainability)
> - `docs/ACCESSIBILITE.md` : analyse accessibilité par livrable + adaptations de poste + plan Phase 2. Représentations formelles dans `docs/ARCHITECTURE.md` (Mermaid).

---

## C4. Réaliser une veille technique et réglementaire en sélectionnant des sources et en collectant et traitant les informations collectées afin de formuler des recommandations projet toujours en phase avec l'état de l'art.

### Critères d'évaluation

- [x] La thématique de veille choisie porte sur un outil et/ou une réglementation mobilisée dans la mise en situation.
- [x] Les temps de veille sont planifiés régulièrement (à minima une récurrence d'une heure hebdomadaire).
- [x] Le choix des outils d'agrégation est cohérent avec les sources d'informations visées et le budget disponible (flux RSS, flux réseaux sociaux, agrégation newsletter, etc.).
- [ ] Les synthèses sont communiquées aux parties prenantes dans un format qui respecte les recommandations d'accessibilité (par exemple celles de l'association Valentin Haüy ou d'Atalan - AcceDe).
- [x] Les informations partagées dans la synthèse répondent à la thématique de veille choisie.
- [x] Les sources et flux identifiés répondent aux critères de fiabilité :
- [x] L'auteur de la page est identifié.
- [x] Des informations sur l'auteur sont disponibles et confirment ses compétences, sa notoriété et l'absence d'intérêts personnels.
- [x] L'analyse du contenu est valable (date de publication récente, sources de l'information indiquées, niveau de langue correct).
- [x] La source (site) ou le document est structuré.
- [ ] Les sources (sites) ou documents respectant les normes d'accessibilité sont privilégiés.
- [x] L'information peut être confirmée par d'autres sites de confiance.

> **Preuves** :
> - Thématiques : API Riot (developer.riotgames.com), RGESN 2024, BigQuery pricing, dbt pricing, GRID/Bayes Esports, Oracle's Elixir, SAP/Team Liquid — toutes directement mobilisées dans le projet.
> - Planification : section 4.5 "Veille hebdomadaire sur developer.riotgames.com/blog via Inoreader" + planning S2 "Configuration webhook Discord + Inoreader".
> - Outil d'agrégation : Inoreader Pro 7€/mois (90$/an), cohérent budget et types de sources (flux RSS, blogs techniques).
> - Sources citées avec auteur identifié : SAP (corporate, sap.com), sportsvideo.org, yogonet.com (journalisme esport), Google Cloud (cloud.google.com), leanopstech.com, finout.io.
> - Dates récentes : toutes les sources citées avec date de publication (déc. 2023, sept. 2025, mai 2026, etc.).
> - Confirmation croisée : partenariat GRID cité par sportsvideo.org ET yogonet.com ; faillite Bayes Esports corroborée.
> - **Manquants** : pas de mention de format accessible (Haüy/AcceDe) pour les synthèses de veille ; pas d'indication que les sources choisies respectent les normes d'accessibilité web.

---

## C6. Superviser la réalisation d'un projet data en organisant les méthodes, les outils de travail et la communication entre les parties prenantes, afin d'accompagner les membres de l'équipes dans la réussite du projet

### Critères d'évaluation

- [ ] L'animation des échanges est adaptée à l'information à transmettre : les supports et les modalités d'animation sont adaptés aux besoins de communication.
- [x] Toutes les personnes concernées sont impliquées dans les échanges. Le contenu et le discours sont adaptés au public et au contexte des échanges.
- [ ] Les outils de suivi sont configurés et accessibles à toutes les parties prenantes.
- [ ] Les outils de suivi respectant les normes d'accessibilité (par exemple : RGAA) sont privilégiés.
- [ ] Les rituels sont documentés : règles de participation et d'organisation aux rituels, planification, etc.
- [ ] Les indicateurs de suivi sont mis à jour tout au long du projet, lors des rituels de suivi de l'avancement du projet.
- [ ] Les dépenses sont imputées au budget prévisionnel tout au long du projet.
- [ ] Les commandes communiqués aux prestataires externes couvrent les objectifs, la méthodologies de travail, les outils à utiliser, les livrables et les critères d'acceptance.

> **Preuves cochées** : 3 entretiens avec DG, Analyste, Chargé clients — toutes les parties prenantes identifiées et impliquées ; discours adapté à chaque interlocuteur (stratégique pour DG, opérationnel pour Yasmine, client pour Thomas).
> **Manquants** : C6 évalue la supervision EN COURS de projet (rituels, indicateurs mis à jour, dépenses imputées). Ces éléments ne peuvent pas être démontrés dans un rapport de pré-cadrage — à démontrer lors de la soutenance orale ou avec des artefacts de suivi de projet (tableau kanban, compte-rendus de réunion, etc.).
