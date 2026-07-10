# Email Configuration

The pipeline sends reports via **SendGrid**. The API key is stored in Secret Manager and never hardcoded. All per-client email settings (recipients, sender name) are managed in code.

---

## How emails are sent

1. The pipeline builds the HTML report.
2. `src/email_sender.py` fetches the SendGrid API key from Secret Manager (`sendgrid-api-key`).
3. It sends the HTML directly as the email body (not an attachment).
4. Subject line format: `{client_name} - Marketing Report {Month DD, YYYY}`

---

## Changing recipient emails

Recipients are configured per client in `src/config.py` under `email_recipients`. It's a list, so you can add as many addresses as needed:

```python
"client-b-demo": {
    ...
    "email_recipients": [
        "client@example.com",
        "manager@example.com",
        "albert@acme.io",
    ],
},
```

Push the change to `main`; the deploy pipeline will redeploy Cloud Run with the new config.

---

## Changing the sender address or name

The sender is hardcoded in `src/email_sender.py`:

```python
_FROM_EMAIL = "albert@acme.io"
_FROM_NAME  = "Acme Marketing Reports"
```

To change it, edit those two constants and push. The sender address must be **verified in SendGrid** (either as a single sender or via domain authentication). Otherwise SendGrid will reject the send.

To verify a new sender address in SendGrid:
1. Log in to [app.sendgrid.com](https://app.sendgrid.com)
2. Settings -> Sender Authentication -> Single Sender Verification (for individual addresses) or Authenticate a Domain (for full domain)

---

## Rotating the SendGrid API key

The API key is stored in Secret Manager as `sendgrid-api-key`. To rotate it:

```bash
# 1. Generate a new key in SendGrid dashboard
#    app.sendgrid.com -> Settings -> API Keys -> Create API Key
#    Required permission: "Mail Send" (restricted key is enough)

# 2. Add a new version to Secret Manager
echo -n "SG.your-new-api-key" | gcloud secrets versions add sendgrid-api-key \
  --data-stdin \
  --project=acme-prod

# 3. Find the old version number
# Output example:
# NAME  STATE    CREATED
# 2     ENABLED  2026-05-28T...   <- this is the new one just added
# 1     ENABLED  2026-01-10T...   <- this is the old one to disable
gcloud secrets versions list sendgrid-api-key --project=acme-prod

# 4. Disable the old version (use the number from the list above)
gcloud secrets versions disable 1 \
  --secret=sendgrid-api-key \
  --project=acme-prod
```

No code changes or redeployment needed. Secret Manager always returns the latest active version at runtime.

---

## Verifying the integration

To test that SendGrid is working without running the full pipeline:

```bash
uv run python tests/e2e_preview.py client-b-demo
```

This runs the full pipeline locally but **does not send an email** - it only opens the HTML in the browser. To actually trigger an email send, use the Cloud Run endpoint:

```bash
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{"client_id": "client-b-demo"}' \
  https://llm-report-pipeline-235610948324.europe-west1.run.app/run
```

---

## SendGrid dashboard

Monitor sends, bounces, and delivery errors at [app.sendgrid.com](https://app.sendgrid.com) -> Activity Feed.

Key things to check if emails aren't arriving:
- **Bounces** — invalid recipient address
- **Blocks** — recipient domain blocking Acme's sender
- **Spam reports** — email flagged by recipient's spam filter
- **Invalid** — API key missing or expired (check Secret Manager)
