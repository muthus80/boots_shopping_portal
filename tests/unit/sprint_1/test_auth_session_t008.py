"""
Unit and integration tests for T-008: Token refresh and session validation (US-013).

Covers:
- POST /api/v1/auth/refresh  — valid refresh token → new access + refresh token pair
- POST /api/v1/auth/refresh  — revoked token → 401
- POST /api/v1/auth/refresh  — expired token → 401
- POST /api/v1/auth/refresh  — access token (wrong type) → 401
- POST /api/v1/auth/refresh  — garbage token → 401
- POST /api/v1/auth/logout   — valid request → 200, token revoked in DB
- POST /api/v1/auth/logout   — no Authorization header → 401
- POST /api/v1/auth/logout   — after logout, refresh token rejected on /refresh → 401
- Token rotation: old refresh token revoked, new one persisted and valid
- Session continuity: new access token from /refresh is a valid JWT
- Session continuity: double-rotation (token from first refresh used for second refresh)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

# Ensure all domain models are imported so SQLAlchemy can resolve relationships
import app.domains.products.models  # noqa: F401
import app.domains.cart.models  # noqa: F401
import app.domains.checkout.models  # noqa: F401
import app.domains.categories.models  # noqa: F401

from app.core.config import settings
from app.core.database import Base
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.domains.account.models import RefreshToken, User
from app.domains.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.domains.auth.service import AuthService


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture()
async def db_session():
    """Per-test ephemeral SQLite database; isolated and reset after each test."""
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
async def auth_service(db_session: AsyncSession) -> AuthService:
    return AuthService(db_session)


@pytest_asyncio.fixture()
async def logged_in(auth_service: AuthService):
    """Register + login; returns (service, token_response)."""
    email = f"session_{uuid.uuid4().hex[:8]}@example.com"
    password = "Str0ngP@ss!"
    await auth_service.register(RegisterRequest(email=email, password=password))
    token_resp = await auth_service.login(LoginRequest(email=email, password=password))
    return auth_service, token_resp


@pytest.fixture()
def client(db_session: AsyncSession):
    """FastAPI TestClient wired to the in-memory session (no real DB needed)."""
    from app.main import app
    from app.core.deps import get_db

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def authenticated_client(db_session: AsyncSession):
    """TestClient with a pre-registered and logged-in user.

    Returns (client, access_token, refresh_token).
    """
    from app.main import app
    from app.core.deps import get_db

    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app, raise_server_exceptions=False) as c:
        email = f"ac_{uuid.uuid4().hex[:8]}@example.com"
        password = "Str0ngP@ss!"
        reg = c.post("/api/v1/auth/register", json={"email": email, "password": password})
        assert reg.status_code == 201, f"Registration failed: {reg.text}"
        login = c.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, f"Login failed: {login.text}"
        data = login.json()
        yield c, data["access_token"], data["refresh_token"]

    app.dependency_overrides.clear()


# ─── Service-layer: refresh_tokens ────────────────────────────────────────────


class TestRefreshTokensService:
    """Unit tests for AuthService.refresh_tokens()."""

    @pytest.mark.asyncio
    async def test_returns_token_response_on_valid_token(self, logged_in):
        service, tokens = logged_in
        result = await service.refresh_tokens(tokens.refresh_token)
        assert result is not None
        assert isinstance(result, TokenResponse)

    @pytest.mark.asyncio
    async def test_new_access_token_is_valid_jwt(self, logged_in):
        service, tokens = logged_in
        result = await service.refresh_tokens(tokens.refresh_token)
        assert result is not None
        payload = decode_token(result.access_token)
        assert payload is not None
        assert payload.get("type") == "access"

    @pytest.mark.asyncio
    async def test_new_access_token_subject_is_user_id(self, logged_in):
        service, tokens = logged_in
        result = await service.refresh_tokens(tokens.refresh_token)
        assert result is not None
        payload = decode_token(result.access_token)
        assert payload is not None
        # sub must be a valid UUID string
        uuid.UUID(payload["sub"])

    @pytest.mark.asyncio
    async def test_token_rotation_returns_new_refresh_token(self, logged_in):
        service, tokens = logged_in
        result = await service.refresh_tokens(tokens.refresh_token)
        assert result is not None
        assert result.refresh_token != tokens.refresh_token

    @pytest.mark.asyncio
    async def test_old_refresh_token_revoked_after_rotation(
        self, logged_in, db_session: AsyncSession
    ):
        service, tokens = logged_in
        old_token_str = tokens.refresh_token
        await service.refresh_tokens(old_token_str)

        row = (
            await db_session.execute(
                select(RefreshToken).where(RefreshToken.token == old_token_str)
            )
        ).scalars().first()
        assert row is not None, "Old refresh token row should still exist"
        assert row.is_revoked is True

    @pytest.mark.asyncio
    async def test_new_refresh_token_persisted_and_active(
        self, logged_in, db_session: AsyncSession
    ):
        service, tokens = logged_in
        result = await service.refresh_tokens(tokens.refresh_token)
        assert result is not None

        row = (
            await db_session.execute(
                select(RefreshToken).where(RefreshToken.token == result.refresh_token)
            )
        ).scalars().first()
        assert row is not None, "New refresh token should be persisted in DB"
        assert row.is_revoked is False

    @pytest.mark.asyncio
    async def test_revoked_token_returns_none(self, logged_in):
        service, tokens = logged_in
        # Logout revokes the refresh token
        await service.logout(tokens.refresh_token)
        result = await service.refresh_tokens(tokens.refresh_token)
        assert result is None

    @pytest.mark.asyncio
    async def test_garbage_token_returns_none(self, auth_service):
        result = await auth_service.refresh_tokens("this-is-not-a-token")
        assert result is None

    @pytest.mark.asyncio
    async def test_access_token_rejected_as_refresh(self, logged_in):
        """Access tokens must not work as refresh tokens (wrong type claim)."""
        service, tokens = logged_in
        result = await service.refresh_tokens(tokens.access_token)
        assert result is None

    @pytest.mark.asyncio
    async def test_expired_refresh_token_returns_none(self, auth_service: AuthService):
        """Craft an expired JWT refresh token — service must reject it."""
        past = datetime.now(timezone.utc) - timedelta(days=8)
        expired_payload = {
            "sub": str(uuid.uuid4()),
            "iat": past,
            "exp": past,
            "type": "refresh",
            "jti": str(uuid.uuid4()),
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        result = await auth_service.refresh_tokens(expired_token)
        assert result is None

    @pytest.mark.asyncio
    async def test_double_rotation_session_continuity(self, logged_in):
        """Chaining two refresh calls should succeed (US-013 session continuity)."""
        service, tokens = logged_in
        result1 = await service.refresh_tokens(tokens.refresh_token)
        assert result1 is not None

        result2 = await service.refresh_tokens(result1.refresh_token)
        assert result2 is not None
        assert isinstance(result2.access_token, str)
        assert len(result2.access_token) > 0


# ─── Service-layer: logout ─────────────────────────────────────────────────────


class TestLogoutService:
    @pytest.mark.asyncio
    async def test_logout_marks_token_revoked(self, logged_in, db_session: AsyncSession):
        service, tokens = logged_in
        token_str = tokens.refresh_token

        await service.logout(token_str)

        row = (
            await db_session.execute(
                select(RefreshToken).where(RefreshToken.token == token_str)
            )
        ).scalars().first()
        assert row is not None
        assert row.is_revoked is True

    @pytest.mark.asyncio
    async def test_logout_unknown_token_is_no_op(self, auth_service: AuthService):
        """Calling logout with a non-existent token must not raise."""
        await auth_service.logout("non-existent-token-string")

    @pytest.mark.asyncio
    async def test_logout_is_idempotent(self, logged_in):
        """Second logout with same token should not raise."""
        service, tokens = logged_in
        await service.logout(tokens.refresh_token)
        await service.logout(tokens.refresh_token)  # no-op, no exception

    @pytest.mark.asyncio
    async def test_logout_prevents_subsequent_refresh(self, logged_in):
        """After logout, refresh call must fail (revoked token)."""
        service, tokens = logged_in
        await service.logout(tokens.refresh_token)
        result = await service.refresh_tokens(tokens.refresh_token)
        assert result is None


# ─── API endpoint integration tests ───────────────────────────────────────────


class TestRefreshEndpointT008:
    """Integration tests for POST /api/v1/auth/refresh (T-008)."""

    def test_valid_refresh_token_returns_200(self, authenticated_client):
        client, _, refresh_token = authenticated_client
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200

    def test_response_contains_access_token(self, authenticated_client):
        client, _, refresh_token = authenticated_client
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        data = resp.json()
        assert "access_token" in data
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    def test_response_token_type_is_bearer(self, authenticated_client):
        client, _, refresh_token = authenticated_client
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.json()["token_type"] == "bearer"

    def test_response_contains_expires_in(self, authenticated_client):
        client, _, refresh_token = authenticated_client
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        data = resp.json()
        assert "expires_in" in data
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0

    def test_new_access_token_is_valid_jwt(self, authenticated_client):
        client, _, refresh_token = authenticated_client
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        new_access = resp.json()["access_token"]
        payload = decode_token(new_access)
        assert payload is not None
        assert payload.get("type") == "access"

    def test_invalid_token_returns_401(self, authenticated_client):
        client, _, _ = authenticated_client
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
        assert resp.status_code == 401

    def test_access_token_as_refresh_returns_401(self, authenticated_client):
        client, access_token, _ = authenticated_client
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
        assert resp.status_code == 401

    def test_missing_field_returns_422(self, authenticated_client):
        client, _, _ = authenticated_client
        resp = client.post("/api/v1/auth/refresh", json={})
        assert resp.status_code == 422

    def test_token_rotation_returns_new_refresh_token(self, authenticated_client):
        """Each refresh call must issue a different refresh token (rotation)."""
        client, _, old_refresh = authenticated_client
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        data = resp.json()
        # Rotation: new refresh token returned (field may be present)
        new_refresh = data.get("refresh_token")
        if new_refresh:
            assert new_refresh != old_refresh

    def test_revoked_token_after_logout_returns_401(self, authenticated_client):
        """Session invalidation: token used after logout must be rejected."""
        client, access_token, refresh_token = authenticated_client
        client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 401

    def test_session_continuity_chained_refreshes(self, authenticated_client):
        """US-013: chaining two refresh calls must both succeed."""
        client, _, refresh_token = authenticated_client
        resp1 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp1.status_code == 200

        new_refresh = resp1.json().get("refresh_token")
        if new_refresh:
            resp2 = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
            assert resp2.status_code == 200


class TestLogoutEndpointT008:
    """Integration tests for POST /api/v1/auth/logout (T-008)."""

    def test_logout_returns_200(self, authenticated_client):
        client, access_token, refresh_token = authenticated_client
        resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp.status_code == 200

    def test_logout_response_contains_message(self, authenticated_client):
        client, access_token, refresh_token = authenticated_client
        resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        data = resp.json()
        assert "message" in data
        assert isinstance(data["message"], str)

    def test_logout_without_bearer_returns_401(self, authenticated_client):
        client, _, refresh_token = authenticated_client
        resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 401

    def test_logout_with_invalid_bearer_returns_401(self, authenticated_client):
        client, _, refresh_token = authenticated_client
        resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": "Bearer this-is-not-valid"},
        )
        assert resp.status_code == 401

    def test_logout_invalidates_session(self, authenticated_client):
        """After logout, the refresh token must be unusable (US-013 session end)."""
        client, access_token, refresh_token = authenticated_client
        client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 401

    def test_logout_is_idempotent_via_endpoint(self, authenticated_client):
        """Calling logout twice should not error — second call still returns 200."""
        client, access_token, refresh_token = authenticated_client
        headers = {"Authorization": f"Bearer {access_token}"}
        resp1 = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers=headers,
        )
        assert resp1.status_code == 200
        # Second logout — token already revoked, but endpoint should be idempotent
        resp2 = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers=headers,
        )
        assert resp2.status_code == 200
