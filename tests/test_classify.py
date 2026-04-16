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
async def test_classify_sales_message(api_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/classify",
            json={"message": "I am interested in your services and want a demo"},
            headers=api_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] in [
        "sales_enquiry", "support_request", "partnership",
        "job_application", "spam", "general_inquiry",
    ]
    assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_classify_support_message(api_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/classify",
            json={"message": "My account is broken and I need help fixing this error"},
            headers=api_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] in [
        "sales_enquiry", "support_request", "partnership",
        "job_application", "spam", "general_inquiry",
    ]
    assert data["confidence"] > 0


@pytest.mark.asyncio
async def test_classify_empty_message(api_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/classify",
            json={"message": ""},
            headers=api_headers,
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_classify_ambiguous_message(api_headers):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/classify",
            json={"message": "hello there"},
            headers=api_headers,
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "general_inquiry"
