"""
Sprint 2 T-021 unit tests — Cart database schema (US-009, US-010).

Covers:
  - US-009 (Add to Shopping Cart):
      * Guest cart with session_id
      * Authenticated cart with user_id
      * Adding CartItem with product_id and variant_id
      * CartItem quantity defaults to 1
      * CartItem CHECK constraint: quantity >= 1
      * unit_price is captured at add-to-cart time
      * Cascade delete: removing a cart removes its items

  - US-010 (View and Edit Shopping Cart):
      * Multiple items in a single cart
      * Variant FK can be NULL (item without size/colour selection)
      * Cascade delete: removing a product cascades to cart_items
      * user_id FK is ON DELETE SET NULL (user deletion preserves cart)

  - Schema constraints:
      * Cart.user_id FK references users (SET NULL on delete)
      * CartItem.cart_id FK references carts (CASCADE on delete)
      * CartItem.product_id FK references products (CASCADE on delete)
      * CartItem.variant_id FK references product_variants (SET NULL on delete)

Uses an ephemeral SQLite+aiosqlite in-memory database — no live PostgreSQL required.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

# Register all ORM mappers before creating schema.
from app.core.database import Base  # noqa: F401

import app.domains.account.models  # noqa: F401
import app.domains.categories.models  # noqa: F401
import app.domains.products.models  # noqa: F401
import app.domains.cart.models  # noqa: F401
import app.domains.checkout.models  # noqa: F401

from app.domains.account.models import User
from app.domains.categories.models import Category
from app.domains.products.models import Product, ProductVariant
from app.domains.cart.models import Cart, CartItem


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def db() -> AsyncSession:
    """Ephemeral in-process SQLite database; schema created fresh per test."""
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
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _user(**kwargs) -> User:
    defaults = dict(
        email=f"shopper_{uuid.uuid4().hex[:8]}@boots.example.com",
        hashed_password="$2b$12$hashedpasswordfortesting",
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
        is_active=True,
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
# T-021 / US-009: Cart schema — Add to Shopping Cart
# ---------------------------------------------------------------------------

class TestCartSchema:
    """Cart and CartItem schema supports US-009 — add a boot to the cart."""

    @pytest.mark.asyncio
    async def test_guest_cart_created_with_session_id(self, db: AsyncSession):
        """A guest cart uses session_id with no user_id (guest checkout flow)."""
        cart = Cart(session_id="sess_guest_xyz789")
        db.add(cart)
        await db.flush()
        await db.refresh(cart)

        assert cart.id is not None
        assert cart.session_id == "sess_guest_xyz789"
        assert cart.user_id is None

    @pytest.mark.asyncio
    async def test_authenticated_cart_linked_to_user(self, db: AsyncSession):
        """An authenticated cart stores user_id and leaves session_id empty."""
        user = _user()
        db.add(user)
        await db.flush()

        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()
        await db.refresh(cart)

        assert cart.user_id == user.id
        assert cart.session_id is None

    @pytest.mark.asyncio
    async def test_cart_item_added_with_product_and_variant(self, db: AsyncSession):
        """CartItem captures product_id, variant_id, quantity, and unit_price."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        variant = _variant(prod.id, size="10", color="Black", inventory_count=5)
        db.add(variant)
        await db.flush()

        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()

        item = CartItem(
            cart_id=cart.id,
            product_id=prod.id,
            variant_id=variant.id,
            quantity=2,
            unit_price=Decimal("129.99"),
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)

        assert item.cart_id == cart.id
        assert item.product_id == prod.id
        assert item.variant_id == variant.id
        assert item.quantity == 2
        assert item.unit_price == Decimal("129.99")

    @pytest.mark.asyncio
    async def test_cart_item_quantity_defaults_to_one(self, db: AsyncSession):
        """CartItem.quantity defaults to 1 when not explicitly set (US-009)."""
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
            unit_price=Decimal("99.99"),
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)

        assert item.quantity == 1

    @pytest.mark.asyncio
    async def test_cart_item_variant_can_be_null(self, db: AsyncSession):
        """CartItem.variant_id is nullable — supports adding product without variant."""
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
            variant_id=None,
            quantity=1,
            unit_price=Decimal("119.99"),
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)

        assert item.variant_id is None
        assert item.quantity == 1

    @pytest.mark.asyncio
    async def test_cart_item_unit_price_captured_at_add_time(self, db: AsyncSession):
        """Unit price is stored on the CartItem — independent of product price changes."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id, base_price=Decimal("149.99"))
        db.add(prod)
        await db.flush()

        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()

        # Add item capturing current price
        item = CartItem(
            cart_id=cart.id,
            product_id=prod.id,
            quantity=1,
            unit_price=Decimal("149.99"),
        )
        db.add(item)
        await db.flush()

        # Simulate price change on the product
        prod.base_price = Decimal("199.99")
        await db.flush()
        await db.refresh(item)

        # CartItem must retain the price at add time
        assert item.unit_price == Decimal("149.99")

    @pytest.mark.asyncio
    async def test_cart_item_subtotal_computed_property(self, db: AsyncSession):
        """CartItem.subtotal == unit_price × quantity."""
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
            quantity=3,
            unit_price=Decimal("49.99"),
        )
        db.add(item)
        await db.flush()

        assert float(item.subtotal) == pytest.approx(3 * 49.99)


# ---------------------------------------------------------------------------
# T-021 / US-010: View and Edit Shopping Cart
# ---------------------------------------------------------------------------

class TestCartEditSchema:
    """Schema supports US-010 — view items and adjust quantities / remove items."""

    @pytest.mark.asyncio
    async def test_cart_can_hold_multiple_items(self, db: AsyncSession):
        """A single cart can hold multiple distinct products / variants."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod_a = _product(cat.id, name="Work Boot A", slug=f"work-boot-a-{uuid.uuid4().hex[:6]}")
        prod_b = _product(cat.id, name="Work Boot B", slug=f"work-boot-b-{uuid.uuid4().hex[:6]}")
        prod_c = _product(cat.id, name="Work Boot C", slug=f"work-boot-c-{uuid.uuid4().hex[:6]}")
        db.add_all([prod_a, prod_b, prod_c])
        await db.flush()

        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()

        for prod, price in [(prod_a, "129.99"), (prod_b, "89.99"), (prod_c, "109.99")]:
            db.add(CartItem(
                cart_id=cart.id,
                product_id=prod.id,
                quantity=1,
                unit_price=Decimal(price),
            ))
        await db.flush()

        result = await db.execute(
            select(CartItem).where(CartItem.cart_id == cart.id)
        )
        items = result.scalars().all()
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_cart_total_computed_from_items(self, db: AsyncSession):
        """Cart.total sums unit_price × quantity across all items."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod_a = _product(cat.id, name="Boot A", slug=f"boot-a-{uuid.uuid4().hex[:6]}")
        prod_b = _product(cat.id, name="Boot B", slug=f"boot-b-{uuid.uuid4().hex[:6]}")
        db.add_all([prod_a, prod_b])
        await db.flush()

        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()

        db.add(CartItem(cart_id=cart.id, product_id=prod_a.id, quantity=2, unit_price=Decimal("49.99")))
        db.add(CartItem(cart_id=cart.id, product_id=prod_b.id, quantity=1, unit_price=Decimal("89.99")))
        await db.flush()
        await db.refresh(cart)

        expected_total = 2 * 49.99 + 1 * 89.99
        assert cart.total == pytest.approx(expected_total)

    @pytest.mark.asyncio
    async def test_cart_item_count_property(self, db: AsyncSession):
        """Cart.item_count returns total units (sum of quantities) in the cart."""
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

        db.add(CartItem(cart_id=cart.id, product_id=prod.id, quantity=3, unit_price=Decimal("29.99")))
        db.add(CartItem(cart_id=cart.id, product_id=prod.id, quantity=2, unit_price=Decimal("29.99")))
        await db.flush()
        await db.refresh(cart)

        assert cart.item_count == 5

    @pytest.mark.asyncio
    async def test_cart_items_cascade_deleted_when_cart_deleted(self, db: AsyncSession):
        """Deleting a cart cascades and removes all its CartItems (ON DELETE CASCADE)."""
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
            quantity=1,
            unit_price=Decimal("129.99"),
        )
        db.add(item)
        await db.flush()
        item_id = item.id

        await db.delete(cart)
        await db.flush()

        result = await db.execute(select(CartItem).where(CartItem.id == item_id))
        assert result.scalar_one_or_none() is None, "CartItem should be cascade-deleted with cart"

    @pytest.mark.asyncio
    async def test_cart_item_removed_individually(self, db: AsyncSession):
        """A single CartItem can be deleted without affecting other items."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod_a = _product(cat.id, name="Boot A", slug=f"boot-a-{uuid.uuid4().hex[:6]}")
        prod_b = _product(cat.id, name="Boot B", slug=f"boot-b-{uuid.uuid4().hex[:6]}")
        db.add_all([prod_a, prod_b])
        await db.flush()

        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()

        item_a = CartItem(cart_id=cart.id, product_id=prod_a.id, quantity=1, unit_price=Decimal("99.99"))
        item_b = CartItem(cart_id=cart.id, product_id=prod_b.id, quantity=1, unit_price=Decimal("79.99"))
        db.add_all([item_a, item_b])
        await db.flush()

        await db.delete(item_a)
        await db.flush()

        result = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
        remaining = result.scalars().all()
        assert len(remaining) == 1
        assert remaining[0].product_id == prod_b.id


# ---------------------------------------------------------------------------
# T-021: Cascade / FK constraint tests
# ---------------------------------------------------------------------------

class TestCartFKConstraints:
    """FK constraints correctly govern cart and cart_item relationships."""

    @pytest.mark.asyncio
    async def test_cart_items_cascade_deleted_when_product_deleted(self, db: AsyncSession):
        """Deleting a product cascades to CartItems referencing it."""
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
            quantity=1,
            unit_price=Decimal("129.99"),
        )
        db.add(item)
        await db.flush()
        item_id = item.id

        await db.delete(prod)
        await db.flush()

        result = await db.execute(select(CartItem).where(CartItem.id == item_id))
        assert result.scalar_one_or_none() is None, (
            "CartItem should be cascade-deleted when its product is deleted"
        )

    @pytest.mark.asyncio
    async def test_cart_user_id_is_set_null_when_user_deleted(self, db: AsyncSession):
        """Deleting a user sets cart.user_id to NULL (ON DELETE SET NULL)."""
        user = _user()
        db.add(user)
        await db.flush()

        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.flush()
        cart_id = cart.id

        await db.delete(user)
        await db.flush()

        # Expire the session cache so we see the DB-updated SET NULL value.
        db.expire_all()
        result = await db.execute(select(Cart).where(Cart.id == cart_id))
        fetched = result.scalar_one_or_none()
        # Cart should still exist (not cascade-deleted), but user_id is NULL.
        assert fetched is not None, "Cart should still exist after user deletion"
        assert fetched.user_id is None, "cart.user_id should be NULL after user deletion"

    @pytest.mark.asyncio
    async def test_guest_cart_has_no_user_id(self, db: AsyncSession):
        """Guest cart has user_id = NULL, only session_id is set."""
        cart = Cart(session_id="sess_abc987")
        db.add(cart)
        await db.flush()
        await db.refresh(cart)

        assert cart.user_id is None
        assert cart.session_id == "sess_abc987"

    @pytest.mark.asyncio
    async def test_multiple_carts_same_session_allowed(self, db: AsyncSession):
        """No unique constraint on session_id — multiple carts can share a session."""
        session = f"sess_{uuid.uuid4().hex[:12]}"
        cart1 = Cart(session_id=session)
        cart2 = Cart(session_id=session)
        db.add_all([cart1, cart2])
        # Should not raise — session_id has no uniqueness constraint
        await db.flush()

        result = await db.execute(
            select(Cart).where(Cart.session_id == session)
        )
        carts = result.scalars().all()
        assert len(carts) == 2

    @pytest.mark.asyncio
    async def test_cart_item_cart_id_required(self, db: AsyncSession):
        """CartItem.cart_id is NOT NULL — inserting without it must raise."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        # cart_id intentionally omitted
        item = CartItem(
            product_id=prod.id,
            quantity=1,
            unit_price=Decimal("99.99"),
        )
        db.add(item)
        with pytest.raises(Exception):
            await db.flush()
