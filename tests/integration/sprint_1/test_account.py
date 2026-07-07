"""Integration tests for US-003 (Order History).

Covers the GET /api/v1/account/orders endpoint.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.checkout.models import Order, OrderItem
from tests.integration.sprint_1.conftest import (
    auth_headers,
    create_user_in_db,
    login_user,
)

pytestmark = pytest.mark.asyncio


class TestOrderHistory:
    """US-003 – View Order History"""

    async def test_authenticated_user_sees_their_orders(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        registered_user: dict,
        user_order: Order,
    ):
        """Logged-in user navigates to order history and sees a list with order details."""
        response = await async_client.get(
            "/api/v1/account/orders",
            headers=auth_headers(registered_user["access_token"]),
        )
        assert response.status_code == 200
        orders = response.json()
        assert isinstance(orders, list)
        assert len(orders) >= 1

        # AC: each order shows id (order number), date, total price, and status
        order_data = orders[0]
        assert "id" in order_data
        assert "status" in order_data
        assert "total_amount" in order_data
        assert "created_at" in order_data
        # AC: items are included
        assert "items" in order_data

    async def test_order_history_shows_expected_fields(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        registered_user: dict,
        user_order: Order,
    ):
        """Each order entry exposes order number, date, total price, and status."""
        response = await async_client.get(
            "/api/v1/account/orders",
            headers=auth_headers(registered_user["access_token"]),
        )
        assert response.status_code == 200
        orders = response.json()
        assert len(orders) >= 1
        o = orders[0]
        # AC: all required display fields present
        assert o["status"] in (
            "pending", "confirmed", "processing", "shipped", "delivered", "cancelled", "refunded"
        )
        assert float(o["total_amount"]) > 0

    async def test_order_history_empty_for_new_user(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """New user with no orders sees an empty list (AC: 'no orders yet' state)."""
        user, password = await create_user_in_db(
            db_session, email="noorders@example.com"
        )
        await db_session.commit()
        tokens = await login_user(async_client, user.email, password)

        response = await async_client.get(
            "/api/v1/account/orders",
            headers=auth_headers(tokens["access_token"]),
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_order_history_requires_authentication(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Unauthenticated request to order history returns 401 (AC: session continuity check)."""
        response = await async_client.get("/api/v1/account/orders")
        assert response.status_code == 401

    async def test_user_only_sees_own_orders(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """User A's orders are not visible to User B."""
        user_a, pass_a = await create_user_in_db(db_session, email="usera@example.com")
        user_b, pass_b = await create_user_in_db(db_session, email="userb@example.com")
        await db_session.commit()

        # Create an order for user_a
        order = Order(
            user_id=user_a.id,
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            status="confirmed",
            payment_status="paid",
            subtotal=Decimal("50.00"),
            shipping_cost=Decimal("4.99"),
            tax=Decimal("0.00"),
            total=Decimal("54.99"),
            total_amount=Decimal("54.99"),
            currency="GBP",
            shipping_address={},
        )
        db_session.add(order)
        await db_session.commit()

        # User B should see empty list
        tokens_b = await login_user(async_client, user_b.email, pass_b)
        response = await async_client.get(
            "/api/v1/account/orders",
            headers=auth_headers(tokens_b["access_token"]),
        )
        assert response.status_code == 200
        assert response.json() == []
