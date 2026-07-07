"""Cart domain ORM models — Sprint 2 T-021 (US-009, US-010).

Implements:
  Cart      — supports both guest (session_id) and authenticated (user_id) carts.
  CartItem  — individual line item referencing a product and optional variant.

Architecture spec: Cart.user_id FK is ON DELETE SET NULL (user deletion does
NOT destroy the cart — allows order history recovery).  cart_items.cart_id is
ON DELETE CASCADE (deleting a cart removes all its items).
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Cart(Base):
    """Shopping cart supporting both guest (session-based) and authenticated users.

    Fields
    ------
    id          : UUID PK
    user_id     : nullable FK → users.id ON DELETE SET NULL
    session_id  : nullable VARCHAR(255) — identifies guest sessions
    created_at  : TIMESTAMPTZ
    updated_at  : TIMESTAMPTZ (server trigger on PostgreSQL)
    """

    __tablename__ = "carts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(  # noqa: F821
        "User", back_populates="carts"
    )
    items: Mapped[List["CartItem"]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ------------------------------------------------------------------ #
    # Computed response-contract fields (CartRead schema).                #
    # items is eager (lazy="selectin") so these never trigger a lazy load.#
    # ------------------------------------------------------------------ #
    @property
    def total(self) -> float:
        """Sum of (unit_price × quantity) for all items."""
        return float(sum(
            (i.unit_price or Decimal("0")) * i.quantity
            for i in self.items
        ))

    @property
    def item_count(self) -> int:
        """Total number of units across all cart items."""
        return sum(i.quantity for i in self.items)

    def __repr__(self) -> str:
        return (
            f"<Cart id={self.id} user_id={self.user_id} "
            f"session_id={self.session_id!r}>"
        )


class CartItem(Base):
    """Individual line item in a shopping cart.

    Fields
    ------
    id                : UUID PK
    cart_id           : FK → carts.id ON DELETE CASCADE
    product_id        : FK → products.id ON DELETE CASCADE
    variant_id        : nullable FK → product_variants.id ON DELETE SET NULL
    quantity          : INTEGER CHECK (>= 1), default 1
    unit_price        : NUMERIC(10,2) — price captured at time of add-to-cart
    created_at        : TIMESTAMPTZ
    updated_at        : TIMESTAMPTZ (server trigger on PostgreSQL)

    Indexes (migration 0003)
    -------------------------
    ix_cart_items_cart_id    — already in 0001 DDL
    ix_cart_items_product_id — added in Sprint 2 migration 0003 (T-021)
    ix_cart_items_variant_id — added in Sprint 2 migration 0003 (T-021)
    """

    __tablename__ = "cart_items"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="chk_cart_items_quantity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cart_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("carts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    product: Mapped["Product"] = relationship(  # noqa: F821
        "Product", back_populates="cart_items"
    )
    variant: Mapped[Optional["ProductVariant"]] = relationship(  # noqa: F821
        "ProductVariant", back_populates="cart_items"
    )

    # ------------------------------------------------------------------ #
    # Response-contract computed fields (CartItemRead schema).            #
    # product is NOT eagerly loaded by default — guard against async      #
    # lazy load; return safe defaults instead of raising MissingGreenlet. #
    # ------------------------------------------------------------------ #
    @property
    def product_name(self) -> str:
        try:
            if "product" in sa_inspect(self).unloaded:
                return ""
        except Exception:
            pass
        return self.product.name if self.product else ""

    @property
    def product_image_url(self) -> Optional[str]:
        try:
            if "product" in sa_inspect(self).unloaded:
                return None
        except Exception:
            pass
        return self.product.image_url if self.product else None

    @property
    def subtotal(self) -> float:
        """unit_price × quantity for this line item."""
        return float((self.unit_price or Decimal("0")) * self.quantity)

    def __repr__(self) -> str:
        return (
            f"<CartItem id={self.id} cart_id={self.cart_id} "
            f"product_id={self.product_id} qty={self.quantity}>"
        )
