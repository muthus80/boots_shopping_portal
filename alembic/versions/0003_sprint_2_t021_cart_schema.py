"""Sprint 2 T-021 cart schema — add supporting indexes on cart_items for
product_id and variant_id columns.  These indexes optimise the cart service
query patterns for US-009 (add to cart) and US-010 (view/edit cart):

  * ix_cart_items_product_id  — fast deletion / lookup when a product is
                                referenced from the cart (e.g. cascade checks)
  * ix_cart_items_variant_id  — fast lookup by variant when adding or
                                updating cart items

Both indexes are additive (no DDL changes to existing tables or constraints).

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-07 00:00:00.000000
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Index: cart_items.product_id                                        #
    # Supports fast lookup / cascade verification when a product is       #
    # referenced from cart items (US-009 add-to-cart by product+variant). #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_cart_items_product_id",
        "cart_items",
        ["product_id"],
        unique=False,
    )

    # ------------------------------------------------------------------ #
    # Index: cart_items.variant_id                                        #
    # Supports fast lookup when filtering cart items by product variant   #
    # (US-009 / US-010: add, update, or remove a specific variant).       #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_cart_items_variant_id",
        "cart_items",
        ["variant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cart_items_variant_id", table_name="cart_items")
    op.drop_index("ix_cart_items_product_id", table_name="cart_items")
