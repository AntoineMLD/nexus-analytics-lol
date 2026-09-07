-- Snapshot SCD Type 2 : historique des affiliations joueur ↔ équipe.
--
-- Objectif : détecter chaque changement d'équipe d'un joueur LFL
-- et conserver l'historique complet avec des plages de validité.
--
-- Stratégie : 'check' sur la colonne current_team.
--   Si la valeur de current_team change entre deux exécutions de
--   `dbt snapshot`, dbt :
--     1. Ferme la ligne existante : dbt_valid_to = NOW()
--     2. Insère une nouvelle ligne : dbt_valid_to = NULL (actif)
--
-- Colonnes ajoutées automatiquement par dbt :
--   dbt_scd_id      — identifiant unique de la ligne snapshot
--   dbt_updated_at  — timestamp de la dernière mise à jour
--   dbt_valid_from  — début de validité de cette version
--   dbt_valid_to    — fin de validité (NULL = version courante)
--
-- Cas d'usage métier :
--   - "Dans quelle équipe était Caliste au 1er mars 2025 ?"
--     → WHERE player_id = 'Player:Caliste'
--       AND dbt_valid_from <= '2025-03-01'
--       AND (dbt_valid_to > '2025-03-01' OR dbt_valid_to IS NULL)
--
-- Dataset cible : gold_gold (même dataset que les autres dimensions).
-- Fréquence d'exécution recommandée : hebdomadaire, après dbt run.

{% snapshot snap_player_team %}

    {{
        config(
            target_schema="gold",
            unique_key="player_id",
            strategy="check",
            check_cols=["current_team"],
            invalidate_hard_deletes=True,
        )
    }}

    select
        player_id,
        player_name,
        current_team,
        last_game_date,
        total_games_in_team,
        all_teams_played

    from {{ ref("dim_player_current_team") }}

{% endsnapshot %}
