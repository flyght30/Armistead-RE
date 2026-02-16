"""Test transaction CRUD endpoints."""
import pytest

DEV_AGENT_ID = "00000000-0000-0000-0000-000000000001"


@pytest.mark.asyncio
async def test_list_transactions_empty(client, seed_user):
    response = await client.get("/api/transactions")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []


@pytest.mark.asyncio
async def test_create_transaction(client, seed_user):
    payload = {
        "agent_id": DEV_AGENT_ID,
        "representation_side": "buyer",
        "financing_type": "conventional",
        "property_address": "456 Oak Ave",
        "property_city": "Atlanta",
        "property_state": "GA",
        "property_zip": "30305",
        "purchase_price": {"amount": 350000, "currency": "USD"},
    }
    response = await client.post("/api/transactions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["property_address"] == "456 Oak Ave"
    assert data["status"] == "draft"
    assert data["agent_id"] is not None


@pytest.mark.asyncio
async def test_get_transaction(client, seed_transaction):
    txn_id = str(seed_transaction.id)
    response = await client.get(f"/api/transactions/{txn_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["property_address"] == "123 Test St"


@pytest.mark.asyncio
async def test_get_nonexistent_transaction(client, seed_user):
    response = await client.get("/api/transactions/00000000-0000-0000-0000-000000000099")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_transactions_with_data(client, seed_transaction):
    response = await client.get("/api/transactions")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert any(t["property_address"] == "123 Test St" for t in data["items"])
