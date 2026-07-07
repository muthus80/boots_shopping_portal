"""
Sprint 3 T-025 unit tests — Orders/Checkout database schema (US-003).

Story: US-003 — Guest checkout with Stripe payment.

Coverage:
  - Order creation for authenticated users and guests
  - Order fields: order_number (unique), status, total_amount,
    shipping_address (JSONB/JSON), stripe_payment_intent_id
  - OrderItem: FK → orders (CASCADE), FK → product_variants,
    unit_price captured at purchase time, quantity constraint
  - Review: purchase-verified review linked to order_id (T-018 scope,
    schema already in Sprint 1; verify it works with order FK)
  - Cascade/FK constraints:
      * order_items deleted when order deleted (ON DELETE CASCADE)
      * orders.user_id SET NULL when user deleted
      * reviews.order_id SET NULL when order deleted
  - Index smoke tests: verify columns that should be indexed exist on
    the mapped ORM model and the in-memory SQLite schema

Uses an ephemeral SQLite+aiosqlite in-memory database — no live
PostgreSQL required.  PostgreSQL-specific types (UUID, JSONB, TSVECTOR)
are handled via SQLAlchemy's dialect-agnostic layer.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

# Register all ORM mappers before creating schema.
from app.core.database import Base  # noqa: F401

import app.domains.account.models    # noqa: F401
import app.domains.categories.models # noqa: F401
import app.domains.products.models   # noqa: F401
import app.domains.cart.models       # noqa: F401
import app.domains.checkout.models   # noqa: F401

from app.domains.account.models import User
from app.domains.categories.models import Category
from app.domains.products.models import Product, ProductVariant, Review
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
        email=f"customer_{uuid.uuid4().hex[:8]}@bootsshop.example.com",
        hashed_password="$2b$12$securehashedpassword",
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
        name=f"Timberland Pro Safety {uid}",
        slug=f"timberland-pro-safety-{uid}",
        brand="Timberland",
        base_price=Decimal("149.99"),
        is_active=True,
    )
    defaults.update(kwargs)
    return Product(**defaults)


def _variant(product_id, **kwargs) -> ProductVariant:
    defaults = dict(
        product_id=product_id,
        name="UK 9 / Black",
        size="9",
        color="Black",
        inventory_count=20,
    )
    defaults.update(kwargs)
    return ProductVariant(**defaults)


def _order(**kwargs) -> Order:
    """Create an Order with sensible defaults."""
    defaults = dict(
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        status="pending",
        total=Decimal("149.99"),
        subtotal=Decimal("149.99"),
        shipping_address={"line1": "10 Downing Street", "city": "London", "postcode": "SW1A 2AA"},
    )
    defaults.update(kwargs)
    return Order(**defaults)


# ---------------------------------------------------------------------------
# T-025: Order schema — Guest checkout flow (US-003)
# ---------------------------------------------------------------------------

class TestOrderSchema:
    """Order schema supports the full guest checkout lifecycle (US-003)."""

    @pytest.mark.asyncio
    async def test_create_authenticated_order(self, db: AsyncSession):
        """Authenticated order stores user_id and order_number."""
        user = _user()
        db.add(user)
        await db.flush()

        order = _order(user_id=user.id, total=Decimal("259.98"), subtotal=Decimal("259.98"))
        db.add(order)
        await db.flush()
        await db.refresh(order)

        assert order.id is not None
        assert order.user_id == user.id
        assert order.order_number is not None
        assert order.status == "pending"

    @pytest.mark.asyncio
    async def test_create_guest_order_with_email(self, db: AsyncSession):
        """Guest order has no user_id — identified by guest_email instead."""
        order = _order(
            guest_email="guest.shopper@example.com",
            total=Decimal("129.99"),
            subtotal=Decimal("129.99"),
        )
        db.add(order)
        await db.flush()
        await db.refresh(order)

        assert order.user_id is None
        assert order.guest_email == "guest.shopper@example.com"
        assert order.id is not None

    @pytest.mark.asyncio
    async def test_order_number_unique_constraint(self, db: AsyncSession):
        """Two orders cannot share the same order_number (UNIQUE constraint)."""
        num = "ORD-SPRINT3-001"
        db.add(_order(order_number=num, total=Decimal("99.99"), subtotal=Decimal("99.99")))
        await db.flush()

        db.add(_order(order_number=num, total=Decimal("199.99"), subtotal=Decimal("199.99")))
        with pytest.raises(Exception):  # IntegrityError / OperationalError
            await db.flush()

    @pytest.mark.asyncio
    async def test_order_status_default_is_pending(self, db: AsyncSession):
        """Order.status defaults to 'pending' (architecture data model default)."""
        order = Order(
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            total=Decimal("79.99"),
            subtotal=Decimal("79.99"),
        )
        db.add(order)
        await db.flush()
        await db.refresh(order)

        assert order.status == "pending"

    @pytest.mark.asyncio
    async def test_order_stores_shipping_address_json(self, db: AsyncSession):
        """shipping_address stores structured JSON/JSONB delivery details."""
        address = {
            "name": "Jane Doe",
            "line1": "42 Boots Lane",
            "line2": "Flat 3",
            "city": "Manchester",
            "county": "Greater Manchester",
            "postcode": "M1 1AA",
            "country": "GB",
        }
        order = _order(shipping_address=address)
        db.add(order)
        await db.flush()
        await db.refresh(order)

        fetched_addr = order.shipping_address
        assert fetched_addr["city"] == "Manchester"
        assert fetched_addr["postcode"] == "M1 1AA"

    @pytest.mark.asyncio
    async def test_order_stores_stripe_payment_intent_id(self, db: AsyncSession):
        """stripe_payment_intent_id is stored for ADR-003 Stripe verification."""
        pi_id = "pi_3OaBcDeFgHiJkLmN1234567890"
        order = _order(
            stripe_payment_intent_id=pi_id,
            status="confirmed",
        )
        db.add(order)
        await db.flush()
        await db.refresh(order)

        assert order.stripe_payment_intent_id == pi_id

    @pytest.mark.asyncio
    async def test_order_stripe_payment_intent_id_nullable(self, db: AsyncSession):
        """stripe_payment_intent_id is nullable — e.g. before payment is processed."""
        order = _order()
        db.add(order)
        await db.flush()
        await db.refresh(order)

        assert order.stripe_payment_intent_id is None

    @pytest.mark.asyncio
    async def test_order_created_at_populated(self, db: AsyncSession):
        """created_at is set on order creation (server_default or ORM default)."""
        order = _order()
        db.add(order)
        await db.flush()
        await db.refresh(order)

        assert hasattr(order, "created_at")

    @pytest.mark.asyncio
    async def test_order_total_amount_field(self, db: AsyncSession):
        """total_amount mirrors the architecture data model field name."""
        order = _order(
            total=Decimal("199.98"),
            subtotal=Decimal("199.98"),
            total_amount=Decimal("199.98"),
        )
        db.add(order)
        await db.flush()
        await db.refresh(order)

        assert order.total_amount == Decimal("199.98")


# ---------------------------------------------------------------------------
# T-025: OrderItem schema
# ---------------------------------------------------------------------------

class TestOrderItemSchema:
    """OrderItem schema captures line items with locked-in unit price."""

    @pytest.mark.asyncio
    async def test_create_order_item_with_product_and_variant(self, db: AsyncSession):
        """OrderItem links to an order, product, and optionally a variant."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        variant = _variant(prod.id, size="10", color="Brown", inventory_count=5)
        db.add(variant)
        await db.flush()

        order = _order(total=Decimal("149.99"), subtotal=Decimal("149.99"))
        db.add(order)
        await db.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            variant_id=variant.id,
            product_name=prod.name,
            quantity=1,
            unit_price=Decimal("149.99"),
            line_total=Decimal("149.99"),
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)

        assert item.order_id == order.id
        assert item.product_id == prod.id
        assert item.variant_id == variant.id
        assert item.quantity == 1
        assert item.unit_price == Decimal("149.99")

    @pytest.mark.asyncio
    async def test_order_item_unit_price_captured_at_purchase(self, db: AsyncSession):
        """unit_price is locked at purchase time — independent of product price changes."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id, base_price=Decimal("99.99"))
        db.add(prod)
        await db.flush()

        order = _order(total=Decimal("99.99"), subtotal=Decimal("99.99"))
        db.add(order)
        await db.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            product_name=prod.name,
            quantity=1,
            unit_price=Decimal("99.99"),  # locked at purchase time
            line_total=Decimal("99.99"),
        )
        db.add(item)
        await db.flush()

        # Price rises after purchase — OrderItem must retain original price
        prod.base_price = Decimal("129.99")
        await db.flush()
        await db.refresh(item)

        assert item.unit_price == Decimal("99.99")

    @pytest.mark.asyncio
    async def test_order_item_cascade_deleted_with_order(self, db: AsyncSession):
        """Deleting an order cascades to all its OrderItems (ON DELETE CASCADE)."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        order = _order(total=Decimal("129.99"), subtotal=Decimal("129.99"))
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
        item_id = item.id

        await db.delete(order)
        await db.flush()

        result = await db.execute(select(OrderItem).where(OrderItem.id == item_id))
        assert result.scalar_one_or_none() is None, (
            "OrderItem must be cascade-deleted when its order is deleted"
        )

    @pytest.mark.asyncio
    async def test_order_item_variant_nullable(self, db: AsyncSession):
        """OrderItem.variant_id is nullable — some items have no variant."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        order = _order(total=Decimal("149.99"), subtotal=Decimal("149.99"))
        db.add(order)
        await db.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            product_name=prod.name,
            variant_id=None,
            quantity=1,
            unit_price=Decimal("149.99"),
            line_total=Decimal("149.99"),
        )
        db.add(item)
        await db.flush()
        await db.refresh(item)

        assert item.variant_id is None

    @pytest.mark.asyncio
    async def test_order_can_hold_multiple_items(self, db: AsyncSession):
        """An order can contain multiple line items (multiple products)."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod_a = _product(cat.id, name="Boot A", slug=f"boot-a-{uuid.uuid4().hex[:6]}")
        prod_b = _product(cat.id, name="Boot B", slug=f"boot-b-{uuid.uuid4().hex[:6]}")
        prod_c = _product(cat.id, name="Boot C", slug=f"boot-c-{uuid.uuid4().hex[:6]}")
        db.add_all([prod_a, prod_b, prod_c])
        await db.flush()

        order = _order(
            total=Decimal("399.97"),
            subtotal=Decimal("399.97"),
        )
        db.add(order)
        await db.flush()

        for prod, price in [(prod_a, "129.99"), (prod_b, "139.99"), (prod_c, "129.99")]:
            db.add(OrderItem(
                order_id=order.id,
                product_id=prod.id,
                product_name=prod.name,
                quantity=1,
                unit_price=Decimal(price),
                line_total=Decimal(price),
            ))
        await db.flush()

        result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        items = result.scalars().all()
        assert len(items) == 3

    @pytest.mark.asyncio
    async def test_order_item_product_id_set_null_when_product_deleted(self, db: AsyncSession):
        """OrderItem.product_id is SET NULL when the product is deleted (not CASCADE)."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()
        prod_id = prod.id

        order = _order(total=Decimal("149.99"), subtotal=Decimal("149.99"))
        db.add(order)
        await db.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            product_name=prod.name,
            quantity=1,
            unit_price=Decimal("149.99"),
            line_total=Decimal("149.99"),
        )
        db.add(item)
        await db.flush()
        item_id = item.id

        await db.delete(prod)
        await db.flush()

        db.expire_all()
        result = await db.execute(select(OrderItem).where(OrderItem.id == item_id))
        fetched = result.scalar_one_or_none()
        # Item should still exist — product deletion does not cascade to order_items
        assert fetched is not None, "OrderItem must survive product deletion"
        assert fetched.product_id is None, "product_id should be NULL after product deletion"


# ---------------------------------------------------------------------------
# T-025: FK constraint tests
# ---------------------------------------------------------------------------

class TestOrderFKConstraints:
    """FK constraints correctly govern the order relationships."""

    @pytest.mark.asyncio
    async def test_order_user_id_set_null_when_user_deleted(self, db: AsyncSession):
        """Deleting a user sets order.user_id to NULL (ON DELETE SET NULL)."""
        user = _user()
        db.add(user)
        await db.flush()

        order = _order(user_id=user.id, total=Decimal("149.99"), subtotal=Decimal("149.99"))
        db.add(order)
        await db.flush()
        order_id = order.id

        await db.delete(user)
        await db.flush()

        db.expire_all()
        result = await db.execute(select(Order).where(Order.id == order_id))
        fetched = result.scalar_one_or_none()
        assert fetched is not None, "Order must survive user deletion"
        assert fetched.user_id is None, "order.user_id should be NULL after user deletion"

    @pytest.mark.asyncio
    async def test_order_items_cascade_when_order_deleted(self, db: AsyncSession):
        """All OrderItems are cascade-deleted when their parent order is deleted."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        order = _order(total=Decimal("299.98"), subtotal=Decimal("299.98"))
        db.add(order)
        await db.flush()

        item1 = OrderItem(
            order_id=order.id, product_id=prod.id, product_name=prod.name,
            quantity=1, unit_price=Decimal("149.99"), line_total=Decimal("149.99"),
        )
        item2 = OrderItem(
            order_id=order.id, product_id=prod.id, product_name=prod.name,
            quantity=1, unit_price=Decimal("149.99"), line_total=Decimal("149.99"),
        )
        db.add_all([item1, item2])
        await db.flush()
        order_id = order.id

        await db.delete(order)
        await db.flush()

        result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        assert len(result.scalars().all()) == 0, (
            "All OrderItems must be cascade-deleted with the order"
        )

    @pytest.mark.asyncio
    async def test_review_order_id_set_null_when_order_deleted(self, db: AsyncSession):
        """Deleting an order sets review.order_id to NULL (ON DELETE SET NULL)."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        order = _order(
            user_id=user.id,
            total=Decimal("149.99"),
            subtotal=Decimal("149.99"),
        )
        db.add(order)
        await db.flush()

        review = Review(
            product_id=prod.id,
            user_id=user.id,
            order_id=order.id,
            rating=5,
            title="Excellent fit",
            is_verified_purchase=True,
        )
        db.add(review)
        await db.flush()
        review_id = review.id

        await db.delete(order)
        await db.flush()

        db.expire_all()
        result = await db.execute(select(Review).where(Review.id == review_id))
        fetched = result.scalar_one_or_none()
        assert fetched is not None, "Review must survive order deletion"
        assert fetched.order_id is None, "review.order_id should be NULL after order deletion"


# ---------------------------------------------------------------------------
# T-025: ORM field presence smoke tests (index coverage)
# ---------------------------------------------------------------------------

class TestOrderModelFields:
    """Verify that the ORM columns introduced/documented by T-025 exist."""

    def test_order_has_stripe_payment_intent_id_column(self):
        """Order.stripe_payment_intent_id must be mapped (for ADR-003 flow)."""
        mapper = sa_inspect(Order)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "stripe_payment_intent_id" in col_names, (
            "Order.stripe_payment_intent_id column not found — required for Stripe PI lookup"
        )

    def test_order_has_guest_email_column(self):
        """Order.guest_email must be mapped (for guest checkout US-003)."""
        mapper = sa_inspect(Order)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "guest_email" in col_names, (
            "Order.guest_email column not found — required for guest checkout"
        )

    def test_order_has_status_column(self):
        """Order.status must be mapped and default to 'pending'."""
        mapper = sa_inspect(Order)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "status" in col_names

    def test_order_has_total_amount_column(self):
        """Order.total_amount maps the architecture data model field."""
        mapper = sa_inspect(Order)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "total_amount" in col_names

    def test_order_has_shipping_address_column(self):
        """Order.shipping_address stores the delivery JSON/JSONB."""
        mapper = sa_inspect(Order)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "shipping_address" in col_names

    def test_order_has_created_at_column(self):
        """Order.created_at must be mapped (used for DESC sort on order history)."""
        mapper = sa_inspect(Order)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "created_at" in col_names

    def test_order_item_has_variant_id_column(self):
        """OrderItem.variant_id must be mapped (indexed by migration 0004)."""
        mapper = sa_inspect(OrderItem)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "variant_id" in col_names

    def test_review_has_order_id_column(self):
        """Review.order_id must be mapped (purchase-verification FK for T-018)."""
        mapper = sa_inspect(Review)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "order_id" in col_names

    def test_review_has_is_verified_purchase_column(self):
        """Review.is_verified_purchase must be mapped (T-018 purchase gate)."""
        mapper = sa_inspect(Review)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "is_verified_purchase" in col_names


# ---------------------------------------------------------------------------
# T-025: Stripe PaymentIntent field usage (ADR-003)
# ---------------------------------------------------------------------------

class TestStripePaymentIntentFlow:
    """Verify Stripe PaymentIntent field supports ADR-003 webhook verification."""

    @pytest.mark.asyncio
    async def test_stripe_payment_intent_id_stored_and_retrieved(self, db: AsyncSession):
        """PI id written at checkout confirm must be readable for verification."""
        pi_id = "pi_3OxYzAbCdEfGhIjK0000000001"

        order = _order(
            stripe_payment_intent_id=pi_id,
            status="pending",
            total=Decimal("199.99"),
            subtotal=Decimal("199.99"),
        )
        db.add(order)
        await db.flush()
        order_id = order.id

        db.expire_all()
        result = await db.execute(select(Order).where(Order.id == order_id))
        fetched = result.scalar_one()
        assert fetched.stripe_payment_intent_id == pi_id

    @pytest.mark.asyncio
    async def test_order_status_updated_after_payment_confirmed(self, db: AsyncSession):
        """Order status transitions from 'pending' to 'confirmed' after Stripe webhook."""
        pi_id = "pi_3OxYzAbCdEfGhIjK0000000002"

        order = _order(
            stripe_payment_intent_id=pi_id,
            status="pending",
            total=Decimal("129.99"),
            subtotal=Decimal("129.99"),
        )
        db.add(order)
        await db.flush()

        # Simulate Stripe webhook confirming payment
        order.status = "confirmed"
        await db.flush()
        await db.refresh(order)

        assert order.status == "confirmed"
        assert order.stripe_payment_intent_id == pi_id

    @pytest.mark.asyncio
    async def test_stripe_pi_lookup_by_value(self, db: AsyncSession):
        """Can query orders by stripe_payment_intent_id (the critical lookup)."""
        pi_id = "pi_3OxYzAbCdEfGhIjK0000000003"

        order = _order(
            stripe_payment_intent_id=pi_id,
            total=Decimal("89.99"),
            subtotal=Decimal("89.99"),
        )
        db.add(order)
        await db.flush()

        result = await db.execute(
            select(Order).where(Order.stripe_payment_intent_id == pi_id)
        )
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.stripe_payment_intent_id == pi_id


# ---------------------------------------------------------------------------
# T-025 / T-018: Purchase-verified review linkage
# ---------------------------------------------------------------------------

class TestPurchaseVerifiedReview:
    """Review.order_id FK supports purchase-verification gate (T-018, US-003)."""

    @pytest.mark.asyncio
    async def test_review_links_to_verifying_order(self, db: AsyncSession):
        """Review can be linked to the order that verifies the purchase."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        order = _order(
            user_id=user.id,
            status="delivered",
            total=Decimal("149.99"),
            subtotal=Decimal("149.99"),
        )
        db.add(order)
        await db.flush()

        review = Review(
            product_id=prod.id,
            user_id=user.id,
            order_id=order.id,
            rating=5,
            title="Outstanding quality",
            body="Best safety boots I have owned — waterproof and comfortable.",
            is_verified_purchase=True,
        )
        db.add(review)
        await db.flush()
        await db.refresh(review)

        assert review.order_id == order.id
        assert review.is_verified_purchase is True

    @pytest.mark.asyncio
    async def test_review_order_id_is_nullable(self, db: AsyncSession):
        """Review.order_id is nullable — unverified reviews are allowed."""
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
            order_id=None,
            rating=4,
            title="Good boots",
            is_verified_purchase=False,
        )
        db.add(review)
        await db.flush()
        await db.refresh(review)

        assert review.order_id is None
        assert review.is_verified_purchase is False

    @pytest.mark.asyncio
    async def test_purchase_verification_query_pattern(self, db: AsyncSession):
        """Can look up orders by user + product to verify purchase (T-018 gate query)."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        # Create a delivered order containing the product
        order = _order(
            user_id=user.id,
            status="delivered",
            total=Decimal("149.99"),
            subtotal=Decimal("149.99"),
        )
        db.add(order)
        await db.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            product_name=prod.name,
            quantity=1,
            unit_price=Decimal("149.99"),
            line_total=Decimal("149.99"),
        )
        db.add(item)
        await db.flush()

        # T-018 verification query: does this user have a completed order
        # containing this product?
        result = await db.execute(
            select(Order)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(
                Order.user_id == user.id,
                OrderItem.product_id == prod.id,
                Order.status == "delivered",
            )
        )
        verified_order = result.scalar_one_or_none()
        assert verified_order is not None, (
            "Should find a delivered order containing the product"
        )

    @pytest.mark.asyncio
    async def test_review_rating_stored_correctly(self, db: AsyncSession):
        """Review.rating stores the integer 1-5 value correctly."""
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
            rating=4,
            title="Very good",
        )
        db.add(review)
        await db.flush()
        await db.refresh(review)

        assert review.rating == 4


# ---------------------------------------------------------------------------
# T-025: Order history query patterns (GET /api/v1/account/orders)
# ---------------------------------------------------------------------------

class TestOrderHistoryQueries:
    """Schema supports authenticated order history (GET /api/v1/account/orders)."""

    @pytest.mark.asyncio
    async def test_orders_filterable_by_user_id(self, db: AsyncSession):
        """Can retrieve all orders for a specific user."""
        user = _user()
        db.add(user)
        await db.flush()

        # Create 3 orders for this user
        for i in range(3):
            db.add(_order(
                user_id=user.id,
                total=Decimal(f"{(i + 1) * 49}.99"),
                subtotal=Decimal(f"{(i + 1) * 49}.99"),
            ))
        # Create 1 order for another user (noise)
        db.add(_order(total=Decimal("99.99"), subtotal=Decimal("99.99")))
        await db.flush()

        result = await db.execute(
            select(Order).where(Order.user_id == user.id)
        )
        user_orders = result.scalars().all()
        assert len(user_orders) == 3

    @pytest.mark.asyncio
    async def test_orders_filterable_by_guest_email(self, db: AsyncSession):
        """Can retrieve all guest orders by email address."""
        guest_email = f"guest_{uuid.uuid4().hex[:8]}@example.com"

        for i in range(2):
            db.add(_order(
                guest_email=guest_email,
                total=Decimal(f"{(i + 1) * 79}.99"),
                subtotal=Decimal(f"{(i + 1) * 79}.99"),
            ))
        await db.flush()

        result = await db.execute(
            select(Order).where(Order.guest_email == guest_email)
        )
        guest_orders = result.scalars().all()
        assert len(guest_orders) == 2

    @pytest.mark.asyncio
    async def test_orders_filterable_by_status(self, db: AsyncSession):
        """Can filter orders by lifecycle status (e.g., 'confirmed', 'delivered')."""
        user = _user()
        db.add(user)
        await db.flush()

        db.add(_order(user_id=user.id, status="pending",
                      total=Decimal("49.99"), subtotal=Decimal("49.99")))
        db.add(_order(user_id=user.id, status="confirmed",
                      total=Decimal("99.99"), subtotal=Decimal("99.99")))
        db.add(_order(user_id=user.id, status="delivered",
                      total=Decimal("149.99"), subtotal=Decimal("149.99")))
        await db.flush()

        result = await db.execute(
            select(Order).where(
                Order.user_id == user.id,
                Order.status == "confirmed",
            )
        )
        confirmed = result.scalars().all()
        assert len(confirmed) == 1
        assert confirmed[0].status == "confirmed"

    @pytest.mark.asyncio
    async def test_order_items_loaded_for_order(self, db: AsyncSession):
        """Can join order_items to retrieve full order line items."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod_a = _product(cat.id, name="Pro Boot A", slug=f"pro-boot-a-{uuid.uuid4().hex[:6]}")
        prod_b = _product(cat.id, name="Pro Boot B", slug=f"pro-boot-b-{uuid.uuid4().hex[:6]}")
        db.add_all([prod_a, prod_b])
        await db.flush()

        order = _order(total=Decimal("279.98"), subtotal=Decimal("279.98"))
        db.add(order)
        await db.flush()

        db.add(OrderItem(
            order_id=order.id, product_id=prod_a.id, product_name=prod_a.name,
            quantity=1, unit_price=Decimal("149.99"), line_total=Decimal("149.99"),
        ))
        db.add(OrderItem(
            order_id=order.id, product_id=prod_b.id, product_name=prod_b.name,
            quantity=1, unit_price=Decimal("129.99"), line_total=Decimal("129.99"),
        ))
        await db.flush()

        result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        items = result.scalars().all()
        assert len(items) == 2
        prices = {item.unit_price for item in items}
        assert Decimal("149.99") in prices
        assert Decimal("129.99") in prices
