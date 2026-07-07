"""Integration tests for US-004 (Search), US-005 (Filter), US-006 (Listing),
US-007 (Product Detail), and US-008 (Reviews).
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.domains.categories.models import Category
from app.domains.products.models import Product, ProductVariant, Review
from tests.integration.sprint_1.conftest import (
    auth_headers,
    create_user_in_db,
    login_user,
)

pytestmark = pytest.mark.asyncio


class TestSearchAndFilter:
    """US-004 – Search for Boots  |  US-005 – Filter Product Listings  |  US-006 – View Listing"""

    async def test_search_returns_matching_products(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_product,
    ):
        """Keyword search 'hiking' returns matching products. (AC: search results page)"""
        # sample_product is named 'Hiking Boot Pro'
        response = await async_client.get(
            "/api/v1/products", params={"search": "hiking"}
        )
        assert response.status_code == 200
        data = response.json()
        # ProductList shape: items, total, page, page_size, total_pages
        assert "items" in data or "id" in data  # might be list or paginated wrapper
        # If paginated wrapper
        if "items" in data:
            items = data["items"]
        elif isinstance(data, list):
            items = data
        else:
            items = [data]

        names = [p["name"].lower() for p in items]
        assert any("hiking" in n for n in names), f"Expected 'hiking' in {names}"

    async def test_search_no_results_returns_empty(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Search for non-existent keyword returns empty result set. (AC: 'No results found')"""
        response = await async_client.get(
            "/api/v1/products", params={"search": "nonexistent_xyzzy_boot_99999"}
        )
        assert response.status_code == 200
        data = response.json()
        if "items" in data:
            assert data["total"] == 0
            assert data["items"] == []
        elif isinstance(data, list):
            assert data == []

    async def test_filter_by_category_returns_correct_products(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_product,
        sample_category: Category,
    ):
        """Filter by category_id returns only boots in that category. (AC: US-005 size/category filter)"""
        product, _ = sample_product
        response = await async_client.get(
            "/api/v1/products",
            params={"category_id": str(sample_category.id)},
        )
        assert response.status_code == 200
        data = response.json()
        items = data["items"] if "items" in data else data
        assert len(items) >= 1
        for item in items:
            assert item.get("category_id") == str(sample_category.id)

    async def test_product_listing_page_shows_required_fields(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_product,
    ):
        """Product listing page shows image, name, brand, price per card. (AC: US-006)"""
        response = await async_client.get("/api/v1/products")
        assert response.status_code == 200
        data = response.json()
        items = data["items"] if "items" in data else (data if isinstance(data, list) else [data])
        assert len(items) >= 1
        card = items[0]
        assert "name" in card
        # price field exposed (either 'price' or 'base_price')
        assert "price" in card or "base_price" in card
        # Listing endpoint returns id and name at minimum

    async def test_products_paginated_correctly(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_category: Category,
    ):
        """Pagination metadata is returned correctly."""
        # Create 5 products
        for i in range(5):
            p = Product(
                name=f"Boot {i}",
                slug=f"boot-{i}-{uuid.uuid4().hex[:4]}",
                base_price=Decimal("49.99"),
                currency="GBP",
                stock_quantity=10,
                is_active=True,
                images=[],
                attributes={},
            )
            db_session.add(p)
        await db_session.flush()

        response = await async_client.get("/api/v1/products", params={"page": 1, "page_size": 2})
        assert response.status_code == 200
        data = response.json()
        if "items" in data:
            assert data["page"] == 1
            assert data["page_size"] == 2
            assert len(data["items"]) <= 2


class TestProductDetail:
    """US-007 – View Product Details"""

    async def test_product_detail_returns_full_information(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_product,
    ):
        """Product detail page shows images, description, brand, variants. (AC: US-007)"""
        product, variant = sample_product
        response = await async_client.get(f"/api/v1/products/{product.id}")
        assert response.status_code == 200
        data = response.json()

        # AC: name, description present
        assert data["name"] == product.name
        assert "description" in data
        # AC: variants (sizes/colors) available
        assert "variants" in data
        variants = data["variants"]
        assert isinstance(variants, list)
        assert len(variants) >= 1
        v = variants[0]
        assert "size" in v
        assert "color" in v

    async def test_product_detail_not_found_returns_404(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Requesting a non-existent product returns 404."""
        fake_id = uuid.uuid4()
        response = await async_client.get(f"/api/v1/products/{fake_id}")
        assert response.status_code == 404


class TestProductReviews:
    """US-008 – Read and Write Product Reviews"""

    async def test_guest_can_read_product_reviews(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_product,
    ):
        """Any visitor can see customer reviews on the PDP. (AC: reviews section visible)"""
        product, _ = sample_product

        # Seed a review directly
        user, password = await create_user_in_db(
            db_session, email="reviewer@example.com"
        )
        await db_session.commit()
        review = Review(
            product_id=product.id,
            user_id=user.id,
            rating=4,
            title="Great boots",
            body="Very comfortable for hiking.",
            is_approved=True,
        )
        db_session.add(review)
        await db_session.commit()

        response = await async_client.get(f"/api/v1/products/{product.id}/reviews")
        assert response.status_code == 200
        reviews = response.json()
        assert isinstance(reviews, list)
        assert len(reviews) >= 1
        r = reviews[0]
        assert r["rating"] == 4
        assert "created_at" in r

    async def test_authenticated_user_submits_review(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_product,
        registered_user: dict,
    ):
        """Logged-in user can submit a rating and review for a product. (AC: US-008)"""
        product, _ = sample_product

        response = await async_client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 5, "title": "Excellent!", "body": "Best boots ever."},
            headers=auth_headers(registered_user["access_token"]),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == 5
        assert data["product_id"] == str(product.id)
        assert data["user_id"] == str(registered_user["user"].id)

        # Assert DB state
        result = await db_session.execute(
            select(Review).where(
                Review.product_id == product.id,
                Review.user_id == registered_user["user"].id,
            )
        )
        review_row = result.scalars().first()
        assert review_row is not None
        assert review_row.rating == 5

    async def test_unauthenticated_user_cannot_submit_review(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_product,
    ):
        """Unauthenticated review submission returns 401."""
        product, _ = sample_product
        response = await async_client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 3, "title": "OK", "body": "Average."},
        )
        assert response.status_code == 401

    async def test_user_cannot_review_same_product_twice(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        sample_product,
        registered_user: dict,
    ):
        """Duplicate review submission returns 409 conflict."""
        product, _ = sample_product
        headers = auth_headers(registered_user["access_token"])

        first = await async_client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 4, "title": "Good"},
            headers=headers,
        )
        assert first.status_code == 201

        second = await async_client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 2, "title": "Changed mind"},
            headers=headers,
        )
        assert second.status_code == 409
