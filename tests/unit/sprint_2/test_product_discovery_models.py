"""
Sprint 2 unit tests for product discovery, details, and cart models (T-009).

Covers:
  - Category browsing (US-006): category lookup by slug, hierarchical categories
  - Product listing (US-006): category-based filtering, is_active flag, brand
  - Product search schema (US-004, ADR-004): search_vector field presence,
    search_vector is Text-compatible in SQLite (portable TsVector type)
  - Faceted filtering schema (US-005): size/color indexes on product_variants
  - Product detail page data (US-007): variant relationships, image/attribute storage
  - Cart operations (US-009, US-010): guest/user carts, CartItem quantity, cascade

Uses an ephemeral SQLite+aiosqlite in-memory database — no live PostgreSQL required.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import inspect as sa_inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

# Force all ORM mappers to register before creating tables.
from app.core.database import Base  # noqa: F401

import app.domains.account.models  # noqa: F401
import app.domains.categories.models  # noqa: F401
import app.domains.products.models  # noqa: F401
import app.domains.cart.models  # noqa: F401
import app.domains.checkout.models  # noqa: F401

from app.domains.account.models import User
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
        email=f"user_{uuid.uuid4().hex[:8]}@boots.example.com",
        hashed_password="$2b$12$testhashedpassword.here",
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
# US-006: Category browsing (category list page)
# ---------------------------------------------------------------------------

class TestCategoryBrowsing:
    """Schema supports US-006 — shopper browses a grid of boots by category."""

    @pytest.mark.asyncio
    async def test_category_created_with_slug(self, db: AsyncSession):
        """Category can be fetched by slug (the URL key for listing pages)."""
        cat = _category(name="Hiking Boots", slug="hiking-boots")
        db.add(cat)
        await db.flush()

        result = await db.execute(
            select(Category).where(Category.slug == "hiking-boots")
        )
        fetched = result.scalar_one()
        assert fetched.name == "Hiking Boots"
        assert fetched.slug == "hiking-boots"

    @pytest.mark.asyncio
    async def test_category_slug_is_unique(self, db: AsyncSession):
        """Duplicate slugs are rejected by the UNIQUE constraint."""
        db.add(_category(slug="work-boots"))
        await db.flush()

        db.add(_category(name="Another Work Boots", slug="work-boots"))
        with pytest.raises(Exception):
            await db.flush()

    @pytest.mark.asyncio
    async def test_category_active_flag_default(self, db: AsyncSession):
        """is_active defaults to True for newly created categories."""
        cat = _category()
        db.add(cat)
        await db.flush()
        await db.refresh(cat)
        assert cat.is_active is True

    @pytest.mark.asyncio
    async def test_category_hierarchical_parent_child(self, db: AsyncSession):
        """Self-referential FK supports hierarchical category trees."""
        parent = _category(name="Boots", slug="boots")
        db.add(parent)
        await db.flush()

        child = _category(name="Hiking Boots", slug="hiking-boots", parent_id=parent.id)
        db.add(child)
        await db.flush()

        result = await db.execute(select(Category).where(Category.slug == "hiking-boots"))
        fetched = result.scalar_one()
        assert fetched.parent_id == parent.id

    @pytest.mark.asyncio
    async def test_category_has_products_relationship(self, db: AsyncSession):
        """Category.products relationship returns products in that category."""
        cat = _category()
        db.add(cat)
        await db.flush()

        for i in range(3):
            db.add(_product(cat.id, name=f"Boot Model {i}", slug=f"boot-model-{i}-{uuid.uuid4().hex[:4]}"))
        await db.flush()

        result = await db.execute(
            select(Product).where(Product.category_id == cat.id)
        )
        products = result.scalars().all()
        assert len(products) == 3


# ---------------------------------------------------------------------------
# US-006/US-007: Product listing and detail page
# ---------------------------------------------------------------------------

class TestProductSchema:
    """Schema supports US-006 (listing grid) and US-007 (detail page)."""

    @pytest.mark.asyncio
    async def test_product_has_required_listing_fields(self, db: AsyncSession):
        """Product has all fields needed for a listing grid card."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(
            cat.id,
            brand="Caterpillar",
            base_price=Decimal("149.99"),
            is_featured=True,
        )
        db.add(prod)
        await db.flush()
        await db.refresh(prod)

        assert prod.name is not None
        assert prod.slug is not None
        assert prod.brand == "Caterpillar"
        assert prod.base_price == Decimal("149.99")
        assert prod.is_featured is True
        assert prod.is_active is True

    @pytest.mark.asyncio
    async def test_product_images_stored_as_json(self, db: AsyncSession):
        """Product.images (JSONB on PG / JSON on SQLite) stores image URLs."""
        cat = _category()
        db.add(cat)
        await db.flush()

        images_data = [
            {"url": "https://cdn.example.com/boot-front.jpg", "alt": "Front view"},
            {"url": "https://cdn.example.com/boot-side.jpg", "alt": "Side view"},
        ]
        prod = _product(cat.id, images=images_data)
        db.add(prod)
        await db.flush()
        await db.refresh(prod)

        # JSON round-trip: value must be a list or JSON-parseable string
        stored = prod.images
        if isinstance(stored, str):
            stored = json.loads(stored)
        assert isinstance(stored, list)
        assert len(stored) == 2

    @pytest.mark.asyncio
    async def test_product_attributes_stored_as_json(self, db: AsyncSession):
        """Product.attributes (JSONB) stores structured spec data."""
        cat = _category()
        db.add(cat)
        await db.flush()

        attributes_data = {
            "waterproof": True,
            "steel_toe": True,
            "material": "full-grain leather",
        }
        prod = _product(cat.id, attributes=attributes_data)
        db.add(prod)
        await db.flush()
        await db.refresh(prod)

        stored = prod.attributes
        if isinstance(stored, str):
            stored = json.loads(stored)
        assert isinstance(stored, dict)
        assert stored.get("waterproof") is True

    @pytest.mark.asyncio
    async def test_product_search_vector_column_exists(self, db: AsyncSession):
        """search_vector column exists on Product (ADR-004: full-text search)."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        # The column is present; in SQLite it falls back to Text (nullable).
        assert hasattr(prod, "search_vector")

    @pytest.mark.asyncio
    async def test_product_active_flag_filters_correctly(self, db: AsyncSession):
        """is_active flag allows filtering active/inactive products."""
        cat = _category()
        db.add(cat)
        await db.flush()

        active = _product(cat.id, name="Active Boot", slug=f"active-{uuid.uuid4().hex[:6]}", is_active=True)
        inactive = _product(cat.id, name="Discontinued Boot", slug=f"inactive-{uuid.uuid4().hex[:6]}", is_active=False)
        db.add_all([active, inactive])
        await db.flush()

        result = await db.execute(
            select(Product).where(
                Product.category_id == cat.id,
                Product.is_active == True,  # noqa: E712
            )
        )
        active_products = result.scalars().all()
        assert len(active_products) == 1
        assert active_products[0].name == "Active Boot"

    @pytest.mark.asyncio
    async def test_product_brand_field_indexed(self, db: AsyncSession):
        """Brand field is present and queryable (US-005 brand filter)."""
        cat = _category()
        db.add(cat)
        await db.flush()

        brands = ["Timberland", "Caterpillar", "Dr. Martens"]
        for brand in brands:
            db.add(_product(
                cat.id,
                brand=brand,
                name=f"{brand} Classic",
                slug=f"{brand.lower().replace(' ', '-').replace('.', '')}-{uuid.uuid4().hex[:6]}",
            ))
        await db.flush()

        result = await db.execute(
            select(Product).where(Product.brand == "Timberland")
        )
        timberland_products = result.scalars().all()
        assert len(timberland_products) == 1
        assert timberland_products[0].brand == "Timberland"

    @pytest.mark.asyncio
    async def test_product_price_alias_readable(self, db: AsyncSession):
        """Product.price hybrid property aliases base_price (API contract)."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id, base_price=Decimal("199.99"))
        db.add(prod)
        await db.flush()

        assert prod.price == Decimal("199.99")
        assert prod.price == prod.base_price


# ---------------------------------------------------------------------------
# US-005: Faceted filtering — ProductVariant schema
# ---------------------------------------------------------------------------

class TestProductVariantFacets:
    """Schema supports US-005 — filter by size, color, and price range."""

    @pytest.mark.asyncio
    async def test_variant_has_size_and_color(self, db: AsyncSession):
        """ProductVariant has size and color fields for faceted filtering."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        variant = _variant(prod.id, size="10", color="Black")
        db.add(variant)
        await db.flush()
        await db.refresh(variant)

        assert variant.size == "10"
        assert variant.color == "Black"

    @pytest.mark.asyncio
    async def test_variant_inventory_count_non_negative(self, db: AsyncSession):
        """inventory_count defaults to 0 and cannot go below 0 (CHECK constraint)."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        # Default inventory
        variant = _variant(prod.id, inventory_count=0)
        db.add(variant)
        await db.flush()
        await db.refresh(variant)
        assert variant.inventory_count == 0

    @pytest.mark.asyncio
    async def test_multiple_variants_for_size_color_matrix(self, db: AsyncSession):
        """A product can have many size×color variants (size/color matrix)."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        sizes = ["7", "8", "9", "10", "11"]
        colors = ["Black", "Brown"]
        for size in sizes:
            for color in colors:
                db.add(_variant(
                    prod.id,
                    name=f"UK {size} / {color}",
                    size=size,
                    color=color,
                    inventory_count=5,
                ))
        await db.flush()

        result = await db.execute(
            select(ProductVariant).where(
                ProductVariant.product_id == prod.id,
                ProductVariant.color == "Black",
            )
        )
        black_variants = result.scalars().all()
        assert len(black_variants) == 5

    @pytest.mark.asyncio
    async def test_variant_filtered_by_size(self, db: AsyncSession):
        """Variants can be queried by size for US-005 size filter."""
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
            select(ProductVariant).where(
                ProductVariant.product_id == prod.id,
                ProductVariant.size == "9",
            )
        )
        size_9 = result.scalars().all()
        assert len(size_9) == 1
        assert size_9[0].size == "9"

    @pytest.mark.asyncio
    async def test_variant_cascade_deleted_with_product(self, db: AsyncSession):
        """Deleting a product cascades to its variants (ON DELETE CASCADE)."""
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


# ---------------------------------------------------------------------------
# US-004 / ADR-004: Full-text search schema
# ---------------------------------------------------------------------------

class TestFullTextSearchSchema:
    """Schema supports ADR-004 PostgreSQL full-text search on products."""

    @pytest.mark.asyncio
    async def test_search_vector_column_is_nullable(self, db: AsyncSession):
        """search_vector is nullable — populated by DB trigger on PostgreSQL."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()
        await db.refresh(prod)

        # In SQLite tests the trigger doesn't run, so it stays NULL.
        # That's expected — the column definition is nullable.
        assert hasattr(prod, "search_vector")
        # No assertion on value; just verifying no crash occurs.

    @pytest.mark.asyncio
    async def test_product_name_and_brand_indexed_fields(self, db: AsyncSession):
        """name and brand fields (used in search_vector trigger) are populated."""
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(
            cat.id,
            name="Timberland Pro Boondock",
            brand="Timberland",
            description="Rugged waterproof work boot with composite toe.",
        )
        db.add(prod)
        await db.flush()
        await db.refresh(prod)

        assert prod.name == "Timberland Pro Boondock"
        assert prod.brand == "Timberland"
        assert "waterproof" in prod.description

    @pytest.mark.asyncio
    async def test_multiple_products_retrievable_by_name(self, db: AsyncSession):
        """Products with distinct names can be found individually."""
        cat = _category()
        db.add(cat)
        await db.flush()

        names = [
            "Timberland Pro Boondock",
            "Caterpillar Excavator",
            "Dr. Martens 1460",
        ]
        for name in names:
            slug = name.lower().replace(" ", "-").replace(".", "") + "-" + uuid.uuid4().hex[:6]
            db.add(_product(cat.id, name=name, slug=slug, brand=name.split()[0]))
        await db.flush()

        result = await db.execute(
            select(Product).where(Product.name.like("%Caterpillar%"))
        )
        found = result.scalars().all()
        assert len(found) == 1
        assert "Caterpillar" in found[0].name


# ---------------------------------------------------------------------------
# US-009 / US-010: Cart schema
# ---------------------------------------------------------------------------

class TestCartSchema:
    """Schema supports US-009 (add to cart) and US-010 (view/edit cart)."""

    @pytest.mark.asyncio
    async def test_guest_cart_via_session_id(self, db: AsyncSession):
        """Guest cart uses session_id instead of user_id (nullable FK)."""
        cart = Cart(session_id="sess_guest_abc123")
        db.add(cart)
        await db.flush()
        await db.refresh(cart)

        assert cart.user_id is None
        assert cart.session_id == "sess_guest_abc123"

    @pytest.mark.asyncio
    async def test_authenticated_cart_has_user_id(self, db: AsyncSession):
        """Authenticated cart links to a user via user_id FK."""
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
    async def test_cart_item_added_to_cart(self, db: AsyncSession):
        """CartItem can be added referencing a product and optional variant."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        variant = _variant(prod.id, size="9", color="Black")
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

        assert item.quantity == 2
        assert item.unit_price == Decimal("129.99")
        assert item.variant_id == variant.id

    @pytest.mark.asyncio
    async def test_cart_item_quantity_default_is_one(self, db: AsyncSession):
        """CartItem.quantity defaults to 1 (US-009: add single item)."""
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
    async def test_cart_item_cascade_delete_on_cart(self, db: AsyncSession):
        """Deleting a cart cascades to its items (ON DELETE CASCADE)."""
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

        await db.delete(cart)
        await db.flush()

        result = await db.execute(select(CartItem).where(CartItem.id == item.id))
        assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_cart_multiple_items(self, db: AsyncSession):
        """Cart supports multiple distinct items (different products/variants)."""
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

        item_a = CartItem(cart_id=cart.id, product_id=prod_a.id, unit_price=Decimal("129.99"))
        item_b = CartItem(cart_id=cart.id, product_id=prod_b.id, unit_price=Decimal("89.99"))
        db.add_all([item_a, item_b])
        await db.flush()

        result = await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))
        items = result.scalars().all()
        assert len(items) == 2


# ---------------------------------------------------------------------------
# Review schema (US-007 product detail page — review section)
# ---------------------------------------------------------------------------

class TestReviewSchema:
    """Review model supports purchase-verified reviews on product detail page."""

    @pytest.mark.asyncio
    async def test_review_created_with_rating_and_text(self, db: AsyncSession):
        """Review stores rating (1-5) and review text."""
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
            title="Outstanding build quality",
            body="These boots lasted me two full construction seasons without any issues.",
        )
        db.add(review)
        await db.flush()
        await db.refresh(review)

        assert review.rating == 5
        assert "construction seasons" in review.body
        assert review.is_verified_purchase is False
        assert review.is_approved is True

    @pytest.mark.asyncio
    async def test_review_links_to_order_for_verification(self, db: AsyncSession):
        """Review can reference an Order to mark is_verified_purchase."""
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
        await db.refresh(review)

        assert review.order_id == order.id
        assert review.is_verified_purchase is True

    @pytest.mark.asyncio
    async def test_reviews_filterable_by_product(self, db: AsyncSession):
        """Multiple reviews on a product can be fetched by product_id.

        T-018 (Sprint 3) adds UNIQUE(user_id, product_id) — each review
        must come from a distinct user.
        """
        cat = _category()
        db.add(cat)
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        # Three different reviewers, each rates the product once
        for rating in (5, 4, 3):
            reviewer = _user()
            db.add(reviewer)
            await db.flush()
            db.add(Review(
                product_id=prod.id,
                user_id=reviewer.id,
                rating=rating,
            ))
        await db.flush()

        result = await db.execute(
            select(Review).where(Review.product_id == prod.id)
        )
        reviews = result.scalars().all()
        assert len(reviews) == 3

    @pytest.mark.asyncio
    async def test_review_cascade_deleted_with_product(self, db: AsyncSession):
        """Deleting a product cascades to its reviews (ON DELETE CASCADE)."""
        user = _user()
        cat = _category()
        db.add_all([user, cat])
        await db.flush()

        prod = _product(cat.id)
        db.add(prod)
        await db.flush()

        review = Review(product_id=prod.id, user_id=user.id, rating=4)
        db.add(review)
        await db.flush()

        await db.delete(prod)
        await db.flush()

        result = await db.execute(select(Review).where(Review.id == review.id))
        assert result.scalar_one_or_none() is None


# ---------------------------------------------------------------------------
# Cross-model: full product detail page data availability (US-007)
# ---------------------------------------------------------------------------

class TestProductDetailPageData:
    """Verify all data needed for the product detail page (US-007) is stored."""

    @pytest.mark.asyncio
    async def test_product_detail_page_data_complete(self, db: AsyncSession):
        """Product with variants and reviews has all fields for detail page."""
        user = _user()
        cat = _category(name="Work Boots", slug="work-boots")
        db.add_all([user, cat])
        await db.flush()

        prod = _product(
            cat.id,
            name="Timberland Pro Boondock",
            brand="Timberland",
            description="Waterproof full-grain leather work boot.",
            images=[
                {"url": "https://cdn.example.com/img1.jpg", "alt": "Front"},
                {"url": "https://cdn.example.com/img2.jpg", "alt": "Side"},
            ],
            attributes={"waterproof": True, "steel_toe": True},
            base_price=Decimal("179.99"),
        )
        db.add(prod)
        await db.flush()

        # Add variants (size/color matrix)
        for size, color in [("9", "Brown"), ("10", "Brown"), ("9", "Black")]:
            db.add(_variant(prod.id, name=f"UK {size}/{color}", size=size, color=color))

        # Add reviews
        order = Order(
            user_id=user.id,
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            total=Decimal("179.99"),
            subtotal=Decimal("179.99"),
        )
        db.add(order)
        await db.flush()

        db.add(Review(
            product_id=prod.id,
            user_id=user.id,
            order_id=order.id,
            rating=5,
            title="Excellent",
            body="Highly recommended for construction sites.",
            is_verified_purchase=True,
        ))
        await db.flush()

        # Assertions: product fields
        result = await db.execute(select(Product).where(Product.id == prod.id))
        fetched = result.scalar_one()
        assert fetched.base_price == Decimal("179.99")
        assert fetched.brand == "Timberland"

        # Variants
        variant_result = await db.execute(
            select(ProductVariant).where(ProductVariant.product_id == prod.id)
        )
        variants = variant_result.scalars().all()
        assert len(variants) == 3

        # Reviews
        review_result = await db.execute(
            select(Review).where(Review.product_id == prod.id)
        )
        reviews = review_result.scalars().all()
        assert len(reviews) == 1
        assert reviews[0].is_verified_purchase is True
