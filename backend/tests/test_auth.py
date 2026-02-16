"""Test authentication dependency behavior."""
import pytest
from unittest.mock import patch, AsyncMock
from uuid import UUID

from app.auth import get_current_agent_id, DEV_AGENT_ID


@pytest.mark.asyncio
async def test_dev_mode_returns_dev_agent(client):
    """When no Clerk secret is configured, endpoints should use DEV_AGENT_ID."""
    response = await client.get("/api/today")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_missing_auth_header_in_prod_mode():
    """When Clerk is configured but no Bearer token is sent, should 401."""
    from fastapi import Request
    from unittest.mock import MagicMock

    with patch("app.auth.settings") as mock_settings:
        mock_settings.clerk_secret_key = "sk_test_123"
        mock_settings.clerk_frontend_api = "test.clerk.accounts.dev"

        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        mock_db = AsyncMock()

        with pytest.raises(Exception) as exc_info:
            await get_current_agent_id(mock_request, mock_db)
        assert "401" in str(exc_info.value.status_code)


@pytest.mark.asyncio
async def test_dev_agent_id_value():
    """Verify DEV_AGENT_ID is the expected UUID."""
    assert DEV_AGENT_ID == UUID("00000000-0000-0000-0000-000000000001")
