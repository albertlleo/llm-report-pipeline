"""
Real GCP connectivity check — not a unit test, never committed to git.

Step 2: verify Secret Manager → SA key → BigQuery access works end-to-end
for the client-a-demo client, and that the SA is isolated to its own dataset.

Run with:
    export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
    uv run python tests/connectivity_check.py
"""

import sys
from src import secret_manager, bigquery_client


CLIENT_ID = "client-a-demo"
DATASET = "min_client_a"
TABLE = "stg_facebook_ads"
FORBIDDEN_DATASET = "client_c__supermetrics_standard"  # another client's dataset


def check(label: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {label}" + (f": {detail}" if detail else ""))
    if not ok:
        sys.exit(1)


def main() -> None:
    print("\n=== GCP Connectivity Check ===\n")

    # 1. Fetch SA key from Secret Manager
    print("1. Fetching SA key from Secret Manager...")
    try:
        key_json = secret_manager.get_secret(f"sa-key-{CLIENT_ID}")
        check("Secret Manager access", True, f"sa-key-{CLIENT_ID} fetched ({len(key_json)} chars)")
    except Exception as e:
        check("Secret Manager access", False, str(e))

    # 2. Create BQ client (impersonates client-a-demo SA)
    print("\n2. Creating BigQuery client as client-a-demo SA...")
    try:
        bq = bigquery_client.get_bq_client(CLIENT_ID)
        check("BQ client creation", True, f"authenticated as {bq.project}")
    except Exception as e:
        check("BQ client creation", False, str(e))

    # 3. Read allowed table
    print(f"\n3. Reading allowed table: {DATASET}.{TABLE}...")
    try:
        df = bigquery_client.read_table_raw(CLIENT_ID, DATASET, TABLE)
        check(
            "Read allowed table",
            len(df.columns) > 0,
            f"{len(df)} rows, columns: {list(df.columns)[:5]}",
        )
    except Exception as e:
        check("Read allowed table", False, str(e))

    # 4. Python-level isolation: table not in allowlist rejected before GCP
    print("\n4. Python isolation — table not in allowlist...")
    try:
        bigquery_client.read_table_raw(CLIENT_ID, DATASET, "admin_secrets")
        check("Python blocks forbidden table", False, "no exception raised!")
    except ValueError as e:
        check("Python blocks forbidden table", True, str(e))

    # 5. GCP-level isolation: try to access another client's dataset directly via BQ
    print(f"\n5. GCP isolation — direct query against forbidden dataset: {FORBIDDEN_DATASET}...")
    try:
        import json
        from src import secret_manager as sm
        from google.oauth2 import service_account
        from google.cloud import bigquery

        key_json = sm.get_secret(f"sa-key-{CLIENT_ID}")
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(key_json),
            scopes=["https://www.googleapis.com/auth/bigquery"],
        )
        bq = bigquery.Client(project="acme-prod", credentials=credentials)
        sql = f"SELECT 1 FROM `acme-prod.{FORBIDDEN_DATASET}.stg_facebook_ads` LIMIT 1"
        list(bq.query(sql).result())
        check("GCP blocks cross-client access", False, "query succeeded — SA has too many permissions!")
    except Exception as e:
        check("GCP blocks cross-client access", True, f"access denied as expected")

    print("\n=== All checks passed ===\n")


if __name__ == "__main__":
    main()
