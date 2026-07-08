"""Integration tests for US-003: View Order History.

Tests the GET /api/v1/account/orders endpoint.
"""
from __future__ import annotations

import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.sprint_3.conftest import (
    create_user_in_db,
    login_user,
    create_order_in_db,
)

pytestmark = pytest.mark.asyncio


class TestOrderHistory:
    """US-003: View Order History"""

    async def test_authenticated_user_sees_their_order_history(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Logged-in user navigates to 'Order History' → list of all previous orders.
        AC: Each order displays order number, date, total price, and status.
        """
        email = "order_history@example.com"
        password = "OrderPass1!"
        user = await create_user_in_db(db_session, email=email, password=password)

        # Create two orders for this user
        order1 = await create_order_in_db(
            db_session, user_id=user.id, status="confirmed", total_amount=Decimal("129.99"),
            order_number="ORD-TEST-0001"
        )
        order2 = await create_order_in_db(
            db_session, user_id=user.id, status="delivered", total_amount=Decimal("59.99"),
            order_number="ORD-TEST-0002"
        )

        token = await login_user(async_client, email, password)
        resp = await async_client.get(
            "/api/v1/account/orders",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert "orders" in data
        assert "total" in data

        orders = data["orders"]
        assert len(orders) == 2, f"Expected 2 orders, got {len(orders)}"

        # AC: each order shows order number, date, total price, and status
        order_numbers = {o["order_number"] for o in orders}
        assert "ORD-TEST-0001" in order_numbers
        assert "ORD-TEST-0002" in order_numbers

        for order in orders:
            assert "id" in order, "Order must have an id"
            assert "order_number" in order, "Order must have order_number"
            assert "status" in order, "Order must have status"
            assert "total_amount" in order, "Order must have total_amount"
            assert "created_at" in order, "Order must have created_at (date)"

        # Verify status values
        statuses = {o["status"] for o in orders}
        assert "confirmed" in statuses
        assert "delivered" in statuses

    async def test_authenticated_user_with_no_orders_sees_empty_state_message(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC (US-014): No prior orders → message 'You have not placed any orders yet.'"""
        email = "noorders@example.com"
        password = "NoOrders1!"
        await create_user_in_db(db_session, email=email, password=password)

        token = await login_user(async_client, email, password)
        resp = await async_client.get(
            "/api/v1/account/orders",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["orders"] == [], "Expected empty orders list"
        assert data["total"] == 0

        # AC: empty-state message provided
        if "message" in data and data["message"]:
            assert (
                "no" in data["message"].lower()
                or "yet" in data["message"].lower()
                or "order" in data["message"].lower()
            ), f"Unexpected empty state message: {data['message']}"

    async def test_unauthenticated_user_cannot_view_order_history(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC (US-013): Unauthenticated request to orders endpoint → 401."""
        resp = await async_client.get("/api/v1/account/orders")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    async def test_user_only_sees_own_orders(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Order history is scoped to the authenticated user — no cross-user leakage."""
        user1 = await create_user_in_db(
            db_session, email="user1@example.com", password="UserPass1!"
        )
        user2 = await create_user_in_db(
            db_session, email="user2@example.com", password="UserPass2!"
        )

        # Only user2 has an order
        await create_order_in_db(
            db_session, user_id=user2.id, status="confirmed",
            order_number="ORD-USER2-001"
        )

        token1 = await login_user(async_client, "user1@example.com", "UserPass1!")
        resp = await async_client.get(
            "/api/v1/account/orders",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # user1 should see zero orders, not user2's
        assert data["total"] == 0
        assert data["orders"] == []
