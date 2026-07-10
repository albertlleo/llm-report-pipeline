module "client_c" {
  source       = "../modules/client"
  project_id   = var.project_id
  client_id    = "client-c"
  client_name  = "Client C"
  datasets     = ["min_client_c"]
  gcs_bucket   = "prod-acme-ingest-online-data"
}
