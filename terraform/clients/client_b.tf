module "client_b_test" {
  source       = "../modules/client"
  project_id   = var.project_id
  client_id    = "client-b-demo"
  client_name  = "Client B (Test)"
  datasets     = ["min_client_b"]
  gcs_bucket   = "prod-acme-ingest-online-data"
}
