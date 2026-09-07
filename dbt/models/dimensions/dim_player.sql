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

-- CTE principale : agrégation des stats de carrière depuis Leaguepedia
with career_stats as (
    select
        player_link,
        player_name,
        count(distinct game_id)                         as total_games,
        count(distinct team)                            as teams_played_for,
        round(avg(kills), 2)                            as avg_kills,
        round(avg(deaths), 2)                           as avg_deaths,
        round(avg(assists), 2)                          as avg_assists,
        round(avg(cs), 2)                               as avg_cs,
        -- damage_to_champions peut être NULL pour les parties avant 2021
        round(avg(damage_to_champions), 2)              as avg_damage,
        round(avg(vision_score), 2)                     as avg_vision_score,
        countif(player_win = true)                      as total_wins,
        round(
            safe_divide(countif(player_win = true), count(*)) * 100,
            1
        )                                               as win_rate_pct
    from {{ ref('stg_lfl_player_stats') }}
    group by player_link, player_name
)

-- Jointure LEFT sur Riot API pour enrichir dim_player avec le PUUID.
-- La jointure est sur player_name car stg_riot_players utilise le pseudo
-- (ex: "Caliste") et non le player_link wiki (ex: "Player:Caliste").
-- LEFT JOIN : un joueur sans PUUID garde NULL — non bloquant.
select
    cs.player_link                                  as player_id,
    cs.player_name,
    cs.total_games,
    cs.teams_played_for,
    cs.avg_kills,
    cs.avg_deaths,
    cs.avg_assists,
    cs.avg_cs,
    cs.avg_damage,
    cs.avg_vision_score,
    cs.total_wins,
    cs.win_rate_pct,
    -- PUUID depuis l'API Riot Games (NULL si le joueur n'a pas de compte EUW résolu)
    rp.puuid

from career_stats cs
left join {{ ref('stg_riot_players') }} rp
    on cs.player_name = rp.player_name

order by cs.total_games desc
