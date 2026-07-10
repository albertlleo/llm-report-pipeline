"""
Manual LLM smoke test — not a unit test, never committed to git.

Fetches real data from BigQuery and runs it through the LLM client.

Run with:
    export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
    PYTHONPATH=. uv run python tests/llm_check.py
"""

from src import bigquery_client, llm_client

CLIENT_ID = "client-a-demo"
CLIENT_NAME = "Client A (Demo)"
DATASET = "min_client_a"
TABLE = "stg_facebook_ads"


def main() -> None:
    print(f"Fetching {DATASET}.{TABLE}...")
    df = bigquery_client.read_table_raw(CLIENT_ID, DATASET, TABLE)
    print(f"Loaded {len(df)} rows, {len(df.columns)} columns\n")

    print("Calling Gemini 2.5 Pro (streaming)...\n")
    print("=" * 60)
    for chunk in llm_client.analyse_stream(CLIENT_ID, CLIENT_NAME, {TABLE: df}):
        print(chunk, end="", flush=True)
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
