"""Integration tests for US-001 (User Registration) and US-002 (User Login).

Tests traverse the full user path from unauthenticated state through
account creation and login, asserting both API responses and DB state.
"""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.account.models import User, RefreshToken
from tests.integration.sprint_2.conftest import create_user_in_db


pytestmark = pytest.mark.asyncio


class TestUserRegistration:
    """US-001: User Registration"""

    async def test_guest_registers_with_valid_credentials_creates_account(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        AC: Given valid email and password meeting complexity requirements,
        when I submit the registration form, then my account is created.
        AC: Given my account is created, the response includes a confirmation message.
        """
        email = f"new_user_{uuid.uuid4().hex[:6]}@example.com"
        payload = {
            "email": email,
            "password": "SecurePass1!",
            "full_name": "Jane Doe",
        }

        resp = await async_client.post("/api/v1/auth/register", json=payload)

        # AC: 201 Created with user_id and confirmation message
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == email
        assert "user_id" in data
        assert "confirmation" in data["message"].lower() or "registration" in data["message"].lower()

        # Assert DB state: user actually persisted
        result = await db_session.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        assert user is not None
        assert user.is_active is True
        # Password stored hashed, never plain
        assert user.hashed_password != "SecurePass1!"

    async def test_guest_registers_duplicate_email_returns_conflict(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        AC: Given I try to register with an email that already exists,
        then I see an error message indicating the email is already in use.
        """
        email = f"existing_{uuid.uuid4().hex[:6]}@example.com"
        # Create user first
        await create_user_in_db(db_session, email=email, password="SecurePass1!")

        resp = await async_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "SecurePass1!"},
        )

        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower() or "email" in resp.json()["detail"].lower()

    async def test_guest_registers_weak_password_returns_validation_error(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        AC: Password must meet complexity requirements (min 8 chars).
        Short password should be rejected.
        """
        resp = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": f"weakpw_{uuid.uuid4().hex[:6]}@example.com",
                "password": "short",
            },
        )
        # 422 from pydantic field validation (min_length=8)
        assert resp.status_code in (422, 400)


class TestUserLogin:
    """US-002: User Login"""

    async def test_user_logs_in_with_correct_credentials_receives_tokens(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        AC: Given correct credentials, I am successfully logged in and receive
        access and refresh tokens for the redirect to homepage.
        """
        email = f"loginuser_{uuid.uuid4().hex[:6]}@example.com"
        password = "SecurePass1!"
        user = await create_user_in_db(db_session, email=email, password=password)

        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # Assert DB: refresh token persisted
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
        rt = result.scalars().first()
        assert rt is not None
        assert rt.is_revoked is False

    async def test_user_logs_in_with_wrong_password_receives_401(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        AC: Given incorrect credentials, I see an error message and remain on the login page.
        """
        email = f"badpass_{uuid.uuid4().hex[:6]}@example.com"
        await create_user_in_db(db_session, email=email, password="SecurePass1!")

        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword99"},
        )

        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower() or "password" in resp.json()["detail"].lower()

    async def test_user_logs_in_with_nonexistent_email_receives_401(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        Edge case: login attempt for an email that was never registered.
        """
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "ghost@example.com", "password": "SecurePass1!"},
        )

        assert resp.status_code == 401

    async def test_authenticated_user_can_refresh_token(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        US-013 AC: Session continuity — refresh token provides a new access token.
        """
        email = f"refresh_{uuid.uuid4().hex[:6]}@example.com"
        password = "SecurePass1!"
        await create_user_in_db(db_session, email=email, password=password)

        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        refresh_resp = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()
        assert "access_token" in new_tokens
        # Old refresh token should now be revoked (rotation)
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token)
        )
        old_rt = result.scalars().first()
        assert old_rt is not None
        assert old_rt.is_revoked is True

    async def test_authenticated_user_can_logout(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        US-013 AC: Logout revokes the refresh token so it can no longer be used.
        """
        email = f"logout_{uuid.uuid4().hex[:6]}@example.com"
        password = "SecurePass1!"
        await create_user_in_db(db_session, email=email, password=password)

        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        tokens = login_resp.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        logout_resp = await async_client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_resp.status_code == 200

        # Verify token is now revoked in DB
        result = await db_session.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token)
        )
        rt = result.scalars().first()
        assert rt is not None
        assert rt.is_revoked is True
