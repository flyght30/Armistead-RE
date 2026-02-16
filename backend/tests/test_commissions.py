"""Test commission and pipeline endpoints."""
import pytest


@pytest.mark.asyncio
async def test_get_commission_config_default(client, seed_user):
    response = await client.get("/api/commission-config")
    assert response.status_code == 200
    data = response.json()
    assert data["commission_type"] == "percentage"


@pytest.mark.asyncio
async def test_get_pipeline_empty(client, seed_user):
    response = await client.get("/api/pipeline")
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_count"] == 0
    assert data["total_projected_gross"] == "0"


@pytest.mark.asyncio
async def test_export_pipeline_csv(client, seed_user):
    response = await client.get("/api/pipeline/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
