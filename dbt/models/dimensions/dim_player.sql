-- Dimension joueurs : un joueur unique par player_link (identifiant wiki Leaguepedia).
-- Agrège toutes les performances LFL d'un joueur en statistiques de carrière.
--
-- Clé primaire : player_link (ex: "Player:Caliste") — identifiant stable même si
-- le pseudo du joueur change. Utilisée comme FK dans fact_player_game.
--
-- Choix GROUP BY player_link + player_name : player_name est fonctionnellement
-- dépendant de player_link (un lien wiki → un pseudo à un instant t).
-- On garde player_name dans le GROUP BY pour l'exposer sans sous-requête.
--
-- Choix COUNTIF : plus lisible que SUM(CASE WHEN player_win THEN 1 ELSE 0 END)
-- pour compter les victoires. Idiome BigQuery natif.
--
-- Choix SAFE_DIVIDE pour win_rate_pct : évite une division par zéro si un joueur
-- n'a aucune partie (cas théorique mais défensif).
--
-- Choix ORDER BY total_games DESC : facilite la lecture humaine et les exports CSV.
-- N'a pas d'impact sur les requêtes qui filtrent ou joignent (BigQuery ignore l'ordre
-- pour les jointures).

select
    player_link                                     as player_id,
    player_name,
    count(distinct game_id)                         as total_games,
    -- Nombre d'équipes distinctes pour lesquelles le joueur a joué
    count(distinct team)                            as teams_played_for,
    round(avg(kills), 2)                            as avg_kills,
    round(avg(deaths), 2)                           as avg_deaths,
    round(avg(assists), 2)                          as avg_assists,
    round(avg(cs), 2)                               as avg_cs,
    -- damage_to_champions peut être NULL pour les parties avant 2021
    round(avg(damage_to_champions), 2)              as avg_damage,
    round(avg(vision_score), 2)                     as avg_vision_score,
    countif(player_win = true)                      as total_wins,
    -- Win rate en % (0-100), arrondi à 1 décimale
    round(
        safe_divide(countif(player_win = true), count(*)) * 100,
        1
    )                                               as win_rate_pct

from {{ ref('stg_lfl_player_stats') }}

group by player_link, player_name
order by total_games desc
