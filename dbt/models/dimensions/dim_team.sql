-- Dimension équipes : liste dédupliquée de toutes les équipes LFL.
-- Construite à partir des deux colonnes team1/team2 de stg_lfl_matches.

with all_teams as (
    select team1 as team_name from {{ ref('stg_lfl_matches') }}
    union distinct
    select team2 as team_name from {{ ref('stg_lfl_matches') }}
)

select
    team_name,
    count(distinct m.game_id) as total_games

from all_teams t
left join {{ ref('stg_lfl_matches') }} m
    on m.team1 = t.team_name or m.team2 = t.team_name

group by team_name
order by total_games desc
