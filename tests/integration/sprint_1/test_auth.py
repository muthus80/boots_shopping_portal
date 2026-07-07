"""Integration tests for US-001 (Registration) and US-002 (Login).

Each test method covers one caller path and asserts DB state, not just HTTP codes.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.account.models import User, RefreshToken
from tests.integration.sprint_1.conftest import create_user_in_db


pytestmark = pytest.mark.asyncio


class TestUserRegistration:
    """US-001 – User Registration"""

    async def test_user_registers_with_valid_credentials(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Valid email + strong password → 201, user persisted in DB, confirmation message."""
        payload = {
            "email": "new_user@example.com",
            "password": "StrongPass1!",
            "full_name": "Jane Doe",
        }
        response = await async_client.post("/api/v1/auth/register", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == payload["email"]
        assert "user_id" in data
        # AC: confirmation message present
        assert "confirmation" in data["message"].lower() or "registration" in data["message"].lower()

        # Assert DB state — user row was created
        result = await db_session.execute(
            select(User).where(User.email == payload["email"])
        )
        user = result.scalars().first()
        assert user is not None
        assert user.is_active is True
        # Password must be hashed (not stored as plaintext)
        assert user.hashed_password != payload["password"]

    async def test_user_registers_minimum_password_length(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Password exactly 8 chars (minimum) is accepted."""
        payload = {
            "email": "min_pass@example.com",
            "password": "Abcdef1!",  # exactly 8 chars with upper, lower, digit
        }
        response = await async_client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201

        result = await db_session.execute(
            select(User).where(User.email == payload["email"])
        )
        assert result.scalars().first() is not None

    async def test_register_duplicate_email_returns_409(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Registering with an existing email returns 409 and an error message. (AC: error shown)"""
        payload = {
            "email": "duplicate@example.com",
            "password": "StrongPass1!",
        }
        # First registration succeeds
        first = await async_client.post("/api/v1/auth/register", json=payload)
        assert first.status_code == 201

        # Second registration with same email should fail
        second = await async_client.post("/api/v1/auth/register", json=payload)
        assert second.status_code == 409
        detail = second.json()["detail"]
        # AC: error message indicates duplicate email
        assert "email" in detail.lower() or "already" in detail.lower()

    async def test_register_weak_password_rejected(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Password shorter than 8 chars returns 422 (validation error)."""
        payload = {
            "email": "weakpass@example.com",
            "password": "short",
        }
        response = await async_client.post("/api/v1/auth/register", json=payload)
        # Pydantic min_length=8 returns 422
        assert response.status_code == 422

        # No user created
        result = await db_session.execute(
            select(User).where(User.email == payload["email"])
        )
        assert result.scalars().first() is None


class TestUserLogin:
    """US-002 – User Login"""

    async def test_user_logs_in_with_correct_credentials(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Valid credentials → 200, access + refresh tokens issued, refresh token persisted in DB."""
        user, password = await create_user_in_db(db_session, email="logintest@example.com")
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": password},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # AC: DB has a refresh token row for this user
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
        token_rows = result.scalars().all()
        assert len(token_rows) >= 1
        latest = token_rows[-1]
        assert latest.is_revoked is False

    async def test_login_wrong_password_returns_401(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Wrong password → 401, user remains logged out."""
        user, _correct_pw = await create_user_in_db(db_session, email="badpass@example.com")
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "WrongPassword99!"},
        )
        assert response.status_code == 401
        detail = response.json()["detail"]
        assert "invalid" in detail.lower() or "password" in detail.lower()

    async def test_login_nonexistent_email_returns_401(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Unknown email → 401 (not 404 — avoids user enumeration)."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "AnyPass123!"},
        )
        assert response.status_code == 401

    async def test_login_inactive_user_returns_401(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Inactive account cannot log in."""
        user, password = await create_user_in_db(
            db_session, email="inactive@example.com", is_active=False
        )
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": password},
        )
        assert response.status_code == 401

    async def test_token_refresh_issues_new_tokens_and_revokes_old(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Refresh token rotation: old token is revoked, new tokens issued."""
        user, password = await create_user_in_db(db_session, email="refresh@example.com")
        await db_session.commit()

        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": password},
        )
        assert login_resp.status_code == 200
        original_refresh = login_resp.json()["refresh_token"]

        refresh_resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": original_refresh},
        )
        assert refresh_resp.status_code == 200
        new_data = refresh_resp.json()
        assert new_data["access_token"] != login_resp.json()["access_token"]
        assert new_data["refresh_token"] != original_refresh

        # Old token must now be revoked in DB
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.token == original_refresh)
        )
        old_token = result.scalars().first()
        assert old_token is not None
        assert old_token.is_revoked is True

    async def test_logout_revokes_refresh_token(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Logout revokes the refresh token in DB."""
        user, password = await create_user_in_db(db_session, email="logout@example.com")
        await db_session.commit()

        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": password},
        )
        tokens = login_resp.json()

        logout_resp = await async_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert logout_resp.status_code == 200

        # Refresh token must now be revoked
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.token == tokens["refresh_token"])
        )
        token_row = result.scalars().first()
        assert token_row is not None
        assert token_row.is_revoked is True
