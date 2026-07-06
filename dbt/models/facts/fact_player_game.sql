-- Table de faits principale : une ligne par joueur par partie LFL.
-- Granularité : (game_id, player_link) — clé composite unique.
--
-- Enrichissement : les stats individuelles (stg_lfl_player_stats) sont jointes
-- aux informations du match (stg_lfl_matches) via game_id pour ajouter la durée,
-- le patch et les totaux d'équipe sans dupliquer ces colonnes dans le staging joueur.
--
-- Choix LEFT JOIN : on conserve les performances joueurs même si la partie
-- correspondante est absente de stg_lfl_matches (données partielles possibles
-- après une réingestion incomplète). Un INNER JOIN risquerait de perdre des lignes.
--
-- Choix SAFE_DIVIDE + NULLIF : SAFE_DIVIDE renvoie NULL si le diviseur vaut 0
-- (évite une division par zéro sans exception). NULLIF(deaths, 0) traite
-- le cas "0 mort" comme NULL pour que le KDA soit NULL plutôt que +∞,
-- ce qui est plus exploitable en aval (filtres, agrégats).

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

    -- Stats de performance brutes
    ps.kills,
    ps.deaths,
    ps.assists,
    ps.gold,
    ps.cs,
    ps.damage_to_champions,
    ps.vision_score,

    -- KDA ratio calculé : (kills + assists) / deaths
    -- NULLIF(deaths, 0) → NULL si 0 mort, évite une division par zéro
    -- ROUND(..., 2) → 2 décimales suffisent pour la lisibilité
    round(
        safe_divide(ps.kills + ps.assists, nullif(ps.deaths, 0)),
        2
    )                       as kda_ratio,

    -- Contexte du match joint depuis stg_lfl_matches
    m.gamelength_seconds,
    m.patch,
    m.win_team,
    m.loss_team,
    m.team1_gold,
    m.team2_gold,
    m.n_game_in_match

from {{ ref('stg_lfl_player_stats') }} ps
-- LEFT JOIN pour préserver les stats joueurs même sans match correspondant
left join {{ ref('stg_lfl_matches') }} m
    using (game_id)
