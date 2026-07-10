# Architecture
Full Architecture diagrams can be seen here: https://drive.google.com/file/d/1zOQcqUTeornu5D2yTT9z_9i3lvijQNGf/view?usp=sharing
## Overview

The pipeline runs as a serverless container on **Cloud Run**, triggered daily by **Cloud Scheduler**. It uses 
per-client data from BigQuery in a secure way, runs a three-agent LLM analysis via Vertex AI, builds a branded 
HTML report, saves it to GCS, and delivers it by email via SendGrid.

## General Infrastructure architecture

![main_arch.png](images%2Fmain_arch.png)

## Components

| Component | Purpose                                                                  |
|-----------|--------------------------------------------------------------------------|
| Cloud Run | Serverless container, HTTP entrypoint (`/run`, `/health`)                |
| Cloud Scheduler | Fires daily POST per client at configured time (Europe/Madrid)           |
| BigQuery | Data source per-client, isolated datasets with GCP Service Accounts (SA) |
| Secret Manager | Stores SA keys (`sa-key-{client_id}`) and SendGrid API key               |
| Vertex AI | Gemini 3 Flash: Reporter, Verifier, Trends agents                        |
| GCS `acme-prod-reports` | HTML report storage: audit trail and KPI history for trends              |
| SendGrid | Email delivery                                                           |

## LLM Pipeline (three agents)
![llm_agents.png](images%2Fllm_agents.png)



## Security

- **One SA per client**: `sa-{client_id}@acme-prod.iam.gserviceaccount.com`
- Each SA has `bigquery.dataViewer` only on its own dataset (not project-wide)
- Each SA has `bigquery.jobUser` to run sql queries
- SA keys stored in Secret Manager, never in code or environment variables
- Pipeline impersonates the client SA before any BigQuery call
- `CLIENT_ID` validated against a hardcoded allowlist before execution
- Cloud Run deployed with `--no-allow-unauthenticated`
- Cloud Scheduler authenticates via OIDC token (dedicated `sa-cloud-scheduler` SA)

## Report HTML structure

The HTML email contains these sections in order:

1. **Header** - brand name, date badge
2. **Headline** - one-sentence executive summary
3. **KPI summary** - 8 fixed cards (Gross Sales, Net Sales, Total Sales, Orders, Media Spend, ROI, New Customer Orders, Discounts)
4. **Media spend** - total + top 3 channels + full breakdown
5. **New Users** - if available
6. **Expenses** - if available
7. **Watch-outs** - 0–3 signal bullets
8. **Trends** - multi-day pattern analysis (appears once ≥2 days of history exist)
9. **Performance Trend chart** - 5-day bar sparklines for key metrics
10. **Footer** - "View Dashboard" button linking to client dashboard

## Scheduling

```
08:30 CET — client-b-demo
```

Schedules are defined in `terraform/pipeline.tf` --> `local.client_schedules`.



## CICD

![cicd.png](images%2Fcicd.png)