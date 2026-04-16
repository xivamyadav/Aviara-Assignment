import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from app.models.database import Lead, DeadLetterLead, get_session

logger = logging.getLogger(__name__)


async def store_lead(lead_data: dict, idempotency_key: str = None) -> str:
    async with get_session() as session:
        async with session.begin():
            if idempotency_key:
                existing = await session.execute(
                    select(Lead).where(Lead.idempotency_key == idempotency_key)
                )
                found = existing.scalar_one_or_none()
                if found:
                    logger.info(f"Duplicate detected (key={idempotency_key}), returning existing lead")
                    return found.id

            lead = Lead(
                id=str(uuid.uuid4()),
                name=lead_data["name"],
                email=lead_data["email"],
                company=lead_data["company"],
                linkedin_url=lead_data.get("linkedin_url", ""),
                company_size=lead_data.get("company_size", ""),
                industry=lead_data.get("industry", ""),
                intent=lead_data.get("intent", ""),
                confidence=lead_data.get("confidence", 0.0),
                message=lead_data.get("message", ""),
                status="processed",
                idempotency_key=idempotency_key,
            )
            session.add(lead)
            logger.info(f"Lead stored: {lead.id} ({lead.email})")
            return lead.id


async def store_dead_letter(payload: dict, error_msg: str):
    """Failed leads go to the dead-letter table for later retry or inspection."""
    try:
        async with get_session() as session:
            async with session.begin():
                dl = DeadLetterLead(
                    id=str(uuid.uuid4()),
                    payload=json.dumps(payload),
                    error_message=error_msg,
                )
                session.add(dl)
                logger.warning(f"Dead-letter stored: {error_msg[:120]}")
    except Exception as exc:
        logger.error(f"Could not store dead letter: {exc}")
