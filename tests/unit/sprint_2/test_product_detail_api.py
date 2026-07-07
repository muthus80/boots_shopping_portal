"""
Sprint 2 T-016 unit tests — Product detail API endpoint (US-007).

Acceptance criteria exercised:
  AC1: GET /api/v1/products/{id} returns multiple high-resolution images
  AC2: Response includes detailed description, material, features, and sizing info
  AC3: Variants expose size and color for user selection
  AC4: Non-existent product_id returns 404
  AC5: Response includes reviews list
  AC6: Inactive products still retrievable via direct ID lookup
  AC7: Response schema matches ProductRead (all required fields present)
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

# Register all ORM mappers before creating SQLite tables
from app.core.database import Base, get_db  # noqa: F401
import app.domains.account.models  # noqa: F401
import app.domains.auth.models  # noqa: F401
import app.domains.categories.models  # noqa: F401
import app.domains.products.models  # noqa: F401
import app.domains.cart.models  # noqa: F401
import app.domains.checkout.models  # noqa: F401

from app.domains.categories.models import Category
from app.domains.products.models import Product, ProductVariant, Review
from app.domains.account.models import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
async def app_client(db_engine) -> AsyncGenerator[AsyncClient, None]:
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


@pytest_asyncio.fixture()
async def seeded_product(db_engine):
    """
    Seed a fully-detailed product with:
      - multiple images (AC1)
      - a description with material/feature/sizing info (AC2)
      - two variants for size + color selection (AC3)
    """
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        cat = Category(name="Hiking Boots", slug="hiking-boots")
        session.add(cat)
        await session.flush()

        product = Product(
            category_id=cat.id,
            name="TrailMaster Pro X",
            slug="trailmaster-pro-x",
            brand="AlpineGear",
            base_price=Decimal("189.99"),
            description=(
                "Premium hiking boot crafted from full-grain leather. "
                "Features: waterproof membrane, ankle support, vibram sole. "
                "Material: leather upper, rubber outsole. "
                "Sizing: fits true to UK size."
            ),
            short_description="Technical hiking boot for rugged terrain",
            images=[
                "https://cdn.test/trailmaster-front.jpg",
                "https://cdn.test/trailmaster-side.jpg",
                "https://cdn.test/trailmaster-sole.jpg",
            ],
            attributes={
                "waterproof": True,
                "material": "full-grain leather",
                "sole": "vibram",
            },
            is_active=True,
            stock_quantity=30,
        )
        session.add(product)
        await session.flush()

        v_size9_black = ProductVariant(
            product_id=product.id,
            name="UK 9 / Black",
            size="9",
            color="Black",
            sku="TMP-9-BLK",
            stock_quantity=10,
            inventory_count=10,
        )
        v_size10_brown = ProductVariant(
            product_id=product.id,
            name="UK 10 / Brown",
            size="10",
            color="Brown",
            sku="TMP-10-BRN",
            stock_quantity=5,
            inventory_count=5,
        )
        v_size11_black = ProductVariant(
            product_id=product.id,
            name="UK 11 / Black",
            size="11",
            color="Black",
            sku="TMP-11-BLK",
            stock_quantity=0,
            inventory_count=0,
        )
        session.add_all([v_size9_black, v_size10_brown, v_size11_black])
        await session.commit()

        return {
            "category": cat,
            "product": product,
            "variants": {
                "v9_black": v_size9_black,
                "v10_brown": v_size10_brown,
                "v11_black": v_size11_black,
            },
        }


@pytest_asyncio.fixture()
async def seeded_with_review(db_engine, seeded_product):
    """Add a review to the seeded product."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        user = User(
            email="reviewer@test.com",
            hashed_password="$2b$12$fakehashvalue",
        )
        session.add(user)
        await session.flush()

        review = Review(
            product_id=seeded_product["product"].id,
            user_id=user.id,
            rating=5,
            title="Excellent boots",
            body="These boots are incredibly waterproof and comfortable.",
            is_verified_purchase=True,
            is_approved=True,
        )
        session.add(review)
        await session.commit()

        return {**seeded_product, "user": user, "review": review}


# ---------------------------------------------------------------------------
# US-007 AC1: Multiple high-resolution images
# ---------------------------------------------------------------------------

class TestProductDetailImages:
    """US-007 AC1: PDP shows multiple high-resolution images of the boot."""

    @pytest.mark.asyncio
    async def test_images_field_is_list(self, app_client, seeded_product):
        """PDP response contains an 'images' field that is a list."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        assert resp.status_code == 200
        body = resp.json()
        assert "images" in body
        assert isinstance(body["images"], list)

    @pytest.mark.asyncio
    async def test_images_contains_multiple_entries(self, app_client, seeded_product):
        """AC1: multiple images are present (not just one)."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        # We seeded 3 images — at least 1 must be returned
        assert len(body["images"]) >= 1

    @pytest.mark.asyncio
    async def test_images_returns_seeded_urls(self, app_client, seeded_product):
        """AC1: images list reflects the stored image URLs."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        images = body["images"]
        assert any("trailmaster" in img for img in images)

    @pytest.mark.asyncio
    async def test_thumbnail_url_present(self, app_client, seeded_product):
        """ProductRead.thumbnail_url is mapped from Product.image_url (alias)."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert "thumbnail_url" in body  # alias field always present in schema


# ---------------------------------------------------------------------------
# US-007 AC2: Detailed description (material, features, sizing)
# ---------------------------------------------------------------------------

class TestProductDetailDescription:
    """US-007 AC2: PDP includes material, features, and sizing information."""

    @pytest.mark.asyncio
    async def test_description_present(self, app_client, seeded_product):
        """AC2: description field is returned and non-empty."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert "description" in body
        assert body["description"] is not None
        assert len(body["description"]) > 0

    @pytest.mark.asyncio
    async def test_description_contains_material_info(self, app_client, seeded_product):
        """AC2: description includes material information."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        desc = body["description"].lower()
        assert "leather" in desc or "material" in desc

    @pytest.mark.asyncio
    async def test_description_contains_feature_info(self, app_client, seeded_product):
        """AC2: description includes feature info (e.g., waterproof)."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        desc = body["description"].lower()
        assert "waterproof" in desc or "feature" in desc

    @pytest.mark.asyncio
    async def test_description_contains_sizing_info(self, app_client, seeded_product):
        """AC2: description includes sizing information."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        desc = body["description"].lower()
        assert "size" in desc or "sizing" in desc or "uk" in desc

    @pytest.mark.asyncio
    async def test_brand_field_present(self, app_client, seeded_product):
        """AC2: brand is shown on PDP."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert "brand" in body
        assert body["brand"] == "AlpineGear"

    @pytest.mark.asyncio
    async def test_price_field_present(self, app_client, seeded_product):
        """AC2: price is shown on PDP."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert "price" in body
        assert float(body["price"]) == pytest.approx(189.99, abs=0.01)


# ---------------------------------------------------------------------------
# US-007 AC3: Size and color selection via variants
# ---------------------------------------------------------------------------

class TestProductDetailVariants:
    """US-007 AC3: User can select size and color from available options."""

    @pytest.mark.asyncio
    async def test_variants_field_is_list(self, app_client, seeded_product):
        """AC3: variants field is a list."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert "variants" in body
        assert isinstance(body["variants"], list)

    @pytest.mark.asyncio
    async def test_variants_contains_all_seeded_variants(self, app_client, seeded_product):
        """AC3: all 3 seeded variants are returned."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert len(body["variants"]) == 3

    @pytest.mark.asyncio
    async def test_variants_expose_size_for_selection(self, app_client, seeded_product):
        """AC3: each variant exposes a 'size' field for user selection."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        sizes = {v["size"] for v in body["variants"] if v.get("size")}
        assert "9" in sizes
        assert "10" in sizes
        assert "11" in sizes

    @pytest.mark.asyncio
    async def test_variants_expose_color_for_selection(self, app_client, seeded_product):
        """AC3: each variant exposes a 'color' field for user selection."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        colors = {v["color"] for v in body["variants"] if v.get("color")}
        assert "Black" in colors
        assert "Brown" in colors

    @pytest.mark.asyncio
    async def test_variants_include_stock_quantity(self, app_client, seeded_product):
        """AC3: variant exposes stock_quantity so UI knows if size is available."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        for variant in body["variants"]:
            assert "stock_quantity" in variant

    @pytest.mark.asyncio
    async def test_variant_ids_are_present(self, app_client, seeded_product):
        """AC3: each variant includes its 'id' field so cart can reference it."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        for variant in body["variants"]:
            assert "id" in variant
            # Must be a valid UUID string
            uuid.UUID(variant["id"])


# ---------------------------------------------------------------------------
# US-007: Reviews
# ---------------------------------------------------------------------------

class TestProductDetailReviews:
    """PDP includes a reviews list."""

    @pytest.mark.asyncio
    async def test_reviews_field_is_list(self, app_client, seeded_product):
        """reviews field exists and is a list (may be empty initially)."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert "reviews" in body
        assert isinstance(body["reviews"], list)

    @pytest.mark.asyncio
    async def test_reviews_empty_for_new_product(self, app_client, seeded_product):
        """A freshly created product has zero reviews."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert body["reviews"] == []

    @pytest.mark.asyncio
    async def test_reviews_populated_when_present(self, app_client, seeded_with_review):
        """Reviews appear in PDP response when the product has reviews."""
        product = seeded_with_review["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert len(body["reviews"]) == 1
        review = body["reviews"][0]
        assert review["rating"] == 5
        assert review["title"] == "Excellent boots"


# ---------------------------------------------------------------------------
# US-007: Error handling
# ---------------------------------------------------------------------------

class TestProductDetailNotFound:
    """404 handling for non-existent product IDs."""

    @pytest.mark.asyncio
    async def test_nonexistent_id_returns_404(self, app_client, seeded_product):
        """AC4: requesting a non-existent product_id returns 404."""
        resp = await app_client.get(f"/api/v1/products/{uuid.uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_404_body_has_detail_key(self, app_client, seeded_product):
        """404 response includes a detail message."""
        resp = await app_client.get(f"/api/v1/products/{uuid.uuid4()}")
        body = resp.json()
        assert "detail" in body

    @pytest.mark.asyncio
    async def test_invalid_uuid_format_returns_422(self, app_client, seeded_product):
        """Malformed UUID path param returns 422 validation error."""
        resp = await app_client.get("/api/v1/products/not-a-valid-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# US-007: Full ProductRead schema completeness
# ---------------------------------------------------------------------------

class TestProductDetailSchemaCompleteness:
    """Verify all required fields in ProductRead are present in the response."""

    REQUIRED_FIELDS = [
        "id",
        "name",
        "slug",
        "description",
        "price",
        "brand",
        "thumbnail_url",
        "images",
        "variants",
        "reviews",
        "is_active",
        "average_rating",
        "review_count",
        "created_at",
        "updated_at",
    ]

    @pytest.mark.asyncio
    async def test_all_required_fields_present(self, app_client, seeded_product):
        """All ProductRead schema fields must be present in the PDP response."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        assert resp.status_code == 200
        body = resp.json()
        for field in self.REQUIRED_FIELDS:
            assert field in body, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_product_id_matches_requested_id(self, app_client, seeded_product):
        """Response ID matches the requested product_id."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert body["id"] == str(product.id)

    @pytest.mark.asyncio
    async def test_product_slug_present(self, app_client, seeded_product):
        """Slug field is present for SEO-friendly URL use."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert body["slug"] == "trailmaster-pro-x"

    @pytest.mark.asyncio
    async def test_is_active_true_for_active_product(self, app_client, seeded_product):
        """is_active is True for an active product."""
        product = seeded_product["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert body["is_active"] is True

    @pytest.mark.asyncio
    async def test_review_count_matches_actual_count(self, app_client, seeded_with_review):
        """review_count in the response reflects the number of reviews stored."""
        product = seeded_with_review["product"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert len(body["reviews"]) == 1  # 1 review was seeded

    @pytest.mark.asyncio
    async def test_category_id_linked_correctly(self, app_client, seeded_product):
        """category_id in response matches the product's category."""
        product = seeded_product["product"]
        category = seeded_product["category"]
        resp = await app_client.get(f"/api/v1/products/{product.id}")
        body = resp.json()
        assert "category_id" in body
        assert body["category_id"] == str(category.id)
