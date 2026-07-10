# Adding a New Client

Step-by-step guide to onboard a new client. All 5 steps are required; steps 4 and 5 are optional depending on whether the client needs custom SQL or a custom prompt.

---

## Step 1 - Terraform: infrastructure and permissions

Copy the client template and fill in the values:

```bash
cp terraform/clients/_template.tf terraform/clients/{client_id}.tf
```

You can see the already created .tf files. Edit the following fields from the new file:
- `client_id`: must match the key used everywhere (e.g. `client-c`)
- `dataset_id`: the BigQuery dataset name in `acme-prod`
- `display_name`: human-readable name for the SA

Then add the client to the Cloud Scheduler in `terraform/pipeline.tf`:

```hcl
locals {
  client_schedules = {
    "client-a-demo"        = "0 8 * * *"
    "client-b-demo" = "30 8 * * *"
    "client-c"       = "0 9 * * *"   # <-- add this line
  }
}
```

Push the `terraform/**` changes to `main` — the `infra.yml` GitHub Action will run `terraform apply` automatically.

> The Terraform module creates everything automatically: a dedicated Service Account, generates its key, stores it in Secret Manager as `sa-key-{client_id}`, grants BigQuery dataset-level IAM bindings, and creates the Cloud Scheduler job. No manual key handling required.

---

## Step 2 - Config: register the client in `src/config.py`

Add the client to `CLIENT_CONFIG` and it will be included in `VALID_CLIENT_IDS` automatically:

```python
"client-c": {
    "client_id": "client-c",
    "client_name": "Client C",
    "brand_name": "Client C",           # short name shown in email header
    "datasets": ["client_c__supermetrics_standard"],
    "tables": {
        "client_c__supermetrics_standard": [
            "stg_dv360__campaign",
            "stg_dv360__geo",
            "stg_facebook_ads",
        ],
    },
    "email_recipients": ["client@example.com", "albert@acme.io"],
    "dashboard_url": "https://app.acme.io/...",   # optional: footer button URL redirecting to clients Dashboard
},
```

The `tables` key maps each dataset to the list of tables to fetch. The pipeline fetches all listed tables and passes them to the LLM.

---

## Step 3 - Test locally

Run the full end-to-end pipeline locally before deploying. 

**If it fails due to SQL error (missing/wrong columns), proceed to step 4 and run again this local test before pushing**:

```bash
uv run python tests/e2e_preview.py client-c
```

This fetches real BQ data, runs the full LLM pipeline, and opens the HTML report in your browser. It does **not** send an email or save to GCS.

To also save the report to GCS (needed to seed the history for the Trends section):

```bash
uv run python tests/e2e_preview.py client-c --save
```
> **If ERROR, move to step 4. Create the correct SQL for that client, and git push**

---

## Step 4 (optional) - Custom SQL queries

By default the pipeline fetches the raw table rows and passes them to the LLM. If the client's table schema requires aggregation or filtering before the LLM sees it (e.g. product-level tables that need `COUNT(DISTINCT order_id)`), create a custom SQL directory:

```
queries/
└── client-c/
    ├── sales_daily.sql
    └── media_by_channel.sql
```

Then register the queries in `config.py` under the client entry. You can take Client B client as example:

```python
"queries": {
    "sales_daily": {
        "file": "queries/client-c/sales_daily.sql",
        "table": "stg_sales",              # which table to run this query against
    },
    "media_by_channel": {
        "file": "queries/client-c/media_by_channel.sql",
        "table": "stg_media",
    },
},
"aggregate_queries": ["sales_daily"],      # queries that aggregate (GROUP BY) their table
```

**SQL placeholders available:**

| Placeholder | Replaced with |
|------------|--------------|
| `{project}` | `acme-prod` |
| `{dataset}` | the client's dataset ID |
| `{table}` | the table name from the `table` key above |

**Important for date ranges:** always fetch at least 2 days of data so the LLM can compute Δ% vs the previous day:

```sql
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY)
  AND date < CURRENT_DATE()
```

---

## Step 5 (optional) - Custom prompt

The default prompt is at `prompts/default/reporter.md`. If the client needs a different tone, different section order, or client-specific instructions, create a client-specific override:

```
prompts/
└── client-c/
    └── reporter.md     # overrides prompts/default/reporter.md
```

The pipeline automatically picks up `prompts/{client_id}/reporter.md` if it exists, falling back to `prompts/default/reporter.md`.

You can also override `verifier.md` and `trends.md` the same way.

---

## Step 6 - Deploy

Push all changes (`src/`, `queries/`, `prompts/`) to `main`. The `deploy.yml` GitHub Action will build and push the Docker image and redeploy Cloud Run automatically.

```bash
git add src/config.py queries/client-c/ prompts/client-c/
git commit -m "[Feature] Onboard client-c client"
git push
```

---

## Checklist

- [ ] `terraform/clients/client-c.tf` created and pushed
- [ ] `client-c` added to `local.client_schedules` in `pipeline.tf`
- [ ] Push changes. `infra.yml` applied successfully (SA + key + Secret Manager + Scheduler created automatically)
- [ ] `client-c` added to `CLIENT_CONFIG` in `src/config.py`
- [ ] Local e2e test passed: `uv run python tests/e2e_preview.py the-client-c`
- [ ] Custom SQL added if needed (`queries/the-client-c/`)
- [ ] Custom prompt added if needed (`prompts/client-c/`)
- [ ] Changes pushed to `main` — `deploy.yml` triggered
