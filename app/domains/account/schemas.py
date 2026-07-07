from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    phone: Optional[str] = None


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class OrderItemRead(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    product_sku: Optional[str] = None
    quantity: int
    unit_price: Decimal
    total_price: Decimal

    model_config = {"from_attributes": True}


class OrderRead(BaseModel):
    id: UUID
    status: str
    total_amount: Optional[Decimal] = None
    shipping_address: Optional[str] = None
    items: list[OrderItemRead] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── T-026: Order History API (GET /api/v1/account/orders) ────────────────────


class OrderSummaryRead(BaseModel):
    """Lightweight order summary returned in the order history list."""

    id: UUID
    order_number: Optional[str] = None
    status: str
    total_amount: Optional[Decimal] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderHistoryResponse(BaseModel):
    """Paginated order history response (US-003)."""

    orders: List[OrderSummaryRead]
    total: int
    message: Optional[str] = None