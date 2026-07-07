"""
Unit tests for T-002: User Registration endpoint (US-001).

Tests cover:
- Successful registration returns 201 with user_id, email, message
- Duplicate email returns 409
- Weak password returns 422
- Invalid email returns 422
- Service-layer: register creates user record with hashed password
- Service-layer: register raises ConflictError on duplicate email
- Security: hash_password/verify_password round-trip
- Security: create_refresh_token returns (token_str, jti, expires_at)
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

from app.core.database import Base
from app.core.exceptions import ConflictError, ValidationError
from app.core.security import hash_password, verify_password, create_refresh_token
from app.domains.account.models import User, RefreshToken
from app.domains.auth.schemas import RegisterRequest, RegisterResponse
from app.domains.auth.service import AuthService

# Import all models so SQLAlchemy mapper can resolve string references in relationships
import app.domains.products.models  # noqa: F401
import app.domains.cart.models  # noqa: F401
import app.domains.checkout.models  # noqa: F401
import app.domains.categories.models  # noqa: F401


# ─── In-process SQLite DB fixture ─────────────────────────────────────────────

@pytest_asyncio.fixture()
async def db_session():
    """Ephemeral in-process SQLite database; tables created and dropped per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ─── Security helpers unit tests ──────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        plain = "S3cur3P@ss!"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_verify_correct_password_returns_true(self):
        plain = "S3cur3P@ss!"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password_returns_false(self):
        hashed = hash_password("correct_password_123")
        assert verify_password("wrong_password_123", hashed) is False

    def test_two_hashes_of_same_password_differ(self):
        """Bcrypt uses a salt — same plain text must not produce same hash."""
        plain = "SamePassword99!"
        h1 = hash_password(plain)
        h2 = hash_password(plain)
        assert h1 != h2


class TestCreateRefreshToken:
    def test_returns_tuple_of_three(self):
        result = create_refresh_token("user-123")
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_token_is_string(self):
        token_str, jti, expires_at = create_refresh_token("user-123")
        assert isinstance(token_str, str)
        assert len(token_str) > 0

    def test_jti_is_unique_per_call(self):
        _, jti1, _ = create_refresh_token("user-123")
        _, jti2, _ = create_refresh_token("user-123")
        assert jti1 != jti2

    def test_tokens_differ_per_call(self):
        t1, _, _ = create_refresh_token("user-123")
        t2, _, _ = create_refresh_token("user-123")
        assert t1 != t2


# ─── Service-layer unit tests ──────────────────────────────────────────────────

class TestAuthServiceRegister:
    @pytest.mark.asyncio
    async def test_register_creates_user(self, db_session: AsyncSession):
        service = AuthService(db_session)
        payload = RegisterRequest(email="newuser@example.com", password="Str0ngP@ss!")
        response = await service.register(payload)

        assert isinstance(response, RegisterResponse)
        assert response.email == "newuser@example.com"
        assert response.user_id is not None
        assert "successful" in response.message.lower() or "registration" in response.message.lower()

    @pytest.mark.asyncio
    async def test_register_stores_hashed_password(self, db_session: AsyncSession):
        service = AuthService(db_session)
        payload = RegisterRequest(email="hashed@example.com", password="MyPassword123!")
        response = await service.register(payload)

        result = await db_session.execute(
            select(User).where(User.id == uuid.UUID(response.user_id))
        )
        user = result.scalars().first()
        assert user is not None
        assert user.hashed_password != "MyPassword123!"
        assert verify_password("MyPassword123!", user.hashed_password) is True

    @pytest.mark.asyncio
    async def test_register_creates_refresh_token_record(self, db_session: AsyncSession):
        service = AuthService(db_session)
        payload = RegisterRequest(email="withtoken@example.com", password="Str0ngP@ss!")
        response = await service.register(payload)

        result = await db_session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == uuid.UUID(response.user_id)
            )
        )
        token_record = result.scalars().first()
        assert token_record is not None
        assert token_record.is_revoked is False

    @pytest.mark.asyncio
    async def test_register_duplicate_email_raises_conflict(self, db_session: AsyncSession):
        service = AuthService(db_session)
        payload = RegisterRequest(email="duplicate@example.com", password="Str0ngP@ss!")
        await service.register(payload)

        with pytest.raises(ConflictError):
            await service.register(payload)

    @pytest.mark.asyncio
    async def test_register_weak_password_raises_validation_error(self, db_session: AsyncSession):
        """Password shorter than 8 chars should raise ValidationError at service layer."""
        service = AuthService(db_session)
        # Bypass pydantic min_length by constructing manually
        payload = RegisterRequest.model_construct(
            email="weak@example.com",
            password="short",
            full_name=None,
        )
        with pytest.raises(ValidationError):
            await service.register(payload)


# ─── API endpoint integration tests (in-process TestClient) ──────────────────

@pytest.fixture()
def client(db_session: AsyncSession):
    """FastAPI TestClient wired to the in-memory SQLite session."""
    import asyncio
    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.deps import get_db

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


class TestRegisterEndpoint:
    def test_register_returns_201_on_success(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "alice@example.com", "password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 201

    def test_register_response_body_shape(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "bob@example.com", "password": "Str0ngP@ss!"},
        )
        data = resp.json()
        assert "user_id" in data
        assert "email" in data
        assert "message" in data
        assert data["email"] == "bob@example.com"

    def test_register_duplicate_email_returns_409(self, client):
        payload = {"email": "charlie@example.com", "password": "Str0ngP@ss!"}
        client.post("/api/v1/auth/register", json=payload)
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409

    def test_register_invalid_email_returns_422(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 422

    def test_register_password_too_short_returns_422(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "short@example.com", "password": "ab"},
        )
        assert resp.status_code == 422

    def test_register_missing_fields_returns_422(self, client):
        resp = client.post("/api/v1/auth/register", json={"email": "nopass@example.com"})
        assert resp.status_code == 422

    def test_register_with_full_name_succeeds(self, client):
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "fullname@example.com",
                "password": "Str0ngP@ss!",
                "full_name": "Jane Doe",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "fullname@example.com"
