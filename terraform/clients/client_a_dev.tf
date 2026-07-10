# client_a_demo.tf — Test_Peter_data client


module "client_a_dev" {
  source       = "../modules/client"
  project_id   = var.project_id
  client_id    = "albert-test"
  client_name  = "Client A (Albert Test)"
  datasets     = ["min_client_a"]
  # Since the stg_tables are views from external tables, I need to pass the bucket and prefix as well to have access.
  gcs_bucket   = "prod-acme-ingest-online-data"
}
