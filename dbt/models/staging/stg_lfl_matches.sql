-- Staging : matchs LFL depuis la table raw chargée par bq_loader.
-- Un match = une partie entre deux équipes.
-- Sélectionne les colonnes utiles et caste datetime_utc en TIMESTAMP.

select
    game_id,
    match_id,
    overview_page,
    tournament,
    patch,
    cast(datetime_utc as timestamp)  as datetime_utc,
    team1,
    team2,
    win_team,
    loss_team,
    gamelength,
    gamelength_seconds,
    team1_gold,
    team2_gold,
    team1_kills,
    team2_kills,
    team1_dragons,
    team2_dragons,
    team1_barons,
    team2_barons,
    team1_towers,
    team2_towers,
    n_game_in_match

from {{ source('raw', 'lfl_matches') }}
