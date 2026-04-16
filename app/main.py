import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.database import init_db
from app.routers import enrich, classify, leads

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logging.info("Database ready")
    yield
    logging.info("Shutting down")


app = FastAPI(
    title="Lead Automation API",
    description="AI-powered lead enrichment, classification, and processing pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(enrich.router, tags=["Enrichment"])
app.include_router(classify.router, tags=["Classification"])
app.include_router(leads.router, tags=["Leads"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}
