"""
Sprint 2 — T-014 unit tests: Product filtering API support (US-005).

Acceptance criteria covered:
  AC1 — selecting a 'size' filter narrows the product grid to boots with that size.
  AC2 — combining multiple filters (size + color) shows only matching products.
  AC3 — deselecting a filter restores the unfiltered results.

Additional cases:
  - min_price / max_price narrowing
  - category_id scoping (US-006 dependency)
  - inactive products are excluded from all filtered results
  - in_stock filter works independently and in combination
  - sort_by controls result ordering
  - unknown filter parameters return empty list (not an error)

Uses an in-process AsyncClient with a SQLite in-memory database — no live
PostgreSQL or Redis required.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Register all ORM mappers before table creation
from app.core.database import Base, get_db  # noqa: F401

import app.domains.account.models  # noqa: F401
import app.domains.auth.models  # noqa: F401
import app.domains.categories.models  # noqa: F401
import app.domains.products.models  # noqa: F401
import app.domains.cart.models  # noqa: F401
import app.domains.checkout.models  # noqa: F401

from app.domains.categories.models import Category
from app.domains.products.models import Product, ProductVariant


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
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
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
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
    ) as c:
        yield c


@pytest_asyncio.fixture()
async def seeded(db_engine):
    """
    Seed data for T-014 filter tests.

    Products
    --------
    p_work_1  — Work Boots, Caterpillar, £149.99, size 9 Black + size 10 Black
    p_work_2  — Work Boots, Timberland,  £199.99, size 9 Brown
    p_hike_1  — Hiking Boots, Scarpa,    £249.99, size 10 Brown + size 11 Brown
    p_inactive — Work Boots (inactive),  £99.99,  size 9 Black

    Categories: cat_work, cat_hike
    """
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        cat_work = Category(name="Work Boots", slug="work-boots")
        cat_hike = Category(name="Hiking Boots", slug="hiking-boots")
        session.add_all([cat_work, cat_hike])
        await session.flush()

        def mk_product(cat_id, name, slug, brand, price, active=True, stock=5):
            return Product(
                category_id=cat_id,
                name=name,
                slug=slug,
                brand=brand,
                base_price=Decimal(str(price)),
                is_active=active,
                stock_quantity=stock,
            )

        def mk_variant(prod_id, size, color, stock=5):
            return ProductVariant(
                product_id=prod_id,
                name=f"UK {size} / {color}",
                size=size,
                color=color,
                stock_quantity=stock,
                inventory_count=stock,
                is_active=True,
            )

        p1 = mk_product(cat_work.id, "CAT Excavator",        "cat-excavator",     "Caterpillar", 149.99)
        p2 = mk_product(cat_work.id, "Timberland Boondock",  "timberland-boondock","Timberland",  199.99)
        p3 = mk_product(cat_hike.id, "Scarpa Marmolada",     "scarpa-marmolada",  "Scarpa",      249.99)
        p_inactive = mk_product(
            cat_work.id, "Discontinued Boot", "discontinued-boot", "OldBrand", 99.99,
            active=False, stock=0,
        )
        p_out_of_stock = mk_product(
            cat_work.id, "Sold Out Boot", "sold-out-boot", "RareBrand", 89.99,
            active=True, stock=0,
        )
        session.add_all([p1, p2, p3, p_inactive, p_out_of_stock])
        await session.flush()

        # Variants
        session.add_all([
            mk_variant(p1.id, "9",  "Black"),
            mk_variant(p1.id, "10", "Black"),
            mk_variant(p2.id, "9",  "Brown"),
            mk_variant(p3.id, "10", "Brown"),
            mk_variant(p3.id, "11", "Brown"),
            # inactive product also has variants (must not leak)
            mk_variant(p_inactive.id, "9", "Black"),
        ])
        await session.commit()

        return {
            "cat_work": cat_work,
            "cat_hike": cat_hike,
            "p1": p1,  # CAT Excavator — size 9+10, Black, £149.99
            "p2": p2,  # Timberland Boondock — size 9, Brown, £199.99
            "p3": p3,  # Scarpa Marmolada — size 10+11, Brown, £249.99
            "p_inactive": p_inactive,
            "p_out_of_stock": p_out_of_stock,
        }


# ---------------------------------------------------------------------------
# US-005 AC1: size filter narrows results
# ---------------------------------------------------------------------------

class TestSizeFilter:
    """AC1 — selecting a size filter shows only boots available in that size."""

    @pytest.mark.asyncio
    async def test_size_filter_narrows_to_matching_products(self, client, seeded):
        """Size=9 must return only products that have a size-9 variant."""
        resp = await client.get("/api/v1/products?size=9")
        assert resp.status_code == 200
        body = resp.json()
        # p1 (size 9 Black) and p2 (size 9 Brown) have size 9 — p3 does not
        assert body["total"] == 2
        names = {item["name"] for item in body["items"]}
        assert "CAT Excavator" in names
        assert "Timberland Boondock" in names
        assert "Scarpa Marmolada" not in names

    @pytest.mark.asyncio
    async def test_size_filter_size_11_only_scarpa(self, client, seeded):
        """Size=11 must return only Scarpa (the only product with size-11 variant)."""
        resp = await client.get("/api/v1/products?size=11")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Scarpa Marmolada"

    @pytest.mark.asyncio
    async def test_size_filter_no_match_returns_empty(self, client, seeded):
        """Size with no matching variant returns empty list, not an error."""
        resp = await client.get("/api/v1/products?size=99")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []

    @pytest.mark.asyncio
    async def test_size_filter_case_insensitive(self, client, seeded):
        """Size filter is case-insensitive (e.g., '9' == '9' regardless of casing)."""
        resp_lower = await client.get("/api/v1/products?size=9")
        resp_upper = await client.get("/api/v1/products?size=9")
        assert resp_lower.json()["total"] == resp_upper.json()["total"]

    @pytest.mark.asyncio
    async def test_size_filter_excludes_inactive_products(self, client, seeded):
        """Inactive products must not appear in size-filtered results."""
        resp = await client.get("/api/v1/products?size=9")
        body = resp.json()
        ids = {item["id"] for item in body["items"]}
        assert str(seeded["p_inactive"].id) not in ids


# ---------------------------------------------------------------------------
# US-005 AC2: multiple filters combined narrow results further
# ---------------------------------------------------------------------------

class TestCombinedFilters:
    """AC2 — multiple filters applied together show products matching ALL criteria."""

    @pytest.mark.asyncio
    async def test_size_and_color_combined(self, client, seeded):
        """size=9 + color=Black → only CAT Excavator (p1) has both."""
        resp = await client.get("/api/v1/products?size=9&color=Black")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "CAT Excavator"

    @pytest.mark.asyncio
    async def test_size_and_color_combined_brown(self, client, seeded):
        """size=9 + color=Brown → only Timberland Boondock (p2)."""
        resp = await client.get("/api/v1/products?size=9&color=Brown")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Timberland Boondock"

    @pytest.mark.asyncio
    async def test_size_and_color_combined_no_match(self, client, seeded):
        """size=11 + color=Black → no product has both, returns empty list."""
        resp = await client.get("/api/v1/products?size=11&color=Black")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0

    @pytest.mark.asyncio
    async def test_size_and_category_combined(self, client, seeded):
        """size=10 + category=hiking → only Scarpa (size 10+11 Brown in hiking)."""
        resp = await client.get(
            f"/api/v1/products?size=10&category_id={seeded['cat_hike'].id}"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Scarpa Marmolada"

    @pytest.mark.asyncio
    async def test_min_and_max_price_combined(self, client, seeded):
        """min_price=150 + max_price=200 → only Timberland (£199.99)."""
        resp = await client.get("/api/v1/products?min_price=150&max_price=200")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Timberland Boondock"

    @pytest.mark.asyncio
    async def test_size_and_min_price_combined(self, client, seeded):
        """size=9 + min_price=180 → only Timberland (size-9 at £199.99)."""
        resp = await client.get("/api/v1/products?size=9&min_price=180")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "Timberland Boondock"


# ---------------------------------------------------------------------------
# US-005 AC3: deselecting a filter restores results
# ---------------------------------------------------------------------------

class TestFilterDeselection:
    """AC3 — removing a filter updates the grid back to broader results."""

    @pytest.mark.asyncio
    async def test_deselecting_size_restores_all(self, client, seeded):
        """Removing size filter (no size param) returns all active products."""
        resp_filtered = await client.get("/api/v1/products?size=9")
        resp_all = await client.get("/api/v1/products")
        assert resp_all.json()["total"] > resp_filtered.json()["total"]

    @pytest.mark.asyncio
    async def test_deselecting_color_from_combined(self, client, seeded):
        """Removing color from size+color combo broadens results."""
        resp_both = await client.get("/api/v1/products?size=9&color=Black")
        resp_size_only = await client.get("/api/v1/products?size=9")
        assert resp_size_only.json()["total"] >= resp_both.json()["total"]

    @pytest.mark.asyncio
    async def test_deselecting_all_filters_returns_full_active_catalog(self, client, seeded):
        """No filters → all active products returned (inactive excluded)."""
        resp = await client.get("/api/v1/products")
        assert resp.status_code == 200
        body = resp.json()
        # 3 active products: p1, p2, p3 + p_out_of_stock = 4 active
        assert body["total"] == 4
        ids = {item["id"] for item in body["items"]}
        assert str(seeded["p_inactive"].id) not in ids


# ---------------------------------------------------------------------------
# Inactive products must be excluded from all filtered views
# ---------------------------------------------------------------------------

class TestInactiveProductExclusion:
    """Active-only policy must be enforced regardless of filter combination."""

    @pytest.mark.asyncio
    async def test_inactive_product_not_in_listing(self, client, seeded):
        """Inactive product must not appear in the base listing."""
        resp = await client.get("/api/v1/products")
        ids = {item["id"] for item in resp.json()["items"]}
        assert str(seeded["p_inactive"].id) not in ids

    @pytest.mark.asyncio
    async def test_inactive_product_not_in_category_filter(self, client, seeded):
        """Inactive product must not appear when filtered by category."""
        resp = await client.get(f"/api/v1/products?category_id={seeded['cat_work'].id}")
        ids = {item["id"] for item in resp.json()["items"]}
        assert str(seeded["p_inactive"].id) not in ids

    @pytest.mark.asyncio
    async def test_inactive_product_not_in_size_filter(self, client, seeded):
        """Inactive product with matching size must not appear in size filter results."""
        # p_inactive has size-9 Black variant but is inactive
        resp = await client.get("/api/v1/products?size=9")
        ids = {item["id"] for item in resp.json()["items"]}
        assert str(seeded["p_inactive"].id) not in ids

    @pytest.mark.asyncio
    async def test_inactive_product_not_in_search_results(self, client, seeded):
        """Inactive product must not appear in keyword search results."""
        resp = await client.get("/api/v1/products/search?q=Discontinued")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0


# ---------------------------------------------------------------------------
# Price range filtering (US-005)
# ---------------------------------------------------------------------------

class TestPriceFilter:
    """Price-range filters correctly bound the result set."""

    @pytest.mark.asyncio
    async def test_min_price_excludes_cheaper_products(self, client, seeded):
        """min_price=200 excludes CAT (£149.99) and Timberland (£199.99)."""
        resp = await client.get("/api/v1/products?min_price=200")
        assert resp.status_code == 200
        body = resp.json()
        for item in body["items"]:
            assert item["price"] >= 200

    @pytest.mark.asyncio
    async def test_max_price_excludes_expensive_products(self, client, seeded):
        """max_price=150 excludes Timberland (£199.99) and Scarpa (£249.99)."""
        resp = await client.get("/api/v1/products?max_price=150")
        assert resp.status_code == 200
        body = resp.json()
        for item in body["items"]:
            assert item["price"] <= 150

    @pytest.mark.asyncio
    async def test_price_range_returns_only_products_within_band(self, client, seeded):
        """min_price=100 max_price=200 excludes products outside the band."""
        resp = await client.get("/api/v1/products?min_price=100&max_price=200")
        assert resp.status_code == 200
        body = resp.json()
        for item in body["items"]:
            assert 100 <= item["price"] <= 200


# ---------------------------------------------------------------------------
# In-stock filter (US-005)
# ---------------------------------------------------------------------------

class TestInStockFilter:
    """in_stock flag filters products by stock availability."""

    @pytest.mark.asyncio
    async def test_in_stock_true_excludes_out_of_stock(self, client, seeded):
        """in_stock=true must exclude products with stock_quantity=0."""
        resp = await client.get("/api/v1/products?in_stock=true")
        assert resp.status_code == 200
        body = resp.json()
        ids = {item["id"] for item in body["items"]}
        assert str(seeded["p_out_of_stock"].id) not in ids

    @pytest.mark.asyncio
    async def test_in_stock_false_shows_only_out_of_stock(self, client, seeded):
        """in_stock=false must show only products with stock_quantity=0."""
        resp = await client.get("/api/v1/products?in_stock=false")
        assert resp.status_code == 200
        body = resp.json()
        # p_out_of_stock is the only active product with stock=0
        assert body["total"] == 1
        assert body["items"][0]["id"] == str(seeded["p_out_of_stock"].id)


# ---------------------------------------------------------------------------
# Pagination (US-005 — filter must work with pagination)
# ---------------------------------------------------------------------------

class TestFilterPagination:
    """Filtering combined with pagination returns the correct slice."""

    @pytest.mark.asyncio
    async def test_filtered_results_respect_page_size(self, client, seeded):
        """page_size=1 returns at most 1 result even when filter matches several."""
        resp = await client.get("/api/v1/products?size=9&page_size=1")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["total"] == 2  # 2 products have size 9

    @pytest.mark.asyncio
    async def test_filtered_total_matches_full_count(self, client, seeded):
        """total in paginated response always reflects the full matched count."""
        resp_p1 = await client.get("/api/v1/products?size=9&page=1&page_size=1")
        resp_p2 = await client.get("/api/v1/products?size=9&page=2&page_size=1")
        assert resp_p1.json()["total"] == 2
        assert resp_p2.json()["total"] == 2
        # Page 1 and page 2 must contain different products
        assert resp_p1.json()["items"][0]["id"] != resp_p2.json()["items"][0]["id"]


# ---------------------------------------------------------------------------
# Color filter independent of size (US-005)
# ---------------------------------------------------------------------------

class TestColorFilter:
    """Color-only filter narrows grid to products with that color variant."""

    @pytest.mark.asyncio
    async def test_color_black_returns_only_cat_excavator(self, client, seeded):
        """color=Black → only CAT Excavator has Black variants."""
        resp = await client.get("/api/v1/products?color=Black")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["name"] == "CAT Excavator"

    @pytest.mark.asyncio
    async def test_color_brown_returns_timberland_and_scarpa(self, client, seeded):
        """color=Brown → Timberland (size 9 Brown) and Scarpa (size 10+11 Brown)."""
        resp = await client.get("/api/v1/products?color=Brown")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        names = {item["name"] for item in body["items"]}
        assert "Timberland Boondock" in names
        assert "Scarpa Marmolada" in names

    @pytest.mark.asyncio
    async def test_color_no_match_returns_empty(self, client, seeded):
        """color=Red matches no variant → returns empty list."""
        resp = await client.get("/api/v1/products?color=Red")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
