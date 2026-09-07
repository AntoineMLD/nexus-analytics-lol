variable "project_id" {
  description = "GCP project ID."
  type        = string
  default     = "nexus-analytics-prod-498107"
}

variable "region" {
  description = "GCP region for all resources."
  type        = string
  default     = "europe-west1"
}

variable "bucket_name" {
  description = "Name of the GCS bucket used for Bronze and Silver storage."
  type        = string
  default     = "nexus-analytics-bucket"
}

variable "bronze_coldline_days" {
  description = "Number of days before Bronze objects are transitioned to Coldline storage."
  type        = number
  default     = 90
}

variable "gold_table_expiration_days" {
  description = "Number of days before Gold BigQuery tables expire (default 24 months)."
  type        = number
  default     = 730
}
