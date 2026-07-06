# ─── Compte de service : ingestion ───────────────────────────────────────────
# Utilisé par les scripts d'ingestion (Bronze → GCS) et le loader BigQuery
# (Silver → raw). Droits limités au strict nécessaire (principe moindre privilège).

resource "google_service_account" "ingestion" {
  account_id   = "nexus-ingestion"
  display_name = "Nexus Analytics — Ingestion"
  description  = "Écriture GCS Bronze/Silver + chargement BigQuery raw."
}

# Écriture et lecture des objets GCS (nécessaire pour save_bronze et bq_loader).
resource "google_storage_bucket_iam_member" "ingestion_gcs_write" {
  bucket = google_storage_bucket.main.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingestion.email}"
}

# Écriture dans le dataset raw (INSERT via bq_loader).
resource "google_bigquery_dataset_iam_member" "ingestion_bq_raw" {
  dataset_id = google_bigquery_dataset.raw.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingestion.email}"
}

# Lancement de jobs BigQuery (obligatoire pour toute opération BQ).
resource "google_project_iam_member" "ingestion_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}


# ─── Compte de service : API ──────────────────────────────────────────────────
# Utilisé par FastAPI pour lire les tables Gold. Lecture seule sur gold_gold
# et gold_staging. Aucun accès à raw ni à GCS.

resource "google_service_account" "api" {
  account_id   = "nexus-api"
  display_name = "Nexus Analytics — API"
  description  = "Lecture BigQuery Gold pour les endpoints FastAPI."
}

# Lecture des tables dbt (dim_player, dim_team, fact_player_game).
resource "google_bigquery_dataset_iam_member" "api_bq_gold" {
  dataset_id = google_bigquery_dataset.gold_gold.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.api.email}"
}

# Lecture des vues staging (stg_lfl_matches, stg_lfl_player_stats).
resource "google_bigquery_dataset_iam_member" "api_bq_staging" {
  dataset_id = google_bigquery_dataset.gold_staging.dataset_id
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.api.email}"
}

# Lancement de jobs BigQuery (obligatoire pour exécuter les requêtes SELECT).
resource "google_project_iam_member" "api_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.api.email}"
}
