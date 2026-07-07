from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Shipping address ──────────────────────────────────────────────────────────

class ShippingAddressIn(BaseModel):
    """Shipping address provided by the customer at checkout."""

    line1: str
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str = "GB"


# ── Payment Intent ────────────────────────────────────────────────────────────

class PaymentIntentRequest(BaseModel):
    """POST /api/v1/checkout/payment-intent request body (ADR-003).

    guest_email is required when not authenticated (guest checkout, US-011).
    shipping_address is stored in Stripe metadata for the confirm step.
    """

    guest_email: Optional[str] = None
    shipping_name: Optional[str] = None
    shipping_address: ShippingAddressIn


class PaymentIntentResponse(BaseModel):
    """Response for POST /api/v1/checkout/payment-intent."""

    client_secret: str
    payment_intent_id: str
    amount: int  # in pence / cents
    currency: str = "gbp"


# ── Confirm Order ─────────────────────────────────────────────────────────────

class ConfirmOrderRequest(BaseModel):
    """POST /api/v1/checkout/confirm request body."""

    payment_intent_id: str


class OrderItemContractRead(BaseModel):
    """Order line item in the confirm-order response (API contract shape)."""

    product_name: str
    color: Optional[str] = None
    size: Optional[str] = None
    quantity: int
    unit_price: Decimal


class ConfirmOrderResponse(BaseModel):
    """Response for POST /api/v1/checkout/confirm — matches API contract."""

    order_id: str  # UUID as string
    order_number: str
    shipping_address: Dict[str, Any]
    total_amount: Decimal
    items: List[OrderItemContractRead] = Field(default_factory=list)


# ── Internal order-read schemas (GET /checkout/orders) ───────────────────────

class OrderItemRead(BaseModel):
    id: UUID
    product_id: Optional[UUID] = None
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = {"from_attributes": True}


class OrderRead(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    status: str
    total_amount: Optional[Decimal] = None
    shipping_address: Any = None
    billing_address: Optional[str] = None
    payment_intent_id: Optional[str] = None
    items: List[OrderItemRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
