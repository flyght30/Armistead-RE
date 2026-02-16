"""
Clerk JWT authentication dependency for FastAPI.

Verifies Clerk-issued JWTs and resolves the authenticated user's database ID.
Falls back to a dev agent when CLERK_SECRET_KEY is not configured.
"""
import logging
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.models.user import User
from app.config import Settings

logger = logging.getLogger(__name__)

settings = Settings()

# Dev-mode fallback
DEV_AGENT_ID = UUID("00000000-0000-0000-0000-000000000001")


async def _resolve_user_id(clerk_id: str, db: AsyncSession) -> UUID:
    """Look up the internal user ID from a Clerk user ID. Create if not found."""
    stmt = select(User).where(User.clerk_id == clerk_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user:
        return user.id

    # Auto-provision user on first login
    new_user = User(
        clerk_id=clerk_id,
        email=f"{clerk_id}@placeholder.local",
        name="New User",
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    logger.info("Auto-provisioned user %s for clerk_id=%s", new_user.id, clerk_id)
    return new_user.id


async def get_current_agent_id(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> UUID:
    """
    Extract the authenticated agent's UUID from the request.

    When Clerk is configured (CLERK_SECRET_KEY is set):
      - Validates the Bearer JWT
      - Resolves the Clerk user to a local User row
      - Returns the User.id

    When Clerk is not configured (dev mode):
      - Returns DEV_AGENT_ID so the app works without auth
    """
    if not settings.clerk_secret_key:
        return DEV_AGENT_ID

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header.split(" ", 1)[1]

    try:
        import jwt
        from jwt import PyJWKClient

        # Clerk JWKS endpoint
        jwks_url = f"https://{settings.clerk_frontend_api}/.well-known/jwks.json"
        jwks_client = PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )

        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            raise HTTPException(status_code=401, detail="Token missing sub claim")

        return await _resolve_user_id(clerk_user_id, db)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT: %s", e)
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.exception("Auth error: %s", e)
        raise HTTPException(status_code=401, detail="Authentication failed")
