-- Fait Oracle's Elixir : métriques avancées par joueur par partie LFL.
--
-- Source : stg_oracle_elixir (Oracle's Elixir CSV via Bronze/Silver).
--
-- Complément indépendant de fact_player_game (Leaguepedia) :
--   - fact_player_game : résultats officiels, picks/bans, équipes (Leaguepedia)
--   - fact_oe_player_game : métriques avancées non disponibles dans Leaguepedia :
--       * gold_diff_at_15 : différentiel d'or à 15 minutes (indicateur early game)
--       * cs_diff_at_15 : différentiel de CS à 15 minutes
--       * cs_per_min : CS par minute
--       * damage_per_min : DPM (dégâts par minute)
--
-- Clé de grain : (game_id, player_name) — un joueur par partie.
--
-- Les métriques de diff sont NULL pour les parties avant ~2021.
-- dpm est calculé si damage_to_champions et game_length_s sont disponibles.
-- Le résultat est exprimé en win/loss (1/0) tel que fourni par Oracle's Elixir.

select
    game_id,
    league,
    year,
    split,
    game_date,
    patch,
    side,
    position,
    player_name,
    team_name,
    champion,
    result                                                     as win,
    kills,
    deaths,
    assists,
    round((kills + assists) / nullif(deaths, 0), 2)           as kda,
    -- Early game metrics (NULL pre-2021)
    round(gold_diff_at_15, 0)                                 as gold_diff_at_15,
    round(cs_diff_at_15, 1)                                   as cs_diff_at_15,
    round(xp_diff_at_15, 0)                                   as xp_diff_at_15,
    round(gold_diff_at_10, 0)                                 as gold_diff_at_10,
    round(cs_diff_at_10, 1)                                   as cs_diff_at_10,
    -- Per-minute metrics
    round(cs_per_min, 2)                                      as cs_per_min,
    -- DPM : use pre-calculated field if available, compute otherwise
    round(
        coalesce(
            damage_per_min,
            safe_divide(damage_to_champions, game_length_s / 60.0)
        ),
        0
    )                                                         as damage_per_min,
    round(damage_to_champions, 0)                             as damage_to_champions,
    round(vision_score, 1)                                    as vision_score,
    game_length_s

from {{ ref('stg_oracle_elixir') }}
