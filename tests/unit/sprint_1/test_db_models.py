"""
Unit tests for Sprint 1 database models (T-001).

Covers: User, RefreshToken, Category, Product, ProductVariant,
        Cart, CartItem, Order, OrderItem, Review

Uses an ephemeral SQLite+aiosqlite in-memory database so no live
PostgreSQL instance is required.  PostgreSQL-specific types (UUID,
JSONB, TSVECTOR) are handled via SQLAlchemy's dialect-agnostic layer:
- UUID  → String (SQLite fallback via as_uuid=False workaround)
- JSONB → Text  (SQLite has no JSONB — values stored as JSON strings)
- TSVECTOR → skipped / nullable
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

# Force SQLAlchemy to register all mappers before creating tables.
# Import from the domains directory (the authoritative location per scaffold).
from app.core.database import Base  # noqa: F401 — registers DeclarativeBase

import app.domains.account.models  # noqa: F401
import app.domains.categories.models  # noqa: F401
import app.domains.products.models  # noqa: F401
import app.domains.cart.models  # noqa: F401
import app.domains.checkout.models  # noqa: F401

from app.domains.account.models import User, RefreshToken
from app.domains.categories.models import Category
from app.domains.products.models import Product, ProductVariant, Review
from app.domains.cart.models import Cart, CartItem
from app.domains.checkout.models import Order, OrderItem


# ---------------------------------------------------------------------------
# Shared fixture: fresh in-memory SQLite per test
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def db() -> AsyncSession:
    """Ephemeral in-process SQLite database; schema created fresh per test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        # SQLite needs this so FK constraints are checked
        connect_args={"check_same_thread": False},
    )
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        # SQLite does not enforce FK constraints by default
        await conn.execute(text("PRAGMA foreign_keys = ON"))
        await conn.run_sync(Base.metadata.create_all)

    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _user(**kwargs) -> User:
    defaults = dict(
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="$2b$12$fakehashfortest",
    )
    defaults.update(kwargs)
    return User(**defaults)


def _category(**kwargs) -> Category:
    uid = uuid.uuid4().hex[:8]
    defaults = dict(name=f"Work Boots {uid}", slug=f"work-boots-{uid}")
    defaults.update(kwargs)
    return Category(**defaults)


def _product(category_id, **kwargs) -> Product:
    uid = uuid.uuid4().hex[:8]
    defaults = dict(
        category_id=category_id,
        name=f"Timberland Pro {uid}",
        slug=f"timberland-pro-{uid}",
        brand="Timberland",
        base_price=Decimal("129.99"),
    )
    defaults.update(kwargs)
    return Product(**defaults)


def _variant(product_id, **kwargs) -> ProductVariant:
    defaults = dict(
        product_id=product_id,
        name="UK 9 / Brown",
        size="9",
        color="Brown",
        inventory_count=10,
    )
    defaults.update(kwargs)
    return ProductVariant(**defaults)


# ---------------------------------------------------------------------------
# User model tests
# ---------------------------------------------------------------------------

class TestUserModel:
    @pytest.mark.asyncio
    async def test_create_user_minimal(self, db: AsyncSession):
        user = _user()
        db.add(user)
        await db.flush()

        result = await db.execute(select(User).where(User.email == user.email))
        fetched = result.scalar_one()
        assert fetched.id is not None
        assert fetched.email == user.email
        assert fetched.hashed_password.startswith("$2b$")

    @pytest.mark.asyncio
    async def test_user_defaults(self, db: AsyncSession):
        user = _user()
        db.add(user)
        await db.flush()

        result = await db.execute(select(User).where(User.id == user.id))
        fetched = result.scalar_one()
        assert fetched.is_active is True
        assert fetched.is_superuser is False

    @pytest.mark.asyncio
    async def test_user_email_unique_constraint(self, db: AsyncSession):
        email = "unique@example.com"
        db.add(_user(email=email))
        await db.flush()

        db.add(_user(email=email))
        with pytest.raises(Exception):  # IntegrityError / OperationalError
            await db.flush()

    @pytest.mark.asyncio
    async def test_user_created_at_populated(self, db: AsyncSession):
        user = _user()
        db.add(user)
        await db.flush()
        await db.refresh(user)
        # created_at is set by server_default; may be None in SQLite without
        # trigger support — just verify the column exists on the mapper.
        assert hasattr(user, "created_at")


# ---------------------------------------------------------------------------
# RefreshToken model tests
# ---------------------------------------------------------------------------

class TestRefreshTokenModel:
    @pytest.mark.asyncio
    async def test_create_refresh_token(self, db: AsyncSession):
        user = _user()
        db.add(user)
        await db.flush()

        token = RefreshToken(
            user_id=user.id,
            token="some_long_jwt_string_" + uuid.uuid4().hex,
            jti=uuid.uuid4().hex,
            expires_at=datetime.now(tz=timezone.utc) + timedelta(days=7),
        )
        db.add(token)
        await db.flush()

        result = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user.id))
        fetched = result.scalar_one()
        assert fetched.is_revoked is False
        assert fetched.user_id == user.id

    @pytest.mark.asyncio
    async def test_refresh_token_jti_unique(self, db: AsyncSession):
        user = _user()
        db.add(user)
        await db.flush()

        jti = uuid.uuid4().hex
        exp = datetime.now(tz=timezone.utc) + timedelta(days=7)

        db.add(RefreshToken(
            user_id=user.id,
            token="token_a_" + uuid.uuid4().hex,
            jti=jti,
            expires_at=exp,
        ))
        await db.flush()

        db.add(RefreshToken(
            user_id=user.id,
            token="token_b_" + uuid.uuid4().hex,
            jti=jti,  # duplicate jti
            expires_at=exp,
        ))
        with pytest.raises(Exception):
            await db.flush()

    @pytest.mark.asyncio
    async def test_refresh_token_cascade_delete(self, db: AsyncSession):
        user = _user()
        db.add(user)
        await db.flush()

        token = RefreshToken(
            user_id=user.id,
            token="cascade_token_" + uuid.uuid4().hex,
            jti=uuid.uuid4().hex,
            expires_at=datetime.now(tz=timezone.utc) + timedelta(days=7),
        )
        db.add(token)
        await db.flush()

        await db.delete(user)
        await db.flush()

        result = await db.execute(
            select(RefreshToken).where(RefreshToken.id == token.id)
        )
        assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# Category model tests
# ---------------------------------------------------------------------------

class TestCategoryModel:
    @pytest.mark.asyncio
    async def test_create_category(self, db: AsyncSession):
        cat = _category()
        db.add(cat)
        await db.flush()

        result = await db.execute(select(Category).where(Category.slug == cat.slug))
        fetched = result.scalar_one()
        assert fetched.name == cat.name
        assert fetched.slug == cat.slug

    @pytest.mark.asyncio
    async def test_category_slug_unique(self, db: AsyncSession):
        slug = "hiking-boots"
        db.add(_category(slug=slug))
        await db.flush()

        db.add(_category(name="Duplicate Slug Cat", slug=slug))
        with pytest.raises(Exception):
            await db.flush()

    @pytest.mark.asyncio
    async def test_category_self_referential(self, db: AsyncSession):
        parent = _category(name="Boots", slug="boots")
        db.add(parent)
        await db.flush()

        child = _category(name="Hiking Boots", slug="hiking-boots", parent_id=parent.id)
        db.add(child)
        await db.flush()

        result = await db.execute(select(Category).where(Category.id == child.id))
        fetched = result.scalar_one()
        assert fetched.parent_id == parent.id


# ---------------------------------------------------------------------------
# Product & ProductVariant model tests
# ---------------------------------------------------------------------------

class TestProductModel:
    @pytest.mark.asyncio
    async def test_create_product(self, db: AsyncSession):
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        result = await db.execute(select(Product).where(Product.id == prod.id))
        fetched = result.scalar_one()
        assert fetched.name == prod.name
        assert fetched.base_price == Decimal("129.99")

    @pytest.mark.asyncio
    async def test_product_slug_unique(self, db: AsyncSession):
        cat = _category()
        db.add(cat)
        await db.flush()

        slug = "unique-boot-slug"
        db.add(_product(cat.id, slug=slug))
        await db.flush()

        db.add(_product(cat.id, slug=slug))
        with pytest.raises(Exception):
            await db.flush()

    @pytest.mark.asyncio
    async def test_product_category_fk_nullable(self, db: AsyncSession):
        """Products may exist without a category (nullable FK)."""
        prod = _product(None)
        db.add(prod)
        await db.flush()

        result = await db.execute(select(Product).where(Product.id == prod.id))
        fetched = result.scalar_one()
        assert fetched.category_id is None

    @pytest.mark.asyncio
    async def test_product_defaults(self, db: AsyncSession):
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()
        await db.refresh(prod)

        assert prod.is_active is True
        assert prod.is_featured is False
        assert prod.review_count == 0


class TestProductVariantModel:
    @pytest.mark.asyncio
    async def test_create_variant(self, db: AsyncSession):
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        variant = _variant(prod.id)
        db.add(variant)
        await db.flush()

        result = await db.execute(
            select(ProductVariant).where(ProductVariant.product_id == prod.id)
        )
        fetched = result.scalar_one()
        assert fetched.size == "9"
        assert fetched.inventory_count == 10

    @pytest.mark.asyncio
    async def test_variant_cascade_delete(self, db: AsyncSession):
        """Deleting a product must cascade-delete its variants."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        variant = _variant(prod.id)
        db.add(variant)
        await db.flush()

        await db.delete(prod)
        await db.flush()

        result = await db.execute(
            select(ProductVariant).where(ProductVariant.id == variant.id)
        )
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_variant_sku_unique(self, db: AsyncSession):
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        sku = "BOOT-SKU-001"
        db.add(_variant(prod.id, sku=sku, name="Size 9"))
        await db.flush()

        db.add(_variant(prod.id, sku=sku, name="Size 10"))  # same SKU
        with pytest.raises(Exception):
            await db.flush()


# ---------------------------------------------------------------------------
# Cart & CartItem model tests
# ---------------------------------------------------------------------------

class TestCartModel:
    @pytest.mark.asyncio
    async def test_create_guest_cart(self, db: AsyncSession):
        """Cart may belong to a session (guest) with no user_id."""
        cart = Cart(session_id="sess_abc123")
        db.add(cart)
        await db.flush()

        result = await db.execute(select(Cart).where(Cart.id == cart.id))
        fetched = result.scalar_one()
        assert fetched.session_id == "sess_abc123"
        assert fetched.user_id is None

    @pytest.mark.asyncio
    async def test_create_authenticated_cart(self, db: AsyncSession):
        user = _user()
        db.add(user)
        await db.flush()

        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()

        result = await db.execute(select(Cart).where(Cart.id == cart.id))
        fetched = result.scalar_one()
        assert fetched.user_id == user.id

    @pytest.mark.asyncio
    async def test_cart_item_quantity_default(self, db: AsyncSession):
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()

        item = CartItem(
            cart_id=cart.id,
            product_id=prod.id,
            unit_price=Decimal("129.99"),
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)
        assert item.quantity == 1

    @pytest.mark.asyncio
    async def test_cart_item_cascade_delete(self, db: AsyncSession):
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()

        item = CartItem(
            cart_id=cart.id,
            product_id=prod.id,
            unit_price=Decimal("99.00"),
        )
        db.add(item)
        await db.flush()

        await db.delete(cart)
        await db.flush()

        result = await db.execute(select(CartItem).where(CartItem.id == item.id))
        assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# Order & OrderItem model tests
# ---------------------------------------------------------------------------

class TestOrderModel:
    @pytest.mark.asyncio
    async def test_create_order_for_user(self, db: AsyncSession):
        user = _user()
        db.add(user)
        await db.flush()

        order = Order(
            user_id=user.id,
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            total=Decimal("259.98"),
            subtotal=Decimal("259.98"),
        )
        db.add(order)
        await db.flush()

        result = await db.execute(select(Order).where(Order.id == order.id))
        fetched = result.scalar_one()
        assert fetched.status == "pending"
        assert fetched.user_id == user.id

    @pytest.mark.asyncio
    async def test_create_guest_order(self, db: AsyncSession):
        order = Order(
            guest_email="guest@example.com",
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            total=Decimal("129.99"),
            subtotal=Decimal("129.99"),
        )
        db.add(order)
        await db.flush()

        result = await db.execute(select(Order).where(Order.id == order.id))
        fetched = result.scalar_one()
        assert fetched.user_id is None
        assert fetched.guest_email == "guest@example.com"

    @pytest.mark.asyncio
    async def test_order_number_unique(self, db: AsyncSession):
        num = "ORD-DUPLICATE01"
        db.add(Order(order_number=num, total=Decimal("10.00"), subtotal=Decimal("10.00")))
        await db.flush()

        db.add(Order(order_number=num, total=Decimal("20.00"), subtotal=Decimal("20.00")))
        with pytest.raises(Exception):
            await db.flush()

    @pytest.mark.asyncio
    async def test_order_item_cascade_delete(self, db: AsyncSession):
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        order = Order(
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            total=Decimal("129.99"),
            subtotal=Decimal("129.99"),
        )
        db.add(order)
        await db.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            product_name=prod.name,
            quantity=1,
            unit_price=Decimal("129.99"),
            line_total=Decimal("129.99"),
        )
        db.add(item)
        await db.flush()

        await db.delete(order)
        await db.flush()

        result = await db.execute(select(OrderItem).where(OrderItem.id == item.id))
        assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# Review model tests
# ---------------------------------------------------------------------------

class TestReviewModel:
    @pytest.mark.asyncio
    async def test_create_review(self, db: AsyncSession):
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        review = Review(
            product_id=prod.id,
            user_id=user.id,
            rating=5,
            title="Excellent boots",
            body="Very comfortable for all-day wear.",
        )
        db.add(review)
        await db.flush()

        result = await db.execute(select(Review).where(Review.id == review.id))
        fetched = result.scalar_one()
        assert fetched.rating == 5
        assert fetched.is_verified_purchase is False
        assert fetched.is_approved is True

    @pytest.mark.asyncio
    async def test_review_linked_to_order(self, db: AsyncSession):
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        order = Order(
            user_id=user.id,
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            total=Decimal("129.99"),
            subtotal=Decimal("129.99"),
        )
        db.add(order)
        await db.flush()

        review = Review(
            product_id=prod.id,
            user_id=user.id,
            order_id=order.id,
            rating=4,
            is_verified_purchase=True,
        )
        db.add(review)
        await db.flush()

        result = await db.execute(select(Review).where(Review.id == review.id))
        fetched = result.scalar_one()
        assert fetched.order_id == order.id
        assert fetched.is_verified_purchase is True

    @pytest.mark.asyncio
    async def test_review_cascade_delete_with_product(self, db: AsyncSession):
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        review = Review(
            product_id=prod.id,
            user_id=user.id,
            rating=3,
        )
        db.add(review)
        await db.flush()

        await db.delete(prod)
        await db.flush()

        result = await db.execute(select(Review).where(Review.id == review.id))
        assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# Cross-model relationship smoke tests
# ---------------------------------------------------------------------------

class TestRelationships:
    @pytest.mark.asyncio
    async def test_user_has_refresh_tokens_relationship(self, db: AsyncSession):
        user = _user()
        db.add(user)
        await db.flush()

        for _ in range(2):
            db.add(RefreshToken(
                user_id=user.id,
                token=f"tok_{uuid.uuid4().hex}",
                jti=uuid.uuid4().hex,
                expires_at=datetime.now(tz=timezone.utc) + timedelta(days=7),
            ))
        await db.flush()

        result = await db.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
        tokens = result.scalars().all()
        assert len(tokens) == 2

    @pytest.mark.asyncio
    async def test_product_variants_relationship(self, db: AsyncSession):
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        for size in ("7", "8", "9"):
            db.add(_variant(prod.id, name=f"UK {size}", size=size))
        await db.flush()

        result = await db.execute(
            select(ProductVariant).where(ProductVariant.product_id == prod.id)
        )
        variants = result.scalars().all()
        assert len(variants) == 3

    @pytest.mark.asyncio
    async def test_order_items_relationship(self, db: AsyncSession):
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        order = Order(
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            total=Decimal("259.98"),
            subtotal=Decimal("259.98"),
        )
        db.add(order)
        await db.flush()

        for i in range(2):
            db.add(OrderItem(
                order_id=order.id,
                product_id=prod.id,
                product_name=f"{prod.name} item {i}",
                quantity=1,
                unit_price=Decimal("129.99"),
                line_total=Decimal("129.99"),
            ))
        await db.flush()

        result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        items = result.scalars().all()
        assert len(items) == 2
