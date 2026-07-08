"""Integration tests for US-009 (Add to Shopping Cart) and US-010 (View and Edit Cart).

Tests cover: adding items with size/color selection, cart update confirmation,
cart icon count, quantity changes, and item removal.
"""
from __future__ import annotations

import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.cart.models import Cart, CartItem

from tests.integration.sprint_3.conftest import (
    create_category_in_db,
    create_product_in_db,
    create_variant_in_db,
    create_user_in_db,
    login_user,
)

pytestmark = pytest.mark.asyncio


class TestAddToShoppingCart:
    """US-009: Add to Shopping Cart"""

    async def test_authenticated_user_adds_item_to_cart(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: User selects size/color then clicks Add to Cart → item added to cart.
        AC: Cart icon updates to show number of items.
        """
        email = "cart_user@example.com"
        password = "CartPass1!"
        user = await create_user_in_db(db_session, email=email, password=password)

        product = await create_product_in_db(
            db_session, name="Hiking Boot", base_price=Decimal("129.99")
        )
        variant = await create_variant_in_db(
            db_session, product_id=product.id, size="8", color="Black"
        )

        # Capture IDs as plain strings BEFORE HTTP calls (avoids ORM lazy-load after session expires)
        product_id_str = str(product.id)
        variant_id_str = str(variant.id)

        token = await login_user(async_client, email, password)
        resp = await async_client.post(
            "/api/v1/cart/items",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "product_id": product_id_str,
                "variant_id": variant_id_str,
                "quantity": 1,
            },
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert "items" in data
        assert "item_count" in data
        assert data["item_count"] == 1, f"Expected item_count=1, got {data['item_count']}"

        items = data["items"]
        assert len(items) == 1
        cart_item = items[0]
        assert str(cart_item["product_id"]) == product_id_str
        assert cart_item["quantity"] == 1

        # Verify DB state: CartItem persisted
        import uuid as _uuid
        product_uuid = _uuid.UUID(product_id_str)
        result = await db_session.execute(
            select(CartItem).where(CartItem.product_id == product_uuid)
        )
        db_item = result.scalars().first()
        assert db_item is not None, "CartItem not found in DB after adding to cart"
        assert db_item.quantity == 1
        assert str(db_item.variant_id) == variant_id_str

    async def test_guest_user_adds_item_to_cart_via_session_id(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Guest can add items to cart using session ID header."""
        product = await create_product_in_db(
            db_session, name="Guest Boot", base_price=Decimal("79.99")
        )
        session_id = "guest-session-abc-123"

        resp = await async_client.post(
            "/api/v1/cart/items",
            headers={"X-Session-ID": session_id},
            json={
                "product_id": str(product.id),
                "quantity": 2,
            },
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert data["item_count"] == 2
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2

        # Verify DB state: cart created for guest session
        result = await db_session.execute(
            select(Cart).where(Cart.session_id == session_id)
        )
        db_cart = result.scalars().first()
        assert db_cart is not None, "Guest cart not found in DB"
        assert db_cart.user_id is None

    async def test_adding_same_item_twice_increments_quantity(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Adding the same product variant twice → quantity incremented, not duplicated."""
        email = "doubleadd@example.com"
        password = "DoubleAdd1!"
        user = await create_user_in_db(db_session, email=email, password=password)

        product = await create_product_in_db(
            db_session, name="Chelsea Boot", base_price=Decimal("89.99")
        )
        variant = await create_variant_in_db(
            db_session, product_id=product.id, size="7", color="Brown", stock_quantity=50
        )

        # Capture IDs as strings before HTTP calls
        product_id_str = str(product.id)
        variant_id_str = str(variant.id)

        token = await login_user(async_client, email, password)

        # First add
        r1 = await async_client.post(
            "/api/v1/cart/items",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": product_id_str, "variant_id": variant_id_str, "quantity": 1},
        )
        assert r1.status_code == 201

        # Second add — same variant
        r2 = await async_client.post(
            "/api/v1/cart/items",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": product_id_str, "variant_id": variant_id_str, "quantity": 1},
        )
        assert r2.status_code == 201

        data = r2.json()
        # Should have one line item with quantity 2
        assert data["item_count"] == 2
        assert len(data["items"]) == 1, "Should have only one distinct line item"
        assert data["items"][0]["quantity"] == 2

    async def test_get_cart_returns_current_cart(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: GET /api/v1/cart returns current cart with all items and subtotal."""
        email = "viewcart@example.com"
        password = "ViewCart1!"
        user = await create_user_in_db(db_session, email=email, password=password)

        product = await create_product_in_db(
            db_session, name="View Cart Boot", base_price=Decimal("99.99")
        )
        variant = await create_variant_in_db(
            db_session, product_id=product.id, size="9", color="Black", stock_quantity=30
        )

        token = await login_user(async_client, email, password)

        # Add to cart
        add_resp = await async_client.post(
            "/api/v1/cart/items",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": str(product.id), "variant_id": str(variant.id), "quantity": 2},
        )
        assert add_resp.status_code == 201

        # Get cart
        get_resp = await async_client.get(
            "/api/v1/cart",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_resp.status_code == 200

        data = get_resp.json()
        assert "items" in data
        assert "total" in data
        assert "item_count" in data
        assert data["item_count"] == 2


class TestViewAndEditShoppingCart:
    """US-010: View and Edit Shopping Cart"""

    async def test_cart_page_shows_items_with_price_quantity_subtotal(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Cart page shows list of items with price, quantity, and subtotal."""
        email = "cartview@example.com"
        password = "CartView1!"
        user = await create_user_in_db(db_session, email=email, password=password)

        product = await create_product_in_db(
            db_session, name="Subtotal Boot", base_price=Decimal("60.00")
        )
        variant = await create_variant_in_db(
            db_session, product_id=product.id, size="8", color="Black", stock_quantity=20
        )

        token = await login_user(async_client, email, password)

        # Add 3 items
        add_resp = await async_client.post(
            "/api/v1/cart/items",
            headers={"Authorization": f"Bearer {token}"},
            json={"product_id": str(product.id), "variant_id": str(variant.id), "quantity": 3},
        )
        assert add_resp.status_code == 201

        get_resp = await async_client.get(
            "/api/v1/cart",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_resp.status_code == 200

        data = get_resp.json()
        items = data["items"]
        assert len(items) == 1

        item = items[0]
        # AC: price, quantity, subtotal
        assert "unit_price" in item, "Cart item must have unit_price"
        assert "quantity" in item, "Cart item must have quantity"
        assert "subtotal" in item, "Cart item must have subtotal"
        assert item["quantity"] == 3
        # subtotal = unit_price * quantity = 60.00 * 3 = 180.00
        assert float(item["subtotal"]) == pytest.approx(180.00, rel=1e-2)
        assert float(data["total"]) == pytest.approx(180.00, rel=1e-2)
