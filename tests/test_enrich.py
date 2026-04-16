import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
def api_headers():
    return {
        "X-API-Key": "ase-lead-automation-2024",
        "Content-Type": "application/json",
    }


@pytest.mark.asyncio
async def test_enrich_valid_input(api_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/enrich",
            json={
                "name": "John Doe",
                "email": "john@google.com",
                "company": "Google",
            },
            headers=api_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "linkedin_url" in data
    assert data["company_size"] == "10000+"
    assert data["industry"] == "Technology"


@pytest.mark.asyncio
async def test_enrich_unknown_company(api_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/enrich",
            json={
                "name": "Jane Smith",
                "email": "jane@randomstartup.io",
                "company": "Random Startup",
            },
            headers=api_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["linkedin_url"] == "https://linkedin.com/in/jane-smith"
    assert data["company_size"] != ""
    assert data["industry"] != ""


@pytest.mark.asyncio
async def test_enrich_missing_fields(api_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/enrich",
            json={"name": "John"},
            headers=api_headers,
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_enrich_no_api_key():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/enrich",
            json={
                "name": "John",
                "email": "john@test.com",
                "company": "Test",
            },
        )
    assert resp.status_code == 422  # missing header
