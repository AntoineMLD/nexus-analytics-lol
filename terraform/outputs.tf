output "bucket_name" {
  description = "Nom du bucket GCS Bronze/Silver."
  value       = google_storage_bucket.main.name
}

output "bucket_url" {
  description = "URL gsutil du bucket."
  value       = google_storage_bucket.main.url
}

output "dataset_raw" {
  description = "Dataset BigQuery Silver (raw)."
  value       = google_bigquery_dataset.raw.dataset_id
}

output "dataset_gold" {
  description = "Dataset BigQuery Gold — tables dbt."
  value       = google_bigquery_dataset.gold_gold.dataset_id
}

output "dataset_staging" {
  description = "Dataset BigQuery Staging — vues dbt."
  value       = google_bigquery_dataset.gold_staging.dataset_id
}

output "ingestion_service_account" {
  description = "Email du compte de service ingestion."
  value       = google_service_account.ingestion.email
}

output "api_service_account" {
  description = "Email du compte de service API."
  value       = google_service_account.api.email
}

output "cloud_run_url" {
  description = "URL publique du service Cloud Run nexus-api."
  value       = google_cloud_run_v2_service.nexus_api.uri
}

output "artifact_registry_repo" {
  description = "URL du dépôt Artifact Registry pour pousser les images Docker."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/nexus"
}
