-- Staging : matchs LFL depuis la table raw chargée par bq_loader.
-- Granularité : une ligne par partie (game_id unique).
--
-- Rôle du staging : couche légère (VIEW) entre raw et les modèles Gold.
-- Ne filtre pas, ne transforme pas la logique métier — se contente de
-- typer les colonnes et de sélectionner les champs utiles.
--
-- Choix CAST(datetime_utc AS TIMESTAMP) : bq_loader charge datetime_utc
-- comme STRING depuis le NDJSON. Le CAST ici centralise la conversion
-- pour que tous les modèles aval reçoivent un vrai TIMESTAMP.
-- Un CAST échoue silencieusement en NULL sur BigQuery si la valeur est
-- malformée, ce qui est préférable à une erreur de job complète.

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
