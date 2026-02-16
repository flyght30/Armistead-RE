"""Test action item endpoints."""
import pytest


@pytest.mark.asyncio
async def test_list_action_items_empty(client, seed_transaction):
    txn_id = str(seed_transaction.id)
    response = await client.get(f"/api/transactions/{txn_id}/action-items")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_action_item(client, seed_transaction):
    txn_id = str(seed_transaction.id)
    payload = {
        "type": "manual",
        "title": "Review contract terms",
        "description": "Check amendment clause",
        "priority": "high",
    }
    response = await client.post(f"/api/transactions/{txn_id}/action-items", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Review contract terms"
    assert data["status"] == "pending"
    assert data["priority"] == "high"
    return data["id"]


@pytest.mark.asyncio
async def test_complete_action_item(client, seed_transaction):
    txn_id = str(seed_transaction.id)
    # Create
    payload = {
        "type": "manual",
        "title": "Sign docs",
        "priority": "medium",
    }
    create_resp = await client.post(f"/api/transactions/{txn_id}/action-items", json=payload)
    item_id = create_resp.json()["id"]

    # Complete
    response = await client.patch(f"/api/action-items/{item_id}/complete")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_dismiss_action_item(client, seed_transaction):
    txn_id = str(seed_transaction.id)
    payload = {
        "type": "manual",
        "title": "Optional task",
        "priority": "low",
    }
    create_resp = await client.post(f"/api/transactions/{txn_id}/action-items", json=payload)
    item_id = create_resp.json()["id"]

    response = await client.patch(f"/api/action-items/{item_id}/dismiss")
    assert response.status_code == 200
    assert response.json()["status"] == "dismissed"


@pytest.mark.asyncio
async def test_complete_nonexistent_item(client, seed_user):
    response = await client.patch("/api/action-items/00000000-0000-0000-0000-000000000099/complete")
    assert response.status_code == 404
