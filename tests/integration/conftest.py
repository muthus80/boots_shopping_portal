"""Base fixtures for integration tests.

Provides async_client (httpx) and db_session (SQLAlchemy) wired to a
dedicated test database. Sprint-level conftests import from here and
add sprint-specific factories and helpers.
"""
from __future__ import annotations

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.database import Base
from app.core.deps import get_db
from app.main import app

# Separate test database — never touches the dev DB
_TEST_DB_URL = str(settings.DATABASE_URL).rsplit("/", 1)[0] + "/test_boots_shopping_app"


# IMPORTANT: the engine is created PER TEST (function scope), not at
# module level, and there is NO custom event_loop fixture. Under
# pytest-asyncio asyncio_mode=auto every test runs on its own event
# loop; a module-level engine (or a session-scoped event_loop) binds
# to the first loop and then raises "Task got Future attached to a
# different loop" on every subsequent test. A fresh per-test engine
# avoids that entirely.
@pytest_asyncio.fixture()
async def db_session():
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def async_client(db_session: AsyncSession):
    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()
