"""
Self-check for T-004: User Login (US-002).

Exercises each acceptance criterion for US-002 against the FastAPI in-process TestClient.

US-002 Acceptance Criteria:
  AC1: Given correct credentials → successfully logged in (200) with JWT tokens
  AC2: Given incorrect credentials → error message (401), remain on login page
"""
from __future__ import annotations

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Must import all models before creating DB so all tables exist
import app.domains.products.models  # noqa: F401
import app.domains.cart.models  # noqa: F401
import app.domains.checkout.models  # noqa: F401
import app.domains.categories.models  # noqa: F401

from app.core.database import Base, get_db
from app.core.security import decode_token
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


@pytest.fixture(scope="module")
def registered_user(client):
    """Pre-register one user for login tests."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "Str0ngP@ss!"
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert r.status_code == 201, f"Pre-registration failed: {r.text}"
    return email, password


class TestUS002UserLogin:
    """US-002 Acceptance Criteria checks for T-004."""

    def test_ac1_correct_credentials_returns_200(self, client, registered_user):
        """AC1: Correct credentials → 200 OK."""
        email, password = registered_user
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    def test_ac1_response_contains_jwt_tokens(self, client, registered_user):
        """AC1: Response body contains access_token, refresh_token, token_type, expires_in."""
        email, password = registered_user
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        data = resp.json()
        assert "access_token" in data, "Missing access_token"
        assert "refresh_token" in data, "Missing refresh_token"
        assert data["token_type"] == "bearer", f"Expected bearer, got {data.get('token_type')}"
        assert isinstance(data["expires_in"], int) and data["expires_in"] > 0

    def test_ac1_access_token_is_valid_jwt(self, client, registered_user):
        """AC1: Access token decodes as valid JWT with correct sub claim."""
        email, password = registered_user
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        access_token = resp.json()["access_token"]
        payload = decode_token(access_token)
        assert payload is not None, "Access token failed to decode"
        assert payload.get("type") == "access"
        assert uuid.UUID(payload["sub"])  # sub is a valid UUID

    def test_ac1_refresh_token_is_non_empty_string(self, client, registered_user):
        """AC1: Refresh token is a non-empty string."""
        email, password = registered_user
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        rt = resp.json()["refresh_token"]
        assert isinstance(rt, str) and len(rt) > 0

    def test_ac2_wrong_password_returns_401(self, client, registered_user):
        """AC2: Wrong password → 401 Unauthorized."""
        email, _ = registered_user
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword999!"},
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "detail" in data, "Error response must contain 'detail'"

    def test_ac2_unknown_email_returns_401(self, client, registered_user):
        """AC2: Unknown email → 401 Unauthorized."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@notregistered.com", "password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "detail" in data

    def test_ac2_error_does_not_reveal_user_existence(self, client, registered_user):
        """AC2: Error message for wrong-password same as for unknown-user (no user enumeration)."""
        email, _ = registered_user
        r_wrong_pw = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPW!"},
        )
        r_unknown = client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@ghost.com", "password": "WrongPW!"},
        )
        assert r_wrong_pw.status_code == 401
        assert r_unknown.status_code == 401
        # Both should have identical error messages (constant-time-safe behaviour)
        assert r_wrong_pw.json()["detail"] == r_unknown.json()["detail"]

    def test_ac_missing_credentials_returns_422(self, client):
        """Missing required fields → 422 validation error."""
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422

    def test_ac_invalid_email_format_returns_422(self, client):
        """Invalid email format → 422 validation error."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": "Str0ngP@ss!"},
        )
        assert resp.status_code == 422


class TestUS013SessionContinuity:
    """US-013: Session continuity checks (refresh + logout)."""

    def test_refresh_with_valid_token_issues_new_access_token(self, client, registered_user):
        """AC: After login, refresh token can be used to get a new access token."""
        email, password = registered_user
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        refresh_token = login_resp.json()["refresh_token"]

        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_with_invalid_token_returns_401(self, client):
        """AC: Invalid refresh token → 401."""
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "this-is-not-valid"},
        )
        assert resp.status_code == 401

    def test_logout_revokes_session(self, client, registered_user):
        """AC: After logout, the revoked refresh token is rejected."""
        email, password = registered_user
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        access_token = login_resp.json()["access_token"]
        refresh_token = login_resp.json()["refresh_token"]

        # Logout
        logout_resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_resp.status_code == 200
        assert "message" in logout_resp.json()

        # Now the refresh token should be revoked
        refresh_resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 401, (
            f"Revoked token should return 401, got {refresh_resp.status_code}"
        )

    def test_logout_without_auth_header_returns_401(self, client, registered_user):
        """AC: Logout requires a valid access token (401 if not authenticated)."""
        email, password = registered_user
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        refresh_token = login_resp.json()["refresh_token"]

        resp = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            # No Authorization header
        )
        assert resp.status_code == 401
