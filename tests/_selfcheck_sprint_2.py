"""
Sprint 2 self-check — T-012 (US-004): Product search API endpoint.

Exercises:
  - GET /api/v1/products/search?q=hiking  -> results found
  - GET /api/v1/products/search?q=nonexistent  -> empty list (no 404)
  - GET /api/v1/products/search  -> 422 (missing q param)
  - GET /api/v1/products  -> 200 with pagination fields (US-005, US-006)
  - GET /api/v1/products?size=9  -> narrowed results (US-005)
  - GET /api/v1/categories  -> 200 with items + total (US-006)
  - GET /api/v1/products/{id}  -> 200 with description, images, variants (US-007)
  - POST /api/v1/cart/items  -> 201, cart with item_count (US-009)
  - POST /api/v1/cart/items (no token, guest session)  -> 201 (no auth required)
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from app.core.database import Base, get_db
import app.domains.account.models  # noqa
import app.domains.auth.models  # noqa
import app.domains.categories.models  # noqa
import app.domains.products.models  # noqa
import app.domains.cart.models  # noqa
import app.domains.checkout.models  # noqa

from app.domains.categories.models import Category
from app.domains.products.models import Product, ProductVariant


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
    await engine.dispose()


@pytest_asyncio.fixture()
async def client(db_engine) -> AsyncClient:
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

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture()
async def seeded(db_engine):
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        cat_hike = Category(name="Hiking Boots", slug="hiking-boots")
        cat_work = Category(name="Work Boots", slug="work-boots")
        session.add_all([cat_hike, cat_work])
        await session.flush()

        p1 = Product(
            category_id=cat_hike.id,
            name="Hiking Pro X",
            slug="hiking-pro-x",
            brand="TrailBlazers",
            base_price=Decimal("129.99"),
            description="Best hiking boot for rugged terrain",
            is_active=True,
        )
        p2 = Product(
            category_id=cat_work.id,
            name="Steel Toe Work Boot",
            slug="steel-toe-work",
            brand="SafetyFirst",
            base_price=Decimal("89.99"),
            description="Heavy-duty work boot with steel toe",
            is_active=True,
        )
        session.add_all([p1, p2])
        await session.flush()

        v1 = ProductVariant(
            product_id=p1.id,
            name="UK 9 / Black",
            size="9",
            color="Black",
            stock_quantity=10,
            inventory_count=10,
        )
        v2 = ProductVariant(
            product_id=p1.id,
            name="UK 10 / Black",
            size="10",
            color="Black",
            stock_quantity=5,
            inventory_count=5,
        )
        session.add_all([v1, v2])
        await session.commit()

        return {
            "cat_hike": cat_hike,
            "cat_work": cat_work,
            "p1": p1,
            "p2": p2,
            "v1": v1,
            "v2": v2,
        }


# ---------------------------------------------------------------------------
# US-004: Search for Boots
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_keyword_hiking_returns_results(client, seeded):
    """US-004 AC1: searching 'hiking' shows relevant boots."""
    resp = await client.get("/api/v1/products/search?q=hiking")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any("hiking" in item["name"].lower() or "hiking" in (item.get("description") or "").lower()
               for item in body["items"])


@pytest.mark.asyncio
async def test_search_no_match_returns_empty_not_404(client, seeded):
    """US-004 AC2: no-match search returns empty list, not 404."""
    resp = await client.get("/api/v1/products/search?q=XYZ_NORESULTS_99999")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_search_missing_q_returns_422(client, seeded):
    """US-004: missing q param returns 422."""
    resp = await client.get("/api/v1/products/search")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# US-005: Filter Product Listings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_size_filter_narrows_results(client, seeded):
    """US-005 AC1: size filter narrows product grid to products with that size."""
    resp_all = await client.get("/api/v1/products")
    count_all = resp_all.json()["total"]

    resp_filtered = await client.get("/api/v1/products?size=9")
    count_filtered = resp_filtered.json()["total"]

    assert resp_filtered.status_code == 200
    assert count_filtered < count_all or count_filtered == count_all  # at most all
    # p1 has size 9; p2 has no variants => only p1 should appear
    assert count_filtered == 1


@pytest.mark.asyncio
async def test_multiple_filters_combined(client, seeded):
    """US-005 AC2: multiple filters applied together (size + color)."""
    resp = await client.get("/api/v1/products?size=9&color=Black")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Hiking Pro X"


@pytest.mark.asyncio
async def test_removing_filter_restores_results(client, seeded):
    """US-005 AC3: deselecting a filter restores full results."""
    resp_filtered = await client.get("/api/v1/products?size=9")
    resp_all = await client.get("/api/v1/products")
    assert resp_all.json()["total"] >= resp_filtered.json()["total"]


# ---------------------------------------------------------------------------
# US-006: Product Listing Page
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_categories_endpoint_returns_list(client, seeded):
    """US-006 AC1: clicking a category shows boots in that category."""
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 2


@pytest.mark.asyncio
async def test_product_card_has_image_name_brand_price(client, seeded):
    """US-006 AC2: each product card shows image, name, brand, price."""
    resp = await client.get("/api/v1/products")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    for card in items:
        assert "name" in card
        assert "brand" in card
        assert "price" in card
        assert "thumbnail_url" in card


# ---------------------------------------------------------------------------
# US-007: View Product Details
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_product_detail_has_description_images_variants(client, seeded):
    """US-007: PDP has description, images, and variants for size/color selection."""
    p1_id = seeded["p1"].id
    resp = await client.get(f"/api/v1/products/{p1_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert "description" in body
    assert "images" in body
    assert "variants" in body
    # Has size-9 and size-10 variants
    sizes = {v["size"] for v in body["variants"]}
    assert "9" in sizes
    assert "10" in sizes


@pytest.mark.asyncio
async def test_product_detail_not_found_returns_404(client, seeded):
    """US-007: non-existent product id returns 404."""
    resp = await client.get(f"/api/v1/products/{uuid.uuid4()}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# US-009: Add to Shopping Cart
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_to_cart_creates_cart_201(client, seeded):
    """US-009 AC1: adding item with size/color selected returns 201."""
    p1_id = seeded["p1"].id
    v1_id = seeded["v1"].id
    resp = await client.post(
        "/api/v1/cart/items",
        json={"product_id": str(p1_id), "variant_id": str(v1_id), "quantity": 1},
        headers={"X-Session-ID": "selfcheck-sess-001"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["item_count"] == 1
    assert len(body["items"]) == 1


@pytest.mark.asyncio
async def test_add_to_cart_no_auth_required(client, seeded):
    """US-009: guest (no token) can add to cart using X-Session-ID."""
    p1_id = seeded["p1"].id
    resp = await client.post(
        "/api/v1/cart/items",
        json={"product_id": str(p1_id), "quantity": 1},
        headers={"X-Session-ID": "selfcheck-guest-002"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_add_to_cart_item_count_updates(client, seeded):
    """US-009 AC2: cart icon count (item_count) updates after add."""
    p1_id = seeded["p1"].id
    p2_id = seeded["p2"].id
    session_id = "selfcheck-count-003"

    resp1 = await client.post(
        "/api/v1/cart/items",
        json={"product_id": str(p1_id), "quantity": 1},
        headers={"X-Session-ID": session_id},
    )
    assert resp1.json()["item_count"] == 1

    resp2 = await client.post(
        "/api/v1/cart/items",
        json={"product_id": str(p2_id), "quantity": 1},
        headers={"X-Session-ID": session_id},
    )
    assert resp2.json()["item_count"] == 2
