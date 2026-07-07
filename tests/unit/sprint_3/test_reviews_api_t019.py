"""
Sprint 3 T-019 unit tests — Reviews API endpoints (US-008).

User Story: US-008 — Read and Write Product Reviews
Acceptance Criteria:
  • A customer reviews section is visible on the product detail page.
  • A logged-in user who has purchased the product can submit a review.
  • Returns 403 if the authenticated user has not purchased the product.

Endpoints under test:
  GET  /api/v1/products/{product_id}/reviews
  POST /api/v1/products/{product_id}/reviews

Uses an ephemeral SQLite in-memory database via FastAPI TestClient.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import hash_password, create_access_token
from app.domains.account.models import User
from app.domains.categories.models import Category
from app.domains.checkout.models import Order, OrderItem
from app.domains.products.models import Product, ProductVariant, Review
from app.main import app as fastapi_app

# Register all ORM models before creating schema
import app.domains.auth.models           # noqa: F401
import app.domains.categories.models     # noqa: F401
import app.domains.products.models       # noqa: F401
import app.domains.cart.models           # noqa: F401
import app.domains.checkout.models       # noqa: F401


# ---------------------------------------------------------------------------
# Fixture: ephemeral SQLite + TestClient
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def db_and_client():
    """Yield (db_session, TestClient) wired to an ephemeral SQLite DB."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys = ON"))
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:

        async def _override_db():
            yield session

        fastapi_app.dependency_overrides[get_db] = _override_db
        client = TestClient(fastapi_app, raise_server_exceptions=True)

        yield session, client

    fastapi_app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_user(email: str | None = None) -> User:
    suffix = uuid.uuid4().hex[:8]
    return User(
        email=email or f"user_{suffix}@example.com",
        hashed_password=hash_password("SecurePass1!"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )


def _make_category() -> Category:
    uid = uuid.uuid4().hex[:8]
    return Category(name=f"Boots {uid}", slug=f"boots-{uid}")


def _make_product(category_id: uuid.UUID, name_suffix: str = "") -> Product:
    uid = uuid.uuid4().hex[:8]
    return Product(
        category_id=category_id,
        name=f"Trail Boot {uid}{name_suffix}",
        slug=f"trail-boot-{uid}",
        brand="Scarpa",
        base_price=Decimal("199.99"),
        is_active=True,
    )


def _make_order(user_id: uuid.UUID, status: str = "delivered") -> Order:
    return Order(
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        user_id=user_id,
        status=status,
        payment_status="paid",
        subtotal=Decimal("199.99"),
        shipping_cost=Decimal("5.00"),
        tax=Decimal("20.00"),
        total=Decimal("224.99"),
        total_amount=Decimal("224.99"),
        currency="GBP",
        shipping_address={"line1": "1 High Street", "city": "London"},
    )


def _make_order_item(order_id: uuid.UUID, product_id: uuid.UUID) -> OrderItem:
    return OrderItem(
        order_id=order_id,
        product_id=product_id,
        product_name="Trail Boot",
        quantity=1,
        unit_price=Decimal("199.99"),
        line_total=Decimal("199.99"),
    )


def _auth_header(user: User) -> dict:
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GET /api/v1/products/{product_id}/reviews — listing tests
# ---------------------------------------------------------------------------

class TestGetProductReviews:
    """T-019 / US-008 — GET /api/v1/products/{product_id}/reviews"""

    @pytest.mark.asyncio
    async def test_returns_empty_review_list_for_new_product(self, db_and_client):
        """A product with no reviews returns zero total_reviews and empty list."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        resp = client.get(f"/api/v1/products/{product.id}/reviews")
        assert resp.status_code == 200

        body = resp.json()
        assert body["total_reviews"] == 0
        assert body["reviews"] == []
        assert body["average_rating"] == 0.0

    @pytest.mark.asyncio
    async def test_returns_reviews_with_average_rating(self, db_and_client):
        """Reviews list contains items with correct average_rating aggregate."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        # Create two users and reviews directly
        user_a = _make_user()
        user_b = _make_user()
        db.add_all([user_a, user_b])
        await db.commit()
        await db.refresh(user_a)
        await db.refresh(user_b)

        review_a = Review(
            product_id=product.id,
            user_id=user_a.id,
            rating=4,
            body="Great boots!",
        )
        review_b = Review(
            product_id=product.id,
            user_id=user_b.id,
            rating=2,
            body="Not great.",
        )
        db.add_all([review_a, review_b])
        await db.commit()

        resp = client.get(f"/api/v1/products/{product.id}/reviews")
        assert resp.status_code == 200

        body = resp.json()
        assert body["total_reviews"] == 2
        assert len(body["reviews"]) == 2
        # Average of 4 + 2 = 3.0
        assert body["average_rating"] == pytest.approx(3.0)

    @pytest.mark.asyncio
    async def test_response_schema_matches_api_contract(self, db_and_client):
        """Response contains average_rating, reviews[], and total_reviews."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        resp = client.get(f"/api/v1/products/{product.id}/reviews")
        assert resp.status_code == 200

        body = resp.json()
        assert "average_rating" in body
        assert "reviews" in body
        assert "total_reviews" in body

    @pytest.mark.asyncio
    async def test_review_items_have_contract_fields(self, db_and_client):
        """Each review item exposes id, rating, review_text, created_at."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        review = Review(
            product_id=product.id,
            user_id=user.id,
            rating=5,
            body="Perfect fit and great grip.",
        )
        db.add(review)
        await db.commit()

        resp = client.get(f"/api/v1/products/{product.id}/reviews")
        assert resp.status_code == 200

        reviews = resp.json()["reviews"]
        assert len(reviews) == 1
        item = reviews[0]
        assert "id" in item
        assert "rating" in item
        assert "review_text" in item
        assert "created_at" in item
        assert item["rating"] == 5
        assert item["review_text"] == "Perfect fit and great grip."

    @pytest.mark.asyncio
    async def test_pagination_limits_results(self, db_and_client):
        """per_page parameter limits the number of reviews returned."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        # Create 5 users and reviews
        for _ in range(5):
            u = _make_user()
            db.add(u)
            await db.commit()
            await db.refresh(u)
            db.add(Review(product_id=product.id, user_id=u.id, rating=3, body="OK"))
            await db.commit()

        resp = client.get(f"/api/v1/products/{product.id}/reviews?page=1&per_page=2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_reviews"] == 5
        assert len(body["reviews"]) == 2

    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent_product(self, db_and_client):
        """Non-existent product_id returns 404."""
        _, client = db_and_client
        fake_id = uuid.uuid4()
        resp = client.get(f"/api/v1/products/{fake_id}/reviews")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_does_not_require_authentication(self, db_and_client):
        """GET reviews is public — no auth header required."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        resp = client.get(f"/api/v1/products/{product.id}/reviews")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/v1/products/{product_id}/reviews — submission tests
# ---------------------------------------------------------------------------

class TestPostProductReview:
    """T-019 / US-008 — POST /api/v1/products/{product_id}/reviews"""

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, db_and_client):
        """POST without auth token returns 401."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        resp = client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 5, "review_text": "Excellent!"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_user_without_purchase_gets_403(self, db_and_client):
        """User who hasn't purchased the product receives 403 Forbidden."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        resp = client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 5, "review_text": "Should not work."},
            headers=_auth_header(user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_user_with_pending_order_gets_403(self, db_and_client):
        """A pending (not fulfilled) order does not satisfy the purchase gate."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Pending order — should NOT satisfy the gate
        order = _make_order(user.id, status="pending")
        db.add(order)
        await db.commit()
        await db.refresh(order)

        item = _make_order_item(order.id, product.id)
        db.add(item)
        await db.commit()

        resp = client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 4, "review_text": "Should fail."},
            headers=_auth_header(user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_user_with_delivered_order_can_submit_review(self, db_and_client):
        """User with a delivered order can successfully submit a review (201)."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        order = _make_order(user.id, status="delivered")
        db.add(order)
        await db.commit()
        await db.refresh(order)

        item = _make_order_item(order.id, product.id)
        db.add(item)
        await db.commit()

        resp = client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 5, "review_text": "Absolutely brilliant boots!"},
            headers=_auth_header(user),
        )
        assert resp.status_code == 201

        body = resp.json()
        assert body["rating"] == 5
        assert body["review_text"] == "Absolutely brilliant boots!"
        assert "id" in body
        assert "created_at" in body

    @pytest.mark.asyncio
    async def test_user_with_confirmed_order_can_submit_review(self, db_and_client):
        """A 'confirmed' status also satisfies the purchase gate."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        order = _make_order(user.id, status="confirmed")
        db.add(order)
        await db.commit()
        await db.refresh(order)

        item = _make_order_item(order.id, product.id)
        db.add(item)
        await db.commit()

        resp = client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 4, "review_text": "Good quality leather."},
            headers=_auth_header(user),
        )
        assert resp.status_code == 201
        assert resp.json()["rating"] == 4

    @pytest.mark.asyncio
    async def test_user_with_shipped_order_can_submit_review(self, db_and_client):
        """A 'shipped' status also satisfies the purchase gate."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        order = _make_order(user.id, status="shipped")
        db.add(order)
        await db.commit()
        await db.refresh(order)

        item = _make_order_item(order.id, product.id)
        db.add(item)
        await db.commit()

        resp = client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 3, "review_text": "Decent waterproofing."},
            headers=_auth_header(user),
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_duplicate_review_returns_409(self, db_and_client):
        """Submitting a second review for the same product returns 409 Conflict."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        order = _make_order(user.id, status="delivered")
        db.add(order)
        await db.commit()
        await db.refresh(order)

        item = _make_order_item(order.id, product.id)
        db.add(item)
        await db.commit()

        # First review — should succeed
        resp1 = client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 5, "review_text": "First review."},
            headers=_auth_header(user),
        )
        assert resp1.status_code == 201

        # Second review — must be rejected
        resp2 = client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 3, "review_text": "Second attempt."},
            headers=_auth_header(user),
        )
        assert resp2.status_code == 409

    @pytest.mark.asyncio
    async def test_invalid_rating_returns_422(self, db_and_client):
        """Rating outside 1-5 range returns 422 Unprocessable Entity."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        order = _make_order(user.id, status="delivered")
        db.add(order)
        await db.commit()
        await db.refresh(order)

        item = _make_order_item(order.id, product.id)
        db.add(item)
        await db.commit()

        resp = client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 6, "review_text": "Out of range rating."},
            headers=_auth_header(user),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_review_for_nonexistent_product_returns_404(self, db_and_client):
        """POST to a non-existent product returns 404."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        fake_id = uuid.uuid4()
        resp = client.post(
            f"/api/v1/products/{fake_id}/reviews",
            json={"rating": 5, "review_text": "Should not exist."},
            headers=_auth_header(user),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_review_appears_in_subsequent_get(self, db_and_client):
        """After POSTing a review it appears when listing the product's reviews."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        order = _make_order(user.id, status="delivered")
        db.add(order)
        await db.commit()
        await db.refresh(order)

        item = _make_order_item(order.id, product.id)
        db.add(item)
        await db.commit()

        post_resp = client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"rating": 5, "review_text": "Superb quality boots!"},
            headers=_auth_header(user),
        )
        assert post_resp.status_code == 201
        created_id = post_resp.json()["id"]

        get_resp = client.get(f"/api/v1/products/{product.id}/reviews")
        assert get_resp.status_code == 200
        body = get_resp.json()
        assert body["total_reviews"] == 1
        review_ids = [r["id"] for r in body["reviews"]]
        assert created_id in review_ids
        assert body["average_rating"] == pytest.approx(5.0)

    @pytest.mark.asyncio
    async def test_different_users_can_review_same_product(self, db_and_client):
        """Multiple users each with a purchase can all submit reviews."""
        db, client = db_and_client

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        for rating in [5, 4, 3]:
            user = _make_user()
            db.add(user)
            await db.commit()
            await db.refresh(user)

            order = _make_order(user.id, status="delivered")
            db.add(order)
            await db.commit()
            await db.refresh(order)

            item = _make_order_item(order.id, product.id)
            db.add(item)
            await db.commit()

            resp = client.post(
                f"/api/v1/products/{product.id}/reviews",
                json={"rating": rating, "review_text": f"Review with rating {rating}."},
                headers=_auth_header(user),
            )
            assert resp.status_code == 201

        get_resp = client.get(f"/api/v1/products/{product.id}/reviews")
        body = get_resp.json()
        assert body["total_reviews"] == 3
        # Average of 5+4+3 = 4.0
        assert body["average_rating"] == pytest.approx(4.0)
