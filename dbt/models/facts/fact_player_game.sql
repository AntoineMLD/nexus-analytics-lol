-- Fait principal : une ligne par joueur par partie LFL.
-- Joint stg_lfl_player_stats avec stg_lfl_matches pour enrichir chaque ligne
-- avec les informations du match (durée, patch, équipe gagnante).
-- Calcule le KDA ratio pour chaque performance.

select
    ps.game_id,
    ps.match_id,
    ps.overview_page,
    ps.tournament,
    ps.datetime_utc,

    -- Joueur
    ps.player_link,
    ps.player_name,
    ps.team,
    ps.team_vs,
    ps.champion,
    ps.role,
    ps.side,
    ps.player_win,

    -- Stats de performance
    ps.kills,
    ps.deaths,
    ps.assists,
    ps.gold,
    ps.cs,
    ps.damage_to_champions,
    ps.vision_score,

    -- KDA = (kills + assists) / deaths (0 death → deaths remplacé par 1)
    round(
        safe_divide(ps.kills + ps.assists, nullif(ps.deaths, 0)),
        2
    )                       as kda_ratio,

    -- Contexte du match
    m.gamelength_seconds,
    m.patch,
    m.win_team,
    m.loss_team,
    m.team1_gold,
    m.team2_gold,
    m.n_game_in_match

from {{ ref('stg_lfl_player_stats') }} ps
left join {{ ref('stg_lfl_matches') }} m
    using (game_id)
