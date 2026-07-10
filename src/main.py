"""
Cloud Run HTTP entrypoint for the llm-report-pipeline.

POST /run : run all clients, or one if body contains {"client_id": "..."}
GET  /health : Cloud Run health / readiness probe

Cloud Scheduler fires one POST run per client daily at 08:00 CET.
Manual trigger: curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
                     -d '{"client_id":"client-a-demo"}' <service-url>/run
"""

import logging
import os
from datetime import date

from flask import Flask, jsonify, request

from src import bigquery_client, config, email_sender, gcs_client, history_manager, llm_client, report_builder

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/health")
def health():
    return "ok", 200


@app.route("/run", methods=["POST"])
def run():
    body = request.get_json(silent=True) or {}
    client_id = body.get("client_id", "").strip()

    if client_id:
        try:
            _run_client(client_id)
        except Exception as e:
            log.error("Pipeline failed for %s: %s", client_id, e, exc_info=True)
            return jsonify({"status": "error", "client": client_id, "error": str(e)}), 500
        return jsonify({"status": "ok", "client": client_id}), 200

    errors = []
    for cid in config.VALID_CLIENT_IDS:
        try:
            _run_client(cid)
        except Exception as e:
            log.error("Pipeline failed for %s: %s", cid, e, exc_info=True)
            errors.append(cid)

    if errors:
        return jsonify({"status": "partial_error", "failed": errors}), 500
    return jsonify({"status": "ok"}), 200


def _run_client(client_id: str) -> None:
    client_id = config.validate_client_id(client_id)
    cfg = config.CLIENT_CONFIG[client_id]
    client_name = cfg["client_name"]
    recipients = cfg["email_recipients"]

    log.info("Starting pipeline for %s", client_id)

    tables = bigquery_client.fetch_client_data(client_id)
    if not tables:
        raise RuntimeError(f"No data fetched for {client_id}")
    log.info("Fetched %d table(s) for %s", len(tables), client_id)

    log.info("Fetching KPI history for %s", client_id)
    kpi_history = history_manager.get_kpi_history(client_id, days=14)
    log.info("KPI history: %d day(s) available for %s", len(kpi_history), client_id)

    log.info("Running LLM analysis for %s", client_id)
    report_markdown = llm_client.analyse(client_id, client_name, tables)

    # History management: analyse trends/patterns
    trends_markdown = llm_client.analyse_trends(client_id, client_name, kpi_history, report_markdown)
    if trends_markdown:
        report_markdown += f"\n\n7. Trends\n{trends_markdown}"

    report_date = date.today()

    log.info("Building HTML report for %s", client_id)
    report_html = report_builder.build_html(
        client_name, report_markdown, report_date,
        brand_name=cfg.get("brand_name"),
        kpi_history=kpi_history,
        dashboard_url=cfg.get("dashboard_url"),
    )

    log.info("Saving report to GCS for %s", client_id)
    gcs_client.save_report(client_id, report_date, report_html)

    log.info("Sending report to %s", recipients)
    email_sender.send_report(client_name, recipients, report_html, report_date)

    log.info("Pipeline complete for %s", client_id)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
