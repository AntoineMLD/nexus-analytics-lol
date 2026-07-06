# Bucket principal : stockage Bronze (NDJSON bruts) et Silver (NDJSON nettoyés).
#
# Lifecycle :
#   - Objets dans bronze/ : Standard pendant 90 jours, puis Coldline.
#     Réduit les coûts de stockage pour les données rarement relues.
#   - Objets dans silver/ : pas de transition automatique (données actives).
resource "google_storage_bucket" "main" {
  name                        = var.bucket_name
  # Le bucket existant a été créé en multi-région EU.
  # GCS n'autorise pas de changer la région d'un bucket existant.
  location                    = "EU"
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true

  # Empêche la suppression accidentelle du bucket s'il contient des objets.
  force_destroy = false

  lifecycle_rule {
    condition {
      age            = var.bronze_coldline_days
      matches_prefix = ["bronze/"]
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  labels = {
    environment = "prod"
    project     = "nexus-analytics"
    layer       = "bronze-silver"
  }
}
