"""
Self-check script for Sprint 1 — T-002 User Registration (US-001).

Exercises each acceptance criterion against the FastAPI in-process TestClient.
"""
from __future__ import annotations

import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import event

# Must import all models before creating DB so all tables exist
import app.domains.products.models  # noqa: F401
import app.domains.cart.models  # noqa: F401
import app.domains.checkout.models  # noqa: F401
import app.domains.categories.models  # noqa: F401

from app.core.database import Base, get_db
from app.main import app


@pytest.fixture(scope="module")
def test_db():
    """Module-scoped in-memory SQLite database shared across all self-check tests."""
    import asyncio

    async def _setup():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return engine, factory

    loop = asyncio.new_event_loop()
    engine, factory = loop.run_until_complete(_setup())
    loop.close()
    return engine, factory


@pytest.fixture(scope="module")
def client(test_db):
    engine, factory = test_db

    async def _override_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


class TestUS001UserRegistration:
    """US-001 Acceptance Criteria checks."""

    def test_ac1_valid_email_and_password_creates_account(self, client):
        """AC1: Given valid email + strong password → account is created (201)."""
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["email"] == email
        assert "user_id" in data
        assert uuid.UUID(data["user_id"])  # valid UUID

    def test_ac2_registration_returns_confirmation_message(self, client):
        """AC2: After account creation, response contains confirmation message."""
        email = f"user_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 201
        data = resp.json()
        # The message field is present and non-empty
        assert "message" in data
        assert len(data["message"]) > 0

    def test_ac3_duplicate_email_returns_conflict(self, client):
        """AC3: Registering with existing email → error message (409)."""
        email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
        payload = {"email": email, "password": "Str0ngP@ss!"}

        # First registration
        r1 = client.post("/api/v1/auth/register", json=payload)
        assert r1.status_code == 201

        # Second registration with same email
        r2 = client.post("/api/v1/auth/register", json=payload)
        assert r2.status_code == 409, f"Expected 409 on duplicate, got {r2.status_code}"
        data = r2.json()
        assert "detail" in data

    def test_ac_password_complexity_validation(self, client):
        """Password shorter than 8 chars is rejected before creating account (422)."""
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "pw@example.com", "password": "short"},
        )
        assert resp.status_code == 422

    def test_ac_missing_password_rejected(self, client):
        """Missing password field → 422 validation error."""
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "nopass@example.com"},
        )
        assert resp.status_code == 422

    def test_ac_invalid_email_rejected(self, client):
        """Invalid email format → 422 validation error."""
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "not-valid-email", "password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 422

    def test_ac_optional_full_name_field(self, client):
        """full_name is optional — omitting it still creates the account."""
        email = f"nofullname_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 201

    def test_ac_full_name_accepted_when_provided(self, client):
        """full_name can be provided and account is still created."""
        email = f"fullname_{uuid.uuid4().hex[:8]}@example.com"
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Str0ngP@ss!", "full_name": "John Doe"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == email
