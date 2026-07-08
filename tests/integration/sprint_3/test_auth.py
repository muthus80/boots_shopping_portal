"""Integration tests for US-001 (User Registration) and US-002 (User Login).

Tests traverse complete user paths: registration → verification → login → error cases.
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


class TestUserRegistration:
    """US-001: User Registration"""

    async def test_user_registers_with_valid_credentials(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Given valid email + password (min 8 chars), account is created.
        AC: Given account is created, confirmation message is present in response.
        """
        email = "newboots_user@example.com"
        password = "BootsRules99!"

        resp = await async_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": "Boots Fan"},
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

        data = resp.json()
        # AC: account created — user_id and email returned
        assert "user_id" in data
        assert data["email"] == email
        # AC: confirmation message present
        assert "message" in data
        assert "confirmation" in data["message"].lower() or "check your email" in data["message"].lower() or "registration successful" in data["message"].lower()
        # AC: tokens returned so user is logged in immediately
        assert "access_token" in data
        assert "refresh_token" in data

        # Verify DB state: user record persisted
        result = await db_session.execute(select(User).where(User.email == email))
        db_user = result.scalars().first()
        assert db_user is not None, "User was not persisted to database"
        assert db_user.is_active is True
        assert db_user.hashed_password is not None
        # Password must be hashed — never stored in plain text
        assert db_user.hashed_password != password

        # Verify DB state: refresh token persisted
        rt_result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == db_user.id)
        )
        refresh_token = rt_result.scalars().first()
        assert refresh_token is not None, "Refresh token not stored in DB"
        assert refresh_token.is_revoked is False

    async def test_user_registers_then_duplicate_email_rejected(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Given email already in use, registration returns error indicating duplicate."""
        email = "duplicate@example.com"
        password = "StrongPass1!"

        # First registration — succeeds
        r1 = await async_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )
        assert r1.status_code == 201

        # Second registration with same email — must fail with 409
        r2 = await async_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password},
        )
        assert r2.status_code == 409, f"Expected 409, got {r2.status_code}: {r2.text}"

        data = r2.json()
        assert "detail" in data
        # Error message indicates email is already in use
        assert (
            "already" in data["detail"].lower()
            or "exists" in data["detail"].lower()
            or "email" in data["detail"].lower()
        )

    async def test_registration_rejected_for_weak_password(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Password shorter than 8 characters is rejected (422 or 400)."""
        resp = await async_client.post(
            "/api/v1/auth/register",
            json={"email": "weakpass@example.com", "password": "short"},
        )
        # Either FastAPI validation (422) or our custom validation (422/400)
        assert resp.status_code in (400, 422), f"Expected 400/422, got {resp.status_code}"

        # Confirm user was NOT persisted
        result = await db_session.execute(
            select(User).where(User.email == "weakpass@example.com")
        )
        db_user = result.scalars().first()
        assert db_user is None, "User should not have been saved for weak password"


class TestUserLogin:
    """US-002: User Login"""

    async def test_user_logs_in_with_correct_credentials(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Correct credentials → 200 + JWT tokens; user redirected (token returned)."""
        email = "logintest@example.com"
        password = "LoginPass99!"

        # Seed user
        await create_user_in_db(db_session, email=email, password=password)

        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # Verify refresh token is persisted in DB
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.token == data["refresh_token"])
        )
        rt = result.scalars().first()
        assert rt is not None, "Refresh token not persisted to DB on login"
        assert rt.is_revoked is False

    async def test_user_login_fails_with_wrong_password(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Incorrect credentials → error message, remains on login page (401)."""
        email = "wrongpass@example.com"
        password = "CorrectPass1!"

        await create_user_in_db(db_session, email=email, password=password)

        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword99!"},
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert "detail" in data
        assert (
            "invalid" in data["detail"].lower()
            or "incorrect" in data["detail"].lower()
            or "password" in data["detail"].lower()
        )

    async def test_user_login_fails_with_unknown_email(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Non-existent email → 401 with error message."""
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "AnyPass99!"},
        )
        assert resp.status_code == 401

    async def test_token_refresh_rotates_tokens(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC (US-013): Refresh token issues new access token (session continuity)."""
        email = "refresh@example.com"
        password = "RefreshPass1!"
        await create_user_in_db(db_session, email=email, password=password)

        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200
        old_refresh_token = login_resp.json()["refresh_token"]

        refresh_resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh_token},
        )
        assert refresh_resp.status_code == 200, f"Refresh failed: {refresh_resp.text}"
        new_data = refresh_resp.json()
        assert "access_token" in new_data
        assert "refresh_token" in new_data

        # Old refresh token must now be revoked in DB (rotation)
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.token == old_refresh_token)
        )
        old_rt = result.scalars().first()
        assert old_rt is not None
        assert old_rt.is_revoked is True, "Old refresh token should be revoked after rotation"

    async def test_expired_refresh_token_returns_401(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC (US-013): Expired/invalid session token → 401 (graceful redirect to login)."""
        resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "this.is.not.a.valid.token"},
        )
        assert resp.status_code == 401
