"""
Tests for bigquery_client.py and config.validate_client_id.

All tests are pure unit tests — no real GCP connections are made.
The BQ client is mocked at the get_bq_client boundary so the tests
only verify validation logic and DataFrame plumbing.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.config import validate_client_id
import src.bigquery_client as bq_module

_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_campaigns() -> list[dict]:
    data = json.loads((_FIXTURES / "mock_campaigns.json").read_text())
    return data["rows"]


# ---------------------------------------------------------------------------
# validate_client_id
# ---------------------------------------------------------------------------

def test_validate_client_id_valid():
    result = validate_client_id("client-a-demo")
    assert result == "client-a-demo"


def test_validate_client_id_valid_strips_whitespace():
    result = validate_client_id("  client-a-demo  ")
    assert result == "client-a-demo"


def test_validate_client_id_invalid():
    with pytest.raises(ValueError, match="Invalid client_id"):
        validate_client_id("unknown-client")


def test_validate_client_id_empty_string():
    with pytest.raises(ValueError, match="Invalid client_id"):
        validate_client_id("")


def test_validate_client_id_sql_injection():
    with pytest.raises(ValueError, match="Invalid client_id"):
        validate_client_id("'; DROP TABLE users; --")


# ---------------------------------------------------------------------------
# read_table_raw — validation layer (no BQ calls needed)
# ---------------------------------------------------------------------------

def test_read_table_raw_rejects_invalid_client():
    with pytest.raises(ValueError, match="Invalid client_id"):
        bq_module.read_table_raw("hacker", "min_client_a", "stg_facebook_ads")


def test_read_table_raw_rejects_dataset_not_in_config():
    with pytest.raises(ValueError, match="not in the allowlist"):
        bq_module.read_table_raw("client-a-demo", "some_other_dataset", "stg_facebook_ads")


def test_read_table_raw_rejects_table_not_in_config():
    with pytest.raises(ValueError, match="not in the allowlist"):
        bq_module.read_table_raw("client-a-demo", "min_client_a", "admin_users")


# ---------------------------------------------------------------------------
# read_table_raw — BQ call with mocked client
# ---------------------------------------------------------------------------

def test_read_table_raw_returns_dataframe(mock_campaigns):
    mock_bq = MagicMock()
    mock_bq.query.return_value.to_dataframe.return_value = pd.DataFrame(mock_campaigns)

    with patch.object(bq_module, "get_bq_client", return_value=mock_bq):
        df = bq_module.read_table_raw(
            "client-a-demo", "min_client_a", "stg_facebook_ads"
        )

    assert isinstance(df, pd.DataFrame)
    assert len(df) == len(mock_campaigns)
    assert "campaign_name" in df.columns


def test_read_table_raw_calls_correct_sql(mock_campaigns):
    mock_bq = MagicMock()
    mock_bq.query.return_value.to_dataframe.return_value = pd.DataFrame(mock_campaigns)

    with patch.object(bq_module, "get_bq_client", return_value=mock_bq):
        bq_module.read_table_raw(
            "client-a-demo", "min_client_a", "stg_facebook_ads"
        )

    called_sql = mock_bq.query.call_args[0][0]
    assert "acme-prod" in called_sql
    assert "min_client_a" in called_sql
    assert "stg_facebook_ads" in called_sql
    assert "SELECT *" in called_sql
