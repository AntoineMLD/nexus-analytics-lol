# Bloc de compétences 1 : Piloter la conduite d'un projet data

# E1 — Étude de cas (C1)

## Contexte de l'évaluation

E1. Etude de cas. (C1)

L'évaluation doit se faire dans le cadre d'une étude de cas réelle ou fictive sur la base de l'expression d'un besoin data, de l'organigramme de l'organisation et des activités métiers associées.

Le but de cette étude de cas est de donner à voir à travers les outils que sont les grilles d'entretien, la démarche générale d'analyse de besoin menée par le candidat

Livrables : les grilles d'entretien

Évaluation : Correction des grilles et Présentation orale individuelle

---

## C1. Analyser l'expression d'un besoin de projet data dans une étude de faisabilité en explorant, à l'aune des enjeux stratégiques de l'organisation, le besoin métier avec les parties prenantes pour valider les orientations et sélectionner les hypothèses techniques du projet avec le ou les commanditaire(s).

### Critères d'évaluation

- [x] Les grilles d'entretiens questionnent les activités métiers impliquées dans le projet data
- [x] Les grilles d'entretiens questionnent la caractérisation des données impliquées, des métadonnées, des accès, des stockages et des traitements appliqués.
- [x] La note de synthèse rend compte du questionnement et de l'analyse du besoin, du périmètre fonctionnel du projet, des moyens disponibles, de la faisabilité et de la gouvernance de la donnée liée au projet.
- [x] La note de synthèse est organisée, par exemple selon le plan suivant :
  1. intro : rappel du contexte, enjeux du projet, reformulation de l'expression de besoin initiale, annonce du plan
  2. objectifs et périmètre fonctionnel du projet
  3. étude d'opportunités :
     - a. synthèse des informations issues des entretiens métier au regard des objectifs du projet : opportunités ? Contraintes ?
     - b. benchmark des solutions et projets existants dans le périmètre fonctionnel visé
  4. étude de la faisabilité : rapport objectifs, qualité, coûts, délais, moyens mobilisables.
  5. conclusions : analyse RICE*
- [x] Les objectifs du projet sont rédigés selon la méthode SMART*.
- [x] Le cadrage projet reprend et complète la note de synthèse : hypothèses et préconisations macro de solutions techniques, évaluation des aménagements à implémenter pour l'accessibilité du projet dans sa réalisation et dans l'utilisation future de ses produits, les actions pour la mise en conformité avec le RGPD.
- [x] L'effort d'accessibilité tout au long du projet est anticipé dans l'avant-projet, concernant :
  - la réalisation du projet : adaptation des postes de travail de l'équipe technique,
  - les utilisateurs finaux : adaptation des interfaces homme-machine des outils et des supports techniques (documentations, communications...).
- [x] L'avant-projet liste les actions techniques et non-techniques à mener tout au long du projet pour assurer la conformité du projet avec le RGPD.

---

### Notes d'évaluation

**Preuves cochées :**
- Grilles : 3 entretiens (DG, Analyste senior, Chargé clients) avec questions sur activités métier (contexte organisationnel, flux de travail, relation client) et sur les données (sources, accès, licences, cartographie en synthèse).
- Note de synthèse : sections "Cartographie des sources de données" (source, contenu, accès, licence), "Besoins fonctionnels retenus", "Hypothèses techniques validées", "Limites et risques" dans `BC01_grilles_entretien`.
- Organisation du plan : le rapport professionnel `BC01_rapport_professionnel_nexus_analytics-2.pdf` suit exactement le plan (sections 1 Intro, 2 Objectifs+Périmètre, 3 Étude d'opportunités avec benchmark 5 solutions, 4 Étude de faisabilité, 5 Conclusions+RICE).
- SMART : section 2.1 avec tableau 4 objectifs (O1–O4) décomposés S/M/A/R/T.
- RGPD : section 4.4 du rapport professionnel détaille minimisation, localisation EU, durée de conservation, moindre privilège, traçabilité BigQuery INFORMATION_SCHEMA.JOBS. Absence AIPD justifiée.

**Ajouts qui ont permis de cocher :**
- `docs/ACCESSIBILITE.md` — évaluation complète des besoins d'accessibilité par livrable (API JSON, Swagger UI, Markdown, Discord), analyse des adaptations de poste, plan d'amélioration Phase 2 (RGAA, contrastes Looker Studio).
