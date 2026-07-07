from __future__ import annotations

import enum
import uuid
from typing import List

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    processing = "processing"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"
    refunded = "refunded"


class PaymentStatus(str, enum.Enum):
    unpaid = "unpaid"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class Order(Base):
    __tablename__ = "orders"
    __allow_unmapped__ = True

    id: Column = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    user_id: Column = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_number: Column = Column(String(50), nullable=True, unique=True, index=True)
    guest_email: Column = Column(String(255), nullable=True)
    status: Column = Column(
        String(50),
        nullable=False,
        default=OrderStatus.pending.value,
    )
    payment_status: Column = Column(
        String(50),
        nullable=False,
        default=PaymentStatus.unpaid.value,
    )
    subtotal: Column = Column(Numeric(12, 2), nullable=False, default=0)
    shipping_cost: Column = Column(Numeric(12, 2), nullable=False, default=0)
    tax: Column = Column(Numeric(12, 2), nullable=False, default=0)
    total: Column = Column(Numeric(12, 2), nullable=False, default=0)
    # total_amount mirrors the architecture data model field name
    total_amount: Column = Column(Numeric(10, 2), nullable=True)
    currency: Column = Column(String(8), nullable=False, default="GBP")
    # JSON shipping_address (JSONB on PostgreSQL, JSON/Text on SQLite — test-compatible)
    shipping_address: Column = Column(JSON, nullable=False, default=dict)
    shipping_name: Column = Column(String(255), nullable=True)
    shipping_address_line1: Column = Column(String(255), nullable=True)
    shipping_address_line2: Column = Column(String(255), nullable=True)
    shipping_city: Column = Column(String(100), nullable=True)
    shipping_county: Column = Column(String(100), nullable=True)
    shipping_postcode: Column = Column(String(20), nullable=True)
    shipping_country: Column = Column(String(100), nullable=True)
    billing_name: Column = Column(String(255), nullable=True)
    billing_address_line1: Column = Column(String(255), nullable=True)
    billing_address_line2: Column = Column(String(255), nullable=True)
    billing_city: Column = Column(String(100), nullable=True)
    billing_county: Column = Column(String(100), nullable=True)
    billing_postcode: Column = Column(String(20), nullable=True)
    billing_country: Column = Column(String(100), nullable=True)
    payment_reference: Column = Column(String(255), nullable=True)
    stripe_payment_intent_id: Column = Column(String(255), nullable=True)
    notes: Column = Column(Text, nullable=True)
    created_at: Column = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Column = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="orders")
    items: List["OrderItem"] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reviews = relationship("Review", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    __allow_unmapped__ = True

    id: Column = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    order_id: Column = Column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Column = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    variant_id: Column = Column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_name: Column = Column(String(255), nullable=False)
    variant_name: Column = Column(String(255), nullable=True)
    sku: Column = Column(String(100), nullable=True)
    quantity: Column = Column(Integer, nullable=False, default=1)
    unit_price: Column = Column(Numeric(12, 2), nullable=False)
    line_total: Column = Column(Numeric(12, 2), nullable=False)
    created_at: Column = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    order: "Order" = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    variant = relationship("ProductVariant", back_populates="order_items")
