# Dataset raw : tables Silver chargées par bq_loader.py
# (lfl_matches, lfl_player_stats, lfl_players)
resource "google_bigquery_dataset" "raw" {
  dataset_id  = "raw"
  description = "Données Silver chargées depuis GCS par le loader Python."
  location    = var.region

  labels = {
    environment = "prod"
    layer       = "silver"
  }
}

# Dataset gold_gold : tables dbt — dimensions et faits
# (dim_player, dim_team, fact_player_game)
# Expiration : 730 jours (24 mois) conformément aux règles du projet.
resource "google_bigquery_dataset" "gold_gold" {
  dataset_id                  = "gold_gold"
  description                 = "Tables Gold dbt : dimensions et faits LFL."
  location                    = var.region
  default_table_expiration_ms = var.gold_table_expiration_days * 24 * 3600 * 1000

  labels = {
    environment = "prod"
    layer       = "gold"
  }
}

# Dataset gold_staging : vues dbt — staging sur les tables raw
# (stg_lfl_matches, stg_lfl_player_stats, stg_lfl_players)
# Les vues n'ont pas d'expiration propre (elles héritent des tables raw).
resource "google_bigquery_dataset" "gold_staging" {
  dataset_id  = "gold_staging"
  description = "Vues dbt staging sur les données Silver."
  location    = var.region

  labels = {
    environment = "prod"
    layer       = "staging"
  }
}
