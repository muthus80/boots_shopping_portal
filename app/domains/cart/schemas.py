from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CartItemRead(BaseModel):
    id: UUID
    cart_id: UUID
    product_id: UUID
    product_name: str
    product_image_url: Optional[str] = None
    unit_price: float
    quantity: int
    subtotal: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CartRead(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    items: list[CartItemRead] = Field(default_factory=list)
    total: float
    item_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AddCartItem(BaseModel):
    product_id: UUID
    variant_id: Optional[UUID] = None
    quantity: int = Field(default=1, ge=1)


class UpdateCartItem(BaseModel):
    quantity: int = Field(ge=1)
