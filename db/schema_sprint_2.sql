-- ============================================================
-- Sprint 2 — Product Discovery, Details & Cart
-- Task T-009: Products and categories database schema
-- Task T-021: Cart database schema (US-009, US-010)
-- Engine: PostgreSQL
-- Sprint 2 adds optimisation indexes on top of Sprint 1 tables.
-- All table DDL is managed in schema_sprint_1.sql; this file
-- documents the incremental Sprint 2 additions.
-- ============================================================

-- ============================================================
-- Migration 0002 index additions (T-009 — product discovery)
-- ============================================================

-- Composite index on reviews (user_id, product_id) — used to check whether a
-- user has already reviewed a product before allowing a new submission.
-- Referenced in ADR architecture Review data-model spec.
CREATE INDEX IF NOT EXISTS ix_reviews_user_id_product_id
    ON reviews (user_id, product_id);

-- Index on products.brand — supports US-005 brand-based faceted filtering.
CREATE INDEX IF NOT EXISTS ix_products_brand
    ON products (brand);

-- Partial index on products: only active products — the product listing page
-- (US-006) and search endpoint (US-004) always filter is_active = TRUE.
CREATE INDEX IF NOT EXISTS ix_products_is_active
    ON products (is_active)
    WHERE is_active = TRUE;

-- ============================================================
-- Migration 0003 index additions (T-021 — cart schema)
-- ============================================================

-- Index: cart_items.product_id
-- Supports fast lookup / cascade verification when a product is
-- referenced from cart items (US-009 add-to-cart by product+variant).
CREATE INDEX IF NOT EXISTS ix_cart_items_product_id
    ON cart_items (product_id);

-- Index: cart_items.variant_id
-- Supports fast lookup when filtering cart items by product variant
-- (US-009 / US-010: add, update, or remove a specific variant).
CREATE INDEX IF NOT EXISTS ix_cart_items_variant_id
    ON cart_items (variant_id);

-- ============================================================
-- Sprint 2 query patterns (informational)
-- ============================================================

-- US-004 / ADR-004: Full-text search on products
--   SELECT * FROM products
--   WHERE search_vector @@ plainto_tsquery('english', :query)
--   ORDER BY ts_rank(search_vector, plainto_tsquery('english', :query)) DESC;
--   Index used: ix_products_search_vector (GIN, created in Sprint 1)

-- US-005: Faceted filtering by category, size, color, price
--   SELECT p.* FROM products p
--   JOIN product_variants pv ON pv.product_id = p.id
--   WHERE p.category_id = :category_id
--     AND pv.size = :size
--     AND pv.color = :color
--     AND p.base_price BETWEEN :min_price AND :max_price
--     AND p.is_active = TRUE;
--   Indexes used: ix_products_category_id, ix_product_variants_size,
--                 ix_product_variants_color, ix_products_is_active

-- US-006: Category product listing page
--   SELECT p.*, c.name AS category_name
--   FROM products p
--   JOIN categories c ON c.id = p.category_id
--   WHERE c.slug = :slug AND p.is_active = TRUE
--   ORDER BY p.is_featured DESC, p.created_at DESC;
--   Indexes used: ix_categories_slug (unique), ix_products_category_id,
--                 ix_products_is_active

-- US-007: Product detail page (includes variants and reviews)
--   SELECT p.*, pv.*, r.*
--   FROM products p
--   LEFT JOIN product_variants pv ON pv.product_id = p.id
--   LEFT JOIN reviews r ON r.product_id = p.id AND r.is_approved = TRUE
--   WHERE p.slug = :slug;
--   Indexes used: ix_products_slug (unique), ix_product_variants_product_id,
--                 ix_reviews_product_id

-- US-009: Add to cart (product + variant lookup)
--   SELECT ci.* FROM cart_items ci
--   WHERE ci.cart_id = :cart_id
--     AND ci.product_id = :product_id
--     AND ci.variant_id = :variant_id;
--   Indexes used: ix_cart_items_cart_id, ix_cart_items_product_id,
--                 ix_cart_items_variant_id

-- US-009/010: Cart management (guest and authenticated)
--   SELECT c.*, ci.* FROM carts c
--   JOIN cart_items ci ON ci.cart_id = c.id
--   WHERE c.user_id = :user_id OR c.session_id = :session_id;
--   Indexes used: ix_carts_user_id, ix_carts_session_id, ix_cart_items_cart_id

-- US-010: Update or remove a cart item by variant
--   SELECT ci.* FROM cart_items ci
--   WHERE ci.variant_id = :variant_id AND ci.cart_id = :cart_id;
--   Indexes used: ix_cart_items_variant_id, ix_cart_items_cart_id
