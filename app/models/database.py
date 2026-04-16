from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Float, DateTime, Text, Integer
from datetime import datetime, timezone
import uuid

from app.config import get_settings


def _utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Lead(Base):
    __tablename__ = "leads"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    email = Column(String(320), nullable=False, index=True)
    company = Column(String(300), nullable=False)
    linkedin_url = Column(String(500), default="")
    company_size = Column(String(50), default="")
    industry = Column(String(200), default="")
    intent = Column(String(50), default="")
    confidence = Column(Float, default=0.0)
    message = Column(Text, default="")
    status = Column(String(20), default="processed")
    idempotency_key = Column(String(64), unique=True, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class DeadLetterLead(Base):
    """Leads that failed processing end up here for later inspection."""
    __tablename__ = "dead_letter_leads"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payload = Column(Text, nullable=False)
    error_message = Column(Text, nullable=False)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)


engine = None
async_session = None


async def init_db():
    global engine, async_session
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session():
    if async_session is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    return async_session()
