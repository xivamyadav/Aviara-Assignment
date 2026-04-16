import hashlib
from datetime import datetime, timezone

def generate_idempotency_key(email: str, name: str) -> str:
    """Generate a unique idempotency key for a lead valid for one day to avoid double-processing."""
    raw = f"{email}:{name}:{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    return hashlib.sha256(raw.encode()).hexdigest()
