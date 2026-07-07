"""
Faker-based factory classes for boots-shopping-app models.

Each factory's ``build()`` method returns a plain dict (no DB call).
Imports: stdlib + faker only — no app imports.

IMPORTANT: Models with a hashed credential column (e.g. User.hashed_password)
do NOT include that column in the default dict.  Callers that need a valid hash
must compute it at test-time using app.core.security.hash_password().
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from faker import Faker

_fake = Faker("en_GB")


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------
class CategoryFactory:
    @staticmethod
    def build(**overrides) -> dict:
        name = _fake.unique.word().capitalize()
        data = {
            "id": str(uuid.uuid4()),
            "name": name,
            "slug": name.lower().replace(" ", "-"),
            "description": _fake.sentence(nb_words=10),
            "image_url": None,
            "is_active": True,
            "parent_id": None,
            "display_order": _fake.random_int(min=0, max=100),
        }
        data.update(overrides)
        return data


# ---------------------------------------------------------------------------
# User
# NOTE: hashed_password is intentionally omitted.
#       Compute at test-time:  from app.core.security import hash_password
# ---------------------------------------------------------------------------
class UserFactory:
    @staticmethod
    def build(**overrides) -> dict:
        data = {
            "id": str(uuid.uuid4()),
            "email": _fake.unique.email(),
            # hashed_password deliberately excluded — caller must supply or
            # compute via app.core.security.hash_password(plaintext)
            "full_name": _fake.name(),
            "is_active": True,
            "is_superuser": False,
        }
        data.update(overrides)
        return data


# ---------------------------------------------------------------------------
# RefreshToken
# ---------------------------------------------------------------------------
class RefreshTokenFactory:
    @staticmethod
    def build(**overrides) -> dict:
        data = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "token": _fake.sha256(),
            "jti": str(uuid.uuid4()),
            "is_revoked": False,
            "expires_at": "2026-12-31 23:59:59+00",
        }
        data.update(overrides)
        return data


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------
_BRANDS = ["Heritage Co", "Eleganza", "Titan Works", "StrideWell", "BootCraft"]
_CURRENCIES = ["GBP", "EUR", "USD"]


class ProductFactory:
    @staticmethod
    def build(**overrides) -> dict:
        name = " ".join([_fake.color_name(), _fake.unique.word().capitalize(), "Boot"])
        base_price = round(_fake.pyfloat(min_value=29.99, max_value=199.99, right_digits=2), 2)
        data = {
            "id": str(uuid.uuid4()),
            "category_id": None,
            "name": name,
            "slug": name.lower().replace(" ", "-"),
            "description": _fake.paragraph(nb_sentences=3),
            "short_description": _fake.sentence(nb_words=8),
            "brand": _fake.random_element(_BRANDS),
            "sku": f"SKU-{_fake.unique.lexify('????').upper()}-{_fake.random_int(100, 999)}",
            "base_price": str(Decimal(str(base_price))),
            "sale_price": None,
            "currency": "GBP",
            "stock_quantity": _fake.random_int(0, 100),
            "is_active": True,
            "is_featured": False,
            "image_url": None,
            "images": [],
            "attributes": {},
            "average_rating": None,
            "review_count": 0,
        }
        data.update(overrides)
        return data


# ---------------------------------------------------------------------------
# ProductVariant
# ---------------------------------------------------------------------------
_SIZES = ["3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
_COLORS = ["Black", "Tan", "Brown", "White", "Red", "Navy", "Grey"]
_MATERIALS = ["Leather", "Suede", "Patent", "Canvas", "Synthetic"]


class ProductVariantFactory:
    @staticmethod
    def build(**overrides) -> dict:
        size = _fake.random_element(_SIZES)
        color = _fake.random_element(_COLORS)
        data = {
            "id": str(uuid.uuid4()),
            "product_id": str(uuid.uuid4()),
            "name": f"UK {size} / {color}",
            "sku": f"VAR-{_fake.unique.lexify('????').upper()}",
            "size": size,
            "color": color,
            "material": _fake.random_element(_MATERIALS),
            "price_modifier": "0.00",
            "stock_quantity": _fake.random_int(0, 50),
            "inventory_count": _fake.random_int(0, 50),
            "image_url": None,
            "is_active": True,
        }
        data.update(overrides)
        return data


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------
class CartFactory:
    @staticmethod
    def build(**overrides) -> dict:
        data = {
            "id": str(uuid.uuid4()),
            "user_id": None,
            "session_id": str(uuid.uuid4()),
        }
        data.update(overrides)
        return data


# ---------------------------------------------------------------------------
# CartItem
# ---------------------------------------------------------------------------
class CartItemFactory:
    @staticmethod
    def build(**overrides) -> dict:
        data = {
            "id": str(uuid.uuid4()),
            "cart_id": str(uuid.uuid4()),
            "product_id": str(uuid.uuid4()),
            "variant_id": None,
            "quantity": _fake.random_int(1, 5),
            "unit_price": str(Decimal(str(round(_fake.pyfloat(min_value=19.99, max_value=199.99, right_digits=2), 2)))),
        }
        data.update(overrides)
        return data


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------
_ORDER_STATUSES = ["pending", "confirmed", "processing", "shipped", "delivered", "cancelled"]
_PAYMENT_STATUSES = ["unpaid", "paid", "failed"]


class OrderFactory:
    @staticmethod
    def build(**overrides) -> dict:
        subtotal = round(_fake.pyfloat(min_value=29.99, max_value=499.99, right_digits=2), 2)
        shipping = 4.99
        tax = round(subtotal * 0.12, 2)
        total = round(subtotal + shipping + tax, 2)
        data = {
            "id": str(uuid.uuid4()),
            "user_id": None,
            "order_number": f"ORD-{_fake.numerify('########')}",
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
            "shipping_country": "GB",
            "billing_name": _fake.name(),
            "billing_address_line1": _fake.street_address(),
            "billing_address_line2": None,
            "billing_city": _fake.city(),
            "billing_county": _fake.county(),
            "billing_postcode": _fake.postcode(),
            "billing_country": "GB",
            "payment_reference": None,
            "stripe_payment_intent_id": None,
            "notes": None,
        }
        data.update(overrides)
        return data


# ---------------------------------------------------------------------------
# OrderItem
# ---------------------------------------------------------------------------
class OrderItemFactory:
    @staticmethod
    def build(**overrides) -> dict:
        qty = _fake.random_int(1, 4)
        unit = round(_fake.pyfloat(min_value=29.99, max_value=199.99, right_digits=2), 2)
        data = {
            "id": str(uuid.uuid4()),
            "order_id": str(uuid.uuid4()),
            "product_id": str(uuid.uuid4()),
            "variant_id": None,
            "product_name": " ".join([_fake.color_name(), "Boot"]),
            "variant_name": None,
            "sku": f"SKU-{_fake.unique.lexify('????').upper()}",
            "quantity": qty,
            "unit_price": str(Decimal(str(unit))),
            "line_total": str(Decimal(str(round(unit * qty, 2)))),
        }
        data.update(overrides)
        return data


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------
class ReviewFactory:
    @staticmethod
    def build(**overrides) -> dict:
        data = {
            "id": str(uuid.uuid4()),
            "product_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "order_id": None,
            "rating": _fake.random_int(1, 5),
            "title": _fake.sentence(nb_words=5).rstrip("."),
            "body": _fake.paragraph(nb_sentences=3),
            "is_verified_purchase": False,
            "is_approved": True,
            "helpful_votes": 0,
        }
        data.update(overrides)
        return data
