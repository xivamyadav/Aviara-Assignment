import json
import logging
import re

from google import genai
from app.config import get_settings

logger = logging.getLogger(__name__)

INTENT_CATEGORIES = [
    "sales_enquiry",
    "support_request",
    "partnership",
    "job_application",
    "spam",
    "general_inquiry",
]

# keyword patterns used when Gemini is unavailable
KEYWORD_MAP = {
    "sales_enquiry": [
        "interested", "pricing", "buy", "purchase", "demo", "quote",
        "cost", "plan", "subscribe", "service", "product", "offer",
        "price", "budget", "proposal",
    ],
    "support_request": [
        "help", "issue", "bug", "broken", "error", "fix", "support",
        "problem", "not working", "troubleshoot", "complaint", "down",
        "crash", "fail",
    ],
    "partnership": [
        "partner", "collaborate", "integration", "alliance", "joint",
        "together", "cooperation", "affiliate", "strategic",
    ],
    "job_application": [
        "job", "hiring", "resume", "cv", "apply", "position", "career",
        "vacancy", "opportunity", "role", "openings", "recruit",
    ],
    "spam": [
        "free", "winner", "congratulations", "click here", "urgent",
        "act now", "limited time", "earn money", "lottery", "bitcoin",
        "crypto offer",
    ],
}


async def classify_with_gemini(message: str) -> dict:
    """
    Tries Gemini first, falls back to keyword matching if the key
    is missing or the API call fails for any reason.
    """
    settings = get_settings()

    if not settings.GEMINI_API_KEY:
        logger.warning("No Gemini key configured — using keyword fallback")
        return _classify_with_keywords(message)

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        prompt = (
            "You are an intent classifier for incoming business leads.\n"
            "Classify the message below into exactly ONE of these categories:\n"
            f"{', '.join(INTENT_CATEGORIES)}\n\n"
            f'Message: "{message}"\n\n'
            "Respond with ONLY valid JSON, nothing else:\n"
            '{"intent": "<category>", "confidence": <float 0.0-1.0>}'
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        raw = response.text.strip()

        # pull the JSON object out of whatever the model returned
        json_match = re.search(r"\{.*?\}", raw, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            if result.get("intent") in INTENT_CATEGORIES:
                return {
                    "intent": result["intent"],
                    "confidence": round(float(result["confidence"]), 2),
                }

        logger.warning(f"Gemini returned unexpected format: {raw}")
        return _classify_with_keywords(message)

    except Exception as exc:
        logger.error(f"Gemini API error: {exc}")
        return _classify_with_keywords(message)


def _classify_with_keywords(message: str) -> dict:
    """Simple keyword scorer — deterministic, no API needed."""
    text = message.lower()
    scores = {}

    for intent, keywords in KEYWORD_MAP.items():
        hits = sum(1 for kw in keywords if kw in text)
        if hits > 0:
            scores[intent] = hits

    if not scores:
        return {"intent": "general_inquiry", "confidence": 0.45}

    best = max(scores, key=scores.get)
    confidence = round(min(0.95, 0.5 + (scores[best] * 0.12)), 2)
    return {"intent": best, "confidence": confidence}
