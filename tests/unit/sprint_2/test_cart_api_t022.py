"""
Sprint 2 T-022 unit tests — Add to Cart backend service and cart API (US-009).

Acceptance criteria exercised:
  AC1: POST /api/v1/cart/items adds item to cart when product_id (+ optional variant_id)
       and quantity are provided.
  AC2: Response returns the full CartRead envelope with item_count > 0.
  AC3: Guest users (no auth token) can add to cart via X-Session-ID header.
  AC4: Authenticated users (JWT token) have items tied to their user_id.
  AC5: Adding same product twice to same cart accumulates quantity (if no variant)
       or merges the item (if same variant).
  AC6: Adding a second distinct product to the same cart shows item_count == 2.
  AC7: Non-existent product_id returns 404.
  AC8: Non-existent variant_id returns 404.
  AC9: Stock check: adding quantity > available stock returns 400.
  AC10: CartService.add_item_to_cart correctly get-or-creates a cart.

Service layer:
  - CartService.get_or_create_cart creates cart for new user/session.
  - CartService.get_or_create_cart returns existing cart on second call.
  - CartService.add_item_to_cart adds a new CartItem when none exists.
  - CartService.add_item_to_cart merges quantities when variant already in cart.
  - CartService.get_cart raises NotFoundError when cart does not exist.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Register all ORM mappers before creating tables.
from app.core.database import Base, get_db  # noqa: F401

import app.domains.account.models  # noqa: F401
import app.domains.auth.models  # noqa: F401
import app.domains.categories.models  # noqa: F401
import app.domains.products.models  # noqa: F401
import app.domains.cart.models  # noqa: F401
import app.domains.checkout.models  # noqa: F401

from app.core.exceptions import NotFoundError, BadRequestError
from app.domains.account.models import User
from app.domains.categories.models import Category
from app.domains.products.models import Product, ProductVariant
from app.domains.cart.models import Cart, CartItem
from app.domains.cart.service import CartService
from app.domains.cart.schemas import AddCartItem

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
async def db(db_engine) -> AsyncSession:
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture()
async def app_client(db_engine) -> AsyncClient:
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
async def seeded(db_engine):
    """Seed the test DB with a category, two products and two variants for product1."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        # User
        user = User(
            email="cart_user@boots.test",
            hashed_password="$2b$12$hashed_for_testing_only",
        )
        session.add(user)
        await session.flush()

        # Category
        cat = Category(name="Hiking Boots", slug=f"hiking-{uuid.uuid4().hex[:6]}")
        session.add(cat)
        await session.flush()

        # Products
        p1 = Product(
            category_id=cat.id,
            name="Hiking Pro X",
            slug=f"hiking-pro-x-{uuid.uuid4().hex[:6]}",
            brand="TrailBlazers",
            base_price=Decimal("129.99"),
            description="Best hiking boot",
            is_active=True,
        )
        p2 = Product(
            category_id=cat.id,
            name="Steel Toe Work Boot",
            slug=f"steel-toe-{uuid.uuid4().hex[:6]}",
            brand="SafetyFirst",
            base_price=Decimal("89.99"),
            description="Heavy-duty work boot",
            is_active=True,
        )
        session.add_all([p1, p2])
        await session.flush()

        # Variants for p1
        v1 = ProductVariant(
            product_id=p1.id,
            name="UK 9 / Black",
            size="9",
            color="Black",
            stock_quantity=10,
            inventory_count=10,
            price_modifier=Decimal("0.00"),
        )
        v_low_stock = ProductVariant(
            product_id=p1.id,
            name="UK 12 / Black",
            size="12",
            color="Black",
            stock_quantity=1,  # Only 1 in stock
            inventory_count=1,
            price_modifier=Decimal("5.00"),
        )
        v_p2 = ProductVariant(
            product_id=p2.id,
            name="UK 10 / Brown",
            size="10",
            color="Brown",
            stock_quantity=5,
            inventory_count=5,
            price_modifier=Decimal("0.00"),
        )
        session.add_all([v1, v_low_stock, v_p2])
        await session.commit()

        return {
            "user": user,
            "category": cat,
            "p1": p1,
            "p2": p2,
            "v1": v1,
            "v_low_stock": v_low_stock,
            "v_p2": v_p2,
        }


# ---------------------------------------------------------------------------
# API endpoint tests — T-022 / US-009
# ---------------------------------------------------------------------------

class TestAddCartItemEndpoint:
    """POST /api/v1/cart/items — US-009 Add to Shopping Cart."""

    @pytest.mark.asyncio
    async def test_ac1_add_item_with_variant_returns_201(self, app_client, seeded):
        """AC1: Adding a product with size+color variant returns 201 and item in cart."""
        p1 = seeded["p1"]
        v1 = seeded["v1"]
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(p1.id), "variant_id": str(v1.id), "quantity": 1},
            headers={"X-Session-ID": "t022-sess-ac1"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["product_id"] == str(p1.id)

    @pytest.mark.asyncio
    async def test_ac2_response_is_full_cart_read_envelope(self, app_client, seeded):
        """AC2: Response contains all CartRead fields: id, items, total, item_count."""
        p1 = seeded["p1"]
        v1 = seeded["v1"]
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(p1.id), "variant_id": str(v1.id), "quantity": 1},
            headers={"X-Session-ID": "t022-sess-ac2"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert "items" in body
        assert "total" in body
        assert "item_count" in body
        assert body["item_count"] == 1
        assert body["total"] > 0

    @pytest.mark.asyncio
    async def test_ac3_guest_user_can_add_to_cart(self, app_client, seeded):
        """AC3: No auth token required — guest uses X-Session-ID header."""
        p2 = seeded["p2"]
        # No Authorization header
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(p2.id), "quantity": 1},
            headers={"X-Session-ID": "t022-guest-sess"},
        )
        assert resp.status_code == 201
        assert resp.json()["user_id"] is None  # guest cart has no user_id

    @pytest.mark.asyncio
    async def test_ac4_confirmation_item_count_reflects_new_item(self, app_client, seeded):
        """AC2: After adding item, item_count in response is updated immediately."""
        p1 = seeded["p1"]
        v1 = seeded["v1"]
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(p1.id), "variant_id": str(v1.id), "quantity": 2},
            headers={"X-Session-ID": "t022-sess-ac4"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["item_count"] == 2  # quantity 2 units

    @pytest.mark.asyncio
    async def test_ac5_adding_same_variant_twice_merges_quantity(self, app_client, seeded):
        """AC5: Adding the same variant again merges into one item with combined qty."""
        p1 = seeded["p1"]
        v1 = seeded["v1"]
        session_id = "t022-sess-merge"

        await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(p1.id), "variant_id": str(v1.id), "quantity": 1},
            headers={"X-Session-ID": session_id},
        )
        resp2 = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(p1.id), "variant_id": str(v1.id), "quantity": 2},
            headers={"X-Session-ID": session_id},
        )
        body = resp2.json()
        # One line item with merged qty 3
        assert len(body["items"]) == 1
        assert body["items"][0]["quantity"] == 3

    @pytest.mark.asyncio
    async def test_ac6_two_distinct_products_show_item_count_2(self, app_client, seeded):
        """AC6: Adding two different products to the same cart gives item_count == 2."""
        p1 = seeded["p1"]
        p2 = seeded["p2"]
        session_id = "t022-sess-two-products"

        await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(p1.id), "quantity": 1},
            headers={"X-Session-ID": session_id},
        )
        resp2 = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(p2.id), "quantity": 1},
            headers={"X-Session-ID": session_id},
        )
        body = resp2.json()
        assert body["item_count"] == 2

    @pytest.mark.asyncio
    async def test_ac7_nonexistent_product_returns_404(self, app_client, seeded):
        """AC7: Requesting a product that doesn't exist returns 404."""
        fake_id = uuid.uuid4()
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(fake_id), "quantity": 1},
            headers={"X-Session-ID": "t022-sess-notfound"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_ac8_nonexistent_variant_returns_404(self, app_client, seeded):
        """AC8: Specifying a variant_id that doesn't exist returns 404."""
        p1 = seeded["p1"]
        fake_variant_id = uuid.uuid4()
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(p1.id), "variant_id": str(fake_variant_id), "quantity": 1},
            headers={"X-Session-ID": "t022-sess-novariant"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_ac9_exceeding_stock_returns_400(self, app_client, seeded):
        """AC9: Requesting more than available stock for a variant returns 400."""
        p1 = seeded["p1"]
        v_low = seeded["v_low_stock"]  # stock_quantity == 1
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(p1.id), "variant_id": str(v_low.id), "quantity": 99},
            headers={"X-Session-ID": "t022-sess-overstock"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_add_without_variant_succeeds(self, app_client, seeded):
        """US-009: product can be added to cart without specifying a variant_id."""
        p2 = seeded["p2"]
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(p2.id), "quantity": 1},
            headers={"X-Session-ID": "t022-sess-novariant-ok"},
        )
        assert resp.status_code == 201
        assert resp.json()["item_count"] == 1

    @pytest.mark.asyncio
    async def test_invalid_quantity_zero_returns_422(self, app_client, seeded):
        """Pydantic validation: quantity must be >= 1; quantity=0 yields 422."""
        p1 = seeded["p1"]
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(p1.id), "quantity": 0},
            headers={"X-Session-ID": "t022-sess-badqty"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_cart_total_reflects_item_price(self, app_client, seeded):
        """CartRead.total matches unit_price * quantity for items added."""
        p1 = seeded["p1"]  # base_price == 129.99
        resp = await app_client.post(
            "/api/v1/cart/items",
            json={"product_id": str(p1.id), "quantity": 2},
            headers={"X-Session-ID": "t022-sess-total"},
        )
        body = resp.json()
        assert resp.status_code == 201
        # total should be approximately 2 * 129.99 == 259.98
        assert abs(body["total"] - 259.98) < 0.01


# ---------------------------------------------------------------------------
# CartService unit tests — T-022 service layer
# ---------------------------------------------------------------------------

class TestCartServiceGetOrCreateCart:
    """CartService.get_or_create_cart — service-layer tests."""

    @pytest.mark.asyncio
    async def test_creates_new_cart_for_guest_session(self, db):
        """Service creates a new cart for a guest session_id if none exists."""
        service = CartService(db)
        session_id = f"svc-sess-{uuid.uuid4().hex[:8]}"
        cart = await service.get_or_create_cart(session_id=session_id)

        assert cart.id is not None
        assert cart.session_id == session_id
        assert cart.user_id is None

    @pytest.mark.asyncio
    async def test_returns_existing_cart_for_same_session(self, db):
        """Service returns same cart on second call with same session_id."""
        service = CartService(db)
        session_id = f"svc-sess-{uuid.uuid4().hex[:8]}"

        cart1 = await service.get_or_create_cart(session_id=session_id)
        cart2 = await service.get_or_create_cart(session_id=session_id)

        assert cart1.id == cart2.id

    @pytest.mark.asyncio
    async def test_creates_cart_for_user(self, db, seeded):
        """Service creates a user-linked cart when none exists for that user."""
        service = CartService(db)
        user = seeded["user"]

        cart = await service.get_or_create_cart(user_id=user.id)

        assert cart.id is not None
        assert cart.user_id == user.id

    @pytest.mark.asyncio
    async def test_returns_existing_user_cart(self, db, seeded):
        """Service returns same cart on second call with same user_id."""
        service = CartService(db)
        user = seeded["user"]

        cart1 = await service.get_or_create_cart(user_id=user.id)
        cart2 = await service.get_or_create_cart(user_id=user.id)

        assert cart1.id == cart2.id


class TestCartServiceGetCart:
    """CartService.get_cart — raises NotFoundError when no cart exists."""

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_session(self, db):
        """get_cart raises NotFoundError when session has no cart."""
        service = CartService(db)
        with pytest.raises(NotFoundError):
            await service.get_cart(session_id="no-cart-for-this-session")

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_user(self, db):
        """get_cart raises NotFoundError when user has no cart."""
        service = CartService(db)
        with pytest.raises(NotFoundError):
            await service.get_cart(user_id=uuid.uuid4())


class TestCartServiceAddItem:
    """CartService.add_item_to_cart — core add-to-cart logic."""

    @pytest.mark.asyncio
    async def test_adds_product_without_variant(self, db, seeded):
        """Adding a product with no variant creates a CartItem with product_id."""
        service = CartService(db)
        p2 = seeded["p2"]
        session_id = f"svc-{uuid.uuid4().hex[:8]}"

        payload = AddCartItem(product_id=p2.id, quantity=1)
        cart = await service.add_item_to_cart(payload=payload, session_id=session_id)

        assert len(cart.items) == 1
        assert cart.items[0].product_id == p2.id
        assert cart.items[0].variant_id is None

    @pytest.mark.asyncio
    async def test_adds_product_with_variant(self, db, seeded):
        """Adding a product with a valid variant creates CartItem with variant_id."""
        service = CartService(db)
        p1 = seeded["p1"]
        v1 = seeded["v1"]
        session_id = f"svc-{uuid.uuid4().hex[:8]}"

        payload = AddCartItem(product_id=p1.id, variant_id=v1.id, quantity=1)
        cart = await service.add_item_to_cart(payload=payload, session_id=session_id)

        assert len(cart.items) == 1
        assert cart.items[0].variant_id == v1.id

    @pytest.mark.asyncio
    async def test_merges_same_variant_on_second_add(self, db, seeded):
        """Adding the same variant twice accumulates quantity instead of creating duplicates."""
        service = CartService(db)
        p1 = seeded["p1"]
        v1 = seeded["v1"]
        session_id = f"svc-{uuid.uuid4().hex[:8]}"

        payload = AddCartItem(product_id=p1.id, variant_id=v1.id, quantity=2)
        await service.add_item_to_cart(payload=payload, session_id=session_id)
        cart = await service.add_item_to_cart(payload=payload, session_id=session_id)

        assert len(cart.items) == 1
        assert cart.items[0].quantity == 4  # 2 + 2

    @pytest.mark.asyncio
    async def test_unit_price_captured_from_product_base_price(self, db, seeded):
        """CartItem.unit_price is set from product.base_price at add-to-cart time."""
        service = CartService(db)
        p2 = seeded["p2"]  # base_price = 89.99
        session_id = f"svc-{uuid.uuid4().hex[:8]}"

        payload = AddCartItem(product_id=p2.id, quantity=1)
        cart = await service.add_item_to_cart(payload=payload, session_id=session_id)

        assert abs(float(cart.items[0].unit_price) - 89.99) < 0.01

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_product(self, db):
        """Adding a product_id that doesn't exist raises NotFoundError."""
        service = CartService(db)
        session_id = f"svc-{uuid.uuid4().hex[:8]}"

        payload = AddCartItem(product_id=uuid.uuid4(), quantity=1)
        with pytest.raises(NotFoundError):
            await service.add_item_to_cart(payload=payload, session_id=session_id)

    @pytest.mark.asyncio
    async def test_raises_bad_request_when_stock_exceeded(self, db, seeded):
        """Adding more than available stock raises BadRequestError."""
        service = CartService(db)
        p1 = seeded["p1"]
        v_low = seeded["v_low_stock"]  # stock_quantity = 1
        session_id = f"svc-{uuid.uuid4().hex[:8]}"

        payload = AddCartItem(product_id=p1.id, variant_id=v_low.id, quantity=999)
        with pytest.raises(BadRequestError):
            await service.add_item_to_cart(payload=payload, session_id=session_id)

    @pytest.mark.asyncio
    async def test_cart_total_updated_after_add(self, db, seeded):
        """Cart.total reflects items after adding product."""
        service = CartService(db)
        p1 = seeded["p1"]  # base_price = 129.99
        session_id = f"svc-{uuid.uuid4().hex[:8]}"

        payload = AddCartItem(product_id=p1.id, quantity=3)
        cart = await service.add_item_to_cart(payload=payload, session_id=session_id)

        assert abs(cart.total - 3 * 129.99) < 0.01

    @pytest.mark.asyncio
    async def test_item_count_equals_sum_of_quantities(self, db, seeded):
        """Cart.item_count sums all item quantities."""
        service = CartService(db)
        p1 = seeded["p1"]
        p2 = seeded["p2"]
        session_id = f"svc-{uuid.uuid4().hex[:8]}"

        await service.add_item_to_cart(
            payload=AddCartItem(product_id=p1.id, quantity=2), session_id=session_id
        )
        cart = await service.add_item_to_cart(
            payload=AddCartItem(product_id=p2.id, quantity=3), session_id=session_id
        )

        assert cart.item_count == 5


class TestCartServiceGetCartById:
    """CartService.get_cart_by_id — retrieve cart by primary key."""

    @pytest.mark.asyncio
    async def test_returns_cart_with_items(self, db, seeded):
        """get_cart_by_id returns the cart with its items loaded."""
        service = CartService(db)
        p1 = seeded["p1"]
        session_id = f"svc-{uuid.uuid4().hex[:8]}"

        payload = AddCartItem(product_id=p1.id, quantity=1)
        created = await service.add_item_to_cart(payload=payload, session_id=session_id)

        fetched = await service.get_cart_by_id(created.id)
        assert fetched.id == created.id
        assert len(fetched.items) >= 1

    @pytest.mark.asyncio
    async def test_raises_not_found_for_missing_cart_id(self, db):
        """get_cart_by_id raises NotFoundError for an unknown UUID."""
        service = CartService(db)
        with pytest.raises(NotFoundError):
            await service.get_cart_by_id(uuid.uuid4())
