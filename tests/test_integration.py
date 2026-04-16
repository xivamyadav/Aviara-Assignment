import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.database import init_db


@pytest.fixture
def api_headers():
    return {
        "X-API-Key": "ase-lead-automation-2024",
        "Content-Type": "application/json",
    }


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    await init_db()


@pytest.mark.asyncio
async def test_full_pipeline(api_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhook/lead",
            json={
                "name": "John Doe",
                "email": "john@company.com",
                "company": "Acme Inc",
                "message": "I am interested in your services",
            },
            headers=api_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processed"
    assert data["stored"] is True
    assert "lead_id" in data
    assert data["enrichment"]["linkedin_url"] != ""
    assert data["classification"]["intent"] != ""


@pytest.mark.asyncio
async def test_pipeline_without_message(api_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhook/lead",
            json={
                "name": "Jane Smith",
                "email": "jane@testcorp.com",
                "company": "TestCorp",
            },
            headers=api_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "processed"


@pytest.mark.asyncio
async def test_pipeline_invalid_email(api_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/webhook/lead",
            json={
                "name": "Bad Lead",
                "email": "not-an-email",
                "company": "Test",
            },
            headers=api_headers,
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
