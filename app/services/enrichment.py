import re
import hashlib
import logging
import json
import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)

async def get_redis_client():
    settings = get_settings()
    if settings.REDIS_URL:
        try:
            return redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            return None
    return None

async def enrich_lead(name: str, email: str, company: str) -> dict:
    domain = _extract_domain(email)
    logger.info(f"Enriching lead: {email} (domain: {domain})")

    # Try hitting Redis cache first
    cache_key = f"enrich:{domain}"
    r = await get_redis_client()
    if r:
        try:
            cached = await r.get(cache_key)
            if cached:
                logger.info(f"Cache hit for domain: {domain}")
                await r.aclose()
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")

    linkedin_url = _build_linkedin_url(name)

    if domain in KNOWN_COMPANIES:
        info = KNOWN_COMPANIES[domain]
        company_size = info["company_size"]
        industry = info["industry"]
    else:
        company_size = _guess_size(domain)
        industry = _guess_industry(company, domain)

    result = {
        "linkedin_url": linkedin_url,
        "company_size": company_size,
        "industry": industry,
    }

    # Store result in Redis cache (TTL 24 hours)
    if r:
        try:
            await r.setex(cache_key, 86400, json.dumps(result))
            await r.aclose()
        except Exception as e:
            logger.warning(f"Redis cache write error: {e}")

    return result

# some well-known companies mapped to realistic data
KNOWN_COMPANIES = {
    "google.com": {"company_size": "10000+", "industry": "Technology"},
    "microsoft.com": {"company_size": "10000+", "industry": "Technology"},
    "amazon.com": {"company_size": "10000+", "industry": "E-commerce / Cloud"},
    "apple.com": {"company_size": "10000+", "industry": "Consumer Electronics"},
    "meta.com": {"company_size": "10000+", "industry": "Social Media / Technology"},
    "salesforce.com": {"company_size": "5000-10000", "industry": "CRM / SaaS"},
    "hubspot.com": {"company_size": "1000-5000", "industry": "Marketing Technology"},
    "stripe.com": {"company_size": "1000-5000", "industry": "Fintech"},
    "shopify.com": {"company_size": "5000-10000", "industry": "E-commerce"},
    "slack.com": {"company_size": "1000-5000", "industry": "Communication / SaaS"},
    "notion.so": {"company_size": "500-1000", "industry": "Productivity / SaaS"},
    "figma.com": {"company_size": "500-1000", "industry": "Design / SaaS"},
    "zoho.com": {"company_size": "5000-10000", "industry": "Business Software"},
    "freshworks.com": {"company_size": "1000-5000", "industry": "CRM / SaaS"},
    "razorpay.com": {"company_size": "1000-5000", "industry": "Fintech"},
    "swiggy.com": {"company_size": "5000-10000", "industry": "Food Delivery"},
    "zomato.com": {"company_size": "5000-10000", "industry": "Food Delivery"},
    "flipkart.com": {"company_size": "10000+", "industry": "E-commerce"},
    "infosys.com": {"company_size": "10000+", "industry": "IT Services"},
    "tcs.com": {"company_size": "10000+", "industry": "IT Services"},
    "wipro.com": {"company_size": "10000+", "industry": "IT Services"},
}

# keywords in company name or domain that hint at the industry
INDUSTRY_HINTS = {
    "tech": "Technology",
    "software": "Software Development",
    "ai": "Artificial Intelligence",
    "health": "Healthcare",
    "med": "Healthcare",
    "pharma": "Pharmaceuticals",
    "finance": "Financial Services",
    "bank": "Banking",
    "pay": "Fintech",
    "edu": "Education",
    "learn": "EdTech",
    "retail": "Retail",
    "shop": "E-commerce",
    "consult": "Consulting",
    "legal": "Legal Services",
    "media": "Digital Media",
    "market": "Marketing",
    "energy": "Energy",
    "auto": "Automotive",
    "real": "Real Estate",
    "food": "Food & Beverage",
    "travel": "Travel & Hospitality",
    "logistics": "Logistics",
    "cloud": "Cloud Computing",
    "design": "Design Services",
    "data": "Data Analytics",
}

SIZE_BUCKETS = ["1-50", "50-200", "200-500", "500-1000", "1000-5000", "5000-10000"]


def _extract_domain(email: str) -> str:
    return email.split("@")[1].lower() if "@" in email else ""


def _guess_industry(company: str, domain: str) -> str:
    combined = (company + " " + domain).lower()
    for hint, industry in INDUSTRY_HINTS.items():
        if hint in combined:
            return industry
    return "Business Services"


def _guess_size(domain: str) -> str:
    # hash-based so same domain always returns same size
    hash_val = int(hashlib.md5(domain.encode()).hexdigest()[:8], 16)
    return SIZE_BUCKETS[hash_val % len(SIZE_BUCKETS)]


def _build_linkedin_url(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"https://linkedin.com/in/{slug}"



