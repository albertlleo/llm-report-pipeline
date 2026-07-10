"""
Thin wrapper around GC Secret Manager.

Provides a single function to fetch the latest version of a named secret
('sa-key-{client_id}') and return its payload as UTF-8 string.
Never logs or surfaces secret values.
"""

from google.cloud import secretmanager

_PROJECT = "acme-prod"


def get_secret(secret_name: str) -> str:
    """Return the latest version of `secret_name` from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    resource = f"projects/{_PROJECT}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": resource})
    return response.payload.data.decode("utf-8")
