"""Faker-based factory classes for all ORM models.

Usage::

    from tests.fixtures.factories import UserFactory, ProductFactory

    user_data = UserFactory.build()
    product_data = ProductFactory.build(category_id='00000000-...')

Rules:
- ``build()`` returns a plain dict — no DB calls, no ORM imports.
- Import only stdlib + faker.
- Password-hash columns are OMITTED (set to None) — callers that need a
  valid hash must compute it at test-time via the workspace auth helper.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Dict

from faker import Faker

_fake = Faker("en_GB")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uuid() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return "2026-01-15 10:00:00"


# ---------------------------------------------------------------------------
# Reference / lookup factories
# ---------------------------------------------------------------------------

class CategoryFactory:
    """Factory for the ``categories`` table."""

    @staticmethod
    def build(**overrides: Any) -> Dict[str, Any]:
        word = _fake.unique.word()
        data: Dict[str, Any] = {
            "id": _uuid(),
            "name": word.title() + " Boots",
            "slug": word.lower() + "-boots",
            "description": _fake.sentence(nb_words=10),
            "image_url": f"https://cdn.example.com/cats/{word.lower()}.jpg",
            "is_active": True,
            "parent_id": None,
            "display_order": _fake.random_int(min=0, max=100),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        data.update(overrides)
        return data


# ---------------------------------------------------------------------------
# Transactional factories
# ---------------------------------------------------------------------------

class UserFactory:
    """Factory for the ``users`` table.

    ``hashed_password`` is omitted — compute it with the app's
    ``app.core.security.hash_password`` helper at test-time if needed.
    """

    @staticmethod
    def build(**overrides: Any) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": _uuid(),
            "email": _fake.unique.email(),
            "hashed_password": None,   # INTENTIONALLY OMITTED — see module docstring
            "full_name": _fake.name(),
            "is_active": True,
            "is_superuser": False,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        data.update(overrides)
        return data


class RefreshTokenFactory:
    """Factory for the ``refresh_tokens`` table."""

    @staticmethod
    def build(**overrides: Any) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": _uuid(),
            "user_id": _uuid(),
            "token": _fake.sha256(),
            "jti": str(uuid.uuid4()),
            "is_revoked": False,
            "expires_at": "2026-02-15 10:00:00",
            "created_at": _now_iso(),
        }
        data.update(overrides)
        return data


class ProductFactory:
    """Factory for the ``products`` table."""

    _BRANDS = ["Clarks", "Dr. Martens", "Timberland", "UGG", "Hunter", "Dubarry", "Sorel"]
    _COLORS = ["Black", "Brown", "Tan", "Navy", "Grey", "Burgundy"]

    @staticmethod
    def build(**overrides: Any) -> Dict[str, Any]:
        brand = _fake.random_element(ProductFactory._BRANDS)
        name = f"{brand} {_fake.word().title()} Boot"
        slug = name.lower().replace(" ", "-")
        base_price = round(_fake.pyfloat(min_value=40, max_value=300, right_digits=2), 2)
        data: Dict[str, Any] = {
            "id": _uuid(),
            "category_id": None,
            "name": name,
            "slug": slug,
            "description": _fake.paragraph(nb_sentences=3),
            "short_description": _fake.sentence(nb_words=8),
            "brand": brand,
            "sku": f"{brand[:3].upper()}-{_fake.bothify(text='???-###').upper()}",
            "base_price": str(Decimal(str(base_price))),
            "sale_price": None,
            "currency": "GBP",
            "stock_quantity": _fake.random_int(min=0, max=200),
            "is_active": True,
            "is_featured": False,
            "image_url": f"https://cdn.example.com/products/{slug}.jpg",
            "images": [],
            "attributes": {},
            "average_rating": None,
            "review_count": 0,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        data.update(overrides)
        return data


class ProductVariantFactory:
    """Factory for the ``product_variants`` table."""

    _SIZES = ["3", "4", "5", "6", "7", "8", "9", "10"]
    _COLORS = ["Black", "Tan", "Brown", "Grey", "Navy"]
    _MATERIALS = ["Leather", "Suede", "Rubber", "Synthetic", "Canvas"]

    @staticmethod
    def build(**overrides: Any) -> Dict[str, Any]:
        size = _fake.random_element(ProductVariantFactory._SIZES)
        color = _fake.random_element(ProductVariantFactory._COLORS)
        material = _fake.random_element(ProductVariantFactory._MATERIALS)
        data: Dict[str, Any] = {
            "id": _uuid(),
            "product_id": _uuid(),
            "name": f"UK {size} / {color}",
            "sku": f"VAR-{_fake.bothify(text='???-###').upper()}",
            "size": size,
            "color": color,
            "material": material,
            "price_modifier": "0.00",
            "stock_quantity": _fake.random_int(min=0, max=50),
            "inventory_count": _fake.random_int(min=0, max=50),
            "image_url": None,
            "is_active": True,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        data.update(overrides)
        return data


class CartFactory:
    """Factory for the ``carts`` table."""

    @staticmethod
    def build(**overrides: Any) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": _uuid(),
            "user_id": None,
            "session_id": None,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        data.update(overrides)
        return data


class CartItemFactory:
    """Factory for the ``cart_items`` table."""

    @staticmethod
    def build(**overrides: Any) -> Dict[str, Any]:
        unit_price = round(_fake.pyfloat(min_value=20, max_value=300, right_digits=2), 2)
        quantity = _fake.random_int(min=1, max=5)
        data: Dict[str, Any] = {
            "id": _uuid(),
            "cart_id": _uuid(),
            "product_id": _uuid(),
            "variant_id": None,
            "quantity": quantity,
            "unit_price": str(Decimal(str(unit_price))),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        data.update(overrides)
        return data


class OrderFactory:
    """Factory for the ``orders`` table."""

    _STATUSES = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]
    _PAYMENT_STATUSES = ["unpaid", "paid", "failed", "refunded"]

    @staticmethod
    def build(**overrides: Any) -> Dict[str, Any]:
        subtotal = round(_fake.pyfloat(min_value=30, max_value=500, right_digits=2), 2)
        shipping = 4.99
        tax = round(subtotal * 0.1, 2)
        total = round(subtotal + shipping + tax, 2)
        data: Dict[str, Any] = {
            "id": _uuid(),
            "user_id": None,
            "order_number": f"ORD-{_fake.numerify(text='####-######')}",
            "guest_email": None,
            "status": "pending",
            "payment_status": "unpaid",
            "subtotal": str(Decimal(str(subtotal))),
            "shipping_cost": str(Decimal(str(shipping))),
            "tax": str(Decimal(str(tax))),
            "total": str(Decimal(str(total))),
            "total_amount": str(Decimal(str(total))),
            "currency": "GBP",
            "shipping_address": {},
            "shipping_name": _fake.name(),
            "shipping_address_line1": _fake.street_address(),
            "shipping_address_line2": None,
            "shipping_city": _fake.city(),
            "shipping_county": _fake.county(),
            "shipping_postcode": _fake.postcode(),
            "shipping_country": "United Kingdom",
            "billing_name": None,
            "billing_address_line1": None,
            "billing_address_line2": None,
            "billing_city": None,
            "billing_county": None,
            "billing_postcode": None,
            "billing_country": None,
            "payment_reference": None,
            "stripe_payment_intent_id": None,
            "notes": None,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        data.update(overrides)
        return data


class OrderItemFactory:
    """Factory for the ``order_items`` table."""

    @staticmethod
    def build(**overrides: Any) -> Dict[str, Any]:
        unit_price = round(_fake.pyfloat(min_value=20, max_value=300, right_digits=2), 2)
        quantity = _fake.random_int(min=1, max=3)
        line_total = round(unit_price * quantity, 2)
        data: Dict[str, Any] = {
            "id": _uuid(),
            "order_id": _uuid(),
            "product_id": _uuid(),
            "variant_id": None,
            "product_name": f"{_fake.word().title()} Boot",
            "variant_name": None,
            "sku": f"SKU-{_fake.bothify(text='???-###').upper()}",
            "quantity": quantity,
            "unit_price": str(Decimal(str(unit_price))),
            "line_total": str(Decimal(str(line_total))),
            "created_at": _now_iso(),
        }
        data.update(overrides)
        return data


class ReviewFactory:
    """Factory for the ``reviews`` table.

    rating is constrained to 1–5 (chk_reviews_rating).
    UNIQUE(user_id, product_id) — callers must ensure uniqueness.
    """

    _TITLES = [
        "Great boots!", "Very comfortable", "Perfect fit",
        "Excellent quality", "Disappointed", "Solid choice",
        "Would recommend", "Not as described",
    ]

    @staticmethod
    def build(**overrides: Any) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": _uuid(),
            "product_id": _uuid(),
            "user_id": _uuid(),
            "order_id": None,
            "rating": _fake.random_int(min=1, max=5),
            "title": _fake.random_element(ReviewFactory._TITLES),
            "body": _fake.paragraph(nb_sentences=3),
            "is_verified_purchase": False,
            "is_approved": True,
            "helpful_votes": _fake.random_int(min=0, max=20),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        data.update(overrides)
        return data
