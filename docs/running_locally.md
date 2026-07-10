# Running Locally

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) authenticated with access to `acme-prod`
- Python 3.13 (ARM64 on Apple Silicon — see note below)

## Setup

```bash
uv python install 3.13

# Install dependencies
uv sync

# Authenticate to GCP
gcloud auth application-default login
```

> **Apple Silicon note:** if you get a numpy architecture error (`have 'x86_64', need 'arm64'`), run `rm -rf .venv && uv sync` to recreate the venv with the native Python.

---

## Test scripts

### End-to-end pipeline preview

Runs the full pipeline and opens the HTML in the browser. Does **not** send email.

```bash
uv run python tests/e2e_preview.py client-b-demo
# or
uv run python tests/e2e_preview.py client-c
```

To also save the report to GCS (seeds the history for the Trends section):

```bash
uv run python tests/e2e_preview.py client-b-demo --save
```

---

## Manual Cloud Run trigger

To trigger the production pipeline for a specific client without waiting for the scheduler:

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"client_id": "client-b-demo"}' \
  https://<cloud-run-url>/run
```

To run all clients:

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://<cloud-run-url>/run
```

---
