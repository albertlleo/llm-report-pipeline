# _template.tf — Copy this file to {client_id}.tf to onboard a new client.
#
# module "your_client" {
#   source       = "./modules/client"
#   project_id   = var.project_id
#   client_id    = "new-client-id"        # lowercase, hyphens only
#   client_name  = "Human Readable Name"  # used as SA display name
#   datasets     = [                       # exact BigQuery dataset IDs
#     "bq_dataset_id_one",
#     "bq_dataset_id_two",
#   ]
#   gcs_bucket   = "prod-acme-ingest-online-data"   # GCS bucket backing external BQ tables
# }
