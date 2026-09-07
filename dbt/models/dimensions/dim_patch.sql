-- Dimension patches : une ligne par version du jeu observée dans les données LFL.
-- Permet de filtrer les analyses par méta (chaque patch dure ~2 semaines).
--
-- Source : champ `patch` dans stg_lfl_matches.
-- Yasmine a explicitement demandé lors de l'entretien (14 mai 2026) de pouvoir
-- "filtrer par patch" — c'est le principal axe d'analyse méta.
--
-- Choix MIN/MAX datetime_utc : permet de déterminer la fenêtre temporelle d'un patch
-- et de vérifier qu'un patch ne précède pas chronologiquement le précédent (test dbt).
--
-- Choix ORDER BY patch : l'ordre lexicographique "14.1", "14.2"... est correct
-- pour les patches LoL car le format est stable depuis 2021.

select
    patch,
    count(distinct game_id)         as total_games,
    min(datetime_utc)               as patch_start_date,
    max(datetime_utc)               as patch_end_date,
    count(distinct team1)
        + count(distinct team2)     as distinct_teams,
    count(distinct overview_page)   as tournaments_count

from {{ ref('stg_lfl_matches') }}

where patch is not null

group by patch
order by patch
