-- Staging Oracle's Elixir : une ligne par joueur par partie LFL/LFL D2.
--
-- Source : raw.oracle_elixir, chargé depuis silver/oracle_elixir/{date}.ndjson
-- par pipeline/loaders/bq_loader.py.
--
-- Les métriques de diff (gold_diff_at_15, cs_diff_at_15, xp_diff_at_15) sont
-- NULL pour les parties avant ~2021 car Oracle's Elixir ne les fournit pas
-- pour les années antérieures. SAFE_CAST est utilisé pour gérer les valeurs
-- manquantes sans erreur.
--
-- Clé naturelle : (game_id, player_name) — unique par joueur par partie.
-- game_id ici est au format Riot (ex : ESPORTSTMNT01_123456), différent du
-- format Leaguepedia (ex : LFL 2024 Spring_1_1). Les deux tables ne sont pas
-- joignables sur game_id directement — fact_oe_player_game est une source
-- indépendante complémentaire.

select
    safe_cast(game_id          as string)  as game_id,
    safe_cast(league           as string)  as league,
    safe_cast(year             as int64)   as year,
    safe_cast(split            as string)  as split,
    safe_cast(date             as date)    as game_date,
    safe_cast(patch            as string)  as patch,
    safe_cast(side             as string)  as side,
    safe_cast(position         as string)  as position,
    safe_cast(player_name      as string)  as player_name,
    safe_cast(team_name        as string)  as team_name,
    safe_cast(champion         as string)  as champion,
    safe_cast(result           as int64)   as result,
    safe_cast(kills            as int64)   as kills,
    safe_cast(deaths           as int64)   as deaths,
    safe_cast(assists          as int64)   as assists,
    -- Timeline diff metrics — NULL for pre-2021 games
    safe_cast(gold_diff_at_15  as float64) as gold_diff_at_15,
    safe_cast(cs_diff_at_15    as float64) as cs_diff_at_15,
    safe_cast(xp_diff_at_15    as float64) as xp_diff_at_15,
    safe_cast(gold_diff_at_10  as float64) as gold_diff_at_10,
    safe_cast(cs_diff_at_10    as float64) as cs_diff_at_10,
    -- Per-minute metrics
    safe_cast(cs_per_min       as float64) as cs_per_min,
    safe_cast(damage_per_min   as float64) as damage_per_min,
    -- Totals
    safe_cast(damage_to_champions as float64) as damage_to_champions,
    safe_cast(vision_score     as float64) as vision_score,
    safe_cast(game_length_s    as int64)   as game_length_s

from {{ source('raw', 'oracle_elixir') }}
where player_name is not null
  and position in ('top', 'jng', 'mid', 'bot', 'sup')
