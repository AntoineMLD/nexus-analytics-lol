-- Staging : stats joueurs LFL depuis la table raw chargée par bq_loader.
-- Une ligne = un joueur dans une partie.

select
    game_id,
    match_id,
    overview_page,
    tournament,
    cast(datetime_utc as timestamp)  as datetime_utc,
    team,
    team_vs,
    player_link,
    player_name,
    champion,
    role,
    side,
    player_win,
    kills,
    deaths,
    assists,
    gold,
    cs,
    damage_to_champions,
    vision_score

from {{ source('raw', 'lfl_player_stats') }}
