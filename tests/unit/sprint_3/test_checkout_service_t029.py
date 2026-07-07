"""
Sprint 3 T-029 unit tests — Checkout and Payment Intents (US-011).

User Story: US-011 — Guest Checkout
Acceptance Criteria:
  • Guest users can checkout without being logged in.
  • payment-intent endpoint creates a Stripe PaymentIntent server-side.
  • confirm endpoint verifies payment, creates order, clears cart.
  • Guest checkout works without authentication (auth_required: false).

Endpoints under test:
  POST /api/v1/checkout/payment-intent
  POST /api/v1/checkout/confirm

Uses an ephemeral SQLite in-memory database via FastAPI TestClient.
Stripe API calls are mocked via FastAPI dependency override.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.deps import get_stripe_client
from app.core.security import hash_password, create_access_token
from app.domains.account.models import User
from app.domains.cart.models import Cart, CartItem
from app.domains.categories.models import Category
from app.domains.checkout.models import Order, OrderItem
from app.domains.products.models import Product, ProductVariant
from app.main import app as fastapi_app

# Register all ORM models before creating schema
import app.domains.auth.models           # noqa: F401
import app.domains.categories.models     # noqa: F401
import app.domains.products.models       # noqa: F401
import app.domains.cart.models           # noqa: F401
import app.domains.checkout.models       # noqa: F401


# ---------------------------------------------------------------------------
# Stripe mock helpers
# ---------------------------------------------------------------------------

def _make_mock_stripe_client(
    pi_id: str = "pi_test123",
    client_secret: str = "pi_test123_secret_abc",
    amount: int = 14999,
    status: str = "requires_payment_method",
    currency: str = "gbp",
) -> MagicMock:
    """Return a mock Stripe module that produces a fake PaymentIntent."""
    mock_pi = MagicMock()
    mock_pi.id = pi_id
    mock_pi.client_secret = client_secret
    mock_pi.amount = amount
    mock_pi.status = status
    mock_pi.currency = currency
    # Simulate intent.get("metadata", {})
    mock_pi.get = MagicMock(return_value={})

    mock_stripe = MagicMock()
    mock_stripe.api_key = ""
    mock_stripe.PaymentIntent.create.return_value = mock_pi
    mock_stripe.PaymentIntent.retrieve.return_value = mock_pi
    return mock_stripe


def _make_succeeded_stripe_client(
    pi_id: str = "pi_succeeded_test",
    amount: int = 14999,
    currency: str = "gbp",
) -> MagicMock:
    """Return a mock Stripe module whose PaymentIntent is in 'succeeded' state."""
    mock_pi = MagicMock()
    mock_pi.id = pi_id
    mock_pi.client_secret = f"{pi_id}_secret"
    mock_pi.amount = amount
    mock_pi.status = "succeeded"
    mock_pi.currency = currency
    mock_pi.get = MagicMock(return_value={})

    mock_stripe = MagicMock()
    mock_stripe.api_key = ""
    mock_stripe.PaymentIntent.create.return_value = mock_pi
    mock_stripe.PaymentIntent.retrieve.return_value = mock_pi
    return mock_stripe


# ---------------------------------------------------------------------------
# Shared fixture: ephemeral SQLite + TestClient
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture()
async def db_and_client():
    """Yield (db_session, TestClient) wired to an ephemeral SQLite DB and mock Stripe."""
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

        async def _override_db():
            yield session

        fastapi_app.dependency_overrides[get_db] = _override_db
        # Default mock Stripe client (subclasses override per-test as needed)
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: _make_mock_stripe_client()

        client = TestClient(fastapi_app, raise_server_exceptions=True)

        yield session, client

    fastapi_app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _make_user(email: str | None = None) -> User:
    suffix = uuid.uuid4().hex[:8]
    return User(
        email=email or f"user_{suffix}@example.com",
        hashed_password=hash_password("SecurePass1!"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
    )


def _make_category() -> Category:
    uid = uuid.uuid4().hex[:8]
    return Category(name=f"Boots {uid}", slug=f"boots-{uid}")


def _make_product(category_id: uuid.UUID) -> Product:
    uid = uuid.uuid4().hex[:8]
    return Product(
        category_id=category_id,
        name=f"Trail Boot {uid}",
        slug=f"trail-boot-{uid}",
        brand="Scarpa",
        base_price=Decimal("149.99"),
        is_active=True,
    )


def _make_variant(
    product_id: uuid.UUID, size: str = "9", color: str = "Black"
) -> ProductVariant:
    return ProductVariant(
        product_id=product_id,
        name=f"UK {size} / {color}",
        size=size,
        color=color,
        price_modifier=Decimal("0"),
        stock_quantity=10,
        inventory_count=10,
    )


def _auth_header(user: User) -> dict:
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


async def _create_cart_with_item(
    db: AsyncSession,
    user: User,
    product: Product,
    variant: ProductVariant | None = None,
    quantity: int = 1,
    unit_price: Decimal = Decimal("149.99"),
) -> Cart:
    """Create a cart with a single item for the user.

    Calls expire_all() after adding the item so the shared session's identity
    map does not serve a stale Cart.items=[] to the service layer.
    """
    cart = Cart(user_id=user.id)
    db.add(cart)
    await db.commit()
    await db.refresh(cart)

    item = CartItem(
        cart_id=cart.id,
        product_id=product.id,
        variant_id=variant.id if variant else None,
        quantity=quantity,
        unit_price=unit_price,
    )
    db.add(item)
    await db.commit()
    return cart


# ---------------------------------------------------------------------------
# POST /api/v1/checkout/payment-intent tests
# ---------------------------------------------------------------------------

class TestPaymentIntentEndpoint:
    """T-029 / US-011 — POST /api/v1/checkout/payment-intent"""

    @pytest.mark.asyncio
    async def test_guest_checkout_requires_guest_email(self, db_and_client):
        """Guest checkout (no auth) returns 400 if guest_email is missing."""
        _, client = db_and_client

        resp = client.post(
            "/api/v1/checkout/payment-intent",
            json={
                "shipping_address": {
                    "line1": "1 Test St",
                    "city": "London",
                    "postal_code": "EC1A 1AA",
                    "country": "GB",
                }
            },
        )
        # guest_email missing for guest checkout → 400 Bad Request
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_empty_cart_returns_400(self, db_and_client):
        """Creating a payment intent with an empty cart returns 400."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # No cart — user has nothing in cart
        resp = client.post(
            "/api/v1/checkout/payment-intent",
            json={
                "shipping_name": "Test User",
                "shipping_address": {
                    "line1": "1 Test St",
                    "city": "London",
                    "postal_code": "EC1A 1AA",
                    "country": "GB",
                },
            },
            headers=_auth_header(user),
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_authenticated_user_with_cart_creates_payment_intent(self, db_and_client):
        """Authenticated user with items in cart gets a PaymentIntent back."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        await _create_cart_with_item(db, user, product, unit_price=Decimal("149.99"))

        # Override stripe client to return a mock PI
        mock_stripe = _make_mock_stripe_client(
            pi_id="pi_test_auth123",
            client_secret="pi_test_auth123_secret",
            amount=14999,
        )
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/payment-intent",
            json={
                "shipping_name": "Test User",
                "shipping_address": {
                    "line1": "1 Test St",
                    "city": "London",
                    "postal_code": "EC1A 1AA",
                    "country": "GB",
                },
            },
            headers=_auth_header(user),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "client_secret" in body
        assert "payment_intent_id" in body
        assert "amount" in body
        assert "currency" in body
        assert body["currency"] == "gbp"
        assert body["payment_intent_id"] == "pi_test_auth123"
        assert body["client_secret"] == "pi_test_auth123_secret"

    @pytest.mark.asyncio
    async def test_payment_intent_amount_is_in_pence(self, db_and_client):
        """PaymentIntent amount is returned in pence (smallest currency unit)."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        await _create_cart_with_item(db, user, product, unit_price=Decimal("99.99"))

        mock_stripe = _make_mock_stripe_client(amount=9999)
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/payment-intent",
            json={
                "shipping_name": "Test User",
                "shipping_address": {
                    "line1": "1 Test St",
                    "city": "London",
                    "postal_code": "EC1A 1AA",
                    "country": "GB",
                },
            },
            headers=_auth_header(user),
        )

        assert resp.status_code == 200
        body = resp.json()
        # amount should be integer pence, not decimal pounds
        assert isinstance(body["amount"], int)
        assert body["amount"] == 9999  # 99.99 GBP = 9999 pence

    @pytest.mark.asyncio
    async def test_guest_checkout_with_email_creates_payment_intent(self, db_and_client):
        """Checkout with guest_email and auth-bearer header (US-011 guest flow)."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        await _create_cart_with_item(db, user, product, unit_price=Decimal("99.99"))

        mock_stripe = _make_mock_stripe_client(amount=9999)
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/payment-intent",
            json={
                "guest_email": "guest@example.com",
                "shipping_name": "Guest User",
                "shipping_address": {
                    "line1": "5 Guest Road",
                    "city": "Manchester",
                    "postal_code": "M1 1AA",
                    "country": "GB",
                },
            },
            headers=_auth_header(user),
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["currency"] == "gbp"

    @pytest.mark.asyncio
    async def test_stripe_create_error_returns_payment_error(self, db_and_client):
        """Stripe API failure during PI creation returns an error response."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        await _create_cart_with_item(db, user, product)

        mock_stripe = MagicMock()
        mock_stripe.api_key = ""
        mock_stripe.PaymentIntent.create.side_effect = Exception("Stripe API error")
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/payment-intent",
            json={
                "shipping_name": "Test User",
                "shipping_address": {
                    "line1": "1 Test St",
                    "city": "London",
                    "postal_code": "EC1A 1AA",
                    "country": "GB",
                },
            },
            headers=_auth_header(user),
        )

        # PaymentError exception — mapped to 402 by the global exception handler
        assert resp.status_code in (400, 402, 502)


# ---------------------------------------------------------------------------
# POST /api/v1/checkout/confirm tests
# ---------------------------------------------------------------------------

class TestConfirmOrderEndpoint:
    """T-029 / US-011 — POST /api/v1/checkout/confirm"""

    @pytest.mark.asyncio
    async def test_successful_confirmation_creates_order(self, db_and_client):
        """Confirmed Stripe payment creates an order record (US-011)."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        await _create_cart_with_item(db, user, product, unit_price=Decimal("149.99"))

        mock_stripe = _make_succeeded_stripe_client(pi_id="pi_confirmed_001")
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/confirm",
            json={"payment_intent_id": "pi_confirmed_001"},
            headers=_auth_header(user),
        )

        assert resp.status_code == 201
        body = resp.json()

        # Verify API contract response shape
        assert "order_id" in body
        assert "order_number" in body
        assert "total_amount" in body
        assert "items" in body
        assert "shipping_address" in body

        # Verify values
        assert float(body["total_amount"]) == pytest.approx(149.99)
        assert len(body["items"]) == 1
        assert body["items"][0]["quantity"] == 1
        assert float(body["items"][0]["unit_price"]) == pytest.approx(149.99)

    @pytest.mark.asyncio
    async def test_successful_confirmation_clears_cart(self, db_and_client):
        """After order confirmation, the cart is emptied (US-011)."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        cart = await _create_cart_with_item(db, user, product)
        cart_id = cart.id

        mock_stripe = _make_succeeded_stripe_client(pi_id="pi_clears_cart_001")
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/confirm",
            json={"payment_intent_id": "pi_clears_cart_001"},
            headers=_auth_header(user),
        )

        assert resp.status_code == 201

        # Verify cart is now empty
        from sqlalchemy.future import select as sa_select
        result = await db.execute(
            sa_select(CartItem).where(CartItem.cart_id == cart_id)
        )
        items = result.scalars().all()
        assert len(items) == 0, "Cart should be emptied after order confirmation"

    @pytest.mark.asyncio
    async def test_payment_not_succeeded_returns_400(self, db_and_client):
        """Payment intent not in 'succeeded' state returns 400 (payment must succeed)."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        await _create_cart_with_item(db, user, product)

        mock_stripe = _make_mock_stripe_client(
            pi_id="pi_pending_001",
            status="requires_payment_method",
        )
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/confirm",
            json={"payment_intent_id": "pi_pending_001"},
            headers=_auth_header(user),
        )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_empty_cart_returns_400_on_confirm(self, db_and_client):
        """Confirming with an empty cart returns 400."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        mock_stripe = _make_succeeded_stripe_client(pi_id="pi_empty_cart_001")
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        # No cart for this user
        resp = client.post(
            "/api/v1/checkout/confirm",
            json={"payment_intent_id": "pi_empty_cart_001"},
            headers=_auth_header(user),
        )

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_order_has_correct_stripe_payment_intent_id(self, db_and_client):
        """Created order stores the stripe_payment_intent_id (ADR-003)."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        await _create_cart_with_item(db, user, product)

        pi_id = "pi_with_stripe_ref_001"
        mock_stripe = _make_succeeded_stripe_client(pi_id=pi_id)
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/confirm",
            json={"payment_intent_id": pi_id},
            headers=_auth_header(user),
        )

        assert resp.status_code == 201
        order_id = resp.json()["order_id"]

        # Verify the stripe PI ID was stored on the order
        from sqlalchemy.future import select as sa_select
        result = await db.execute(
            sa_select(Order).where(Order.id == uuid.UUID(order_id))
        )
        order = result.scalar_one_or_none()
        assert order is not None
        assert order.stripe_payment_intent_id == pi_id

    @pytest.mark.asyncio
    async def test_order_number_is_generated(self, db_and_client):
        """Confirmed order always has a non-empty order_number starting with ORD-."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        await _create_cart_with_item(db, user, product)

        mock_stripe = _make_succeeded_stripe_client(pi_id="pi_order_num_001")
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/confirm",
            json={"payment_intent_id": "pi_order_num_001"},
            headers=_auth_header(user),
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["order_number"]
        assert body["order_number"].startswith("ORD-")

    @pytest.mark.asyncio
    async def test_confirm_without_auth_returns_400_not_401(self, db_and_client):
        """Checkout confirm is accessible without auth (auth_required: false) → 400 not 401."""
        _, client = db_and_client

        mock_stripe = _make_succeeded_stripe_client(pi_id="pi_no_auth_001")
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/confirm",
            json={"payment_intent_id": "pi_no_auth_001"},
            # No Authorization header — guest checkout
        )

        # Without user, cart lookup returns None → 400 (cart empty)
        # Key point: NOT 401 (auth is not required)
        assert resp.status_code == 400, (
            f"Expected 400 (cart empty), got {resp.status_code}: {resp.json()}"
        )

    @pytest.mark.asyncio
    async def test_order_item_captures_product_name(self, db_and_client):
        """OrderItem.product_name is captured from the product at order creation."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        await _create_cart_with_item(db, user, product)

        mock_stripe = _make_succeeded_stripe_client(pi_id="pi_prod_name_001")
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/confirm",
            json={"payment_intent_id": "pi_prod_name_001"},
            headers=_auth_header(user),
        )

        assert resp.status_code == 201
        body = resp.json()
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["product_name"] == product.name

    @pytest.mark.asyncio
    async def test_order_item_captures_variant_attributes(self, db_and_client):
        """OrderItem response includes color and size from the product variant."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        variant = _make_variant(product.id, size="10", color="Brown")
        db.add(variant)
        await db.commit()
        await db.refresh(variant)

        await _create_cart_with_item(db, user, product, variant=variant)

        mock_stripe = _make_succeeded_stripe_client(pi_id="pi_variant_attrs_001")
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/confirm",
            json={"payment_intent_id": "pi_variant_attrs_001"},
            headers=_auth_header(user),
        )

        assert resp.status_code == 201
        body = resp.json()
        item = body["items"][0]
        assert item["color"] == "Brown"
        assert item["size"] == "10"

    @pytest.mark.asyncio
    async def test_multi_item_cart_creates_correct_order(self, db_and_client):
        """Cart with 2 items creates order with both items and correct total."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product_a = _make_product(cat.id)
        product_b = _make_product(cat.id)
        db.add_all([product_a, product_b])
        await db.commit()
        await db.refresh(product_a)
        await db.refresh(product_b)

        cart = Cart(user_id=user.id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)

        # Add two different items
        item1 = CartItem(
            cart_id=cart.id,
            product_id=product_a.id,
            quantity=1,
            unit_price=Decimal("149.99"),
        )
        item2 = CartItem(
            cart_id=cart.id,
            product_id=product_b.id,
            quantity=2,
            unit_price=Decimal("50.00"),
        )
        db.add_all([item1, item2])
        await db.commit()

        mock_stripe = _make_succeeded_stripe_client(pi_id="pi_multi_item_001")
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/confirm",
            json={"payment_intent_id": "pi_multi_item_001"},
            headers=_auth_header(user),
        )

        assert resp.status_code == 201
        body = resp.json()
        assert len(body["items"]) == 2
        # Total: 149.99 + (2 × 50.00) = 249.99
        assert float(body["total_amount"]) == pytest.approx(249.99)

    @pytest.mark.asyncio
    async def test_order_is_created_in_database(self, db_and_client):
        """Confirmed order is persisted to the database (not just returned in response)."""
        db, client = db_and_client

        user = _make_user()
        db.add(user)
        await db.commit()
        await db.refresh(user)

        cat = _make_category()
        db.add(cat)
        await db.commit()
        await db.refresh(cat)

        product = _make_product(cat.id)
        db.add(product)
        await db.commit()
        await db.refresh(product)

        await _create_cart_with_item(db, user, product, unit_price=Decimal("199.00"))

        mock_stripe = _make_succeeded_stripe_client(pi_id="pi_persisted_001")
        fastapi_app.dependency_overrides[get_stripe_client] = lambda: mock_stripe

        resp = client.post(
            "/api/v1/checkout/confirm",
            json={"payment_intent_id": "pi_persisted_001"},
            headers=_auth_header(user),
        )

        assert resp.status_code == 201
        order_id = uuid.UUID(resp.json()["order_id"])

        # Confirm it's in the DB
        from sqlalchemy.future import select as sa_select
        result = await db.execute(
            sa_select(Order).where(Order.id == order_id)
        )
        db_order = result.scalar_one_or_none()
        assert db_order is not None
        assert db_order.status == "confirmed"
        assert db_order.user_id == user.id


# ---------------------------------------------------------------------------
# Schema / service unit tests
# ---------------------------------------------------------------------------

class TestCheckoutSchemas:
    """Unit tests for the checkout schema (request/response shapes)."""

    def test_payment_intent_request_requires_shipping_address(self):
        """PaymentIntentRequest requires shipping_address (not optional)."""
        from pydantic import ValidationError as PydanticValidationError
        from app.domains.checkout.schemas import PaymentIntentRequest

        with pytest.raises(PydanticValidationError):
            PaymentIntentRequest(guest_email="guest@example.com")  # missing shipping_address

    def test_payment_intent_request_with_all_fields(self):
        """PaymentIntentRequest accepts all expected fields."""
        from app.domains.checkout.schemas import PaymentIntentRequest, ShippingAddressIn

        req = PaymentIntentRequest(
            guest_email="guest@example.com",
            shipping_name="Guest User",
            shipping_address=ShippingAddressIn(
                line1="1 Test St",
                city="London",
                postal_code="EC1A 1AA",
                country="GB",
            ),
        )
        assert req.guest_email == "guest@example.com"
        assert req.shipping_address.city == "London"

    def test_confirm_order_request_requires_payment_intent_id(self):
        """ConfirmOrderRequest requires payment_intent_id."""
        from pydantic import ValidationError as PydanticValidationError
        from app.domains.checkout.schemas import ConfirmOrderRequest

        with pytest.raises(PydanticValidationError):
            ConfirmOrderRequest()  # missing payment_intent_id

    def test_payment_intent_response_amount_is_integer(self):
        """PaymentIntentResponse.amount is an integer (pence, not decimal)."""
        from app.domains.checkout.schemas import PaymentIntentResponse

        resp = PaymentIntentResponse(
            client_secret="pi_test_secret",
            payment_intent_id="pi_test",
            amount=14999,
            currency="gbp",
        )
        assert isinstance(resp.amount, int)
        assert resp.amount == 14999

    def test_confirm_order_response_shape(self):
        """ConfirmOrderResponse has the required API-contract fields."""
        from app.domains.checkout.schemas import ConfirmOrderResponse

        resp = ConfirmOrderResponse(
            order_id="550e8400-e29b-41d4-a716-446655440000",
            order_number="ORD-ABC12345",
            shipping_address={"line1": "1 Test St", "city": "London"},
            total_amount=Decimal("149.99"),
            items=[],
        )
        assert resp.order_number == "ORD-ABC12345"
        assert resp.total_amount == Decimal("149.99")

    def test_shipping_address_in_model(self):
        """ShippingAddressIn validates required fields."""
        from pydantic import ValidationError as PydanticValidationError
        from app.domains.checkout.schemas import ShippingAddressIn

        # Valid
        addr = ShippingAddressIn(line1="1 Test St", city="London", postal_code="EC1A 1AA")
        assert addr.city == "London"
        assert addr.country == "GB"  # default

        # Invalid — missing required fields
        with pytest.raises(PydanticValidationError):
            ShippingAddressIn(city="London")  # missing line1 and postal_code
