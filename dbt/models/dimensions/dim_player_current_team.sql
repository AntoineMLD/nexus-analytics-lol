-- Dimension : équipe actuelle de chaque joueur LFL.
-- Granularité : une ligne par joueur (player_link).
--
-- Source : stg_lfl_player_stats (historique complet des matchs joués).
-- Détermine l'équipe la plus récente par joueur via la date du dernier match.
--
-- Utilisé comme source par le snapshot snap_player_team (SCD Type 2)
-- pour tracer les changements d'équipes dans le temps.

select
    player_link                                                             as player_id,
    player_name,
    team                                                                    as current_team,
    cast(max(datetime_utc) as date)                                         as last_game_date,
    count(distinct game_id)                                                 as total_games_in_team,
    array_agg(
        distinct team
        order by team
    ) over (partition by player_link)                                       as all_teams_played

from {{ ref('stg_lfl_player_stats') }}

qualify
    row_number() over (
        partition by player_link
        order by max(datetime_utc) over (partition by player_link, team) desc
    ) = 1
