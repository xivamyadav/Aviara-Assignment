from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class EnrichmentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    company: str = Field(..., min_length=1, max_length=300)


class EnrichmentResponse(BaseModel):
    linkedin_url: str
    company_size: str
    industry: str


class ClassifyRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)


class ClassifyResponse(BaseModel):
    intent: str
    confidence: float


class LeadInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr
    company: str = Field(..., min_length=1, max_length=300)
    message: Optional[str] = Field(default="")


class LeadProcessingResult(BaseModel):
    lead_id: str
    status: str
    enrichment: EnrichmentResponse
    classification: ClassifyResponse
    stored: bool
    notified: bool
    processed_at: str
