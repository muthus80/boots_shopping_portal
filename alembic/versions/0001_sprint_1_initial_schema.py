"""Sprint 1 initial schema — users, refresh_tokens, categories, products,
product_variants, carts, cart_items, orders, order_items, reviews.

Revision ID: 0001
Revises:
Create Date: 2026-07-07 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # Helper: updated_at trigger function (idempotent)                    #
    # ------------------------------------------------------------------ #
    op.execute(
        """
        CREATE OR REPLACE FUNCTION _set_updated_at()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.updated_at := NOW();
            RETURN NEW;
        END;
        $$;
        """
    )

    # ------------------------------------------------------------------ #
    # users                                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.execute(
        """
        CREATE TRIGGER trg_users_updated_at
            BEFORE UPDATE ON users
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
        """
    )

    # ------------------------------------------------------------------ #
    # refresh_tokens                                                      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token", sa.String(512), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=True),
        sa.Column("jti", sa.String(255), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("token", name="uq_refresh_tokens_token"),
        sa.UniqueConstraint("jti", name="uq_refresh_tokens_jti"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_refresh_tokens_user",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)
    op.create_index("ix_refresh_tokens_jti", "refresh_tokens", ["jti"], unique=True)

    # ------------------------------------------------------------------ #
    # categories                                                          #
    # ------------------------------------------------------------------ #
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
        sa.ForeignKeyConstraint(
            ["parent_id"], ["categories.id"],
            name="fk_categories_parent",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=True)
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"], unique=False)

    op.execute(
        """
        CREATE TRIGGER trg_categories_updated_at
            BEFORE UPDATE ON categories
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
        """
    )

    # ------------------------------------------------------------------ #
    # products                                                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("short_description", sa.String(500), nullable=True),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("sale_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'GBP'")),
        sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("images", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'[]'")),
        sa.Column("attributes", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("average_rating", sa.Float(), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("slug", name="uq_products_slug"),
        sa.UniqueConstraint("sku", name="uq_products_sku"),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"],
            name="fk_products_category",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_products_category_id", "products", ["category_id"], unique=False)
    op.create_index("ix_products_slug", "products", ["slug"], unique=True)
    # GIN index for full-text search (ADR-004)
    op.execute(
        "CREATE INDEX ix_products_search_vector ON products USING GIN (search_vector);"
    )

    # Full-text search vector trigger (ADR-004)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION _products_search_vector_update()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.brand, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'C');
            RETURN NEW;
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_products_search_vector
            BEFORE INSERT OR UPDATE OF name, brand, description ON products
            FOR EACH ROW EXECUTE FUNCTION _products_search_vector_update();
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_products_updated_at
            BEFORE UPDATE ON products
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
        """
    )

    # ------------------------------------------------------------------ #
    # product_variants                                                    #
    # ------------------------------------------------------------------ #
    op.create_table(
        "product_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("size", sa.String(50), nullable=True),
        sa.Column("color", sa.String(50), nullable=True),
        sa.Column("material", sa.String(100), nullable=True),
        sa.Column("price_modifier", sa.Numeric(10, 2), nullable=False,
                  server_default=sa.text("0")),
        sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("inventory_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("sku", name="uq_product_variants_sku"),
        sa.CheckConstraint("inventory_count >= 0", name="chk_product_variants_inventory"),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"],
            name="fk_product_variants_product",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"],
                    unique=False)
    op.create_index("ix_product_variants_size", "product_variants", ["size"], unique=False)
    op.create_index("ix_product_variants_color", "product_variants", ["color"], unique=False)

    op.execute(
        """
        CREATE TRIGGER trg_product_variants_updated_at
            BEFORE UPDATE ON product_variants
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
        """
    )

    # ------------------------------------------------------------------ #
    # carts                                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "carts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_carts_user",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_carts_user_id", "carts", ["user_id"], unique=False)
    op.create_index("ix_carts_session_id", "carts", ["session_id"], unique=False)

    op.execute(
        """
        CREATE TRIGGER trg_carts_updated_at
            BEFORE UPDATE ON carts
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
        """
    )

    # ------------------------------------------------------------------ #
    # cart_items                                                          #
    # ------------------------------------------------------------------ #
    op.create_table(
        "cart_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("cart_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.CheckConstraint("quantity >= 1", name="chk_cart_items_quantity"),
        sa.ForeignKeyConstraint(
            ["cart_id"], ["carts.id"],
            name="fk_cart_items_cart",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"],
            name="fk_cart_items_product",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"], ["product_variants.id"],
            name="fk_cart_items_variant",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_cart_items_cart_id", "cart_items", ["cart_id"], unique=False)

    op.execute(
        """
        CREATE TRIGGER trg_cart_items_updated_at
            BEFORE UPDATE ON cart_items
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
        """
    )

    # ------------------------------------------------------------------ #
    # orders                                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("order_number", sa.String(50), nullable=True),
        sa.Column("guest_email", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False,
                  server_default=sa.text("'pending'")),
        sa.Column("payment_status", sa.String(50), nullable=False,
                  server_default=sa.text("'unpaid'")),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("shipping_cost", sa.Numeric(12, 2), nullable=False,
                  server_default=sa.text("0")),
        sa.Column("tax", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default=sa.text("0")),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("currency", sa.String(8), nullable=False, server_default=sa.text("'GBP'")),
        sa.Column("shipping_address", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'")),
        sa.Column("shipping_name", sa.String(255), nullable=True),
        sa.Column("shipping_address_line1", sa.String(255), nullable=True),
        sa.Column("shipping_address_line2", sa.String(255), nullable=True),
        sa.Column("shipping_city", sa.String(100), nullable=True),
        sa.Column("shipping_county", sa.String(100), nullable=True),
        sa.Column("shipping_postcode", sa.String(20), nullable=True),
        sa.Column("shipping_country", sa.String(100), nullable=True),
        sa.Column("billing_name", sa.String(255), nullable=True),
        sa.Column("billing_address_line1", sa.String(255), nullable=True),
        sa.Column("billing_address_line2", sa.String(255), nullable=True),
        sa.Column("billing_city", sa.String(100), nullable=True),
        sa.Column("billing_county", sa.String(100), nullable=True),
        sa.Column("billing_postcode", sa.String(20), nullable=True),
        sa.Column("billing_country", sa.String(100), nullable=True),
        sa.Column("payment_reference", sa.String(255), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.UniqueConstraint("order_number", name="uq_orders_order_number"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_orders_user",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"], unique=False)
    op.create_index("ix_orders_order_number", "orders", ["order_number"], unique=True)

    op.execute(
        """
        CREATE TRIGGER trg_orders_updated_at
            BEFORE UPDATE ON orders
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
        """
    )

    # ------------------------------------------------------------------ #
    # order_items                                                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("variant_name", sa.String(255), nullable=True),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.CheckConstraint("quantity >= 1", name="chk_order_items_quantity"),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"],
            name="fk_order_items_order",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"],
            name="fk_order_items_product",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["variant_id"], ["product_variants.id"],
            name="fk_order_items_variant",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"], unique=False)
    op.create_index("ix_order_items_product_id", "order_items", ["product_id"], unique=False)

    # ------------------------------------------------------------------ #
    # reviews                                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("is_verified_purchase", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("is_approved", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("helpful_votes", sa.Integer(), nullable=False,
                  server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="chk_reviews_rating"),
        sa.ForeignKeyConstraint(
            ["product_id"], ["products.id"],
            name="fk_reviews_product",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_reviews_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["order_id"], ["orders.id"],
            name="fk_reviews_order",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_reviews_product_id", "reviews", ["product_id"], unique=False)
    op.create_index("ix_reviews_user_id", "reviews", ["user_id"], unique=False)

    op.execute(
        """
        CREATE TRIGGER trg_reviews_updated_at
            BEFORE UPDATE ON reviews
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
        """
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("reviews")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("cart_items")
    op.drop_table("carts")
    op.drop_table("product_variants")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_table("refresh_tokens")
    op.drop_table("users")

    op.execute("DROP FUNCTION IF EXISTS _products_search_vector_update() CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS _set_updated_at() CASCADE;")
