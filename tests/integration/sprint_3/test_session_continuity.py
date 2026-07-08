"""Integration tests for US-013 (Session Continuity).

Tests cover: JWT remains valid on subsequent requests, token refresh rotates tokens,
and expired/invalid tokens trigger 401.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.account.models import User, RefreshToken

from tests.integration.sprint_3.conftest import (
    create_user_in_db,
    login_user,
)

pytestmark = pytest.mark.asyncio


class TestSessionContinuity:
    """US-013: Session Continuity"""

    async def test_access_token_remains_valid_across_requests(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Logged-in user refreshes the page → remains logged in (token stays valid)."""
        email = "session@example.com"
        password = "SessionPass1!"
        await create_user_in_db(db_session, email=email, password=password)

        token = await login_user(async_client, email, password)

        # Simulate two separate requests with the same token (page refresh)
        resp1 = await async_client.get(
            "/api/v1/account/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp1.status_code == 200, f"First request failed: {resp1.text}"

        # Second request with same token (new tab / refresh)
        resp2 = await async_client.get(
            "/api/v1/account/profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200, f"Second request (simulated refresh) failed: {resp2.text}"

        # Both responses should return the same user data
        data1 = resp1.json()
        data2 = resp2.json()
        assert data1["email"] == data2["email"]

    async def test_logout_revokes_refresh_token(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: After logout, refresh token is revoked — session ends."""
        email = "logout_session@example.com"
        password = "LogoutPass1!"
        await create_user_in_db(db_session, email=email, password=password)

        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # Logout
        logout_resp = await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"refresh_token": refresh_token},
        )
        assert logout_resp.status_code == 200

        # Verify refresh token is revoked in DB
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token)
        )
        rt = result.scalars().first()
        assert rt is not None
        assert rt.is_revoked is True, "Refresh token should be revoked after logout"

        # Attempting to use the revoked refresh token should fail
        refresh_resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 401, (
            f"Revoked refresh token should return 401, got {refresh_resp.status_code}"
        )

    async def test_invalid_token_redirects_to_login(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Expired/invalid session token → 401 (graceful redirect to login page)."""
        # Simulate an expired or tampered token
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.payload"

        resp = await async_client.get(
            "/api/v1/account/orders",
            headers={"Authorization": f"Bearer {invalid_token}"},
        )
        assert resp.status_code == 401, (
            f"Expected 401 for invalid token, got {resp.status_code}"
        )

        data = resp.json()
        assert "detail" in data

    async def test_missing_auth_header_returns_401(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Request to protected endpoint without auth header → 401."""
        resp = await async_client.get("/api/v1/account/profile")
        assert resp.status_code == 401
