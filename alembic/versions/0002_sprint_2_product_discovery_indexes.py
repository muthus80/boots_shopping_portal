"""Sprint 2 product discovery indexes — composite review index, brand and
active-product partial indexes for faceted filtering (T-009, US-004 – US-010).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-07 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Composite index: reviews(user_id, product_id)                       #
    # Used to check whether a user has already reviewed a product.        #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_reviews_user_id_product_id",
        "reviews",
        ["user_id", "product_id"],
        unique=False,
    )

    # ------------------------------------------------------------------ #
    # Index: products.brand                                               #
    # Supports US-005 brand-based faceted filtering.                      #
    # ------------------------------------------------------------------ #
    op.create_index(
        "ix_products_brand",
        "products",
        ["brand"],
        unique=False,
    )

    # ------------------------------------------------------------------ #
    # Partial index: active products only (is_active = TRUE)             #
    # The product listing (US-006) and search (US-004) always filter on  #
    # is_active = TRUE; a partial index cuts index size and improves LCP. #
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_products_is_active
            ON products (is_active)
            WHERE is_active = TRUE;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_products_is_active;")
    op.drop_index("ix_products_brand", table_name="products")
    op.drop_index("ix_reviews_user_id_product_id", table_name="reviews")
