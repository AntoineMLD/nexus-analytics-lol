-- Dimension joueurs : un joueur unique par player_link (identifiant wiki).
-- Agrège les statistiques de carrière sur toutes les parties LFL.

select
    player_link                                     as player_id,
    player_name,
    count(distinct game_id)                         as total_games,
    count(distinct team)                            as teams_played_for,
    round(avg(kills), 2)                            as avg_kills,
    round(avg(deaths), 2)                           as avg_deaths,
    round(avg(assists), 2)                          as avg_assists,
    round(avg(cs), 2)                               as avg_cs,
    round(avg(damage_to_champions), 2)              as avg_damage,
    round(avg(vision_score), 2)                     as avg_vision_score,
    countif(player_win = true)                      as total_wins,
    round(
        safe_divide(countif(player_win = true), count(*)) * 100,
        1
    )                                               as win_rate_pct

from {{ ref('stg_lfl_player_stats') }}

group by player_link, player_name
order by total_games desc
