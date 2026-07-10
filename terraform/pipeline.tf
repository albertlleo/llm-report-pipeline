# shared infrastructure for the Cloud Run pipeline service.
# Manages: Artifact Registry, Cloud Run service, Cloud Scheduler jobs,
# pipeline runner SA, SendGrid secret container (mail), and failure alerting.
#
# Image updates are handled by the deploy.yml CI workflow (gcloud run deploy).
# Terraform owns all configuration except the container image tag.


# Artifact Registry (Docker Hub)
resource "google_artifact_registry_repository" "pipeline" {
  project       = var.project_id
  location      = var.region
  repository_id = "llm-report-pipeline"
  format        = "DOCKER"
}

# Pipeline runner service account (Cloud Run identity)
resource "google_service_account" "pipeline_runner" {
  project      = var.project_id
  account_id   = "sa-pipeline-runner"
  display_name = "LLM Report Pipeline Runner"
}

# Give IAM Policy to read secrets so it can authenticate. Read any secret (SA keys per client + sendgrid-api-key)
resource "google_project_iam_member" "pipeline_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.pipeline_runner.email}"
}

# IAM role to call Vertex AI (using Gemini now)
resource "google_project_iam_member" "pipeline_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.pipeline_runner.email}"
}

# Cloud Run service: Here we define where our image will run
# lifecycle.ignore_changes prevents Terraform from reverting the image on infra-only applies

resource "google_cloud_run_v2_service" "pipeline" {
  project  = var.project_id
  name     = "llm-report-pipeline"
  location = var.region # europe-west1
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account                  = google_service_account.pipeline_runner.email
    timeout                          = "3600s" # We set the pipeline to hold for 60 mins, else it cuts after 5 mins.
    max_instance_request_concurrency = 1

    scaling {
      min_instance_count = 0
      max_instance_count = 8 # one per concurrent client run. if we have more than 8 clients, increase here
    }

    containers {
      image = "gcr.io/cloudrun/hello" # replaced by CI on first deploy

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle = true
      }
    }
  }

  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }
}

resource "google_service_account" "scheduler" {
  project      = var.project_id
  account_id   = "sa-cloud-scheduler"
  display_name = "Cloud Scheduler — Pipeline Invoker"
}

resource "google_cloud_run_v2_service_iam_member" "scheduler_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.pipeline.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduler.email}"
}

locals {
  client_schedules = {
    #"client-a-demo"        = "0 8 * * *"  # 08:00 CET
    "client-b-demo" = "30 8 * * *" # 08:30 CET
    "client-c" = "40 8 * * *" # 08:40 CET
  }
}

resource "google_cloud_scheduler_job" "client_report" {
  for_each  = local.client_schedules
  project   = var.project_id
  region    = var.region
  name      = "llm-report-${each.key}"
  schedule  = each.value
  time_zone = "Europe/Madrid"

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.pipeline.uri}/run"
    body        = base64encode(jsonencode({ client_id = each.key }))
    headers     = { "Content-Type" = "application/json" }

    oidc_token {
      service_account_email = google_service_account.scheduler.email
      audience              = google_cloud_run_v2_service.pipeline.uri
    }
  }
}

# GCS bucket for PDF audit trail (report_YYYY-MM-DD.pdf per client)
resource "google_storage_bucket" "reports" {
  project                     = var.project_id
  name                        = "acme-prod-reports"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true

  lifecycle_rule {
    condition { age = 365 }
    action    { type = "Delete" }
  }
}

resource "google_storage_bucket_iam_member" "pipeline_reports_writer" {
  bucket = google_storage_bucket.reports.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.pipeline_runner.email}"
}

#  SendGrid secret (container only — add the key value manually after terraform apply)
resource "google_secret_manager_secret" "sendgrid" {
  project   = var.project_id
  secret_id = "sendgrid-api-key"

  replication {
    auto {}
  }
}

# Failure alerting
resource "google_monitoring_notification_channel" "email_ops" {
  project      = var.project_id
  display_name = "Pipeline Ops — albert@acme.io"
  type         = "email"
  labels = {
    email_address = "albert@acme.io"
  }
}

resource "google_monitoring_alert_policy" "pipeline_5xx" {
  project      = var.project_id
  display_name = "LLM Report Pipeline — 5xx Error"
  combiner     = "OR"

  conditions {
    display_name = "Cloud Run 5xx response rate > 0"
    condition_threshold {
      filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"llm-report-pipeline\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""

      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0

      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email_ops.name]

  alert_strategy {
    auto_close = "86400s"
  }
}
