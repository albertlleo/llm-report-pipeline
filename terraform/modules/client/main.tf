# Creating SA
resource "google_service_account" "client" {
  project      = var.project_id
  account_id   = "sa-${var.client_id}"
  display_name = "${var.client_name} Report SA"
}

# Grant IAM Policies: dataViewer role on each of this client's datasets, not at project level
resource "google_bigquery_dataset_iam_member" "viewer" {
  for_each   = toset(var.datasets)
  project    = var.project_id
  dataset_id = each.value
  role       = "roles/bigquery.dataViewer"
  member     = "serviceAccount:${google_service_account.client.email}"
}

# jobUser is required to actually run queries
resource "google_project_iam_member" "job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.client.email}"
}

# Role objectViewer on the shared ingest bucket. Isolation made in resource line 8 (BQ level)
# Required because stg_* views refer to external tables backed by GCS objects.
resource "google_storage_bucket_iam_member" "gcs_viewer" {
  bucket = var.gcs_bucket
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.client.email}"
}

resource "google_service_account_key" "client" {
  service_account_id = google_service_account.client.name
}

# This creates the container to save the secret
resource "google_secret_manager_secret" "sa_key" {
  project   = var.project_id
  secret_id = "sa-key-${var.client_id}"

  # Auto replication for different regions
  replication {
    auto {}
  }
}

# Creating the secret
resource "google_secret_manager_secret_version" "sa_key" {
  secret      = google_secret_manager_secret.sa_key.id
  secret_data = base64decode(google_service_account_key.client.private_key)
}
