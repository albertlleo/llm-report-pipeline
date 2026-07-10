"""
Email delivery via SendGrid with HTML body.

Fetches the SendGrid API key from Secret Manager and sends the HTML report
directly as the email body.
"""

from datetime import date

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from src import secret_manager

_FROM_EMAIL = "albert@acme.io"
_FROM_NAME = "Acme AI insights"
_SECRET_NAME = "sendgrid-api-key"


def send_report(
    client_name: str,
    recipients: list[str],
    html_content: str,
    report_date: date | None = None,
) -> None:
    """
    Send the HTML report as the email body to all configured recipients.

    Args:
        client_name: Used in the email subject line.
        recipients: List of destination addresses from CLIENT_CONFIG.
        html_content: HTML string returned by report_builder.build_html().
        report_date: Date shown in the subject line. Defaults to today.
    """
    if report_date is None:
        report_date = date.today()

    api_key = secret_manager.get_secret(_SECRET_NAME)
    subject = f"{client_name} - Acme AI Insights {report_date.strftime('%B %d, %Y')}"

    message = Mail(
        from_email=(_FROM_EMAIL, _FROM_NAME),
        to_emails=recipients,
        subject=subject,
        html_content=html_content,
        plain_text_content=(
            f"Acme AI Insights for {client_name}.\n\n"
            f"Report date: {report_date.strftime('%B %d, %Y')}\n\n"
            f"- Acme AI"
        ),
    )

    SendGridAPIClient(api_key).send(message)
