"""Sprint 3 integration test conftest.

Provides:
- db_session and async_client wired to the per-project test DB
- Helpers to register/login a user and obtain an auth token
- Sprint-specific fixture factories for products, categories, cart, orders, reviews
"""
from __future__ import annotations

import os
import uuid
from decimal import Decimal
from typing import Optional

import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.database import Base
from app.core.deps import get_db
from app.core.security import hash_password
from app.domains.account.models import User, RefreshToken
from app.domains.categories.models import Category
from app.domains.products.models import Product, ProductVariant, Review
from app.domains.cart.models import Cart, CartItem
from app.domains.checkout.models import Order, OrderItem
from app.main import app

# ── Read DATABASE_URL from environment — NEVER hardcode credentials ──────────
TEST_DATABASE_URL = os.environ["DATABASE_URL"]
# Convert postgres:// / postgresql:// → asyncpg driver
if TEST_DATABASE_URL.startswith("postgresql://"):
    TEST_DATABASE_URL = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif TEST_DATABASE_URL.startswith("postgres://"):
    TEST_DATABASE_URL = TEST_DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)


@pytest_asyncio.fixture()
async def db_session():
    """Per-test async DB session with schema created fresh."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
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
async def async_client(db_session: AsyncSession):
    """HTTP test client wired to the in-memory test DB."""
    async def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


# ── DB helpers ────────────────────────────────────────────────────────────────

async def create_user_in_db(
    db: AsyncSession,
    email: str = "test@example.com",
    password: str = "SecurePass1!",
    full_name: str = "Test User",
    is_active: bool = True,
) -> User:
    """Directly insert a user into the DB and return the ORM object."""
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        is_active=is_active,
        is_superuser=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def login_user(client: AsyncClient, email: str, password: str) -> str:
    """Login and return the access_token string."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


async def register_user(
    client: AsyncClient,
    email: str = "newuser@example.com",
    password: str = "SecurePass1!",
    full_name: str = "New User",
) -> dict:
    """Register a user and return the full response JSON."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    return resp


async def create_category_in_db(
    db: AsyncSession,
    name: str = "Chelsea Boots",
    slug: str = "chelsea-boots",
) -> Category:
    cat = Category(
        name=name,
        slug=slug,
        description=f"{name} description",
        is_active=True,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


async def create_product_in_db(
    db: AsyncSession,
    name: str = "Test Boot",
    base_price: Decimal = Decimal("79.99"),
    category_id: Optional[uuid.UUID] = None,
    is_active: bool = True,
    brand: str = "TestBrand",
    description: str = "A test boot with waterproof features and leather upper.",
) -> Product:
    slug = name.lower().replace(" ", "-") + "-" + str(uuid.uuid4())[:8]
    product = Product(
        name=name,
        slug=slug,
        description=description,
        short_description="Great test boot",
        brand=brand,
        sku=f"SKU-{uuid.uuid4().hex[:8].upper()}",
        base_price=base_price,
        currency="GBP",
        stock_quantity=50,
        is_active=is_active,
        is_featured=False,
        images=["https://cdn.example.com/img1.jpg", "https://cdn.example.com/img2.jpg"],
        attributes={"material": "Leather", "waterproof": True},
        category_id=category_id,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def create_variant_in_db(
    db: AsyncSession,
    product_id: uuid.UUID,
    size: str = "8",
    color: str = "Black",
    stock_quantity: int = 20,
    price_modifier: Decimal = Decimal("0.00"),
) -> ProductVariant:
    variant = ProductVariant(
        product_id=product_id,
        name=f"UK {size} / {color}",
        sku=f"VAR-{uuid.uuid4().hex[:8].upper()}",
        size=size,
        color=color,
        material="Leather",
        price_modifier=price_modifier,
        stock_quantity=stock_quantity,
        inventory_count=stock_quantity,
        is_active=True,
    )
    db.add(variant)
    await db.commit()
    await db.refresh(variant)
    return variant


async def create_order_in_db(
    db: AsyncSession,
    user_id: uuid.UUID,
    status: str = "confirmed",
    total_amount: Decimal = Decimal("99.99"),
    order_number: Optional[str] = None,
) -> Order:
    order = Order(
        user_id=user_id,
        order_number=order_number or f"ORD-{uuid.uuid4().hex[:8].upper()}",
        status=status,
        payment_status="paid",
        subtotal=total_amount,
        shipping_cost=Decimal("4.99"),
        tax=Decimal("10.00"),
        total=total_amount,
        total_amount=total_amount,
        currency="GBP",
        shipping_address={"line1": "123 Test St", "city": "London", "postal_code": "EC1A 1BB", "country": "GB"},
        shipping_address_line1="123 Test Street",
        shipping_city="London",
        shipping_postcode="EC1A 1BB",
        shipping_country="GB",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def create_review_in_db(
    db: AsyncSession,
    product_id: uuid.UUID,
    user_id: uuid.UUID,
    rating: int = 5,
    title: str = "Great boots!",
    body: str = "Really comfortable and well-made.",
    order_id: Optional[uuid.UUID] = None,
) -> Review:
    review = Review(
        product_id=product_id,
        user_id=user_id,
        order_id=order_id,
        rating=rating,
        title=title,
        body=body,
        is_verified_purchase=(order_id is not None),
        is_approved=True,
        helpful_votes=0,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review
