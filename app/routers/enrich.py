from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import EnrichmentRequest, EnrichmentResponse
from app.services.enrichment import enrich_lead
from app.dependencies import verify_api_key

router = APIRouter()


@router.post("/enrich", response_model=EnrichmentResponse)
async def enrich(
    request: EnrichmentRequest,
    api_key: str = Depends(verify_api_key),
):
    try:
        result = await enrich_lead(request.name, request.email, request.company)
        return EnrichmentResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(exc)}")
