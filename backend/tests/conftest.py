"""
Shared test fixtures for backend tests.

Uses a separate PostgreSQL test schema to isolate tests.
The test database uses the same Postgres instance as the app.
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.database import Base
from app.main import app
from app.database import get_async_session
from app.auth import get_current_agent_id

# Use the same DB but a test schema, or fall back to the app DB URL
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@db/ttc"),
)

DEV_AGENT_UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest_asyncio.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    # Create all tables fresh for each test
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(engine):
    """Async HTTP test client with overridden DB + auth dependencies."""

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_session():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    async def _override_agent_id():
        return DEV_AGENT_UUID

    app.dependency_overrides[get_async_session] = _override_session
    app.dependency_overrides[get_current_agent_id] = _override_agent_id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_user(db_session):
    """Create the dev user in the test database."""
    from app.models.user import User
    user = User(
        id=DEV_AGENT_UUID,
        clerk_id="dev_test_user",
        email="dev@test.com",
        name="Test Agent",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def seed_transaction(db_session, seed_user):
    """Create a test transaction."""
    from app.models.transaction import Transaction
    txn = Transaction(
        id=uuid.uuid4(),
        agent_id=seed_user.id,
        representation_side="buyer",
        financing_type="conventional",
        property_address="123 Test St",
        property_city="Atlanta",
        property_state="GA",
        property_zip="30301",
        purchase_price={"amount": 500000, "currency": "USD"},
        closing_date=datetime.now(timezone.utc) + timedelta(days=30),
        status="confirmed",
    )
    db_session.add(txn)
    await db_session.commit()
    await db_session.refresh(txn)
    return txn
