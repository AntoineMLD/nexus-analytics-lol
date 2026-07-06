-- Dimension champions : statistiques agrégées par champion sur toutes les parties LFL.
-- Granularité : un champion unique par ligne.
--
-- Source : stg_lfl_player_stats — champ `champion` présent sur chaque ligne de performance.
-- Permet à Yasmine d'analyser les tendances méta par champion (pick rates, winrates).
--
-- Choix COUNTIF : plus lisible que SUM(CASE WHEN ...) pour les totaux conditionnels.
-- Choix COUNT(DISTINCT game_id) pour total_games_played : nombre de parties où ce champion
-- a été joué (peut différer de total_picks si un champion est joué plusieurs fois dans
-- la même partie sur des lanes différentes — cas rare mais défensif).

select
    champion,

    -- Volume
    count(distinct game_id)                         as total_games_played,
    count(*)                                        as total_picks,
    countif(player_win = true)                      as total_wins,

    -- Win rate global sur toutes les saisons LFL
    round(
        safe_divide(countif(player_win = true), count(*)) * 100,
        1
    )                                               as win_rate_pct,

    -- Répartition par rôle (permet de voir si le champion est versatile)
    countif(role = 'Top')                           as picks_top,
    countif(role = 'Jungle')                        as picks_jungle,
    countif(role = 'Mid')                           as picks_mid,
    countif(role = 'Bot')                           as picks_bot,
    countif(role = 'Support')                       as picks_support,

    -- Stats moyennes de performance
    round(avg(kills), 2)                            as avg_kills,
    round(avg(deaths), 2)                           as avg_deaths,
    round(avg(assists), 2)                          as avg_assists,
    round(avg(cs), 2)                               as avg_cs,
    round(avg(damage_to_champions), 2)              as avg_damage,

    -- Période couverte dans les données LFL
    min(datetime_utc)                               as first_played,
    max(datetime_utc)                               as last_played

from {{ ref('stg_lfl_player_stats') }}

where champion is not null

group by champion
order by total_games_played desc
