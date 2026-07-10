"""
Client configuration and validation for the llm-report-pipeline.

Defines CLIENT_CONFIG (per-client BigQuery datasets and allowed tables),
VALID_CLIENT_IDS allowlist, validate_client_id(), and LLM (model settings).
"""

from dataclasses import dataclass

GCS_REPORTS_BUCKET = "acme-prod-reports"

CLIENT_CONFIG: dict = {
    "client-a-demo": {
        "client_id": "client-a-demo",
        "client_name": "Client A (Demo)",
        "brand_name": "Client A",
        "datasets": ["min_client_a"],
        "tables": {
            "min_client_a": [
                "stg_facebook_ads",
                "stg_google_ads",
                "stg_linkedin_ads",
                "stg_microsoft_ads",
                "stg_mntn",
                # "stg_reddit_ads",  #- view broken in BQ: column amount_spent missing in ext_reddit_ads
                "stg_stackadapt",
            ],
        },
        "dashboard_url": "https://app.acme.io",
    },
    "client-b-demo": {
        "client_id": "client-b-demo",
        "client_name": "Client B",
        "brand_name": "Client B",
        "datasets": ["min_client_b"],
        "queries": {  # If we need different sql, we add the file here
            "media_by_channel": {
                "file": "queries/client-b-demo/media_by_channel.sql",
                "table": "online_media_data_proof_mapped",
            },
            "sales_daily": {
                "file": "queries/client-b-demo/sales_daily.sql",
                "table": "online_sales_data_proof_mapped",
            },
        },
        "aggregate_queries": ["sales_daily"],  # Where to use aggregator
        "dashboard_url": "https://app.acme.io/product-performance",
    },
    "client-c": {
        "client_id": "client-c",
        "client_name": "Client C",
        "brand_name": "Client C",
        "datasets": ["min_client_c"],
        "queries": {  # If we need different sql, we add the file here
            "media_by_channel": {
                "file": "queries/client-c/media_by_channel.sql",
                "table": "online_media_data_proof_mapped",
            },
            "sales_daily": {
                "file": "queries/client-c/sales_daily.sql",
                "table": "online_sales_data_proof_mapped",
            },
        },
        "aggregate_queries": ["sales_daily"],  # Where to use aggregator
        "dashboard_url": "https://app.acme.io/product-performance",
    },
}

VALID_CLIENT_IDS: frozenset = frozenset(CLIENT_CONFIG.keys())


@dataclass(frozen=True)
class _LLMSettings:
    """
    LLM Client settings
    """
    project: str
    location: str
    model: str
    thinking_budget: int
    max_output_tokens: int
    max_rows_per_table: int


LLM = _LLMSettings(
    project="acme-prod",
    location="global",
    model="gemini-3-flash-preview",
    thinking_budget=25000,  # Output budget (thinking + output) model cap: 65,536 tokens
    max_output_tokens=32768,  # Model cap: 65,536 tokens
    max_rows_per_table=3000,  # Due to MAX input 1M, study or redefine on each client's case
)


def validate_client_id(client_id: str) -> str:
    """
    Normalise and validate a client_id against the hardcoded allowlist.

    Strips whitespace, lowercases, then checks VALID_CLIENT_IDS.
    Returns the normalised client_id on success.
    """
    normalised = client_id.strip().lower()
    if normalised not in VALID_CLIENT_IDS:
        raise ValueError(f"Invalid client_id: '{client_id}'")
    return normalised
