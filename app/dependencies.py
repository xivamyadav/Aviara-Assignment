from fastapi import Header, HTTPException
from app.config import get_settings


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    settings = get_settings()
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
