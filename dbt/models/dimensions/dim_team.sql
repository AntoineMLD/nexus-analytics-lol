-- Dimension équipes : liste dédupliquée de toutes les équipes LFL.
-- Construite à partir des colonnes team1 et team2 de stg_lfl_matches.
--
-- Choix UNION DISTINCT (et non UNION ALL) : team1 et team2 peuvent contenir
-- les mêmes équipes sur des parties différentes. UNION DISTINCT garantit
-- l'unicité du team_name sans doublons.
--
-- Choix CTE all_teams : sépare la déduplication de l'agrégation pour la lisibilité.
-- Évite une sous-requête imbriquée qui serait plus difficile à lire.
--
-- Choix LEFT JOIN avec condition OR : une équipe peut être team1 ou team2
-- selon le côté (bleu/rouge) tiré au sort. On compte toutes les parties
-- où l'équipe a joué, indépendamment du côté.
-- Note : OR dans la condition de JOIN est moins performant qu'un INNER JOIN simple,
-- mais le volume (<= 3 000 parties) rend ce surcoût négligeable sur BigQuery.

with all_teams as (
    -- Collecter toutes les équipes depuis les deux côtés de chaque partie
    select team1 as team_name from {{ ref('stg_lfl_matches') }}
    union distinct
    select team2 as team_name from {{ ref('stg_lfl_matches') }}
)

select
    team_name,
    count(distinct m.game_id) as total_games

from all_teams t
-- LEFT JOIN pour conserver les équipes même si elles n'ont plus de parties
-- (cas d'une équipe dissoute après une saison)
left join {{ ref('stg_lfl_matches') }} m
    on m.team1 = t.team_name or m.team2 = t.team_name

group by team_name
order by total_games desc
