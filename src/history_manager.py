"""
Per-client report history: reads stored HTML reports from GCS and extracts
historical KPI values for trend charting and LLM context.
"""

import logging
import re

from bs4 import BeautifulSoup

from src import gcs_client

log = logging.getLogger(__name__)

_TRACKED_METRICS = [
    "Gross Sales",
    "Net Sales",
    "Total Sales",
    "Orders",
    "Media Spend",
    "ROI",
    "New Customer Orders",
    "Discounts",
]


def get_kpi_history(client_id: str, days: int = 14) -> list[dict]:
    """
    Parse the last N stored HTML reports for a client and return their KPI values.

    Returns:
        List of {"date": "YYYY-MM-DD", "metrics": {"Gross Sales": "$104,171.46", ...}}
        sorted ascending by date (oldest first).
    """
    try:
        blob_names = gcs_client.list_reports(client_id)
    except Exception as e:
        log.warning("Could not list reports for %s: %s", client_id, e)
        return []

    history = []
    for blob_name in blob_names[:days]:
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", blob_name)
        if not date_match:
            continue
        report_date = date_match.group(1)
        try:
            html = gcs_client.get_report_html(blob_name)
            metrics = _parse_kpi_metrics(html)
            if metrics:
                history.append({"date": report_date, "metrics": metrics})
        except Exception as e:
            log.warning("Could not parse report %s: %s", blob_name, e)

    return sorted(history, key=lambda x: x["date"])


def parse_numeric(value_str: str) -> float | None:
    """Convert display strings like '$104,171.46', '9.4x', '325' to float."""
    if not value_str:
        return None
    cleaned = re.sub(r"[$,x%\s]", "", value_str)
    if cleaned.upper().endswith("K"):
        try:
            return float(cleaned[:-1]) * 1_000
        except ValueError:
            return None
    if cleaned.upper().endswith("M"):
        try:
            return float(cleaned[:-1]) * 1_000_000
        except ValueError:
            return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def format_history_for_llm(history: list[dict]) -> str:
    """Format KPI history as a markdown table to prepend to the LLM data context."""
    if not history:
        return ""

    present = [m for m in _TRACKED_METRICS if any(m in h["metrics"] for h in history)]
    if not present:
        return ""

    header = "| Date | " + " | ".join(present) + " |"
    sep = "| --- | " + " | ".join(["---"] * len(present)) + " |"
    rows = []
    for entry in history:
        vals = [entry["metrics"].get(m, "—") for m in present]
        rows.append("| " + entry["date"] + " | " + " | ".join(vals) + " |")

    return (
        "## Historical KPI Data (last {} day{})\n{}\n{}\n{}\n".format(
            len(history), "s" if len(history) != 1 else "",
            header, sep, "\n".join(rows),
        )
    )


def _parse_kpi_metrics(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    metrics = {}
    for elem in soup.find_all(attrs={"data-kpi-metric": True}):
        name = elem.get("data-kpi-metric", "").strip()
        value = elem.get("data-kpi-value", "").strip()
        if name and value:
            metrics[name] = value
    return metrics
