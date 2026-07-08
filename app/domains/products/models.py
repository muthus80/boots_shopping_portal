from __future__ import annotations

import uuid as _uuid
from typing import List

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    TypeDecorator,
    func,
    types,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from app.core.database import Base


class TsVector(TypeDecorator):
    """
    Portable wrapper around PostgreSQL TSVECTOR.
    Falls back to Text on non-PostgreSQL engines (e.g., SQLite for tests).
    """
    impl = types.Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import TSVECTOR
            return dialect.type_descriptor(TSVECTOR())
        return dialect.type_descriptor(types.Text())


class Product(Base):
    __tablename__ = "products"
    __allow_unmapped__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, index=True)
    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)
    brand = Column(String(100), nullable=True)
    sku = Column(String(100), nullable=True, unique=True, index=True)
    base_price = Column(Numeric(10, 2), nullable=False)
    sale_price = Column(Numeric(10, 2), nullable=True)

    # ------------------------------------------------------------------ #
    # price — read/write alias for base_price (QA-fix: ProductRead uses   #
    # 'price' field name; the DB column is 'base_price').                 #
    # ------------------------------------------------------------------ #
    @hybrid_property
    def price(self):  # type: ignore[override]
        return self.base_price

    @price.setter
    def price(self, value):
        self.base_price = value

    @price.expression
    def price(cls):  # noqa: N805
        return cls.base_price

    currency = Column(String(3), nullable=False, default="GBP")
    stock_quantity = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    is_featured = Column(Boolean, nullable=False, default=False)
    image_url = Column(String(500), nullable=True)

    # thumbnail_url — alias for image_url (schema uses thumbnail_url)
    @hybrid_property
    def thumbnail_url(self):  # type: ignore[override]
        return self.image_url

    @thumbnail_url.setter
    def thumbnail_url(self, value):
        self.image_url = value

    # JSON renders as JSONB on PostgreSQL, as JSON/TEXT on SQLite (test-compatible)
    images = Column(JSON, nullable=False, default=list)
    attributes = Column(JSON, nullable=False, default=dict)
    # TsVector: TSVECTOR on PG, TEXT on SQLite — maintained by DB trigger (ADR-004)
    search_vector = Column(TsVector, nullable=True)
    average_rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    category = relationship("Category", back_populates="products")
    variants: List["ProductVariant"] = relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan"
    )
    reviews: List["Review"] = relationship(
        "Review", back_populates="product", cascade="all, delete-orphan"
    )
    cart_items = relationship("CartItem", back_populates="product", passive_deletes=True)
    order_items = relationship("OrderItem", back_populates="product", passive_deletes=True)


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __allow_unmapped__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, index=True)
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=True, unique=True, index=True)
    size = Column(String(50), nullable=True, index=True)
    color = Column(String(50), nullable=True, index=True)
    material = Column(String(100), nullable=True)
    price_modifier = Column(Numeric(10, 2), nullable=False, default=0)
    stock_quantity = Column(Integer, nullable=False, default=0)
    # inventory_count mirrors the architecture data model (>= 0 check)
    inventory_count = Column(Integer, nullable=False, default=0)
    image_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    product: "Product" = relationship("Product", back_populates="variants")
    cart_items = relationship("CartItem", back_populates="variant")
    order_items = relationship("OrderItem", back_populates="variant")


class Review(Base):
    """Purchase-verified product review linking product, user, and verifying order.

    T-018 (US-008) — one review per user per product enforced at DB level
    via UNIQUE(user_id, product_id).

    Fields
    ------
    id                  : UUID PK
    product_id          : FK → products.id ON DELETE CASCADE
    user_id             : FK → users.id ON DELETE CASCADE
    order_id            : nullable FK → orders.id ON DELETE SET NULL
                          Used for purchase-verification (T-018 gate).
    rating              : INTEGER CHECK (1..5)
    title               : VARCHAR(255) nullable
    body                : TEXT nullable
    is_verified_purchase: BOOLEAN default False — set True when order_id
                          is confirmed as a completed purchase.
    is_approved         : BOOLEAN default True
    helpful_votes       : INTEGER default 0
    created_at          : TIMESTAMPTZ
    updated_at          : TIMESTAMPTZ (updated via trigger on PostgreSQL)

    Table-level constraints
    -----------------------
    uq_reviews_user_product : UNIQUE(user_id, product_id)
        Enforces one review per user per product.  Adding migration 0005
        also drops the non-unique ix_reviews_user_id_product_id index (0002)
        in favour of this UNIQUE index.
    chk_reviews_rating      : CHECK(rating BETWEEN 1 AND 5)
    """

    __tablename__ = "reviews"
    __allow_unmapped__ = True
    __table_args__ = (
        # T-018: one review per user per product
        sa.UniqueConstraint("user_id", "product_id", name="uq_reviews_user_product"),
        # Re-declare check constraint so SQLite (unit tests) sees it too
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="chk_reviews_rating"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, index=True)
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rating = Column(Integer, nullable=False)  # 1-5 enforced by chk_reviews_rating
    title = Column(String(255), nullable=True)
    body = Column(Text, nullable=True)
    is_verified_purchase = Column(Boolean, nullable=False, default=False)
    is_approved = Column(Boolean, nullable=False, default=True)
    helpful_votes = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    product: "Product" = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews")
    order = relationship("Order", back_populates="reviews")
