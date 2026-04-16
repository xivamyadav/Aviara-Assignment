import httpx
import logging
from datetime import datetime, timezone

from app.config import get_settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


async def send_notification(lead_data: dict) -> bool:
    """
    Sends a webhook notification with lead details.
    Retries up to MAX_RETRIES times with basic back-off.
    """
    settings = get_settings()
    webhook_url = settings.NOTIFICATION_WEBHOOK_URL

    if not webhook_url:
        logger.info("No webhook URL set, skipping notification")
        return False

    payload = {
        "event": "lead_processed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "lead": {
            "name": lead_data.get("name"),
            "email": lead_data.get("email"),
            "company": lead_data.get("company"),
            "intent": lead_data.get("intent"),
            "confidence": lead_data.get("confidence"),
            "industry": lead_data.get("industry"),
        },
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json=payload)
                if resp.status_code < 400:
                    logger.info(f"Notification sent (attempt {attempt})")
                    return True
                logger.warning(
                    f"Notification got status {resp.status_code} on attempt {attempt}"
                )
        except Exception as exc:
            logger.error(f"Notification error attempt {attempt}: {exc}")

    logger.error("All notification attempts exhausted")
    return False
