from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentIntentRequest(BaseModel):
    cart_id: UUID
    shipping_address: str
    billing_address: Optional[str] = None


class PaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str
    amount: Decimal
    currency: str = "gbp"


class ConfirmOrderRequest(BaseModel):
    payment_intent_id: str
    cart_id: UUID
    shipping_address: str
    billing_address: Optional[str] = None


class OrderItemRead(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = {"from_attributes": True}


class OrderRead(BaseModel):
    id: UUID
    user_id: UUID
    status: str
    total_amount: Decimal
    shipping_address: str
    billing_address: Optional[str] = None
    payment_intent_id: Optional[str] = None
    items: List[OrderItemRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}