import logging

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file.

    Pydantic raises a ValidationError at startup if any required field is missing.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gcs_bucket_name: str
    api_key: str
    discord_webhook_url: str = ""


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
