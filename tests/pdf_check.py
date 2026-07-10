"""
Manual PDF smoke test — not a unit test, never committed to git.

Fetches real data, calls the LLM, builds a PDF, and saves it locally.

Run with:
    export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
    PYTHONPATH=. uv run python tests/pdf_check.py
"""

from src import bigquery_client, llm_client, report_builder

CLIENT_ID = "client-a-demo"
CLIENT_NAME = "Client A (Demo)"
DATASET = "min_client_a"
TABLE = "stg_facebook_ads"
OUTPUT_PATH = "/tmp/report_client_a_demo.pdf"


def main() -> None:
    print(f"Fetching {DATASET}.{TABLE}...")
    df = bigquery_client.read_table_raw(CLIENT_ID, DATASET, TABLE)
    print(f"Loaded {len(df)} rows\n")

    print("Calling Gemini 2.5 Flash (streaming)...")
    chunks = []
    for chunk in llm_client.analyse_stream(CLIENT_ID, CLIENT_NAME, {TABLE: df}):
        print(chunk, end="", flush=True)
        chunks.append(chunk)
    report_markdown = "".join(chunks)
    print("\n")

    print("Building PDF...")
    pdf_bytes = report_builder.build_pdf(CLIENT_NAME, report_markdown)

    with open(OUTPUT_PATH, "wb") as f:
        f.write(pdf_bytes)

    print(f"PDF saved to {OUTPUT_PATH} ({len(pdf_bytes):,} bytes)")


if __name__ == "__main__":
    main()
