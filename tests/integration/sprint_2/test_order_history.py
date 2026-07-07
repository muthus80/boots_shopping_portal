"""Integration tests for US-003: View Order History.

Tests the /api/v1/account/orders endpoint — authenticated user views
their own order history with order number, date, total price, and status.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.sprint_2.conftest import (
    create_user_in_db,
    create_order_in_db,
    login_user,
)

pytestmark = pytest.mark.asyncio


class TestOrderHistory:
    """US-003: View Order History"""

    async def test_authenticated_user_views_order_history(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        AC: Given I am logged in, when I navigate to Order History,
        then I see a list of all my previous orders.
        AC: Each order displays order number (id), date, total price, and status.
        """
        email = f"orders_{uuid.uuid4().hex[:6]}@example.com"
        password = "SecurePass1!"
        user = await create_user_in_db(db_session, email=email, password=password)

        # Create two orders for this user
        order1 = await create_order_in_db(
            db_session,
            user_id=user.id,
            status="confirmed",
            total_amount=Decimal("99.99"),
        )
        order2 = await create_order_in_db(
            db_session,
            user_id=user.id,
            status="delivered",
            total_amount=Decimal("149.50"),
        )

        access_token = await login_user(async_client, email, password)

        resp = await async_client.get(
            "/api/v1/account/orders",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 200
        orders = resp.json()
        assert isinstance(orders, list)
        assert len(orders) >= 2

        order_ids = [o["id"] for o in orders]
        assert str(order1.id) in order_ids
        assert str(order2.id) in order_ids

        # AC: each order has id (order number), status, total_amount, created_at
        for order in orders:
            assert "id" in order
            assert "status" in order
            assert "total_amount" in order or "total" in order
            assert "created_at" in order

    async def test_authenticated_user_has_no_orders_returns_empty_list(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        US-014 AC: Given I navigate to order history with no prior orders,
        a message is displayed saying 'You have not placed any orders yet.'
        — the API returns an empty list which the frontend renders as the empty state.
        """
        email = f"noorders_{uuid.uuid4().hex[:6]}@example.com"
        password = "SecurePass1!"
        await create_user_in_db(db_session, email=email, password=password)

        access_token = await login_user(async_client, email, password)

        resp = await async_client.get(
            "/api/v1/account/orders",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 200
        assert resp.json() == []

    async def test_unauthenticated_user_cannot_view_order_history(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        US-013 AC: Session expiry — attempting to access order history
        without a token returns 401 so the frontend redirects to login.
        """
        resp = await async_client.get("/api/v1/account/orders")
        assert resp.status_code == 401

    async def test_user_cannot_see_other_users_orders(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """
        Security: User A's orders are not returned when User B is authenticated.
        """
        email_a = f"usera_{uuid.uuid4().hex[:6]}@example.com"
        email_b = f"userb_{uuid.uuid4().hex[:6]}@example.com"
        password = "SecurePass1!"

        user_a = await create_user_in_db(db_session, email=email_a, password=password)
        await create_user_in_db(db_session, email=email_b, password=password)

        # Create order for user A
        order_a = await create_order_in_db(
            db_session, user_id=user_a.id, total_amount=Decimal("200.00")
        )

        # Login as user B
        access_token_b = await login_user(async_client, email_b, password)

        resp = await async_client.get(
            "/api/v1/account/orders",
            headers={"Authorization": f"Bearer {access_token_b}"},
        )

        assert resp.status_code == 200
        orders = resp.json()
        order_ids = [o["id"] for o in orders]
        # User A's order should NOT be visible to user B
        assert str(order_a.id) not in order_ids
