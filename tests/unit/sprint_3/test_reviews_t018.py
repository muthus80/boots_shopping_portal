"""
Sprint 3 T-018 unit tests — Reviews database schema (US-008).

Story: US-008 — Purchase-verified product reviews.
Acceptance criteria:
  * A logged-in user who has purchased a product can leave a review.
  * A user cannot leave more than one review per product
    (UNIQUE constraint on user_id + product_id).
  * The review carries is_verified_purchase=True when backed by an order.
  * Review.order_id FK links to the verifying Order (ON DELETE SET NULL).
  * Review.rating is stored as an integer.
  * Review.title and body are nullable free-text fields.
  * Review.is_approved defaults to True.

ORM model under test: Review  (app.domains.products.models)
Migration under test:  0005_sprint_3_t018_reviews_unique_user_product

Uses an ephemeral SQLite+aiosqlite in-memory database — no live PostgreSQL.
PostgreSQL-specific types (UUID, TSVECTOR) are handled via dialect-agnostic
wrappers already defined in the ORM models.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.exc import IntegrityError
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
        email=f"reviewer_{uuid.uuid4().hex[:8]}@bootsshop.example.com",
        hashed_password="$2b$12$securehashedpasswordhash",
    )
    defaults.update(kwargs)
    return User(**defaults)


def _category(**kwargs) -> Category:
    uid = uuid.uuid4().hex[:8]
    defaults = dict(name=f"Hiking Boots {uid}", slug=f"hiking-boots-{uid}")
    defaults.update(kwargs)
    return Category(**defaults)


def _product(category_id, **kwargs) -> Product:
    uid = uuid.uuid4().hex[:8]
    defaults = dict(
        category_id=category_id,
        name=f"Scarpa Marmolada Pro {uid}",
        slug=f"scarpa-marmolada-pro-{uid}",
        brand="Scarpa",
        base_price=Decimal("289.99"),
        is_active=True,
    )
    defaults.update(kwargs)
    return Product(**defaults)


def _variant(product_id, **kwargs) -> ProductVariant:
    defaults = dict(
        product_id=product_id,
        name="UK 8 / Dark Brown",
        size="8",
        color="Dark Brown",
        inventory_count=15,
    )
    defaults.update(kwargs)
    return ProductVariant(**defaults)


def _order(user_id=None, **kwargs) -> Order:
    defaults = dict(
        order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
        user_id=user_id,
        status="delivered",
        total=Decimal("289.99"),
        subtotal=Decimal("289.99"),
        shipping_address={
            "line1": "1 Adventure Way",
            "city": "Edinburgh",
            "postcode": "EH1 1BB",
        },
    )
    defaults.update(kwargs)
    return Order(**defaults)


def _review(product_id, user_id, **kwargs) -> Review:
    defaults = dict(
        product_id=product_id,
        user_id=user_id,
        rating=5,
        title="Superb mountain boot",
        body="Excellent ankle support and waterproofing — highly recommended.",
        is_verified_purchase=True,
    )
    defaults.update(kwargs)
    return Review(**defaults)


# ---------------------------------------------------------------------------
# T-018: Review schema — field-level tests
# ---------------------------------------------------------------------------

class TestReviewSchema:
    """Review model fields satisfy the US-008 data model specification."""

    @pytest.mark.asyncio
    async def test_create_verified_review(self, db: AsyncSession):
        """Authenticated user with a completed order can submit a verified review."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        order = _order(user_id=user.id)
        db.add(order)
        await db.flush()

        review = _review(
            prod.id,
            user.id,
            order_id=order.id,
            is_verified_purchase=True,
        )
        db.add(review)
        await db.flush()
        await db.refresh(review)

        assert review.id is not None
        assert review.product_id == prod.id
        assert review.user_id == user.id
        assert review.order_id == order.id
        assert review.is_verified_purchase is True
        assert review.rating == 5

    @pytest.mark.asyncio
    async def test_review_rating_stored_as_integer(self, db: AsyncSession):
        """Review.rating must store integer values 1-5."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        for rating in (1, 2, 3, 4, 5):
            other_user = _user()
            db.add(other_user)
            await db.flush()

            review = _review(prod.id, other_user.id, rating=rating)
            db.add(review)
            await db.flush()
            await db.refresh(review)
            assert review.rating == rating

    @pytest.mark.asyncio
    async def test_review_title_and_body_nullable(self, db: AsyncSession):
        """Review.title and body are optional — model allows None."""
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
            title=None,
            body=None,
            is_verified_purchase=False,
        )
        db.add(review)
        await db.flush()
        await db.refresh(review)

        assert review.title is None
        assert review.body is None

    @pytest.mark.asyncio
    async def test_review_is_approved_defaults_true(self, db: AsyncSession):
        """Review.is_approved defaults to True (auto-approve on creation)."""
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
        )
        db.add(review)
        await db.flush()
        await db.refresh(review)

        assert review.is_approved is True

    @pytest.mark.asyncio
    async def test_review_is_verified_purchase_defaults_false(self, db: AsyncSession):
        """Review.is_verified_purchase defaults to False for anonymous/unverified."""
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
        await db.refresh(review)

        assert review.is_verified_purchase is False

    @pytest.mark.asyncio
    async def test_review_order_id_nullable(self, db: AsyncSession):
        """Review.order_id is nullable — allows unverified reviews."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        review = _review(prod.id, user.id, order_id=None, is_verified_purchase=False)
        db.add(review)
        await db.flush()
        await db.refresh(review)

        assert review.order_id is None

    @pytest.mark.asyncio
    async def test_review_created_at_populated(self, db: AsyncSession):
        """Review.created_at is set on creation."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        review = _review(prod.id, user.id)
        db.add(review)
        await db.flush()
        await db.refresh(review)

        assert hasattr(review, "created_at")
        assert review.created_at is not None


# ---------------------------------------------------------------------------
# T-018: UNIQUE(user_id, product_id) constraint — one review per product
# ---------------------------------------------------------------------------

class TestReviewUniqueConstraint:
    """UNIQUE constraint on (user_id, product_id) prevents duplicate reviews."""

    @pytest.mark.asyncio
    async def test_duplicate_review_raises_integrity_error(self, db: AsyncSession):
        """Submitting a second review for the same product raises IntegrityError."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        # First review succeeds
        review1 = _review(prod.id, user.id, title="Great boots", rating=5)
        db.add(review1)
        await db.flush()

        # Second review from the same user on the same product must fail
        review2 = _review(prod.id, user.id, title="Second attempt", rating=4)
        db.add(review2)
        with pytest.raises((IntegrityError, Exception)):
            await db.flush()

    @pytest.mark.asyncio
    async def test_different_users_can_review_same_product(self, db: AsyncSession):
        """Two different users can each review the same product."""
        user_a = _user()
        user_b = _user()
        cat = _category()
        db.add_all([user_a, user_b, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        db.add(_review(prod.id, user_a.id, rating=5, title="Love these boots"))
        db.add(_review(prod.id, user_b.id, rating=4, title="Very comfortable"))
        await db.flush()

        result = await db.execute(
            select(Review).where(Review.product_id == prod.id)
        )
        reviews = result.scalars().all()
        assert len(reviews) == 2

    @pytest.mark.asyncio
    async def test_same_user_can_review_different_products(self, db: AsyncSession):
        """One user can review multiple different products."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod_a = _product(cat.id, name="Boot Alpha", slug=f"boot-alpha-{uuid.uuid4().hex[:6]}")
        prod_b = _product(cat.id, name="Boot Beta", slug=f"boot-beta-{uuid.uuid4().hex[:6]}")
        prod_c = _product(cat.id, name="Boot Gamma", slug=f"boot-gamma-{uuid.uuid4().hex[:6]}")
        db.add_all([prod_a, prod_b, prod_c])
        await db.flush()

        for prod, title in [
            (prod_a, "Best all-round boot"),
            (prod_b, "Good value option"),
            (prod_c, "Excellent waterproofing"),
        ]:
            db.add(_review(prod.id, user.id, title=title, rating=4))

        await db.flush()

        result = await db.execute(
            select(Review).where(Review.user_id == user.id)
        )
        reviews = result.scalars().all()
        assert len(reviews) == 3


# ---------------------------------------------------------------------------
# T-018: FK constraints
# ---------------------------------------------------------------------------

class TestReviewFKConstraints:
    """FK constraints govern Review relationships correctly."""

    @pytest.mark.asyncio
    async def test_review_deleted_when_product_deleted(self, db: AsyncSession):
        """Deleting the product cascades to its reviews (ON DELETE CASCADE)."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()
        prod_id = prod.id

        review = _review(prod.id, user.id)
        db.add(review)
        await db.flush()
        review_id = review.id

        await db.delete(prod)
        await db.flush()

        result = await db.execute(select(Review).where(Review.id == review_id))
        assert result.scalar_one_or_none() is None, (
            "Review must be cascade-deleted when its product is deleted"
        )

    @pytest.mark.asyncio
    async def test_review_deleted_when_user_deleted(self, db: AsyncSession):
        """Deleting the user cascades to their reviews (ON DELETE CASCADE)."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        review = _review(prod.id, user.id)
        db.add(review)
        await db.flush()
        review_id = review.id

        await db.delete(user)
        await db.flush()

        result = await db.execute(select(Review).where(Review.id == review_id))
        assert result.scalar_one_or_none() is None, (
            "Review must be cascade-deleted when its author is deleted"
        )

    @pytest.mark.asyncio
    async def test_review_order_id_set_null_when_order_deleted(self, db: AsyncSession):
        """Deleting the order sets review.order_id to NULL (ON DELETE SET NULL)."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        order = _order(user_id=user.id)
        db.add(order)
        await db.flush()

        review = _review(prod.id, user.id, order_id=order.id, is_verified_purchase=True)
        db.add(review)
        await db.flush()
        review_id = review.id

        await db.delete(order)
        await db.flush()

        db.expire_all()
        result = await db.execute(select(Review).where(Review.id == review_id))
        fetched = result.scalar_one_or_none()
        assert fetched is not None, "Review must survive order deletion"
        assert fetched.order_id is None, (
            "review.order_id should be NULL after order deletion (ON DELETE SET NULL)"
        )
        # is_verified_purchase remains True even after order deletion
        assert fetched.is_verified_purchase is True


# ---------------------------------------------------------------------------
# T-018: Purchase verification gate query patterns
# ---------------------------------------------------------------------------

class TestPurchaseVerificationGate:
    """Schema supports the POST /api/v1/products/{product_id}/reviews gate."""

    @pytest.mark.asyncio
    async def test_can_verify_purchase_via_order_and_order_items(self, db: AsyncSession):
        """The service can confirm purchase by querying orders + order_items."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        # Delivered order containing the product
        order = _order(user_id=user.id, status="delivered")
        db.add(order)
        await db.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            product_name=prod.name,
            quantity=1,
            unit_price=Decimal("289.99"),
            line_total=Decimal("289.99"),
        )
        db.add(item)
        await db.flush()

        # T-018 verification query pattern
        result = await db.execute(
            select(Order)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(
                Order.user_id == user.id,
                OrderItem.product_id == prod.id,
                Order.status.in_(["confirmed", "shipped", "delivered"]),
            )
        )
        verified = result.scalar_one_or_none()
        assert verified is not None, (
            "Purchase verification query must find the completed order"
        )
        assert verified.status == "delivered"

    @pytest.mark.asyncio
    async def test_pending_order_does_not_satisfy_purchase_gate(self, db: AsyncSession):
        """A 'pending' order does not satisfy the purchase-verified gate."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        # Pending (not yet fulfilled) order
        order = _order(user_id=user.id, status="pending")
        db.add(order)
        await db.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=prod.id,
            product_name=prod.name,
            quantity=1,
            unit_price=Decimal("289.99"),
            line_total=Decimal("289.99"),
        )
        db.add(item)
        await db.flush()

        # Query only accepts confirmed/shipped/delivered
        result = await db.execute(
            select(Order)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(
                Order.user_id == user.id,
                OrderItem.product_id == prod.id,
                Order.status.in_(["confirmed", "shipped", "delivered"]),
            )
        )
        assert result.scalar_one_or_none() is None, (
            "Pending order must NOT satisfy the purchase-verified gate"
        )

    @pytest.mark.asyncio
    async def test_unrelated_product_not_verified(self, db: AsyncSession):
        """Purchase verification correctly rejects products not in the order."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod_bought = _product(cat.id, name="Boot Bought",
                               slug=f"boot-bought-{uuid.uuid4().hex[:6]}")
        prod_not_bought = _product(cat.id, name="Boot Not Bought",
                                   slug=f"boot-not-bought-{uuid.uuid4().hex[:6]}")
        db.add_all([prod_bought, prod_not_bought])
        await db.flush()

        order = _order(user_id=user.id, status="delivered")
        db.add(order)
        await db.flush()

        # Only prod_bought is in the order
        item = OrderItem(
            order_id=order.id,
            product_id=prod_bought.id,
            product_name=prod_bought.name,
            quantity=1,
            unit_price=Decimal("289.99"),
            line_total=Decimal("289.99"),
        )
        db.add(item)
        await db.flush()

        # Verify prod_not_bought is rejected
        result = await db.execute(
            select(Order)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(
                Order.user_id == user.id,
                OrderItem.product_id == prod_not_bought.id,
                Order.status.in_(["confirmed", "shipped", "delivered"]),
            )
        )
        assert result.scalar_one_or_none() is None, (
            "User must NOT be verified for a product they did not purchase"
        )


# ---------------------------------------------------------------------------
# T-018: ORM field presence smoke tests
# ---------------------------------------------------------------------------

class TestReviewModelFields:
    """Verify all T-018 required ORM columns are present on the Review mapper."""

    def test_review_has_product_id_column(self):
        """Review.product_id maps the product FK."""
        mapper = sa_inspect(Review)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "product_id" in col_names

    def test_review_has_user_id_column(self):
        """Review.user_id maps the author FK."""
        mapper = sa_inspect(Review)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "user_id" in col_names

    def test_review_has_order_id_column(self):
        """Review.order_id maps the verifying order FK (T-018 purchase gate)."""
        mapper = sa_inspect(Review)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "order_id" in col_names

    def test_review_has_rating_column(self):
        """Review.rating stores the 1-5 integer rating."""
        mapper = sa_inspect(Review)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "rating" in col_names

    def test_review_has_title_column(self):
        """Review.title maps the optional headline string."""
        mapper = sa_inspect(Review)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "title" in col_names

    def test_review_has_body_column(self):
        """Review.body maps the optional long-form text."""
        mapper = sa_inspect(Review)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "body" in col_names

    def test_review_has_is_verified_purchase_column(self):
        """Review.is_verified_purchase is the T-018 verification flag."""
        mapper = sa_inspect(Review)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "is_verified_purchase" in col_names

    def test_review_has_is_approved_column(self):
        """Review.is_approved controls review visibility."""
        mapper = sa_inspect(Review)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "is_approved" in col_names

    def test_review_has_created_at_column(self):
        """Review.created_at used for review ordering."""
        mapper = sa_inspect(Review)
        col_names = [col.key for col in mapper.mapper.column_attrs]
        assert "created_at" in col_names

    def test_review_unique_constraint_user_product_in_table_args(self):
        """Review.__table_args__ must include uq_reviews_user_product constraint."""
        from sqlalchemy import UniqueConstraint
        table = Review.__table__
        unique_constraints = {c.name for c in table.constraints
                              if hasattr(c, "columns")}
        assert "uq_reviews_user_product" in unique_constraints, (
            "uq_reviews_user_product UNIQUE constraint must be declared in "
            "Review.__table_args__ — required for T-018 one-review-per-product gate"
        )

    def test_review_has_relationship_to_product(self):
        """Review.product relationship must exist for ORM navigation."""
        mapper = sa_inspect(Review)
        rel_names = [r.key for r in mapper.mapper.relationships]
        assert "product" in rel_names

    def test_review_has_relationship_to_user(self):
        """Review.user relationship must exist for ORM navigation."""
        mapper = sa_inspect(Review)
        rel_names = [r.key for r in mapper.mapper.relationships]
        assert "user" in rel_names

    def test_review_has_relationship_to_order(self):
        """Review.order relationship must exist for ORM navigation."""
        mapper = sa_inspect(Review)
        rel_names = [r.key for r in mapper.mapper.relationships]
        assert "order" in rel_names
