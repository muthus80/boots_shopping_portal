"""Sprint 3 T-018 — purchase-verified product reviews schema.

Adds the UNIQUE(user_id, product_id) constraint on the reviews table to
enforce one review per user per product (US-008).  The constraint acts as
the database-level guard for the POST /api/v1/products/{product_id}/reviews
endpoint after the service layer verifies the purchase.

Changes
-------
1. DROP the non-unique composite index ix_reviews_user_id_product_id (Sprint 2
   migration 0002) — it is superseded by the new UNIQUE constraint which
   implicitly creates an equally-efficient B-tree index.
2. ADD UNIQUE CONSTRAINT uq_reviews_user_product ON reviews(user_id, product_id).

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-07 00:00:00.000000
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Drop the non-unique composite index added in Sprint 2 migration     #
    # 0002.  The UNIQUE constraint below creates an equivalent B-tree     #
    # index, so keeping both would waste storage and slow writes.         #
    # ------------------------------------------------------------------ #
    op.drop_index("ix_reviews_user_id_product_id", table_name="reviews")

    # ------------------------------------------------------------------ #
    # Add UNIQUE constraint: one review per user per product.             #
    # This is the core T-018 data-integrity gate.  The service layer must #
    # verify a completed purchase before inserting; the DB constraint     #
    # guarantees idempotency even if two concurrent requests slip through. #
    # ------------------------------------------------------------------ #
    op.create_unique_constraint(
        "uq_reviews_user_product",
        "reviews",
        ["user_id", "product_id"],
    )


def downgrade() -> None:
    # Reverse: drop the unique constraint, recreate the plain index.
    op.drop_constraint("uq_reviews_user_product", "reviews", type_="unique")

    op.create_index(
        "ix_reviews_user_id_product_id",
        "reviews",
        ["user_id", "product_id"],
        unique=False,
    )
