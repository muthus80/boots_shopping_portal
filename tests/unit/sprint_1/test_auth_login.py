"""
Unit tests for T-004: User Login endpoint (US-002).

Tests cover:
- Successful login returns 200 with access_token, refresh_token, token_type, expires_in
- Invalid password returns 401
- Unknown email returns 401
- Missing fields return 422
- Invalid email format returns 422
- Service-layer: login returns TokenResponse on correct credentials
- Service-layer: login raises UnauthorizedError on wrong password
- Service-layer: login raises UnauthorizedError for unknown user
- Token rotation: refresh_tokens returns new access token
- Logout: marks refresh token as revoked
- Refresh: invalid token returns None
- Refresh: revoked token returns None
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

# Import all domain models so SQLAlchemy mapper resolves relationship string refs
import app.domains.products.models  # noqa: F401
import app.domains.cart.models  # noqa: F401
import app.domains.checkout.models  # noqa: F401
import app.domains.categories.models  # noqa: F401

from app.core.database import Base
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.domains.account.models import RefreshToken, User
from app.domains.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.domains.auth.service import AuthService


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


@pytest_asyncio.fixture()
async def registered_user(db_session: AsyncSession):
    """Pre-registers a user and returns (service, email, password)."""
    service = AuthService(db_session)
    email = f"logintest_{uuid.uuid4().hex[:8]}@example.com"
    password = "Str0ngP@ss!"
    await service.register(RegisterRequest(email=email, password=password))
    return service, email, password


# ─── TestClient fixture ───────────────────────────────────────────────────────


@pytest.fixture()
def client(db_session: AsyncSession):
    """FastAPI TestClient wired to the in-memory SQLite session."""
    from app.main import app
    from app.core.deps import get_db

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_client(db_session: AsyncSession):
    """TestClient with a pre-registered user; returns (client, email, password)."""
    import asyncio
    from app.main import app
    from app.core.deps import get_db

    # Register the user synchronously using the existing session
    email = f"client_{uuid.uuid4().hex[:8]}@example.com"
    password = "Str0ngP@ss!"

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app, raise_server_exceptions=False) as c:
        # Register via the endpoint so the session state is consistent
        resp = c.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )
        assert resp.status_code == 201, f"Pre-registration failed: {resp.text}"
        yield c, email, password

    app.dependency_overrides.clear()


# ─── Security helper unit tests ───────────────────────────────────────────────


class TestCreateAccessToken:
    def test_returns_non_empty_string(self):
        token = create_access_token("user-123")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_returns_correct_subject(self):
        token = create_access_token("user-abc")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-abc"

    def test_token_type_is_access(self):
        token = create_access_token("user-xyz")
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("type") == "access"

    def test_extra_claims_are_included(self):
        token = create_access_token("user-99", extra_claims={"role": "admin"})
        payload = decode_token(token)
        assert payload is not None
        assert payload.get("role") == "admin"

    def test_expired_token_returns_none(self):
        """A token with a past expiry should not decode."""
        from jose import jwt
        from app.core.config import settings

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": "user-expired",
            "iat": past,
            "exp": past,
            "type": "access",
        }
        expired_token = jwt.encode(
            payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )
        assert decode_token(expired_token) is None


# ─── Service-layer unit tests ──────────────────────────────────────────────────


class TestAuthServiceLogin:
    @pytest.mark.asyncio
    async def test_login_returns_token_response(self, registered_user):
        service, email, password = registered_user
        result = await service.login(LoginRequest(email=email, password=password))

        assert isinstance(result, TokenResponse)
        assert result.token_type == "bearer"
        assert isinstance(result.access_token, str)
        assert len(result.access_token) > 0
        assert isinstance(result.refresh_token, str)
        assert len(result.refresh_token) > 0

    @pytest.mark.asyncio
    async def test_login_access_token_is_valid_jwt(self, registered_user):
        service, email, password = registered_user
        result = await service.login(LoginRequest(email=email, password=password))

        payload = decode_token(result.access_token)
        assert payload is not None
        assert payload.get("type") == "access"

    @pytest.mark.asyncio
    async def test_login_access_token_subject_is_user_id(self, registered_user):
        service, email, password = registered_user
        result = await service.login(LoginRequest(email=email, password=password))

        payload = decode_token(result.access_token)
        assert payload is not None
        # subject should be a valid UUID
        assert uuid.UUID(payload["sub"])

    @pytest.mark.asyncio
    async def test_login_persists_refresh_token_record(
        self, registered_user, db_session: AsyncSession
    ):
        service, email, password = registered_user
        result = await service.login(LoginRequest(email=email, password=password))

        db_result = await db_session.execute(
            select(RefreshToken).where(
                RefreshToken.token == result.refresh_token,
                RefreshToken.is_revoked == False,  # noqa: E712
            )
        )
        record = db_result.scalars().first()
        assert record is not None, "Refresh token record should be stored in DB"
        assert record.is_revoked is False

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises_unauthorized(self, registered_user):
        service, email, _ = registered_user
        with pytest.raises(UnauthorizedError):
            await service.login(LoginRequest(email=email, password="WrongPass999!"))

    @pytest.mark.asyncio
    async def test_login_unknown_email_raises_unauthorized(self, db_session: AsyncSession):
        service = AuthService(db_session)
        with pytest.raises(UnauthorizedError):
            await service.login(
                LoginRequest(email="nobody@example.com", password="Str0ngP@ss!")
            )

    @pytest.mark.asyncio
    async def test_login_expires_in_is_positive(self, registered_user):
        service, email, password = registered_user
        result = await service.login(LoginRequest(email=email, password=password))
        assert result.expires_in > 0

    @pytest.mark.asyncio
    async def test_login_multiple_times_creates_multiple_refresh_tokens(
        self, registered_user, db_session: AsyncSession
    ):
        service, email, password = registered_user
        r1 = await service.login(LoginRequest(email=email, password=password))
        r2 = await service.login(LoginRequest(email=email, password=password))

        assert r1.refresh_token != r2.refresh_token


# ─── Service-layer: Token Rotation (refresh_tokens) ──────────────────────────


class TestAuthServiceRefreshTokens:
    @pytest.mark.asyncio
    async def test_refresh_returns_new_access_token(self, registered_user):
        service, email, password = registered_user
        login_result = await service.login(LoginRequest(email=email, password=password))
        refresh_result = await service.refresh_tokens(login_result.refresh_token)

        assert refresh_result is not None
        assert isinstance(refresh_result.access_token, str)
        assert len(refresh_result.access_token) > 0

    @pytest.mark.asyncio
    async def test_refresh_rotates_refresh_token(self, registered_user):
        service, email, password = registered_user
        login_result = await service.login(LoginRequest(email=email, password=password))
        refresh_result = await service.refresh_tokens(login_result.refresh_token)

        assert refresh_result is not None
        assert refresh_result.refresh_token != login_result.refresh_token

    @pytest.mark.asyncio
    async def test_refresh_revokes_old_token(
        self, registered_user, db_session: AsyncSession
    ):
        service, email, password = registered_user
        login_result = await service.login(LoginRequest(email=email, password=password))
        old_token = login_result.refresh_token

        await service.refresh_tokens(old_token)

        db_result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.token == old_token)
        )
        record = db_result.scalars().first()
        assert record is not None
        assert record.is_revoked is True

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token_returns_none(
        self, db_session: AsyncSession
    ):
        service = AuthService(db_session)
        result = await service.refresh_tokens("not-a-valid-token")
        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_returns_none(self, registered_user):
        """Access tokens must not be accepted as refresh tokens."""
        service, email, password = registered_user
        login_result = await service.login(LoginRequest(email=email, password=password))
        # Access token has type="access", not "refresh"
        result = await service.refresh_tokens(login_result.access_token)
        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_with_revoked_token_returns_none(self, registered_user):
        service, email, password = registered_user
        login_result = await service.login(LoginRequest(email=email, password=password))
        refresh_token = login_result.refresh_token

        # Revoke by logging out
        await service.logout(refresh_token)

        result = await service.refresh_tokens(refresh_token)
        assert result is None


# ─── Service-layer: Logout ─────────────────────────────────────────────────────


class TestAuthServiceLogout:
    @pytest.mark.asyncio
    async def test_logout_revokes_refresh_token(
        self, registered_user, db_session: AsyncSession
    ):
        service, email, password = registered_user
        login_result = await service.login(LoginRequest(email=email, password=password))
        token_str = login_result.refresh_token

        await service.logout(token_str)

        db_result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.token == token_str)
        )
        record = db_result.scalars().first()
        assert record is not None
        assert record.is_revoked is True

    @pytest.mark.asyncio
    async def test_logout_unknown_token_does_not_raise(self, db_session: AsyncSession):
        """Logging out with an unknown token should be a no-op, not an error."""
        service = AuthService(db_session)
        # Should not raise any exception
        await service.logout("completely-unknown-token")

    @pytest.mark.asyncio
    async def test_logout_idempotent(self, registered_user):
        """Calling logout twice with same token should not raise."""
        service, email, password = registered_user
        login_result = await service.login(LoginRequest(email=email, password=password))
        token_str = login_result.refresh_token

        await service.logout(token_str)
        # Second logout should be a no-op
        await service.logout(token_str)


# ─── API endpoint integration tests (in-process TestClient) ──────────────────


class TestLoginEndpoint:
    def test_login_returns_200_on_success(self, registered_client):
        client, email, password = registered_client
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_login_response_body_shape(self, registered_client):
        client, email, password = registered_client
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

    def test_login_wrong_password_returns_401(self, registered_client):
        client, email, _ = registered_client
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword!"},
        )
        assert resp.status_code == 401

    def test_login_unknown_email_returns_401(self, registered_client):
        client, _, _ = registered_client
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@unknown.com", "password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 401

    def test_login_missing_password_returns_422(self, registered_client):
        client, email, _ = registered_client
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email},
        )
        assert resp.status_code == 422

    def test_login_missing_email_returns_422(self, registered_client):
        client, _, _ = registered_client
        resp = client.post(
            "/api/v1/auth/login",
            json={"password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 422

    def test_login_invalid_email_format_returns_422(self, registered_client):
        client, _, _ = registered_client
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 422

    def test_login_empty_body_returns_422(self, registered_client):
        client, _, _ = registered_client
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422

    def test_login_access_token_is_valid_jwt(self, registered_client):
        client, email, password = registered_client
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        data = resp.json()
        payload = decode_token(data["access_token"])
        assert payload is not None
        assert payload.get("type") == "access"

    def test_login_returns_unique_refresh_tokens_each_call(self, registered_client):
        """Each login must produce a unique refresh token (guaranteed by JTI)."""
        client, email, password = registered_client
        creds = {"email": email, "password": password}
        r1 = client.post("/api/v1/auth/login", json=creds)
        r2 = client.post("/api/v1/auth/login", json=creds)
        assert r1.json()["refresh_token"] != r2.json()["refresh_token"]


class TestRefreshEndpoint:
    def test_refresh_returns_200_with_new_access_token(self, registered_client):
        client, email, password = registered_client
        login_resp = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        refresh_token = login_resp.json()["refresh_token"]

        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_refresh_with_invalid_token_returns_401(self, registered_client):
        client, _, _ = registered_client
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not-a-valid-token"},
        )
        assert resp.status_code == 401

    def test_refresh_token_rotation_issues_new_refresh_token(self, registered_client):
        client, email, password = registered_client
        login_resp = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        old_refresh = login_resp.json()["refresh_token"]

        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert refresh_resp.status_code == 200
        new_refresh = refresh_resp.json().get("refresh_token")
        if new_refresh:
            assert new_refresh != old_refresh


class TestLogoutEndpoint:
    def test_logout_returns_200(self, registered_client):
        client, email, password = registered_client
        login_resp = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        access_token = login_resp.json()["access_token"]
        refresh_token = login_resp.json()["refresh_token"]

        resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data

    def test_logout_without_auth_returns_401(self, registered_client):
        client, email, password = registered_client
        login_resp = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        refresh_token = login_resp.json()["refresh_token"]

        # No Authorization header
        resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 401

    def test_logout_invalidates_refresh_token(self, registered_client):
        """After logout, using the refresh token should return 401."""
        client, email, password = registered_client
        login_resp = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        access_token = login_resp.json()["access_token"]
        refresh_token = login_resp.json()["refresh_token"]

        # Logout
        client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Attempt to use the revoked refresh token
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 401
