"""
Sprint 3 T-019 acceptance-criteria behavior check (US-008).

Exercises GET and POST /api/v1/products/{product_id}/reviews against the
US-008 acceptance criteria using FastAPI's in-process TestClient + ephemeral SQLite.

Acceptance criteria:
  • Given I am on a product detail page, when I scroll down, I see customer reviews.
  • Given I have purchased a product and I am logged in, I can submit my rating and review.
  • Non-purchasers cannot submit a review (403).
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
from app.domains.products.models import Product, Review
from app.main import app as fastapi_app

import app.domains.auth.models           # noqa: F401
import app.domains.categories.models     # noqa: F401
import app.domains.products.models       # noqa: F401
import app.domains.cart.models           # noqa: F401
import app.domains.checkout.models       # noqa: F401


@pytest_asyncio.fixture()
async def t019_db_client():
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


# ── AC1: Reviews section visible on product detail page (public GET) ────────

@pytest.mark.asyncio
async def test_ac_reviews_visible_on_product_detail_page(t019_db_client):
    """AC: Scrolling down a product page shows reviews — GET returns 200 with shape."""
    db, client = t019_db_client

    uid = uuid.uuid4().hex[:8]
    cat = Category(name=f"Cat {uid}", slug=f"cat-{uid}")
    db.add(cat)
    await db.commit()
    await db.refresh(cat)

    product = Product(
        category_id=cat.id,
        name=f"Boot {uid}",
        slug=f"boot-{uid}",
        brand="Test",
        base_price=Decimal("150.00"),
        is_active=True,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    # Public — no auth required
    resp = client.get(f"/api/v1/products/{product.id}/reviews")
    assert resp.status_code == 200
    body = resp.json()
    assert "average_rating" in body
    assert "reviews" in body
    assert "total_reviews" in body


# ── AC2: Logged-in purchaser can submit review ──────────────────────────────

@pytest.mark.asyncio
async def test_ac_purchaser_can_submit_review(t019_db_client):
    """AC: Logged-in user who purchased the product can submit rating and review."""
    db, client = t019_db_client

    uid = uuid.uuid4().hex[:8]
    cat = Category(name=f"Cat {uid}", slug=f"cat-{uid}")
    db.add(cat)
    await db.commit()
    await db.refresh(cat)

    product = Product(
        category_id=cat.id,
        name=f"Boot {uid}",
        slug=f"boot-{uid}",
        brand="Test",
        base_price=Decimal("150.00"),
        is_active=True,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    user = User(
        email=f"buyer_{uid}@example.com",
        hashed_password=hash_password("SecurePass1!"),
        full_name="Buyer",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    order = Order(
        order_number=f"ORD-{uid.upper()}",
        user_id=user.id,
        status="delivered",
        payment_status="paid",
        subtotal=Decimal("150.00"),
        shipping_cost=Decimal("5.00"),
        tax=Decimal("15.00"),
        total=Decimal("170.00"),
        total_amount=Decimal("170.00"),
        currency="GBP",
        shipping_address={"line1": "1 Test Rd", "city": "London"},
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        quantity=1,
        unit_price=Decimal("150.00"),
        line_total=Decimal("150.00"),
    )
    db.add(item)
    await db.commit()

    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    resp = client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 5, "review_text": "Best hiking boots I've ever owned!"},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["rating"] == 5
    assert body["review_text"] == "Best hiking boots I've ever owned!"
    assert "id" in body
    assert "created_at" in body


# ── AC3: Non-purchaser cannot submit review (403) ───────────────────────────

@pytest.mark.asyncio
async def test_ac_non_purchaser_cannot_submit_review(t019_db_client):
    """AC: A user who has not purchased the product sees an error (403)."""
    db, client = t019_db_client

    uid = uuid.uuid4().hex[:8]
    cat = Category(name=f"Cat {uid}", slug=f"cat-{uid}")
    db.add(cat)
    await db.commit()
    await db.refresh(cat)

    product = Product(
        category_id=cat.id,
        name=f"Boot {uid}",
        slug=f"boot-{uid}",
        brand="Test",
        base_price=Decimal("150.00"),
        is_active=True,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    user = User(
        email=f"nonbuyer_{uid}@example.com",
        hashed_password=hash_password("SecurePass1!"),
        full_name="Non-Buyer",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    resp = client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 3, "review_text": "Should not be allowed."},
        headers=headers,
    )
    assert resp.status_code == 403


# ── AC4: Submitted review appears in the reviews list ───────────────────────

@pytest.mark.asyncio
async def test_ac_submitted_review_appears_in_listing(t019_db_client):
    """AC: After submitting a review it appears in the product reviews section."""
    db, client = t019_db_client

    uid = uuid.uuid4().hex[:8]
    cat = Category(name=f"Cat {uid}", slug=f"cat-{uid}")
    db.add(cat)
    await db.commit()
    await db.refresh(cat)

    product = Product(
        category_id=cat.id,
        name=f"Boot {uid}",
        slug=f"boot-{uid}",
        brand="Test",
        base_price=Decimal("150.00"),
        is_active=True,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    user = User(
        email=f"reviewer_{uid}@example.com",
        hashed_password=hash_password("SecurePass1!"),
        full_name="Reviewer",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    order = Order(
        order_number=f"ORD-R-{uid.upper()}",
        user_id=user.id,
        status="delivered",
        payment_status="paid",
        subtotal=Decimal("150.00"),
        shipping_cost=Decimal("5.00"),
        tax=Decimal("15.00"),
        total=Decimal("170.00"),
        total_amount=Decimal("170.00"),
        currency="GBP",
        shipping_address={"line1": "1 Test Rd", "city": "London"},
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        quantity=1,
        unit_price=Decimal("150.00"),
        line_total=Decimal("150.00"),
    )
    db.add(item)
    await db.commit()

    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    post_resp = client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"rating": 4, "review_text": "Excellent waterproofing."},
        headers=headers,
    )
    assert post_resp.status_code == 201

    get_resp = client.get(f"/api/v1/products/{product.id}/reviews")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["total_reviews"] == 1
    assert body["reviews"][0]["review_text"] == "Excellent waterproofing."
    assert body["average_rating"] == pytest.approx(4.0)
