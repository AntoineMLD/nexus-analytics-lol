import logging
from contextlib import contextmanager

import httpx
from google.cloud import storage
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file.

    Pydantic raises a ValidationError at startup if any required field is missing.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gcs_bucket_name: str
    api_key: str = ""
    riot_api: str = ""
    discord_webhook_url: str = ""
    fandom_bot_name: str = ""
    fandom_bot_password: str = ""
    gcp_project_id: str = ""
    bq_dataset_raw: str = "raw"
    nexus_api_key: str = ""


settings = Settings()


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def send_discord_notification(message: str) -> None:
    """Send a notification message to Discord via webhook.

    Silently skips if DISCORD_WEBHOOK_URL is not set.
    """
    if not settings.discord_webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL not set, skipping notification.")
        return
    try:
        httpx.post(settings.discord_webhook_url, json={"content": message}, timeout=10)
    except httpx.RequestError as exc:
        logger.warning("Failed to send Discord notification: %s", exc)


@contextmanager
def gcs_client():
    """Context manager that opens and closes a Google Cloud Storage client."""
    client = storage.Client(project=settings.gcp_project_id or None)
    try:
        yield client
    finally:
        client.close()


def verify_gcs_object_exists(bucket_name: str, destination: str) -> bool:
    """Return True if the object exists in GCS after upload."""
    with gcs_client() as client:
        return client.bucket(bucket_name).blob(destination).exists()
