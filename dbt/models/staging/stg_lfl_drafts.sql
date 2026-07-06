-- Staging : actions de draft LFL depuis la table raw chargée par bq_loader.
-- Granularité : une ligne par action de pick ou ban, par partie et par équipe.
--
-- Source : raw.lfl_drafts — résultat de l'unpivot Silver de PicksAndBansS7.
-- Une partie de 5 bans + 5 picks par équipe produit jusqu'à 20 actions.
-- Les actions avec champion vide sont déjà filtrées en Silver.
--
-- Choix : pas de logique métier ici, simple typage et renommage pour la lisibilité.

select
    game_id,
    match_id,
    overview_page,
    team_name,
    team_side,
    action_type,
    action_order,
    champion,
    winner,
    n_game_in_match,
    cast(ingested_at as timestamp) as ingested_at

from {{ source('raw', 'lfl_drafts') }}
