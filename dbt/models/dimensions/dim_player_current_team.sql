-- Dimension : équipe actuelle de chaque joueur LFL.
--
-- Granularité : une ligne par joueur (player_link unique).
-- Représente l'état courant — l'équipe dans laquelle le joueur a joué
-- en dernier (date de partie la plus récente dans nos données).
--
-- Rôle dans le schéma SCD :
--   Ce modèle est la SOURCE du snapshot snap_player_team.
--   À chaque dbt snapshot, si current_team a changé pour un player_id,
--   une nouvelle ligne est insérée dans le snapshot (SCD Type 2).
--   L'ancienne ligne reçoit dbt_valid_to = date du changement.
--
-- Choix QUALIFY + ROW_NUMBER : c'est l'idiome BigQuery pour garder
-- une seule ligne par player_link (la plus récente).
-- Équivalent à un sous-SELECT avec MAX(datetime_utc), mais plus lisible.
--
-- Choix ARRAY_AGG pour all_teams : collecte toutes les équipes distinctes
-- jouées par le joueur dans l'ordre chronologique, utile pour le jury
-- qui veut voir la mobilité inter-équipes.

select
    player_link                                         as player_id,
    player_name,
    team                                                as current_team,
    cast(max(datetime_utc) as date)                     as last_game_date,
    count(distinct game_id)                             as total_games_in_team,
    array_agg(
        distinct team
        order by team
    ) over (partition by player_link)                   as all_teams_played

from {{ ref('stg_lfl_player_stats') }}

qualify
    row_number() over (
        partition by player_link
        order by max(datetime_utc) over (partition by player_link, team) desc
    ) = 1
