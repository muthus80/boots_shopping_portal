"""Integration tests for US-004 (Search for Boots), US-005 (Filter Product Listings),
and US-006 (View Product Listing Page).

Tests cover: keyword search, no-results state, filtering by size/color, category listing,
and product card fields.
"""
from __future__ import annotations

import pytest
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.sprint_3.conftest import (
    create_category_in_db,
    create_product_in_db,
    create_variant_in_db,
)

pytestmark = pytest.mark.asyncio


class TestSearchForBoots:
    """US-004: Search for Boots"""

    async def test_keyword_search_returns_relevant_products(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Searching for 'hiking' returns results page with matching boots."""
        # Seed a hiking boot and an unrelated product
        cat = await create_category_in_db(db_session, name="Hiking Boots", slug="hiking-boots")
        await create_product_in_db(
            db_session,
            name="Timberland Hiking Boot",
            base_price=Decimal("149.99"),
            category_id=cat.id,
            brand="Timberland",
            description="Premium hiking boot for outdoor use.",
        )
        await create_product_in_db(
            db_session,
            name="Chelsea Fashion Boot",
            base_price=Decimal("89.99"),
            brand="Clarks",
            description="Elegant chelsea boot for everyday use.",
        )

        resp = await async_client.get("/api/v1/products/search", params={"q": "hiking"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        data = resp.json()
        assert "items" in data
        items = data["items"]
        # At least one result containing 'hiking'
        assert len(items) >= 1, "Expected at least one search result for 'hiking'"

        names = [p["name"].lower() for p in items]
        assert any("hiking" in n for n in names), (
            f"Expected 'hiking' in at least one result name; got: {names}"
        )

    async def test_search_returns_no_results_for_unmatched_query(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: No matching products → items list empty (frontend shows 'No results found')."""
        resp = await async_client.get(
            "/api/v1/products/search",
            params={"q": "xyznonexistentbootquery99999"},
        )
        assert resp.status_code == 200

        data = resp.json()
        assert "items" in data
        assert data["items"] == [], f"Expected empty items for no-match query, got {data['items']}"
        assert data["total"] == 0

    async def test_search_requires_at_least_one_character(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Search query must have at least 1 character (API enforces min_length=1)."""
        resp = await async_client.get("/api/v1/products/search", params={"q": ""})
        # FastAPI validates min_length=1 → 422
        assert resp.status_code == 422


class TestFilterProductListings:
    """US-005: Filter Product Listings"""

    async def test_filter_by_size_returns_only_matching_products(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Size filter applied → product grid shows only boots available in that size."""
        cat = await create_category_in_db(db_session, name="Work Boots", slug="work-boots-filter")

        # Product with size 9 variant
        prod_size9 = await create_product_in_db(
            db_session, name="Work Boot Size 9", category_id=cat.id
        )
        await create_variant_in_db(db_session, product_id=prod_size9.id, size="9", color="Black")

        # Product with size 7 variant (should NOT appear in size=9 filter)
        prod_size7 = await create_product_in_db(
            db_session, name="Work Boot Size 7", category_id=cat.id
        )
        await create_variant_in_db(db_session, product_id=prod_size7.id, size="7", color="Brown")

        resp = await async_client.get("/api/v1/products", params={"size": "9"})
        assert resp.status_code == 200

        data = resp.json()
        items = data["items"]
        # Only the size 9 product should appear
        assert len(items) >= 1, "Expected at least one product with size 9"
        names = [p["name"] for p in items]
        assert "Work Boot Size 9" in names, f"Size 9 product not in results: {names}"
        assert "Work Boot Size 7" not in names, f"Size 7 product unexpectedly in results: {names}"

    async def test_filter_by_size_and_color_combination(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Multiple filters applied (size 8, color Black) → only matching products shown."""
        cat = await create_category_in_db(db_session, name="All Boots", slug="all-boots-filter")

        # Product with size 8, Black
        prod_match = await create_product_in_db(db_session, name="Matching Boot", category_id=cat.id)
        await create_variant_in_db(db_session, product_id=prod_match.id, size="8", color="Black")

        # Product with size 8, Brown — should NOT appear in color=Black filter
        prod_brown = await create_product_in_db(db_session, name="Brown Size 8 Boot", category_id=cat.id)
        await create_variant_in_db(db_session, product_id=prod_brown.id, size="8", color="Brown")

        # Product with size 6, Black — should NOT appear in size=8 filter
        prod_size6 = await create_product_in_db(db_session, name="Black Size 6 Boot", category_id=cat.id)
        await create_variant_in_db(db_session, product_id=prod_size6.id, size="6", color="Black")

        resp = await async_client.get("/api/v1/products", params={"size": "8", "color": "Black"})
        assert resp.status_code == 200

        data = resp.json()
        items = data["items"]
        assert len(items) >= 1

        names = [p["name"] for p in items]
        assert "Matching Boot" in names, f"Matching boot not in results: {names}"
        assert "Brown Size 8 Boot" not in names, "Brown boot should not appear in Black filter"
        assert "Black Size 6 Boot" not in names, "Size 6 boot should not appear in size 8 filter"

    async def test_filter_removal_restores_full_listing(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Removing a filter (deselecting) → product grid updates to show more results."""
        cat = await create_category_in_db(db_session, name="Casual Boots", slug="casual-boots-filter")
        prod1 = await create_product_in_db(db_session, name="Casual Boot A", category_id=cat.id)
        prod2 = await create_product_in_db(db_session, name="Casual Boot B", category_id=cat.id)
        await create_variant_in_db(db_session, product_id=prod1.id, size="8", color="Black")
        await create_variant_in_db(db_session, product_id=prod2.id, size="7", color="Brown")

        # With size filter applied
        filtered_resp = await async_client.get(
            "/api/v1/products", params={"category_id": str(cat.id), "size": "8"}
        )
        assert filtered_resp.status_code == 200
        filtered_count = filtered_resp.json()["total"]

        # Without size filter (filter removed)
        unfiltered_resp = await async_client.get(
            "/api/v1/products", params={"category_id": str(cat.id)}
        )
        assert unfiltered_resp.status_code == 200
        unfiltered_count = unfiltered_resp.json()["total"]

        # Removing the filter yields more (or equal) results
        assert unfiltered_count >= filtered_count, (
            f"Unfiltered ({unfiltered_count}) should be >= filtered ({filtered_count})"
        )


class TestViewProductListingPage:
    """US-006: View Product Listing Page"""

    async def test_clicking_category_shows_all_boots_in_that_category(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Navigating to a category → grid of all boots in that category."""
        cat = await create_category_in_db(db_session, name="Work Boots", slug="work-boots-us006")
        other_cat = await create_category_in_db(db_session, name="Chelsea Boots", slug="chelsea-boots-us006")

        work_boot1 = await create_product_in_db(
            db_session, name="Heavy Duty Work Boot", category_id=cat.id
        )
        work_boot2 = await create_product_in_db(
            db_session, name="Safety Toe Work Boot", category_id=cat.id
        )
        chelsea = await create_product_in_db(
            db_session, name="Classic Chelsea Boot", category_id=other_cat.id
        )

        resp = await async_client.get(
            "/api/v1/products", params={"category_id": str(cat.id)}
        )
        assert resp.status_code == 200

        data = resp.json()
        items = data["items"]
        assert len(items) == 2, f"Expected 2 work boots, got {len(items)}"

        names = {p["name"] for p in items}
        assert "Heavy Duty Work Boot" in names
        assert "Safety Toe Work Boot" in names
        assert "Classic Chelsea Boot" not in names

    async def test_product_card_contains_required_fields(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC: Each product card displays primary image, boot name, brand, and price."""
        cat = await create_category_in_db(db_session, name="Display Boots", slug="display-boots")
        await create_product_in_db(
            db_session,
            name="Clarks Desert Boot",
            brand="Clarks",
            base_price=Decimal("89.99"),
            category_id=cat.id,
        )

        resp = await async_client.get("/api/v1/products", params={"category_id": str(cat.id)})
        assert resp.status_code == 200

        items = resp.json()["items"]
        assert len(items) >= 1

        card = items[0]
        # AC: product card fields
        assert "name" in card, "Product card missing 'name'"
        assert "brand" in card, "Product card missing 'brand'"
        assert "price" in card, "Product card missing 'price'"
        # thumbnail_url may be None but the key must be present
        assert "thumbnail_url" in card, "Product card missing 'thumbnail_url'"
        assert card["name"] == "Clarks Desert Boot"
        assert card["brand"] == "Clarks"
        assert float(card["price"]) == pytest.approx(89.99, rel=1e-3)

    async def test_list_categories_returns_all_active_categories(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """AC (US-006): Categories endpoint returns list for navigation."""
        await create_category_in_db(db_session, name="Hiking Boots Cat", slug="hiking-cat-nav")
        await create_category_in_db(db_session, name="Work Boots Cat", slug="work-cat-nav")

        resp = await async_client.get("/api/v1/categories")
        assert resp.status_code == 200

        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 2

        slugs = {c["slug"] for c in data["items"]}
        assert "hiking-cat-nav" in slugs
        assert "work-cat-nav" in slugs
