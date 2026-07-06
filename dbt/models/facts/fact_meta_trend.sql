-- Table de faits méta : agrégation des pick rates et winrates par champion et par patch.
-- Granularité : (champion, patch, overview_page) — un tournoi par ligne.
--
-- C'est la table directement utilisée pour les rapports de méta de Nexus Analytics :
-- "quels champions émergent en LFL avant d'apparaître en LEC ?",
-- "quel est le winrate de Yone sur le patch 14.5 en LFL ?"
--
-- Choix de granularité (champion, patch, tournament) et non (champion, patch) :
-- permet à Yasmine de filtrer par compétition (LFL vs EMEA Masters).
--
-- Jointure player_stats → matches : le champ `patch` est uniquement dans stg_lfl_matches.
-- On enrichit les stats joueurs en joignant via game_id.
--
-- pick_rate et win_rate sont calculés par rapport au total de parties du tournoi+patch,
-- ce qui donne des pourcentages cohérents pour la comparaison inter-patches.

with
    -- Enrichissement des stats joueurs avec le patch (disponible uniquement dans matches)
    player_stats_with_patch as (
        select
            ps.game_id,
            ps.overview_page,
            ps.champion,
            ps.player_win,
            ps.kills,
            ps.deaths,
            ps.assists,
            ps.damage_to_champions,
            m.patch
        from {{ ref('stg_lfl_player_stats') }} ps
        inner join {{ ref('stg_lfl_matches') }} m
            on ps.game_id = m.game_id
        where ps.champion is not null
          and m.patch is not null
    ),

    -- Total de parties par tournoi et patch (dénominateur pour pick_rate)
    games_per_patch_tournament as (
        select
            overview_page,
            patch,
            count(distinct game_id) as total_games
        from {{ ref('stg_lfl_matches') }}
        where patch is not null
        group by overview_page, patch
    ),

    -- Stats par champion, patch, tournoi
    champion_stats as (
        select
            overview_page,
            patch,
            champion,
            count(distinct game_id)             as picks,
            countif(player_win = true)          as wins,
            round(avg(kills), 2)                as avg_kills,
            round(avg(deaths), 2)               as avg_deaths,
            round(avg(assists), 2)              as avg_assists,
            round(avg(damage_to_champions), 2)  as avg_damage

        from player_stats_with_patch

        group by overview_page, patch, champion
    )

select
    cs.overview_page,
    cs.patch,
    cs.champion,

    -- Volumes bruts
    cs.picks,
    cs.wins,
    gpt.total_games,

    -- Taux calculés (en %)
    round(safe_divide(cs.picks, gpt.total_games) * 100, 1)  as pick_rate_pct,
    round(safe_divide(cs.wins, cs.picks) * 100, 1)          as win_rate_pct,

    -- Performances moyennes
    cs.avg_kills,
    cs.avg_deaths,
    cs.avg_assists,
    cs.avg_damage

from champion_stats cs
left join games_per_patch_tournament gpt
    on cs.overview_page = gpt.overview_page
    and cs.patch = gpt.patch

order by cs.patch, cs.picks desc
