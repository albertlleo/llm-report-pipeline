# llm-report-pipeline

Automated daily marketing intelligence pipeline. Secured per-client LLM analysis over BigQuery data, delivering branded HTML reports by email.

**Stack:** Python 3.13, Cloud Run, Vertex AI (Gemini 3 Flash), BigQuery, SendGrid, Terraform, GitHub Actions.

---

## How it works

Every morning Cloud Scheduler fires a POST request to Cloud Run for each client. The pipeline fetches the client's BigQuery data, runs a three-agent LLM analysis (Reporter -> Verifier -> Trends), builds a branded HTML email with KPI cards and a trend chart, saves the report to GCS, and delivers it via SendGrid.

See [docs/architecture.md](docs/architecture.md) for the full data flow and component diagram.

---

## Documentation

| Doc | Description                                                   |
|-----|---------------------------------------------------------------|
| [docs/architecture.md](docs/architecture.md) | System architecture, data flow, LLM pipeline, security        |
| [docs/adding_new_client.md](docs/adding_new_client.md) | Step-by-step file to onboard a new client                     |
| [docs/running_locally.md](docs/running_locally.md) | Local development, test scripts, manual triggers, log reading |
| [docs/email_configuration.md](docs/email_configuration.md) | SendGrid setup, changing recipients, rotating API key         |

---
## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) authenticated with access to `acme-prod`
## Quick start

```bash
# Install dependencies
uv sync

# Authenticate to GCP
gcloud auth application-default login

# Run end-to-end preview (opens report in browser, no email sent)
uv run python tests/e2e_preview.py client-b-demo
```

---

## Manually trigger a report

To run the pipeline for a specific client without waiting for the scheduler. The email will be sent:

```bash
# 1. Authenticate
gcloud auth login

# 2. Trigger the pipeline
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"client_id": "client-b-demo"}' \
  https://llm-report-pipeline-235610948324.europe-west1.run.app/run
```

---

## Clients

| Client ID | Schedule (CET) | Dataset |
|-----------|---------------|---------|
| `client-a-demo` | 08:00 | `min_client_a` |
| `client-b-demo` | 08:30 | `min_client_b` |
| `client-c` | 08:40 | `min_client_c` |

To add a new client see [docs/adding_new_client.md](docs/adding_new_client.md).

---

## CI/CD

| Workflow         | Trigger | Action |
|------------------|---------|--------|
| `deploy.yml`     | push to `main` with `src/**`, `prompts/**`, `queries/**`, `Dockerfile`, or `pyproject.toml` changes | Docker build + push + Cloud Run deploy |
| `infra.yml`      | push to `main` with `terraform/**` changes | terraform plan + apply (requires manual approval) |
| TODO: `lint.yml` | pull request | flake8 + pytest |

---

## Infrastructure

All GCP resources are managed with Terraform. State is stored in `acme-prod-terraform-state-llm`.

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

See [docs/adding_new_client.md](docs/adding_new_client.md) for per-client Terraform setup.

---

## Security

- One dedicated Service Account per client. No shared credentials
- Each SA has BigQuery access only to its own dataset (dataset-level IAM)
- SA keys stored in Secret Manager, never in code or `.env`
- Cloud Run deployed with `--no-allow-unauthenticated`
- `client_id` validated against hardcoded allowlist before any execution
