from fastapi import APIRouter, Depends, HTTPException
from app.models.schemas import ClassifyRequest, ClassifyResponse
from app.services.classifier import classify_with_gemini
from app.dependencies import verify_api_key

router = APIRouter()


@router.post("/classify", response_model=ClassifyResponse)
async def classify(
    request: ClassifyRequest,
    api_key: str = Depends(verify_api_key),
):
    try:
        result = await classify_with_gemini(request.message)
        return ClassifyResponse(**result)
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Classification failed: {str(exc)}"
        )
