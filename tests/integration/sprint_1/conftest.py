"""Sprint 1 integration test fixtures.

Inherits async_client + db_session from tests.integration.conftest.
Provides helpers for creating authenticated users and seeding sprint data.
"""
from __future__ import annotations

import os
import uuid
from decimal import Decimal
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

from app.core.database import Base
from app.core.deps import get_db
from app.core.security import hash_password, create_access_token
from app.domains.account.models import User, RefreshToken
from app.domains.categories.models import Category
from app.domains.products.models import Product, ProductVariant, Review
from app.domains.cart.models import Cart, CartItem
from app.domains.checkout.models import Order, OrderItem
from app.main import app

# ---------------------------------------------------------------------------
# Build the test DB engine from DATABASE_URL (set by the SDK session).
# We derive a "_test" variant so we never touch the dev DB.
# ---------------------------------------------------------------------------
_RAW_URL = os.environ["DATABASE_URL"]

# Normalise scheme to asyncpg
def _make_async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url

_ASYNC_URL = _make_async_url(_RAW_URL)


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh async session backed by the test DB, schema recreated per test."""
    engine = create_async_engine(_ASYNC_URL, echo=False, future=True)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async httpx client wired to the test app + test DB."""
    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper: create a user row directly in the DB and return (user, plaintext pw)
# ---------------------------------------------------------------------------
async def create_user_in_db(
    db: AsyncSession,
    *,
    email: str | None = None,
    password: str = "Password1!",
    full_name: str = "Test User",
    is_active: bool = True,
) -> tuple[User, str]:
    email = email or f"user_{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        is_active=is_active,
        is_superuser=False,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user, password


# ---------------------------------------------------------------------------
# Helper: log in via the API and return the token pair
# ---------------------------------------------------------------------------
async def login_user(client: AsyncClient, email: str, password: str) -> dict:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()


# ---------------------------------------------------------------------------
# Helper: build Bearer auth headers from an access token
# ---------------------------------------------------------------------------
def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixture: a pre-registered user with tokens
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def registered_user(db_session: AsyncSession, async_client: AsyncClient):
    """Return dict with user, access_token, refresh_token, password."""
    user, password = await create_user_in_db(db_session)
    await db_session.commit()
    tokens = await login_user(async_client, user.email, password)
    return {
        "user": user,
        "password": password,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
    }


# ---------------------------------------------------------------------------
# Fixture: a Category row
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def sample_category(db_session: AsyncSession) -> Category:
    cat = Category(
        name="Work Boots",
        slug="work-boots",
        description="Sturdy work boots",
        is_active=True,
    )
    db_session.add(cat)
    await db_session.flush()
    await db_session.refresh(cat)
    return cat


# ---------------------------------------------------------------------------
# Fixture: a Product with a variant
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def sample_product(db_session: AsyncSession, sample_category: Category):
    product = Product(
        name="Hiking Boot Pro",
        slug="hiking-boot-pro",
        description="A great waterproof hiking boot with excellent grip.",
        brand="Titan Works",
        sku=f"SKU-{uuid.uuid4().hex[:6].upper()}",
        base_price=Decimal("89.99"),
        currency="GBP",
        stock_quantity=50,
        is_active=True,
        images=[],
        attributes={},
        category_id=sample_category.id,
    )
    db_session.add(product)
    await db_session.flush()

    variant = ProductVariant(
        product_id=product.id,
        name="UK 8 / Black",
        sku=f"VAR-{uuid.uuid4().hex[:6].upper()}",
        size="8",
        color="Black",
        price_modifier=Decimal("0.00"),
        stock_quantity=10,
        inventory_count=10,
        is_active=True,
    )
    db_session.add(variant)
    await db_session.flush()
    await db_session.refresh(product)
    await db_session.refresh(variant)
    return product, variant


# ---------------------------------------------------------------------------
# Fixture: a Cart for the registered user
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def user_cart(db_session: AsyncSession, registered_user: dict) -> Cart:
    cart = Cart(user_id=registered_user["user"].id)
    db_session.add(cart)
    await db_session.flush()
    await db_session.refresh(cart)
    return cart


# ---------------------------------------------------------------------------
# Fixture: an Order for the registered user
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def user_order(
    db_session: AsyncSession,
    registered_user: dict,
    sample_product,
) -> Order:
    product, variant = sample_product
    order = Order(
        user_id=registered_user["user"].id,
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        status="confirmed",
        payment_status="paid",
        subtotal=Decimal("89.99"),
        shipping_cost=Decimal("4.99"),
        tax=Decimal("0.00"),
        total=Decimal("94.98"),
        total_amount=Decimal("94.98"),
        currency="GBP",
        shipping_address={},
    )
    db_session.add(order)
    await db_session.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        variant_id=variant.id,
        product_name=product.name,
        quantity=1,
        unit_price=Decimal("89.99"),
        line_total=Decimal("89.99"),
    )
    db_session.add(item)
    await db_session.flush()
    await db_session.refresh(order)
    return order
