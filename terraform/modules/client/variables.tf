variable "client_id" {
  description = "Unique client identifier, e.g. 'client-c'. Used as SA account_id suffix and secret name"
  type        = string
}

variable "client_name" {
  description = "Human-readable client name, e.g. 'Client C'. Used as SA display name."
  type        = string
}

variable "project_id" {
  description = "GCP project ID where all resources are created."
  type        = string
}

variable "datasets" {
  description = "List of BQ dataset (main client dirs) IDs this client's SA is granted dataViewer on."
  type        = list(string)
}

variable "gcs_bucket" {
  description = "GCS bucket name backing the external BQ tables for this client."
  type        = string
}

