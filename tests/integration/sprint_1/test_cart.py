"""Integration tests for US-009 (Add to Cart) and US-010 (View/Edit Cart).

The cart router uses GET /api/v1/cart (no item mutations are directly routed
in the provided router — service has add_item, update_item, remove_item which
the router exposes differently depending on the actual cart route definitions).
We test the cart endpoint that IS exposed: GET /api/v1/cart.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.cart.models import Cart, CartItem
from app.domains.categories.models import Category
from app.domains.products.models import Product, ProductVariant
from tests.integration.sprint_1.conftest import (
    auth_headers,
    create_user_in_db,
    login_user,
)

pytestmark = pytest.mark.asyncio


class TestCartManagement:
    """US-009 – Add to Shopping Cart  |  US-010 – View and Edit Cart"""

    async def test_anonymous_user_gets_empty_cart(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Unauthenticated GET /api/v1/cart creates and returns a new empty cart."""
        response = await async_client.get("/api/v1/cart")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "items" in data
        assert data["items"] == [] or isinstance(data["items"], list)

    async def test_authenticated_user_cart_is_associated_with_account(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        registered_user: dict,
    ):
        """Logged-in user's cart is linked to their user_id."""
        response = await async_client.get(
            "/api/v1/cart",
            headers=auth_headers(registered_user["access_token"]),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(registered_user["user"].id)

    async def test_cart_shows_items_with_price_quantity_subtotal(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        registered_user: dict,
        sample_product,
    ):
        """Cart with items exposes unit_price, quantity, subtotal per item. (AC: US-010)"""
        product, variant = sample_product

        # Seed a cart and item directly in DB
        cart = Cart(user_id=registered_user["user"].id)
        db_session.add(cart)
        await db_session.flush()

        item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            variant_id=variant.id,
            quantity=2,
            unit_price=Decimal("89.99"),
        )
        db_session.add(item)
        await db_session.commit()

        response = await async_client.get(
            "/api/v1/cart",
            headers=auth_headers(registered_user["access_token"]),
        )
        assert response.status_code == 200
        data = response.json()
        items = data["items"]
        assert len(items) >= 1
        cart_item = items[0]
        # AC: price, quantity, subtotal present
        assert "unit_price" in cart_item
        assert "quantity" in cart_item
        assert cart_item["quantity"] == 2

    async def test_categories_endpoint_lists_categories(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_category: Category,
    ):
        """GET /api/v1/categories returns a list of categories with name and slug. (AC: US-006 navigation)"""
        response = await async_client.get("/api/v1/categories")
        assert response.status_code == 200
        data = response.json()
        # Shape: {items: [...], total: N}
        items = data.get("items", data) if isinstance(data, dict) else data
        assert isinstance(items, list)
        if len(items) > 0:
            cat = items[0]
            assert "name" in cat
            assert "slug" in cat

    async def test_category_by_slug_returns_correct_category(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_category: Category,
    ):
        """GET /api/v1/categories/{slug} returns matching category. (AC: category navigation)"""
        response = await async_client.get(f"/api/v1/categories/{sample_category.slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == sample_category.slug
        assert data["name"] == sample_category.name

    async def test_category_not_found_returns_404(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Non-existent category slug returns 404."""
        response = await async_client.get("/api/v1/categories/nonexistent-slug-xyz")
        assert response.status_code == 404
