# Plan de communication et rituels de projet — Nexus Analytics

> Document support pour la réunion de lancement du projet.
> Répond aux critères C5 (planification — rituels) et C7 (communication projet) du référentiel RNCP BC01.
>
> Dernière mise à jour : 2026-07-09

---

## 1. Parties prenantes du projet

| Personne | Rôle | Intérêt dans le projet | Canal de communication |
|----------|------|----------------------|----------------------|
| **Marc Delacroix** | Directeur général — commanditaire | Valider les jalons, arbitrages budgétaires, go/no-go mise en production | Email + Discord |
| **Yasmine Karim** | Analyste senior — utilisatrice principale | Validation fonctionnelle, recette API | Discord + sessions synchrones |
| **Thomas Bourgeois** | Chargé des relations clients | Retours clients, besoins non exprimés | Email |
| **Antoine MLD** | Data Engineer consultant | Réalisation technique complète | — |
| **Jury RNCP** | Évaluateur de la certification | Évaluation des livrables et compétences | Rapport + soutenance orale |

---

## 2. Plan de communication par étape

| Étape du projet | Communication prévue | Destinataires | Format | Délai |
|----------------|---------------------|---------------|--------|-------|
| **Lancement (S1)** | Réunion de lancement — présentation du plan de travail, des jalons, du planning S1–S14 | Marc, Yasmine, Thomas | Visioconférence + support PDF | Début S1 |
| **Jalon Bronze (S4)** | Rapport de statut : "L'ingestion automatisée des 3 sources est opérationnelle" | Marc | Email + Discord | Fin S4 |
| **Jalon Silver (S6)** | Rapport de statut : "Les données LFL sont normalisées et disponibles en Silver" | Marc, Yasmine | Discord | Fin S6 |
| **Jalon Gold / dbt (S9)** | Démonstration technique — présentation du schéma en étoile et des tables Gold | Marc, Yasmine | Visioconférence + dbt docs | Fin S9 |
| **Recette fonctionnelle (S12)** | Session de validation : Yasmine produit un rapport à partir de l'API sans Excel | Yasmine | Session synchrone (demi-journée) | S12 |
| **Go/no-go mise en production (S13)** | Compte-rendu de recette + arbitrage final | Marc | Email + réunion (30 min) | S13 |
| **Mise en production (S14)** | Annonce de mise en production + formation Yasmine | Marc, Yasmine, Thomas | Discord + session formation (1h) | S14 |
| **Suivi hebdomadaire (S1→S14)** | Rapport de qualité automatique pipeline (Discord) | Marc, Yasmine | Discord automatique | Chaque dimanche soir |
| **Bilan final** | Rapport de fin de projet + retour d'expérience | Marc, Thomas | Email + PDF | S14+1 |

---

## 3. Rituels d'animation du projet

### 3.1 Point de statut hebdomadaire (asynchrone)

**Fréquence** : chaque lundi matin (30 minutes d'écriture pour le DE)
**Format** : message structuré dans Discord `#nexus-updates`
**Contenu** :
- Ce qui a été fait cette semaine
- Ce qui est prévu la semaine prochaine
- Blocages éventuels à lever

**Règles** :
- Marc répond dans les 48h si un arbitrage est nécessaire
- Pas de réunion si pas de blocage

### 3.2 Point de jalon (synchrone)

**Fréquence** : à la fin de chaque jalon majeur (S4, S6, S9, S12, S14 — voir section 2)
**Format** : visioconférence ou présentiel — 45 minutes maximum
**Structure type** :
1. (10 min) Démo de ce qui a été livré
2. (15 min) Questions / retours des parties prenantes
3. (15 min) Ajustements de périmètre ou de planning si nécessaire
4. (5 min) Validation du jalon — go/continue ou action corrective

**Règles de participation** :
- Marc Delacroix : présence obligatoire (commanditaire)
- Yasmine Karim : présence requise pour les jalons Silver, Gold, Recette
- Thomas Bourgeois : présence recommandée pour les jalons Recette et mise en production

### 3.3 Alerte blocage (asynchrone, à la demande)

**Déclencheur** : blocage technique non résolu en 24h (ex: rate limit API persistant, accès GCP refusé)
**Format** : message Discord `#nexus-alerts` avec :
- Description du blocage
- Impact sur le planning (décalage estimé en jours)
- Action attendue de Marc (si arbitrage nécessaire) ou information seule

### 3.4 Rapport qualité automatique (asynchrone, hebdomadaire)

**Fréquence** : chaque dimanche soir après run pipeline complet
**Format** : message Discord auto-généré par `run_pipeline.py`
**Contenu** :
```
✅ Pipeline Nexus Analytics — [date]
- ScoreboardGames Bronze : 3053 lignes
- lfl_matches Silver : 3053 lignes
- Gold disponible : ✅ lundi [date] 08:47
- Tests dbt : 47/47 ✅
- Données disponibles : http://localhost:8000/docs
```

---

## 4. Supports de communication

| Support | Format | Destinataire | Disponibilité |
|---------|--------|-------------|--------------|
| Support de lancement (ce document) | Markdown / PDF | Toutes parties prenantes | GitHub + email |
| Rapport professionnel BC01 | PDF | Jury RNCP | Dépôt certification |
| Documentation API (Swagger) | Web (`/docs`) | Yasmine, développeurs | localhost:8000/docs |
| Documentation Postman | Collection JSON | Yasmine | Partagée en S14 |
| Runbook opérationnel | Markdown (docs/RUNBOOK.md) | Data Engineer | GitHub |
| Alertes Discord | Texte | Marc, Yasmine | Discord `#nexus-alerts` |
| Rapports qualité hebdomadaires | Texte automatique | Marc, Yasmine | Discord `#nexus-updates` |

---

## 5. Recueil et traitement des retours des parties prenantes

### Processus de remontée des retours

1. **Yasmine Karim** (utilisatrice) : remonte ses retours pendant la session de recette (S12) via un formulaire de 5 questions (satisfaction, fonctionnalités manquantes, bugs, formation nécessaire, recommandation).
2. **Thomas Bourgeois** (relation clients) : remonte les retours clients non exprimés après chaque livraison d'un rapport aux équipes clientes.
3. **Marc Delacroix** (commanditaire) : valide ou rejette chaque jalon dans les 48h.

### Traitement des retours

| Type de retour | Délai de traitement | Résultat attendu |
|----------------|--------------------|--------------------|
| Bug bloquant (fonctionnalité cassée) | 24h | Correctif livré et mis en production |
| Fonctionnalité manquante Phase 1 | 1 semaine | Ajout au sprint en cours ou déprioritisation documentée |
| Demande Phase 2 | Après mise en production | Ajoutée au backlog Phase 2 (dashboard, alertes méta) |
| Retour positif | — | Documenté dans le rapport final |

### Formulaire de recette (S12)

Questions posées à Yasmine Karim lors de la session de recette :

1. Avez-vous réussi à produire un rapport de préparation de match complet à partir de l'API sans ouvrir Excel ? *(Oui / Non / Partiellement)*
2. Les données de pick/ban rates et winrates correspondent-ils à ce que vous attendiez ? *(Oui / Non / Partiellement — préciser)*
3. Y a-t-il des analyses que vous faisiez manuellement et que l'API ne couvre pas encore ? *(Ouverte)*
4. La documentation Postman est-elle suffisamment claire pour utiliser l'API sans aide ? *(1-5)*
5. Recommanderiez-vous cet outil à un analyste qui rejoint l'équipe ? *(Oui / Non — pourquoi)*
