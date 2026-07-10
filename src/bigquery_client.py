"""
BigQuery client with per-client service account impersonation.

Fetches the client SA key from Secret Manager, impersonates that SA,
then runs queries against the client's own datasets only.
All dataset and table names are validated against CLIENT_CONFIG before
any SQL is executed — dynamic table names from external input are never used.
"""

import json
import logging
from pathlib import Path

import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account

from src import config, data_aggregator, secret_manager

log = logging.getLogger(__name__)

_PROJECT = "acme-prod"
_QUERY_DIR = Path(__file__).parent.parent / "queries"


def get_bq_client(client_id: str) -> bigquery.Client:
    """Return a BigQuery client authenticated as the client's dedicated SA."""
    config.validate_client_id(client_id)
    key_json = secret_manager.get_secret(f"sa-key-{client_id}")
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(key_json),
        scopes=["https://www.googleapis.com/auth/bigquery"],
    )
    return bigquery.Client(project=_PROJECT, credentials=credentials)


def fetch_client_data(client_id: str) -> dict[str, pd.DataFrame]:
    """
    Fetch and pre-process all data for a client.

    If the client config has a 'queries' key, runs named SQL queries (aggregated
    server-side in BQ). Otherwise, falls back to raw table reads with Python
    aggregation. Returns DataFrames ready for the LLM.
    """
    config.validate_client_id(client_id)
    cfg = config.CLIENT_CONFIG[client_id]

    if "queries" in cfg:
        return _fetch_via_queries(client_id, cfg)

    tables = {}
    for dataset_id in cfg["datasets"]:
        for table_name in cfg["tables"][dataset_id]:
            log.info("Fetching %s.%s", dataset_id, table_name)
            try:
                tables[table_name] = read_table_raw(client_id, dataset_id, table_name)
                log.info("  → %d rows", len(tables[table_name]))
            except Exception as e:
                log.warning("Skipping %s.%s: %s", dataset_id, table_name, e)
    return data_aggregator.aggregate_tables(tables)


def _fetch_via_queries(client_id: str, cfg: dict) -> dict[str, pd.DataFrame]:
    bq = get_bq_client(client_id)
    dataset = cfg["datasets"][0]
    aggregate_set = set(cfg.get("aggregate_queries", []))
    results = {}
    for query_name, query_cfg in cfg["queries"].items():
        log.info("Running query: %s", query_name)
        sql = (_QUERY_DIR.parent / query_cfg["file"]).read_text().format(
            project=_PROJECT, dataset=dataset, table=query_cfg["table"]
        )
        df = bq.query(sql).to_dataframe()
        log.info("  → %d rows", len(df))
        results[query_name] = (
            data_aggregator._aggregate(query_name, df)
            if query_name in aggregate_set
            else df
        )
    return results


def read_table_raw(client_id: str, dataset_id: str, table_name: str) -> pd.DataFrame:
    """
    Read a full table from BigQuery and return it as a DataFrame.
    """
    config.validate_client_id(client_id)
    _validate_dataset_and_table(client_id, dataset_id, table_name)

    sql_template = (_QUERY_DIR / "raw_table.sql").read_text()
    sql = sql_template.format(project=_PROJECT, dataset=dataset_id, table=table_name)

    bq = get_bq_client(client_id)
    return bq.query(sql).to_dataframe()


def list_datasets(client_id: str) -> list[str]:
    config.validate_client_id(client_id)
    return list(config.CLIENT_CONFIG[client_id]["datasets"])


def list_tables(client_id: str, dataset_id: str) -> list[str]:
    config.validate_client_id(client_id)
    _validate_dataset(client_id, dataset_id)
    return list(config.CLIENT_CONFIG[client_id]["tables"][dataset_id])


def _validate_dataset(client_id: str, dataset_id: str) -> None:
    allowed = config.CLIENT_CONFIG[client_id]["datasets"]
    if dataset_id not in allowed:
        raise ValueError(
            f"Dataset '{dataset_id}' is not in the allowlist for client '{client_id}'"
        )


def _validate_dataset_and_table(client_id: str, dataset_id: str, table_name: str) -> None:
    _validate_dataset(client_id, dataset_id)
    allowed_tables = config.CLIENT_CONFIG[client_id].get("tables", {}).get(dataset_id, [])
    if table_name not in allowed_tables:
        raise ValueError(
            f"Table '{table_name}' is not in the allowlist for client '{client_id}', "
            f"dataset '{dataset_id}'"
        )
