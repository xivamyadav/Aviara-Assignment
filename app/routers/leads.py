import hashlib
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from app.dependencies import verify_api_key
from app.models.schemas import LeadInput, LeadProcessingResult
from app.services.classifier import classify_with_gemini
from app.services.enrichment import enrich_lead
from app.services.notifier import send_notification
from app.services.storage import store_dead_letter, store_lead
from app.utils.security import generate_idempotency_key

logger = logging.getLogger(__name__)

router = APIRouter()





@router.post("/webhook/lead", response_model=LeadProcessingResult)
async def process_lead(
    lead: LeadInput,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
    x_idempotency_key: str = Header(default=None, alias="X-Idempotency-Key"),
):
    """
    Full pipeline in one call:
    validate -> enrich -> classify -> store -> notify
    """
    idem_key = x_idempotency_key or generate_idempotency_key(lead.email, lead.name)
    logger.info(f"Processing lead: {lead.email}")

    try:
        enrichment = await enrich_lead(lead.name, lead.email, lead.company)

        msg = lead.message if lead.message else f"Lead from {lead.name} at {lead.company}"
        classification = await classify_with_gemini(msg)

        lead_data = {
            "name": lead.name,
            "email": lead.email,
            "company": lead.company,
            "message": lead.message,
            **enrichment,
            **classification,
        }
        lead_id = await store_lead(lead_data, idempotency_key=idem_key)

        background_tasks.add_task(send_notification, lead_data)

        return LeadProcessingResult(
            lead_id=lead_id,
            status="processed",
            enrichment=enrichment,
            classification=classification,
            stored=True,
            notified=True,
            processed_at=datetime.now(timezone.utc).isoformat(),
        )

    except Exception as exc:
        logger.error(f"Pipeline failed for {lead.email}: {exc}")
        await store_dead_letter(lead.model_dump(), str(exc))
        raise HTTPException(
            status_code=500, detail=f"Lead processing failed: {str(exc)}"
        )
