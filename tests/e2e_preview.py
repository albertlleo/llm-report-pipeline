"""
End-to-end local preview - runs the full pipeline for a client and opens the
resulting HTML report in the browser. Does NOT send email or save to GCS.

Usage:
  uv run python tests/e2e_preview.py                      # default: client-b-demo
  uv run python tests/e2e_preview.py client-a-demo

Requires GCP credentials:
  gcloud auth application-default login
"""

import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import bigquery_client, config, gcs_client, history_manager, llm_client, report_builder

CLIENT_ID = sys.argv[1] if len(sys.argv) > 1 else "client-b-demo"
SAVE_TO_GCS = "--save" in sys.argv
OUTPUT_PATH = f"/tmp/acme_e2e_{CLIENT_ID}.html"


def main() -> None:
    client_id = config.validate_client_id(CLIENT_ID)
    cfg = config.CLIENT_CONFIG[client_id]
    client_name = cfg["client_name"]

    print(f"[1/5] Fetching BigQuery data for {client_id}...")
    tables = bigquery_client.fetch_client_data(client_id)
    if not tables:
        print("ERROR: No data returned from BigQuery.")
        sys.exit(1)
    print(f"      {len(tables)} table(s) fetched.")

    print(f"[2/5] Fetching KPI history from GCS...")
    kpi_history = history_manager.get_kpi_history(client_id, days=14)
    print(f"      {len(kpi_history)} day(s) of history available.")

    print(f"[3/5] Running LLM Reporter + Verifier...")
    report_markdown = llm_client.analyse(client_id, client_name, tables)

    print(f"[4/5] Running Trends agent...")
    trends = llm_client.analyse_trends(client_id, client_name, kpi_history, report_markdown)
    if trends:
        report_markdown += f"\n\n7. Trends\n{trends}"
        print("      Trends section generated.")
    else:
        print("      Skipped (not enough history).")

    print(f"[5/5] Building HTML report...")
    report_html = report_builder.build_html(
        client_name, report_markdown, date.today(),
        brand_name=cfg.get("brand_name"),
        kpi_history=kpi_history,
        dashboard_url=cfg.get("dashboard_url"),
    )

    with open(OUTPUT_PATH, "w") as f:
        f.write(report_html)

    if SAVE_TO_GCS:
        gcs_path = gcs_client.save_report(client_id, date.today(), report_html)
        print(f"Report saved to GCS → {gcs_path}")

    print(f"Report saved → {OUTPUT_PATH}")
    subprocess.run(["open", OUTPUT_PATH])


if __name__ == "__main__":
    main()
