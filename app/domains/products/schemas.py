from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProductVariantRead(BaseModel):
    id: UUID
    product_id: UUID
    size: str
    color: Optional[str] = None
    sku: str
    stock_quantity: int
    price_modifier: float = 0.0

    model_config = {"from_attributes": True}


class ReviewRead(BaseModel):
    id: UUID
    product_id: UUID
    user_id: UUID
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = None
    body: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = None
    body: Optional[str] = None


class ProductRead(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    price: float
    sale_price: Optional[float] = None
    category_id: Optional[UUID] = None
    brand: Optional[str] = None
    thumbnail_url: Optional[str] = None
    images: list[str] = Field(default_factory=list)
    is_active: bool
    average_rating: Optional[float] = None
    review_count: int = 0
    variants: list[ProductVariantRead] = Field(default_factory=list)
    reviews: list[ReviewRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductList(BaseModel):
    id: UUID
    name: str
    slug: str
    price: float
    sale_price: Optional[float] = None
    category_id: Optional[UUID] = None
    brand: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_active: bool
    average_rating: Optional[float] = None
    review_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}