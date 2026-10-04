import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def send_alert_message(message: str) -> None:
    """Send a message to the configured webhook. Failures are logged, never raised."""
    url = settings.alert_webhook_url
    if not url:
        logger.warning("ALERT (no webhook configured): %s", message)
        return
    try:
        httpx.post(url, json={"content": message}, timeout=10).raise_for_status()
    except httpx.HTTPError:
        logger.exception("Could not deliver the alert to the webhook")
