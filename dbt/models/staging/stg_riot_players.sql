-- Staging Riot API : association joueur LFL → PUUID.
--
-- Source : raw.riot_players, chargé depuis silver/riot_api/riot_players/{date}.json
-- par pipeline/loaders/bq_loader.py.
--
-- Un PUUID par joueur (78 caractères). Seuls les joueurs avec un PUUID
-- valide sont présents (null filtrés dans le Silver transform).
--
-- Utilisé dans dim_player pour enrichir la dimension joueur avec le PUUID,
-- permettant un lien futur vers les données de matchs solo-ranked Riot API.

select
    safe_cast(player_name as string) as player_name,
    safe_cast(puuid       as string) as puuid

from {{ source('raw', 'riot_players') }}
where player_name is not null
  and puuid is not null
