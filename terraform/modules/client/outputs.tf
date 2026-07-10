output "service_account_email" {
  description = "Email of the client's dedicated GCP Service Account (SA)."
  value       = google_service_account.client.email
}

output "secret_name" {
  description = "Full resource name of the Secret Manager secret holding the SA key."
  value       = google_secret_manager_secret.sa_key.name
}
