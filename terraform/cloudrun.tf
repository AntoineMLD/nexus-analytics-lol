# ─── Cloud Run — FastAPI Nexus Analytics ─────────────────────────────────────
#
# Ce fichier déclare le service Cloud Run pour l'API FastAPI.
#
# Prérequis avant de lancer `terraform apply` pour cette ressource :
#   1. Construire et pousser l'image Docker vers Artifact Registry :
#      gcloud builds submit --tag europe-west1-docker.pkg.dev/$PROJECT_ID/nexus/api:latest .
#   2. Activer les APIs GCP si ce n'est pas déjà fait :
#      gcloud services enable run.googleapis.com artifactregistry.googleapis.com
#
# Note : si l'image n'existe pas encore, commenter ce fichier et l'activer
# après le premier `gcloud builds submit`.

# ─── Artifact Registry ───────────────────────────────────────────────────────
resource "google_artifact_registry_repository" "nexus_api" {
  repository_id = "nexus"
  format        = "DOCKER"
  location      = var.region
  description   = "Images Docker pour le projet Nexus Analytics."
}

# ─── Cloud Run Service ────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "nexus_api" {
  name     = "nexus-api"
  location = var.region

  # Rendre le service invocable publiquement (l'auth est gérée par X-API-Key en app)
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    # Associer le service account avec les droits BigQuery viewer
    service_account = google_service_account.api.email

    scaling {
      # Cloud Run scale à 0 quand inactif (pas de coût au repos)
      min_instance_count = 0
      max_instance_count = 2
    }

    containers {
      # L'image est poussée manuellement via gcloud builds submit.
      # Le tag :latest est résolu au moment du déploiement.
      image = "europe-west1-docker.pkg.dev/${var.project_id}/nexus/api:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      # Variables d'environnement : on ne met pas les secrets ici.
      # NEXUS_API_KEY est injecté via Secret Manager (voir ci-dessous).
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = var.bucket_name
      }
      env {
        name  = "BQ_DATASET_RAW"
        value = "raw"
      }

      # NEXUS_API_KEY depuis Secret Manager (sécurisé, jamais en clair dans Terraform)
      env {
        name = "NEXUS_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.nexus_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_artifact_registry_repository.nexus_api,
    google_secret_manager_secret_version.nexus_api_key_version,
  ]
}

# ─── Accès public (non authentifié au niveau IAM) ─────────────────────────────
# L'authentification est gérée par X-API-Key au niveau applicatif.
# Cloud Run n'exige pas de token Google — n'importe qui peut appeler l'URL,
# mais sans X-API-Key valide l'API retourne 401.
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.nexus_api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ─── Secret Manager — NEXUS_API_KEY ──────────────────────────────────────────
resource "google_secret_manager_secret" "nexus_api_key" {
  secret_id = "nexus-api-key"

  replication {
    auto {}
  }
}

# Valeur initiale du secret : à remplacer par une vraie clé après le premier apply.
# Commande pour mettre à jour : 
#   echo -n "ma-vraie-clé" | gcloud secrets versions add nexus-api-key --data-file=-
resource "google_secret_manager_secret_version" "nexus_api_key_version" {
  secret      = google_secret_manager_secret.nexus_api_key.id
  secret_data = "changeme-update-after-first-apply"

  lifecycle {
    # Ne pas écraser la valeur si elle a été mise à jour manuellement
    ignore_changes = [secret_data]
  }
}

# Autoriser le service account API à lire le secret
resource "google_secret_manager_secret_iam_member" "nexus_api_secret_access" {
  secret_id = google_secret_manager_secret.nexus_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api.email}"
}
