-- Staging : stats joueurs LFL depuis la table raw chargée par bq_loader.
-- Granularité : une ligne par joueur par partie (clé composite game_id + player_link).
--
-- Rôle du staging : VIEW légère sur raw.lfl_player_stats.
-- Sélectionne et type les colonnes sans logique métier.
-- La jointure avec stg_lfl_matches et les calculs (KDA, agrégats)
-- sont faits dans fact_player_game et dim_player respectivement.
--
-- Choix CAST(datetime_utc AS TIMESTAMP) : même raison que stg_lfl_matches —
-- bq_loader charge en STRING, le CAST centralise la conversion en TIMESTAMP.

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
