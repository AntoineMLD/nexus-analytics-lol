# Bloc de compétences 1 : Piloter la conduite d'un projet data

# E3 — Jeu de rôle "lancement d'un projet data" (C5, C6, C7)

## Contexte de l'évaluation

E3. Jeu de rôle "lancement d'un projet data" (C5, C6, C7)

Le/la candidat(e) est mis en situation de documenter et d'animer l'introduction de la réunion de lancement d'un projet data réel ou fictif.

Le jeu de rôle a pour but de mettre le candidat dans la posture de chef de projet lors d'une étape clé de cette activité. Cette simulation permettra au candidat ou à la candidate de présenter les documents ressources pour la coordination de projet, leurs usages, ainsi que de montrer au jury la mise en œuvre du travail de collaboration et de communication (interne et externe).

Livrables :
Le support de la présentation et les documents associés (par exemple : avant-projet, feuille de route, calendrier, stratégie de communication)

Évaluation :
- correction des livrables
- jeu de rôle. Simulation de l'introduction de la réunion de lancement.

---

## C5. Planifier la réalisation d'un projet data en attribuant les moyens nécessaires et en définissant les étapes de réalisation et les méthodes de suivi du projet afin d'organiser sa mise en œuvre.

### Critères d'évaluation

- [x] La préconisation de composition d'équipe couvre en compétences les besoins nécessaires à la réalisation du projet.
- [x] L'équipe projet est composée selon les compétences nécessaires à la réalisation du projet et prend en compte le budget affecté.
- [x] Les moyens financiers alloués correspondent au budget prévisionnel du projet.
- [x] La feuille de route est découpée en grandes étapes de réalisation du projet.
- [x] Les grandes étapes de la feuille de route respectent les ensembles fonctionnels du projet.
- [x] Le calendrier rend compte :
  des tâches et livrables attendus,
  des dates d'échéance associées,
  de l'attribution des ressources,
  de la pondération des efforts nécessaires à la réalisation des tâches.
  des rituels d'animation du travail collaboratif de l'équipe projet sont également inclus.
- [x] Le suivi du calendrier permet d'atteindre les objectifs du projet en respectant les contraintes.
- [x] L'attribution des ressources est cohérente avec la répartition des acquis et non-acquis de compétences au sein des membres de l'équipe.
- [x] La pondération est réalisée selon une méthode choisie et partagée avec l'équipe (poker planning, méthode de l'unité équivalente, etc.).
- [x] Le paramétrage des outils de suivi est cohérent avec les délais et attributions de missions du planning.
- [x] Les outils de suivi intègrent les indicateurs de suivi.
- [ ] Les éléments de planification sont communiqués à l'équipe dans un format qui respecte les recommandations d'accessibilité (par exemple celles de l'association Valentin Haüy ou d'Atalan - AcceDe).
- [x] L'enchaînement des tâches permet la réalisation de chacune d'entre elles.

> **Preuves cochées** :
> - Équipe : tableau "Moyens humains" (section 4.6 rapport) — DE consultant 100%, Yasmine Karim 20% recette, Marc Delacroix 10% comités. Compétences couvertes.
> - Budget : 8€/mois estimé vs 300€ budget commanditaire (tableau de coûts détaillé par poste, section 4.6).
> - Feuille de route : planning S1–S14 avec jalons clairement nommés (Fondations, Socle CI/CD, Ingestion OE, Ingestion Leaguepedia, Silver, Gold, API, Recette, Corrections, Mise en production).
> - Ensembles fonctionnels : F1 (S3), F2 (S4), F3 (S5–S6), F4 (S7–S9), F5 (S10–S11), recette (S12), corrections (S13), mise en prod (S14) — cohérent avec l'analyse RICE.
> - Pondération : effort en semaines-personne + prioritisation RICE (Reach × Impact × Confidence / Effort).
> - Attribution : DE fait tout le développement, Yasmine fait la recette fonctionnelle, Marc fait les jalons stratégiques.
> - Enchaînement : Terraform S1 → CI/CD S2 → Ingestion S3/S4 → Silver S5–S6 → Gold S7–S9 → API S10–S11 → Recette S12 — dépendances respectées.
>
> **Ajouts** :
> - `docs/PLAN_COMMUNICATION.md` section 3 : rituels documentés (point hebdomadaire asynchrone, point de jalon synchrone S4/S6/S9/S12/S14, alerte blocage, rapport qualité automatique Discord).
> - Outils de suivi : rapport qualité automatique Discord (indicateurs hebdomadaires : lignes Bronze/Silver/Gold, tests dbt, timestamp disponibilité) + `docs/RUNBOOK.md` section 10 (tableau indicateurs de santé pipeline).
>
> **Manquant résiduel** : accessibilité des supports de planification (Haüy/AcceDe format) — les documents Markdown/PDF ne sont pas formellement évalués RGAA/Haüy.

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

> **Note** : C6 évalue la supervision ACTIVE pendant la réalisation. Le rapport professionnel est un document de cadrage pré-projet — il ne peut pas démontrer un suivi en cours. Seule "les parties prenantes sont impliquées" est démontrable à ce stade. À préparer pour la soutenance : présenter les outils et rituels de suivi qui seront utilisés.

---

## C7. Communiquer tout au long de la réalisation du projet data sur les orientations, les réalisations et leurs impacts en élaborant la stratégie et les supports de communication afin d'informer toutes les parties prenantes des évolutions ou des opportunités internes comme externes, portés par le projet

### Critères d'évaluation

- [x] Toutes les étapes de communication du projet sont planifiées : au lancement, à chaque jalon de la feuille de route, pour les démonstrations, à la livraison du projet.
- [ ] Les supports de communication sont accessibles à toutes les parties prenantes.
- [ ] Les supports de communications respectent les préconisations de mise en page sur des critères d'accessibilités (par exemples celles de l'association Valentin Haüy ou de Atalan - AcceDe ).
- [x] Toutes les personnes concernées sont impliquées dans les échanges.
- [x] Le contenu et le discours sont adaptés au public et au contexte des échanges.
- [x] Les communications présentent les orientations choisies et arbitrages menés pour la réalisation du projet.
- [x] Les tâches de production de la documentation utilisateurs sont planifiées et réparties entre les membres de l'équipe.
- [x] Les temps d'accompagnement des utilisateurs finaux sont planifiés.
- [x] Les missions des utilisateurs invités aux temps d'accompagnement sont cohérentes avec la prise en main du livrable visée.
- [x] Le recueil des retours des parties prenantes et leur traitement suit un processus qui est intégré à la stratégie de communication du projet.

> **Preuves cochées** :
> - Parties prenantes impliquées : 3 entretiens (DG, Analyste, Chargé clients) + synthèse des convergences.
> - Contenu adapté : section 3.1 adapte le discours à chaque interlocuteur (risque client pour Marc, traçabilité pour Yasmine, confiance client pour Thomas).
> - Orientations et arbitrages : analyse RICE section 5.1 (justification du périmètre P1 vs Phase 2) + benchmark section 3.2 (pourquoi pas GRID, pas Mobalytics, etc.).
> - Documentation utilisateurs planifiée : S14 "Formation Yasmine à l'utilisation de l'API (documentation Postman)" + S14 "Runbook opérationnel".
> - Accompagnement planifié : S12 "Session de validation avec Yasmine Karim (demi-journée)" + S14 "Formation Yasmine".
> - Missions cohérentes : Yasmine fait la recette fonctionnelle (produit un rapport sans Excel en S12), Marc fait le go/no-go.
>
> **Ajouts** :
> - `docs/PLAN_COMMUNICATION.md` section 2 : tableau "Plan de communication par étape" — 9 étapes planifiées (lancement S1, jalons S4/S6/S9, recette S12, go/no-go S13, mise en production S14, rapports Discord hebdomadaires, bilan final).
> - `docs/PLAN_COMMUNICATION.md` section 5 : processus de recueil des retours (formulaire Yasmine 5 questions, remontées Thomas, validation Marc) + tableau de traitement des retours (bug bloquant 24h, fonctionnalité manquante 1 semaine, Phase 2 backlog).
>
> **Manquant résiduel** : supports de communication non évalués pour l'accessibilité Haüy/AcceDe (Markdown/PDF — évaluation partielle dans `docs/ACCESSIBILITE.md`).
