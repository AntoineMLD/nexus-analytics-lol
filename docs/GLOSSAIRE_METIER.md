# Glossaire métier — Nexus Analytics

> Sémantique des données et objets métier propres à l'organisation.
> Répond au critère C2 (cartographie des données — partie sémantique).
>
> Dernière mise à jour : 2026-07-09

---

## Domaine : League of Legends (jeu)

| Terme | Définition |
|-------|-----------|
| **Champion** | Personnage jouable dans League of Legends. Il en existe plus de 160. Chaque joueur en sélectionne un par partie. |
| **Patch** | Version du jeu publiée par Riot Games toutes les deux semaines environ. Chaque patch modifie l'équilibre des champions (buffs/nerfs). Format : `14.5` = saison 14, patch n°5. |
| **Méta** | Ensemble des stratégies, compositions et champions considérés comme optimaux sur un patch donné. La méta change à chaque patch. |
| **Pick / Ban** | Phase de draft avant la partie. Chaque équipe ban 5 champions (interdits pour les deux équipes) et sélectionne 5 champions (un par joueur). |
| **Pick rate** | Pourcentage des parties où un champion a été sélectionné, sur un ensemble de parties donné. |
| **Ban rate** | Pourcentage des parties où un champion a été banni. |
| **Win rate** | Pourcentage de victoires avec un champion sur un ensemble de parties. |
| **KDA** | Kill/Death/Assist ratio : `(kills + assists) / deaths`. Indicateur de performance individuelle. Calculé avec `SAFE_DIVIDE` pour éviter la division par zéro. |
| **Gold** | Monnaie en jeu. Indique la puissance économique d'une équipe ou d'un joueur. |
| **CS (Creep Score)** | Nombre de monstres/sbires tués. Indicateur de farming et de récupération d'or. |
| **Vision score** | Indicateur de contrôle de la vision (wards posées/détruites). |
| **Rôle** | Position d'un joueur dans la composition : Top, Jungle, Mid, Bot (ADC), Support. |
| **Side** | Côté de la carte : Bleu (team 1, côté bas-gauche) ou Rouge (team 2, côté haut-droit). |
| **BO1 / BO3 / BO5** | Best of 1 / 3 / 5 : nombre maximal de parties dans un match. Un BO3 se joue en 2 victoires. |
| **Objectif** | Structure neutre de la carte : Dragon, Baron Nashor, Tour, Inhibiteur, Rift Herald, Void Grub. |

---

## Domaine : Compétition LFL

| Terme | Définition |
|-------|-----------|
| **LFL** | La Ligue Française de League of Legends. Compétition professionnelle française, deuxième division européenne derrière la LEC. |
| **LFL Division 2 (D2)** | Deuxième niveau de la scène compétitive française. Alimenté par le circuit LFL Division 2 Academy. |
| **LEC** | League of Legends EMEA Championship. Premier niveau européen (20 équipes, dont Karmine Corp depuis 2023). |
| **EMEA Masters** | Compétition européenne réunissant les meilleurs joueurs des ligues régionales (ERL), dont la LFL. |
| **Split** | Demi-saison compétitive. Chaque année comprend un Spring Split et un Summer Split. |
| **Regular Season** | Phase de groupes d'un split : round-robin simple ou double. Chaque équipe affronte les autres une ou deux fois. |
| **Playoffs** | Phase finale d'un split. Format bracket simple élimination ou double élimination. |
| **OverviewPage** | Identifiant unique d'une compétition sur Leaguepedia. Format : `LFL/2025 Season/Spring Split`. Clé de jointure primaire entre toutes les tables Leaguepedia. |
| **Overview page LFL** | Parmi les 10 288 tournois Leaguepedia, 71 OverviewPages correspondent à des compétitions LFL D1 ou D2 entre 2013 et 2026. |
| **Roster** | Composition d'une équipe pour une compétition donnée : liste des joueurs et leurs rôles. |
| **Academy** | Équipe de développement d'une organisation LFL, visant à préparer les joueurs pour la D1. |

---

## Domaine : Sources de données

| Terme | Définition |
|-------|-----------|
| **Oracle's Elixir** | Site de référence géré par Tim Sevenhuysen (analyste indépendant). Publie des CSV hebdomadaires de statistiques de matchs pro mondiaux (LFL, LEC, LCK, LCS, LPL, EMEA Masters) depuis 2014. Gratuit. |
| **Leaguepedia** | Wiki collaboratif (Fandom) de référence pour l'esport LoL. Accessible via API Cargo MediaWiki publique. Licence CC BY-SA 3.0. |
| **Cargo API** | Extension MediaWiki permettant de créer des tables structurées interrogeables via HTTP. Utilisée par Leaguepedia pour exposer ses données. |
| **Riot API** | API officielle Riot Games. Permet de récupérer des données de parties classées, PUUIDs, historique de matches. Usage non-commercial uniquement. |
| **GRID** | Distributeur officiel exclusif des données live LEC/ERL depuis décembre 2023. Service commercial, hors périmètre Nexus Analytics. |

---

## Domaine : Identifiants techniques

| Terme | Définition |
|-------|-----------|
| **GameId** | Identifiant unique d'une partie dans Leaguepedia. Format : `LFL/2025 Season/Spring Split_Day 5_3_2` (OverviewPage + round + match + numéro de game). |
| **MatchId** | Identifiant d'un match (série de parties) dans Leaguepedia. Format : `LFL/2025 Season/Spring Split_Day 5_3`. |
| **N GameInMatch** | Numéro de la partie dans le match (1 pour game 1, 2 pour game 2…). |
| **PUUID** | Player Universally Unique Identifier. Identifiant technique pseudonymisé attribué par Riot Games à chaque compte joueur. 78 caractères, format UUID. Donnée à caractère personnel (pseudonymisée). |
| **Riot ID** | Identifiant public d'un compte joueur. Format `gameName#tagLine` (ex: `Caliste#EUW`). Différent du PUUID : lisible par l'humain, choisi par le joueur. |
| **player_link** | Nom de la page wiki Leaguepedia d'un joueur (ex: `Caliste`). Clé de jointure entre `TournamentRosters`, `Players` et `ScoreboardPlayers`. |
| **SoloqueueIds** | Champ Leaguepedia listant les comptes soloqueue d'un joueur, en wikitext MediaWiki. Peut contenir des Riot IDs (`name#tag`) ou d'anciens summoner names. |

---

## Domaine : Architecture données

| Terme | Définition |
|-------|-----------|
| **Medallion Architecture** | Pattern d'organisation des données en trois zones : Bronze (brut), Silver (nettoyé), Gold (agrégé). Standard de l'industrie du data lakehouse. |
| **Bronze** | Zone de stockage des données brutes, sans transformation, avec métadonnées d'ingestion (source, date). |
| **Silver** | Zone de stockage des données normalisées, typées et filtrées. Prête pour le chargement en entrepôt. |
| **Gold** | Couche analytique modélisée en schéma en étoile. Alimentée par dbt, accessible via l'API FastAPI. |
| **NDJSON** | Newline Delimited JSON. Format de fichier où chaque ligne est un objet JSON autonome. Utilisé pour les données Bronze et Silver dans GCS. |
| **Schéma en étoile** | Modèle d'entrepôt avec une table de faits centrale reliée à des tables de dimensions. Optimisé pour les requêtes analytiques. |
| **Dimension** | Table de référence décrivant une entité stable (joueur, équipe, champion, patch). Peu de lignes, beaucoup de colonnes descriptives. |
| **Fait (Fact)** | Table d'événements à grain fin (une ligne par partie par joueur, une ligne par action de draft). Nombreuses lignes, peu de colonnes descriptives. |
| **SCD Type 1** | Slowly Changing Dimension de type 1 : les changements écrasent l'ancienne valeur sans historisation. Choix retenu pour `dim_player` et `dim_team` (stats recalculées à chaque run). |
| **ETL** | Extract, Transform, Load. Processus d'extraction des données sources, transformation et chargement dans l'entrepôt. |
| **Ingestion** | Étape d'extraction et de stockage brut des données (Bronze). |
| **Transform** | Étape de nettoyage et normalisation (Silver). |
| **dbt** | Data Build Tool. Outil open source de transformation SQL versionné, avec tests automatiques et documentation auto-générée. |
| **Partition** | Division d'une table BigQuery par valeur d'une colonne (ex: date). Réduit le volume de données scanné par requête. |
| **Clustering** | Tri physique des données BigQuery selon une ou plusieurs colonnes. Accélère les filtres fréquents (équipe, tournoi). |
| **WRITE_TRUNCATE** | Mode de chargement BigQuery : suppression de toutes les lignes existantes avant insertion. Garantit l'idempotence (pas de doublons). |

---

## Domaine : Qualité des données

| Terme | Définition |
|-------|-----------|
| **Idempotence** | Propriété d'une opération qui produit le même résultat qu'elle soit exécutée une ou plusieurs fois. Garantie par `WRITE_TRUNCATE` dans BigQuery et par le skip GCS dans l'ingestion Oracle's Elixir. |
| **Quarantaine** | Ligne de données rejetée lors de la validation (format incorrect, équipe inconnue, etc.). Stockée séparément avec le motif de rejet pour audit et correction manuelle. |
| **Métadonnée d'ingestion** | Information attachée à un fichier Bronze : source (URL), date d'ingestion (`ingested_at`), version du schéma. Permet la traçabilité complète de chaque donnée jusqu'à sa source. |
| **Rate limit** | Restriction du nombre de requêtes autorisées par unité de temps par une API externe. Géré par exponential backoff dans l'ingestion Leaguepedia. |
| **Exponential backoff** | Stratégie de retry avec délai croissant (1s → 2s → 4s → 8s → 16s → 32s → 60s) pour éviter de saturer une API après une erreur transiente. |
