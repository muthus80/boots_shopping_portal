"""
Sprint 2 unit tests for T-010: Product listing API endpoint (US-006).

Covers:
  - GET /api/v1/categories            (US-006: category listing page)
  - GET /api/v1/products              (US-005, US-006: product grid + filters)
  - GET /api/v1/products/search       (US-004: keyword search)
  - GET /api/v1/products/{id}         (US-007: product detail page)
  - POST /api/v1/cart/items           (US-009: add to cart)

Uses FastAPI's in-process TestClient with an in-memory SQLite database.
No live PostgreSQL or Redis required.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force all ORM mappers to register before creating tables.
from app.core.database import Base  # noqa: F401

import app.domains.account.models  # noqa: F401
import app.domains.auth.models  # noqa: F401
import app.domains.categories.models  # noqa: F401
import app.domains.products.models  # noqa: F401
import app.domains.cart.models  # noqa: F401
import app.domains.checkout.models  # noqa: F401

from app.core.database import get_db
from app.domains.account.models import User
from app.domains.categories.models import Category
from app.domains.products.models import Product, ProductVariant
from app.domains.cart.models import Cart, CartItem

# ---------------------------------------------------------------------------
# Async SQLite test engine + session override
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture()
async def db_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys = ON"))
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture()
async def app_client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI test app that overrides get_db with the in-memory SQLite engine."""
    from app.main import create_app

    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    application = create_app()
    application.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_user(**kwargs) -> User:
    uid = uuid.uuid4().hex[:8]
    defaults: dict = dict(
        email=f"user_{uid}@test.com",
        hashed_password="$2b$12$fakehash",
    )
    defaults.update(kwargs)
    return User(**defaults)


def _make_category(**kwargs) -> Category:
    uid = uuid.uuid4().hex[:8]
    defaults: dict = dict(name=f"Category {uid}", slug=f"category-{uid}")
    defaults.update(kwargs)
    return Category(**defaults)


def _make_product(category_id, **kwargs) -> Product:
    uid = uuid.uuid4().hex[:8]
    defaults: dict = dict(
        category_id=category_id,
        name=f"Boot {uid}",
        slug=f"boot-{uid}",
        brand="Timberland",
        base_price=Decimal("129.99"),
        is_active=True,
    )
    defaults.update(kwargs)
    return Product(**defaults)


def _make_variant(product_id, **kwargs) -> ProductVariant:
    defaults: dict = dict(
        product_id=product_id,
        name="UK 9 / Brown",
        size="9",
        color="Brown",
        stock_quantity=10,
        inventory_count=10,
    )
    defaults.update(kwargs)
    return ProductVariant(**defaults)


# ---------------------------------------------------------------------------
# Fixtures: seeded data for API tests
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def seeded(db_session: AsyncSession):
    """Create categories, products, and variants used across multiple tests."""
    cat_work = _make_category(name="Work Boots", slug="work-boots")
    cat_hike = _make_category(name="Hiking Boots", slug="hiking-boots")
    db_session.add_all([cat_work, cat_hike])
    await db_session.flush()

    prod1 = _make_product(
        cat_work.id,
        name="CAT Excavator",
        slug="cat-excavator",
        brand="Caterpillar",
        base_price=Decimal("149.99"),
        image_url="https://cdn.test/cat.jpg",
        description="Waterproof work boot",
    )
    prod2 = _make_product(
        cat_work.id,
        name="Timberland Boondock",
        slug="timberland-boondock",
        brand="Timberland",
        base_price=Decimal("179.99"),
        image_url="https://cdn.test/tb.jpg",
        description="Rugged hiking boot",
    )
    prod3 = _make_product(
        cat_hike.id,
        name="Scarpa Marmolada",
        slug="scarpa-marmolada",
        brand="Scarpa",
        base_price=Decimal("249.99"),
        image_url="https://cdn.test/sc.jpg",
        description="Technical alpine boot",
    )
    db_session.add_all([prod1, prod2, prod3])
    await db_session.flush()

    var1 = _make_variant(prod1.id, size="9", color="Black", stock_quantity=5)
    var2 = _make_variant(prod1.id, size="10", color="Black", stock_quantity=3)
    var3 = _make_variant(prod2.id, size="9", color="Brown", stock_quantity=8)
    db_session.add_all([var1, var2, var3])
    await db_session.commit()

    return {
        "categories": {"work": cat_work, "hike": cat_hike},
        "products": {"prod1": prod1, "prod2": prod2, "prod3": prod3},
        "variants": {"var1": var1, "var2": var2, "var3": var3},
    }


# ---------------------------------------------------------------------------
# US-006: GET /api/v1/categories
# ---------------------------------------------------------------------------

class TestCategoriesEndpoint:
    """GET /api/v1/categories — US-006: browse category listing page."""

    @pytest.mark.asyncio
    async def test_list_categories_returns_200(self, app_client, seeded):
        resp = await app_client.get("/api/v1/categories")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_categories_has_items_and_total(self, app_client, seeded):
        resp = await app_client.get("/api/v1/categories")
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 2

    @pytest.mark.asyncio
    async def test_category_item_has_required_fields(self, app_client, seeded):
        resp = await app_client.get("/api/v1/categories")
        category = resp.json()["items"][0]
        assert "id" in category
        assert "name" in category
        assert "slug" in category


# ---------------------------------------------------------------------------
# US-006: GET /api/v1/products
# ---------------------------------------------------------------------------

class TestProductListingEndpoint:
    """GET /api/v1/products — US-006: product grid."""

    @pytest.mark.asyncio
    async def test_list_products_returns_200(self, app_client, seeded):
        resp = await app_client.get("/api/v1/products")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_products_has_pagination_fields(self, app_client, seeded):
        resp = await app_client.get("/api/v1/products")
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "page_size" in body
        assert "total_pages" in body

    @pytest.mark.asyncio
    async def test_product_card_has_required_listing_fields(self, app_client, seeded):
        """US-006: each product card shows image, name, brand, and price."""
        resp = await app_client.get("/api/v1/products")
        items = resp.json()["items"]
        assert len(items) >= 1
        card = items[0]
        assert "id" in card
        assert "name" in card
        assert "brand" in card
        assert "price" in card  # mapped from base_price via hybrid_property
        assert "thumbnail_url" in card

    @pytest.mark.asyncio
    async def test_filter_by_category_id(self, app_client, seeded):
        """US-006: filtering by category returns only products in that category."""
        cat_work = seeded["categories"]["work"]
        resp = await app_client.get(f"/api/v1/products?category_id={cat_work.id}")
        body = resp.json()
        assert resp.status_code == 200
        assert body["total"] == 2  # prod1 and prod2 belong to work boots
        for item in body["items"]:
            assert str(item["category_id"]) == str(cat_work.id)

    @pytest.mark.asyncio
    async def test_filter_category_returns_no_other_category_items(self, app_client, seeded):
        """US-006: category filter must exclude products from other categories."""
        cat_hike = seeded["categories"]["hike"]
        resp = await app_client.get(f"/api/v1/products?category_id={cat_hike.id}")
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Scarpa Marmolada"

    @pytest.mark.asyncio
    async def test_filter_by_size(self, app_client, seeded):
        """US-005: size filter returns only products with that variant size available."""
        resp = await app_client.get("/api/v1/products?size=9")
        body = resp.json()
        assert resp.status_code == 200
        # Both prod1 (size 9 Black) and prod2 (size 9 Brown) have size-9 variants
        assert body["total"] >= 2

    @pytest.mark.asyncio
    async def test_filter_by_color(self, app_client, seeded):
        """US-005: color filter returns only products with that variant color."""
        resp = await app_client.get("/api/v1/products?color=Black")
        body = resp.json()
        assert resp.status_code == 200
        # Only prod1 has Black variants
        assert body["total"] == 1
        assert body["items"][0]["name"] == "CAT Excavator"

    @pytest.mark.asyncio
    async def test_filter_by_size_and_color_combined(self, app_client, seeded):
        """US-005: multiple filters applied together narrow results."""
        resp = await app_client.get("/api/v1/products?size=9&color=Black")
        body = resp.json()
        assert resp.status_code == 200
        # Only prod1 has both size=9 AND color=Black
        assert body["total"] == 1
        assert body["items"][0]["name"] == "CAT Excavator"

    @pytest.mark.asyncio
    async def test_filter_by_min_price(self, app_client, seeded):
        """US-005: min_price filter excludes cheaper products."""
        resp = await app_client.get("/api/v1/products?min_price=200")
        body = resp.json()
        assert resp.status_code == 200
        assert body["total"] == 1  # only Scarpa at 249.99

    @pytest.mark.asyncio
    async def test_filter_by_max_price(self, app_client, seeded):
        """US-005: max_price filter excludes expensive products."""
        resp = await app_client.get("/api/v1/products?max_price=150")
        body = resp.json()
        assert resp.status_code == 200
        assert body["total"] == 1  # only CAT at 149.99

    @pytest.mark.asyncio
    async def test_no_filter_returns_all_active_products(self, app_client, seeded):
        resp = await app_client.get("/api/v1/products")
        body = resp.json()
        assert body["total"] == 3

    @pytest.mark.asyncio
    async def test_deselecting_filter_restores_full_results(self, app_client, seeded):
        """US-005: removing a filter restores unfiltered results."""
        # Apply size filter
        resp_filtered = await app_client.get("/api/v1/products?size=9")
        count_filtered = resp_filtered.json()["total"]

        # No filter → all results
        resp_all = await app_client.get("/api/v1/products")
        count_all = resp_all.json()["total"]

        assert count_all >= count_filtered


# ---------------------------------------------------------------------------
# US-004: GET /api/v1/products/search
# ---------------------------------------------------------------------------

class TestProductSearchEndpoint:
    """GET /api/v1/products/search — US-004: full-text keyword search."""

    @pytest.mark.asyncio
    async def test_search_matching_keyword_returns_results(self, app_client, seeded):
        """US-004: searching 'hiking' returns matching products."""
        resp = await app_client.get("/api/v1/products/search?q=Rugged")
        body = resp.json()
        assert resp.status_code == 200
        assert body["total"] >= 1

    @pytest.mark.asyncio
    async def test_search_by_brand_returns_results(self, app_client, seeded):
        """US-004: searching brand name returns matching products."""
        resp = await app_client.get("/api/v1/products/search?q=Caterpillar")
        body = resp.json()
        assert resp.status_code == 200
        assert body["total"] == 1
        assert "CAT" in body["items"][0]["name"]

    @pytest.mark.asyncio
    async def test_search_no_match_returns_empty_list(self, app_client, seeded):
        """US-004: search with no match returns empty items list (not 404)."""
        resp = await app_client.get("/api/v1/products/search?q=XYZ_NONEXISTENT_BRAND_999")
        body = resp.json()
        assert resp.status_code == 200
        assert body["total"] == 0
        assert body["items"] == []

    @pytest.mark.asyncio
    async def test_search_requires_query_param(self, app_client, seeded):
        """US-004: missing q param returns 422 validation error."""
        resp = await app_client.get("/api/v1/products/search")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# US-007: GET /api/v1/products/{product_id}
# ---------------------------------------------------------------------------

class TestProductDetailEndpoint:
    """GET /api/v1/products/{product_id} — US-007: product detail page."""

    @pytest.mark.asyncio
    async def test_get_product_returns_200(self, app_client, seeded):
        prod = seeded["products"]["prod1"]
        resp = await app_client.get(f"/api/v1/products/{prod.id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_product_detail_has_required_fields(self, app_client, seeded):
        """US-007: PDP includes description, images, variants for size/color selection."""
        prod = seeded["products"]["prod1"]
        resp = await app_client.get(f"/api/v1/products/{prod.id}")
        body = resp.json()
        assert "id" in body
        assert "name" in body
        assert "description" in body
        assert "images" in body
        assert "variants" in body  # size/color selection
        assert "brand" in body
        assert "price" in body

    @pytest.mark.asyncio
    async def test_product_detail_includes_variants(self, app_client, seeded):
        """US-007: user can see available size/color variants."""
        prod = seeded["products"]["prod1"]
        resp = await app_client.get(f"/api/v1/products/{prod.id}")
        body = resp.json()
        variants = body["variants"]
        assert len(variants) == 2  # var1 (size 9) and var2 (size 10)
        sizes = {v["size"] for v in variants}
        assert "9" in sizes
        assert "10" in sizes

    @pytest.mark.asyncio
    async def test_product_detail_not_found_returns_404(self, app_client, seeded):
        """US-007: requesting a non-existent product returns 404."""
        fake_id = uuid.uuid4()
        resp = await app_client.get(f"/api/v1/products/{fake_id}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# US-009: POST /api/v1/cart/items
# ---------------------------------------------------------------------------

class TestAddCartItemEndpoint:
    """POST /api/v1/cart/items — US-009: add product to shopping cart."""

    @pytest.mark.asyncio
    async def test_add_item_to_cart_returns_201(self, app_client, seeded):
        """US-009: adding an item creates a cart and returns 201."""
        prod = seeded["products"]["prod1"]
        var = seeded["variants"]["var1"]
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(prod.id), "variant_id": str(var.id), "quantity": 1},
            headers={"X-Session-ID": "test-session-001"},
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_add_item_response_has_cart_structure(self, app_client, seeded):
        """US-009: response contains cart id, items, total, and item_count."""
        prod = seeded["products"]["prod1"]
        var = seeded["variants"]["var1"]
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(prod.id), "variant_id": str(var.id), "quantity": 1},
            headers={"X-Session-ID": "test-session-002"},
        )
        body = resp.json()
        assert "id" in body
        assert "items" in body
        assert "total" in body
        assert "item_count" in body
        assert body["item_count"] == 1

    @pytest.mark.asyncio
    async def test_add_item_without_variant(self, app_client, seeded):
        """US-009: item can be added without specifying a variant."""
        prod = seeded["products"]["prod3"]
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(prod.id), "quantity": 1},
            headers={"X-Session-ID": "test-session-003"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["item_count"] == 1

    @pytest.mark.asyncio
    async def test_add_item_to_same_session_accumulates(self, app_client, seeded):
        """US-009: adding two items to the same guest session cart shows 2 items."""
        prod1 = seeded["products"]["prod1"]
        prod2 = seeded["products"]["prod2"]
        session_id = "test-session-accumulate"
        await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(prod1.id), "quantity": 1},
            headers={"X-Session-ID": session_id},
        )
        resp2 = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(prod2.id), "quantity": 1},
            headers={"X-Session-ID": session_id},
        )
        body = resp2.json()
        assert body["item_count"] == 2

    @pytest.mark.asyncio
    async def test_add_item_invalid_product_id_returns_error(self, app_client, seeded):
        """US-009: adding non-existent product id returns 4xx error."""
        fake_id = uuid.uuid4()
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(fake_id), "quantity": 1},
            headers={"X-Session-ID": "test-session-error"},
        )
        assert resp.status_code in (404, 422, 400)
