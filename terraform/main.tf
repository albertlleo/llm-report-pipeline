# Main basic information so terraform knows what are we dealing with. Terraform init will look into this.
terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    bucket = "acme-prod-terraform-state-llm"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "clients" {
  source     = "./clients"
  project_id = var.project_id
}
