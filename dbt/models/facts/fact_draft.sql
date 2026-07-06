-- Table de faits draft : une ligne par action de pick ou ban, enrichie des métadonnées du match.
-- Granularité : (game_id, team_side, action_type, action_order).
--
-- C'est la table qui permet à Yasmine d'analyser les stratégies de draft LFL :
-- "quels champions LDLC OL ban en priorité 1 ?",
-- "quel est le pick rate de Jayce en pick 1 ?"
--
-- Enrichissement via stg_lfl_matches : on ajoute patch et datetime_utc
-- car ces champs ne sont pas dans PicksAndBansS7 — ils viennent de ScoreboardGames.
-- Choix LEFT JOIN : on conserve les drafts même si le match n'est pas dans stg_lfl_matches
-- (cas de la LFL D2 qui peut être incomplète dans certaines saisons).
--
-- Choix d'inclure action_type et action_order : permet de reconstituer l'ordre
-- du draft complet depuis cette table sans jointures supplémentaires.

select
    d.game_id,
    d.match_id,
    d.overview_page,
    d.team_name,
    d.team_side,
    d.action_type,
    d.action_order,
    d.champion,
    d.winner,
    d.n_game_in_match,

    -- Enrichissement depuis les matchs (patch, date)
    m.patch,
    m.datetime_utc,

    -- Indicateur : est-ce que l'équipe qui a drafté ce champion a gagné ?
    case
        when d.winner = d.team_side then true
        else false
    end as team_won

from {{ ref('stg_lfl_drafts') }} d
left join {{ ref('stg_lfl_matches') }} m
    on d.game_id = m.game_id

order by d.game_id, d.team_side, d.action_type, d.action_order
