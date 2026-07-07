from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ProductVariantRead(BaseModel):
    id: UUID
    product_id: UUID
    size: Optional[str] = None
    color: Optional[str] = None
    sku: Optional[str] = None
    stock_quantity: int
    price_modifier: float = 0.0

    model_config = {"from_attributes": True}


class ReviewRead(BaseModel):
    """Internal review read schema — preserves existing field names (body, title)."""

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
    """Internal review create schema used by service layer."""

    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = None
    body: Optional[str] = None


# ── T-019 (US-008): API-contract schemas ────────────────────────────────────


class ReviewSubmit(BaseModel):
    """Request body for POST /api/v1/products/{product_id}/reviews.

    Uses ``review_text`` as the field name per the API contract.
    """

    rating: int = Field(..., ge=1, le=5, description="Star rating between 1 and 5")
    review_text: str = Field(..., description="Review text content")


class ReviewContractRead(BaseModel):
    """Response schema for review endpoints — matches API contract.

    Maps the ORM ``body`` field to ``review_text`` for API-contract compliance.
    """

    id: UUID
    rating: int
    review_text: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _map_body_to_review_text(cls, data: object) -> object:
        """Map ORM ``body`` attribute → ``review_text`` field."""
        if hasattr(data, "body"):
            # ORM model instance — extract into a plain dict
            return {
                "id": data.id,  # type: ignore[union-attr]
                "rating": data.rating,  # type: ignore[union-attr]
                "review_text": data.body,  # type: ignore[union-attr]
                "created_at": data.created_at,  # type: ignore[union-attr]
            }
        # Already a dict (e.g. from JSON tests)
        if isinstance(data, dict) and "review_text" not in data and "body" in data:
            data = dict(data)
            data["review_text"] = data.pop("body")
        return data


class ReviewListResponse(BaseModel):
    """Paginated response for GET /api/v1/products/{product_id}/reviews."""

    average_rating: float
    reviews: List[ReviewContractRead]
    total_reviews: int


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
    images: list = Field(default_factory=list)
    is_active: bool
    average_rating: Optional[float] = None
    review_count: int = 0
    variants: List[ProductVariantRead] = Field(default_factory=list)
    reviews: List[ReviewRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductCard(BaseModel):
    """Lightweight product card used in listing pages (no nested relations)."""

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


class ProductList(BaseModel):
    """Paginated product listing response — wraps a list of ProductRead items."""

    items: List[ProductRead] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1