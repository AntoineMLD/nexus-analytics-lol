# Registre des traitements de données personnelles — Nexus Analytics

> Document établi conformément à l'article 30 du Règlement Général sur la Protection
> des Données (RGPD — UE 2016/679).
>
> Ce registre recense l'ensemble des traitements de données à caractère personnel
> mis en œuvre dans le cadre du projet Nexus Analytics.
>
> Responsable du traitement : Antoine MLD
> Date de création : 2026-07-06
> Dernière mise à jour : 2026-09-07

---

## Traitement n°1 — Collecte et stockage des PUUIDs Riot Games

### Identification du traitement

| Champ | Valeur |
|-------|--------|
| **Nom du traitement** | Collecte de PUUIDs et match IDs via Riot API |
| **Module concerné** | `ingestion/riot_api/ingest.py` |
| **Couches concernées** | Bronze (`bronze/riot_api/`), Silver (`silver/leaguepedia/lfl_players/`) |
| **Date de mise en œuvre** | 2026-06-04 |

### Données traitées

| Donnée | Nature | Format | Source |
|--------|--------|--------|--------|
| PUUID | Identifiant technique pseudonymisé | Chaîne UUID (78 caractères) | Riot Games API (`account-v1`) |
| Riot ID (`name#tag`) | Nom de jeu public | Chaîne alphanumérique | Leaguepedia + Riot API |
| Match IDs | Identifiant de partie classée | Chaîne alphanumérique | Riot Games API (`match-v5`) |

### Qualification RGPD

**Les PUUIDs sont-ils des données à caractère personnel ?**

Oui, au sens du RGPD (art. 4.1). Un PUUID est un identifiant unique attribué par Riot Games
à chaque compte joueur. Bien qu'il ne contienne pas directement de nom ou d'email, il permet
de ré-identifier une personne physique par croisement avec d'autres données (profil de compte,
historique de parties, nom d'utilisateur public).

Il s'agit de **données pseudonymisées** (et non anonymisées) : la ré-identification reste
possible via l'API Riot, ce qui maintient le caractère personnel.

### Base légale

**Article 6.1.f — Intérêt légitime** du responsable du traitement.

Justification : les joueurs concernés sont des **professionnels de l'esport** dont les
performances publiques en soloqueue sont accessibles à tous via les plateformes Riot Games
(op.gg, u.gg, league of graphs). Le traitement vise exclusivement l'analyse statistique
de leurs performances dans un contexte professionnel, sans aucune donnée civile (nom réel,
email, adresse, téléphone).

**Intérêt légitime démontré :**
- Finalité légitime : analyse de performances sportives professionnelles
- Nécessité : le PUUID est le seul identifiant permettant de relier un joueur pro à son compte
- Proportionnalité : seules les données strictement nécessaires sont collectées
- Préjudice minime pour les personnes : données de jeu public, joueurs professionnels consentant
  implicitement à l'exposition de leurs stats publiques

### Personnes concernées

Joueurs professionnels de la Ligue Française (LFL Division 1 et Division 2) et de l'EMEA Masters.
Nombre total historique : 939 joueurs (2013–2026). Nombre actifs par saison : ~80–120.

### Finalité du traitement

Analyse statistique des performances des joueurs LFL dans le cadre d'un projet de
data engineering à des fins pédagogiques (certification RNCP niveau 7).
Aucune utilisation commerciale, aucune prise de décision automatisée.

### Destinataires des données

| Destinataire | Accès | Localisation |
|-------------|-------|-------------|
| BigQuery (Google Cloud) | Stockage et requêtes | `europe-west1` (UE) |
| Google Cloud Storage | Stockage brut (Bronze) | `EU` multi-région (UE) |
| FastAPI (localhost) | Accès en lecture via API sécurisée | Serveur local |
| Aucun tiers | — | — |

Les données ne sont pas transmises à des tiers. Google Cloud Platform est soumis aux
garanties du RGPD via les clauses contractuelles types (CCT) de la Commission européenne.

### Durée de conservation

| Couche | Durée | Justification |
|--------|-------|--------------|
| Bronze GCS | 90 jours (puis Coldline) | Données brutes, réingérables à tout moment |
| Silver GCS | Durée du projet (≤ 24 mois) | Données nettoyées actives |
| Gold BigQuery | 730 jours (24 mois) | Analyse et mise à disposition API |

À l'issue du projet, les données sont supprimées manuellement ou par expiration automatique
des tables BigQuery (configurée via Terraform).

### Mesures de sécurité

| Mesure | Implémentation |
|--------|---------------|
| Secrets non commitables | `.env` listé dans `.gitignore` ; vérification dans l'historique git |
| Variables d'environnement | `pydantic-settings` — aucun `os.getenv()` dans le code métier |
| Accès GCS | Compte de service dédié `nexus-ingestion` (IAM moindre privilège) |
| Accès BigQuery | Compte de service `nexus-api` en lecture seule sur Gold |
| Chiffrement au repos | GCS et BigQuery chiffrés par défaut par Google |
| Chiffrement en transit | HTTPS/TLS sur tous les appels API |
| Authentification API | X-API-Key obligatoire sur tous les endpoints FastAPI |

### Droits des personnes

Les personnes concernées (joueurs professionnels) bénéficient des droits suivants :

| Droit | Procédure |
|-------|-----------|
| **Droit d'accès** (art. 15) | Demande par email — réponse sous 30 jours |
| **Droit de rectification** (art. 16) | Correction manuelle dans les fichiers Silver et Gold |
| **Droit à l'effacement** (art. 17) | Suppression du PUUID dans Bronze, Silver et Gold via script |
| **Droit d'opposition** (art. 21) | Exclusion du joueur de toutes les ingestions futures |
| **Droit à la limitation** (art. 18) | Anonymisation du PUUID (remplacé par un hash non réversible) |

### Procédure de suppression sur demande

En cas de demande d'exercice des droits :

1. Identifier le joueur par son `player_link` (nom wiki) ou `player_name`
2. Localiser et supprimer les fichiers Bronze concernés :
   `bronze/riot_api/{date}.ndjson` — supprimer les lignes contenant le PUUID
3. Regénérer les fichiers Silver (`lfl_players`, `lfl_player_stats`) sans ce joueur
4. Recharger BigQuery raw et relancer dbt pour mettre à jour le Gold
5. Documenter l'opération dans le PROGRESS.md

### Fréquences d'exécution des traitements de conformité

| Traitement de conformité | Type | Fréquence | Déclencheur |
|--------------------------|------|-----------|-------------|
| Vérification des données collectées vs minimisation | Manuel | À chaque ingestion (hebdomadaire) | Avant `uv run python -m ingestion.riot_api.ingest` |
| Purge automatique Bronze → Coldline | Automatisé (Terraform lifecycle) | Continue (90 jours après création de l'objet GCS) | Google Cloud Storage lifecycle policy |
| Expiration automatique tables BigQuery Gold | Automatisé (Terraform) | Continue (730 jours après création de la table) | BigQuery table expiration |
| Audit des accès IAM | Manuel | Trimestriel | Revue des comptes de service actifs |
| Revue du registre des traitements | Manuel | Annuel ou en cas de changement de traitement | Ajout d'une nouvelle source de données |
| Traitement des demandes d'exercice des droits | Manuel (sur demande) | Dans les 30 jours suivant la réception de la demande | Email du joueur concerné |
| Vérification des accès BigQuery (INFORMATION_SCHEMA.JOBS) | Manuel | Mensuel | Revue des requêtes exécutées sur les données personnelles |

---

## Traitement n°2 — Collecte des Riot IDs publics via scraping wiki

### Identification du traitement

| Champ | Valeur |
|-------|--------|
| **Nom du traitement** | Scraping des pages wiki Leaguepedia pour SoloqueueIds |
| **Module concerné** | `ingestion/leaguepedia_wiki/ingest.py` |
| **Couche concernée** | Bronze (`bronze/leaguepedia_wiki/player_ids/`) |

### Données traitées

| Donnée | Nature | Source |
|--------|--------|--------|
| Nom de joueur wiki | Pseudonyme public | Leaguepedia |
| SoloqueueIds (`name#tag`) | Nom de compte public | Pages wiki Leaguepedia |

### Qualification RGPD

Les SoloqueueIds sont des **données publiques choisies par les joueurs eux-mêmes** comme
identifiants publics sur les plateformes Riot Games. Ils sont publiés volontairement sur
Leaguepedia par la communauté et/ou par les joueurs.

Ces données restent **pseudonymisées** (un SoloqueueId peut identifier une personne physique).

### Base légale

**Article 6.1.f — Intérêt légitime** — identique au traitement n°1.

Les données sont publiquement accessibles sur Leaguepedia, site wiki collaboratif.
Le scraping reproduit ce qui est visible par tout visiteur du site.

### Durée de conservation

90 jours en Bronze GCS, puis expiration ou suppression manuelle.

---

## Données NON collectées

Ce projet ne collecte **jamais** les données suivantes, conformément aux règles définies
dans `.cursorrules` :

- Noms civils (prénom, nom de famille)
- Adresses email ou postales
- Numéros de téléphone
- Données financières
- Données de santé
- Données de géolocalisation précise
- Données relatives aux mineurs
