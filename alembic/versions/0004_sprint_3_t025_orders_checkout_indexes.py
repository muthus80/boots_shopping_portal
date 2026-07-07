"""Sprint 3 T-025 orders/checkout schema — add performance indexes required
for the guest checkout flow, Stripe PaymentIntent webhook verification,
authenticated order history, and purchase-verified review lookups.

New indexes (all additive — no DDL changes to existing tables or constraints):

  orders
  ------
  ix_orders_stripe_payment_intent_id  — unique Stripe PI id lookup used by
      POST /api/v1/checkout/confirm to verify payment status before creating
      the order record (ADR-003: backend verifies payment_intent status).

  ix_orders_guest_email               — supports guest order lookup by email
      address (GET /api/v1/account/orders for guests, email-confirmation flow).

  ix_orders_status                    — fast filtering on order lifecycle status
      (pending → confirmed → shipped → delivered) used by order management.

  ix_orders_created_at                — supports DESC-sorted paginated order
      history queries (GET /api/v1/account/orders returns newest first).

  order_items
  -----------
  ix_order_items_variant_id           — supports JOIN from product_variants
      back to order_items (e.g. variant sold count, purchase history
      per variant).  Complements existing ix_order_items_product_id.

  reviews
  -------
  ix_reviews_order_id                 — supports purchase-verification lookup:
      given an order_id, confirm whether the user already reviewed the product
      (POST /api/v1/products/{product_id}/reviews T-018 gate).

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-07 00:00:00.000000
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # orders: stripe_payment_intent_id                                    #
    # Critical for ADR-003 Stripe PaymentIntents flow — the backend must  #
    # look up and verify a PaymentIntent before creating the order record. #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_orders_stripe_payment_intent_id",
        "orders",
        ["stripe_payment_intent_id"],
        unique=False,
    )

    # ------------------------------------------------------------------ #
    # orders: guest_email                                                 #
    # Supports guest order history lookup by email and order confirmation  #
    # email dispatch (US-003 guest checkout flow).                        #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_orders_guest_email",
        "orders",
        ["guest_email"],
        unique=False,
    )

    # ------------------------------------------------------------------ #
    # orders: status                                                      #
    # Supports filtering order lists by lifecycle status, e.g., all       #
    # "pending" orders, "shipped" orders (order management & admin).      #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_orders_status",
        "orders",
        ["status"],
        unique=False,
    )

    # ------------------------------------------------------------------ #
    # orders: created_at                                                  #
    # GET /api/v1/account/orders returns orders sorted by created_at DESC. #
    # An index on created_at enables efficient ORDER BY + LIMIT/OFFSET.   #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_orders_created_at",
        "orders",
        ["created_at"],
        unique=False,
    )

    # ------------------------------------------------------------------ #
    # order_items: variant_id                                             #
    # Supports JOIN queries from product_variants → order_items (variant  #
    # sales history, purchase-verification per variant).                  #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_order_items_variant_id",
        "order_items",
        ["variant_id"],
        unique=False,
    )

    # ------------------------------------------------------------------ #
    # reviews: order_id                                                   #
    # POST /api/v1/products/{product_id}/reviews (T-018) must verify that #
    # the reviewer has a completed order for the product.  Indexing       #
    # order_id on reviews enables a fast existence check.                 #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_reviews_order_id",
        "reviews",
        ["order_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reviews_order_id", table_name="reviews")
    op.drop_index("ix_order_items_variant_id", table_name="order_items")
    op.drop_index("ix_orders_created_at", table_name="orders")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_guest_email", table_name="orders")
    op.drop_index("ix_orders_stripe_payment_intent_id", table_name="orders")
