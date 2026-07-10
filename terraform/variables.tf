variable "project_id" {
  description = "GCP project ID"
  type        = string
  default     = "acme-prod"
}

variable "region" {
  description = "GCP region for all resources"
  type        = string
  default     = "europe-west1" #I'm using this region since there are no Gemini 2.5 Flash in australia-southeast1 region
}
