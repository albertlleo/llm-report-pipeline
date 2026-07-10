"""
End-to-end local test (not a unit test)

Runs the full pipeline for client-a-demo: BQ fetch -> LLM analysis -> PDF build.
Skips email sending (no SendGrid key yet) and saves the PDF to /tmp instead.

Run with:
    export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
    PYTHONPATH=. uv run python tests/e2e_check.py
"""

import argparse
import logging
import sys

from src import bigquery_client, config, llm_client, report_builder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("client_id", nargs="?", default="client-a-demo")
CLIENT_ID = parser.parse_args().client_id
OUTPUT_PATH = f"/tmp/e2e_report_{CLIENT_ID.replace('-', '_')}.pdf"


def run() -> None:
    client_id = config.validate_client_id(CLIENT_ID)
    cfg = config.CLIENT_CONFIG[client_id]
    client_name = cfg["client_name"]

    # 1. Fetch and pre-process data from BigQuery
    tables = bigquery_client.fetch_client_data(client_id)
    log.info("Total tables fetched: %d", len(tables))

    # 2. LLM analysis (streaming so we see output in real time)
    log.info("Running LLM analysis...")
    chunks = []
    for chunk in llm_client.analyse_stream(client_id, client_name, tables):
        print(chunk, end="", flush=True)
        chunks.append(chunk)
    report_markdown = "".join(chunks)
    print("\n")

    # 3. Build PDF
    log.info("Building PDF...")
    pdf_bytes = report_builder.build_pdf(client_name, report_markdown)
    log.info("PDF size: %d bytes", len(pdf_bytes))

    # 4. Save locally (skip email — no SendGrid key yet)
    with open(OUTPUT_PATH, "wb") as f:
        f.write(pdf_bytes)
    log.info("PDF saved to %s", OUTPUT_PATH)
    log.info("Open with: open %s", OUTPUT_PATH)


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log.error("Pipeline failed: %s", e)
        sys.exit(1)
