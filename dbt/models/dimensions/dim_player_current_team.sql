-- Dimension : équipe actuelle de chaque joueur LFL.
-- Granularité : une ligne par joueur (player_link).
--
-- Deux CTEs :
--   1. all_teams — agrège toutes les équipes jouées par player_link (ARRAY_AGG en GROUP BY,
--      supporté par BigQuery contrairement à ARRAY_AGG dans une window function).
--   2. latest_team — détermine l'équipe la plus récente via QUALIFY + ROW_NUMBER.
--
-- Jointure finale pour combiner équipe actuelle + historique complet.

with all_teams as (

    select
        player_link,
        array_agg(distinct team order by team)  as all_teams_played

    from {{ ref('stg_lfl_player_stats') }}
    where team is not null
    group by player_link

),

latest_team as (

    select
        player_link,
        player_name,
        team                                    as current_team,
        cast(max(datetime_utc) as date)         as last_game_date,
        count(distinct game_id)                 as total_games_in_team

    from {{ ref('stg_lfl_player_stats') }}
    where team is not null
    group by player_link, player_name, team

    qualify
        row_number() over (
            partition by player_link
            order by max(datetime_utc) desc
        ) = 1

)

select
    l.player_link           as player_id,
    l.player_name,
    l.current_team,
    l.last_game_date,
    l.total_games_in_team,
    t.all_teams_played

from latest_team l
join all_teams t on l.player_link = t.player_link
