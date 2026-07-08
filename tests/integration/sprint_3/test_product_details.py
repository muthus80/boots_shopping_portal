"""Integration tests for US-007 (View Product Details) and US-008 (Read and Write Reviews).

Tests cover PDP images, description, size/color selection, reviews listing,
and purchase-verified review submission.
"""
from __future__ import annotations

import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.products.models import Review
from app.domains.checkout.models import OrderItem

from tests.integration.sprint_3.conftest import (
    create_category_in_db,
    create_product_in_db,
    create_variant_in_db,
    create_user_in_db,
    login_user,
    create_order_in_db,
    create_review_in_db,
)

pytestmark = pytest.mark.asyncio


class TestViewProductDetails:
    """US-007: View Product Details"""

    async def test_product_detail_page_returns_full_details(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: PDP loads with multiple images, description (material, features), size & color options."""
        cat = await create_category_in_db(db_session, name="Premium Boots", slug="premium-boots")
        product = await create_product_in_db(
            db_session,
            name="Waterproof Leather Boot",
            brand="Dr. Martens",
            base_price=Decimal("189.99"),
            category_id=cat.id,
            description="Full-grain leather upper. Waterproof. Air-cushioned sole.",
        )
        # Create size variants
        await create_variant_in_db(db_session, product_id=product.id, size="8", color="Black")
        await create_variant_in_db(db_session, product_id=product.id, size="9", color="Black")
        await create_variant_in_db(db_session, product_id=product.id, size="8", color="Brown")

        resp = await async_client.get(f"/api/v1/products/{product.id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()

        # AC: detailed description present (material, features)
        assert "description" in data
        assert data["description"] is not None
        assert "waterproof" in data["description"].lower() or "leather" in data["description"].lower()

        # AC: name and brand
        assert data["name"] == "Waterproof Leather Boot"
        assert data["brand"] == "Dr. Martens"
        assert float(data["price"]) == pytest.approx(189.99, rel=1e-3)

        # AC: variants (size and color options)
        assert "variants" in data
        variants = data["variants"]
        assert len(variants) == 3, f"Expected 3 variants, got {len(variants)}"

        sizes = {v["size"] for v in variants}
        colors = {v["color"] for v in variants}
        assert "8" in sizes
        assert "9" in sizes
        assert "Black" in colors
        assert "Brown" in colors

        # AC: images list present (even if empty, the key must exist)
        assert "images" in data

    async def test_product_detail_not_found_returns_404(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Non-existent product → 404."""
        import uuid
        fake_id = str(uuid.uuid4())
        resp = await async_client.get(f"/api/v1/products/{fake_id}")
        assert resp.status_code == 404


class TestReadAndWriteReviews:
    """US-008: Read and Write Product Reviews"""

    async def test_guest_can_read_product_reviews(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Viewing PDP → customer ratings/reviews section visible (no auth required)."""
        user = await create_user_in_db(
            db_session, email="reviewer1@example.com", password="ReviewPass1!"
        )
        product = await create_product_in_db(db_session, name="Reviewed Boot")
        await create_review_in_db(
            db_session,
            product_id=product.id,
            user_id=user.id,
            rating=4,
            title="Good boots",
            body="Comfortable for long walks.",
        )

        # No auth required to read reviews
        resp = await async_client.get(f"/api/v1/products/{product.id}/reviews")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert "reviews" in data
        assert "average_rating" in data
        assert "total_reviews" in data

        reviews = data["reviews"]
        assert len(reviews) == 1
        review = reviews[0]
        assert review["rating"] == 4
        assert "review_text" in review  # API contract field name
        assert data["total_reviews"] == 1

    async def test_authenticated_user_with_purchase_can_submit_review(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Logged-in user who purchased the product can submit a rating and review.
        Verifies DB state: review record created with correct fields.
        """
        email = "purchaser@example.com"
        password = "PurchasePass1!"
        user = await create_user_in_db(db_session, email=email, password=password)
        product = await create_product_in_db(db_session, name="Purchasable Boot")

        # Create a confirmed order with an OrderItem linking to the product
        # (service verifies purchase via OrderItem.product_id)
        order = await create_order_in_db(db_session, user_id=user.id, status="confirmed")

        # Must add an OrderItem linking this order to the product
        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=1,
            unit_price=product.base_price,
            line_total=product.base_price,
        )
        db_session.add(order_item)
        await db_session.commit()

        # Capture IDs before HTTP calls
        product_id_str = str(product.id)

        token = await login_user(async_client, email, password)
        resp = await async_client.post(
            f"/api/v1/products/{product_id_str}/reviews",
            headers={"Authorization": f"Bearer {token}"},
            json={"rating": 5, "review_text": "Excellent boots, very comfortable."},
        )
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert data["rating"] == 5
        assert "id" in data
        assert "created_at" in data

        # Verify DB state: review persisted
        import uuid as _uuid
        product_uuid = _uuid.UUID(product_id_str)
        result = await db_session.execute(
            select(Review).where(
                Review.product_id == product_uuid,
                Review.user_id == user.id,
            )
        )
        db_review = result.scalars().first()
        assert db_review is not None, "Review not found in DB after submission"
        assert db_review.rating == 5
        assert db_review.body == "Excellent boots, very comfortable."

    async def test_unauthenticated_user_cannot_submit_review(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Review submission requires authentication → 401 without token."""
        product = await create_product_in_db(db_session, name="Unreviewed Boot")

        resp = await async_client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 3, "review_text": "Decent."},
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    async def test_review_aggregate_reflects_new_reviews(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Reviews section shows customer ratings — average rating is computable from data."""
        user1 = await create_user_in_db(
            db_session, email="rater1@example.com", password="RaterPass1!"
        )
        user2 = await create_user_in_db(
            db_session, email="rater2@example.com", password="RaterPass2!"
        )
        product = await create_product_in_db(db_session, name="Rated Boot")

        await create_review_in_db(db_session, product_id=product.id, user_id=user1.id, rating=4)
        await create_review_in_db(db_session, product_id=product.id, user_id=user2.id, rating=2)

        resp = await async_client.get(f"/api/v1/products/{product.id}/reviews")
        assert resp.status_code == 200

        data = resp.json()
        assert data["total_reviews"] == 2
        # Average of 4 and 2 = 3.0
        assert data["average_rating"] == pytest.approx(3.0, rel=1e-3)
