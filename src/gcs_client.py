"""
GCS saving for generated HTML reports.

Saves each report to gs://<bucket>/<client_id>/report_YYYY-MM-DD.html
so reports are retained for audit and historical trend feature engineering.
"""

import logging
import re
from datetime import date

from google.cloud import storage

from src.config import GCS_REPORTS_BUCKET

log = logging.getLogger(__name__)


def save_report(client_id: str, report_date: date, html_content: str) -> str:
    """Upload HTML report to GCS and return the full GCS path."""
    client = storage.Client()
    bucket = client.bucket(GCS_REPORTS_BUCKET)
    blob_name = f"{client_id}/report_{report_date.isoformat()}.html"
    blob = bucket.blob(blob_name)
    blob.upload_from_string(html_content.encode("utf-8"), content_type="text/html; charset=utf-8")
    gcs_path = f"gs://{GCS_REPORTS_BUCKET}/{blob_name}"
    log.info("Report saved to %s", gcs_path)
    return gcs_path


def list_reports(client_id: str) -> list[str]:
    """Return blob names for all stored reports for a client, sorted by date descending."""
    client = storage.Client()
    bucket = client.bucket(GCS_REPORTS_BUCKET)
    blobs = list(bucket.list_blobs(prefix=f"{client_id}/report_"))
    names = [
        b.name for b in blobs
        if re.match(r".+/report_\d{4}-\d{2}-\d{2}\.html$", b.name)
    ]
    return sorted(names, reverse=True)


def get_report_html(blob_name: str) -> str:
    """Download and return the HTML content of a stored report."""
    client = storage.Client()
    bucket = client.bucket(GCS_REPORTS_BUCKET)
    return bucket.blob(blob_name).download_as_text(encoding="utf-8")
