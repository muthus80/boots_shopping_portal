-- ============================================================
-- Sprint 3 — Checkout, Payments, Reviews & Accessibility
-- Task T-025: Orders database schema (US-003 Guest Checkout)
-- Engine: PostgreSQL
-- ------------------------------------------------------------
-- All core table DDL (orders, order_items, reviews) was
-- established in schema_sprint_1.sql.  This file documents
-- the incremental Sprint 3 additions: performance indexes
-- required for the checkout flow, Stripe webhook verification,
-- authenticated order history, and purchase-verified reviews.
-- ============================================================

-- ============================================================
-- Migration 0004: Sprint 3 T-025 checkout indexes
-- ============================================================

-- ----------------------------------------------------------------
-- orders: stripe_payment_intent_id
-- ADR-003 (Stripe PaymentIntents) — the backend verifies the
-- PaymentIntent status before creating the order record.  This
-- index makes the lookup sub-millisecond even at scale.
-- POST /api/v1/checkout/confirm
-- ----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_orders_stripe_payment_intent_id
    ON orders (stripe_payment_intent_id);

-- ----------------------------------------------------------------
-- orders: guest_email
-- Supports guest order history retrieval by email address and
-- order-confirmation email dispatch (US-003 guest checkout).
-- GET /api/v1/account/orders (guest variant), email service
-- ----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_orders_guest_email
    ON orders (guest_email);

-- ----------------------------------------------------------------
-- orders: status
-- Fast lifecycle filtering — "all pending orders", "all shipped"
-- Used by admin order management and order history pages.
-- GET /api/v1/account/orders?status=...
-- ----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_orders_status
    ON orders (status);

-- ----------------------------------------------------------------
-- orders: created_at
-- GET /api/v1/account/orders returns newest-first (DESC).
-- Index on created_at enables efficient ORDER BY + LIMIT/OFFSET
-- pagination without a full table scan.
-- ----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_orders_created_at
    ON orders (created_at);

-- ----------------------------------------------------------------
-- order_items: variant_id
-- Supports JOIN queries from product_variants → order_items
-- (variant sales history, purchase-verification per variant).
-- Complements the existing ix_order_items_product_id index.
-- ----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_order_items_variant_id
    ON order_items (variant_id);

-- ----------------------------------------------------------------
-- reviews: order_id
-- POST /api/v1/products/{product_id}/reviews (T-018) must verify
-- the reviewer has a completed order for the product before
-- allowing review submission.  Index enables a fast existence
-- check against the orders table.
-- ----------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_reviews_order_id
    ON reviews (order_id);

-- ============================================================
-- Sprint 3 query patterns (informational)
-- ============================================================

-- US-003 (Guest Checkout): Verify Stripe PaymentIntent before creating order
--   SELECT id, status, total_amount
--   FROM orders
--   WHERE stripe_payment_intent_id = :payment_intent_id;
--   Index used: ix_orders_stripe_payment_intent_id

-- US-003 (Guest Checkout): Look up guest orders by email
--   SELECT *
--   FROM orders
--   WHERE guest_email = :email
--   ORDER BY created_at DESC;
--   Indexes used: ix_orders_guest_email, ix_orders_created_at

-- US-003 (Order History — Authenticated): Paginated order list for user
--   SELECT o.*, oi.*
--   FROM orders o
--   JOIN order_items oi ON oi.order_id = o.id
--   WHERE o.user_id = :user_id
--   ORDER BY o.created_at DESC
--   LIMIT :limit OFFSET :offset;
--   Indexes used: ix_orders_user_id (Sprint 1), ix_orders_created_at,
--                 ix_order_items_order_id (Sprint 1)

-- T-018 (Purchase-Verified Review): Check if user's order includes product
--   SELECT o.id
--   FROM orders o
--   JOIN order_items oi ON oi.order_id = o.id
--   WHERE o.user_id   = :user_id
--     AND oi.product_id = :product_id
--     AND o.status IN ('confirmed', 'shipped', 'delivered')
--   LIMIT 1;
--   Indexes used: ix_orders_user_id (Sprint 1), ix_order_items_order_id (Sprint 1),
--                 ix_order_items_product_id (Sprint 1), ix_orders_status

-- T-018 (Reviews): Prevent duplicate review per order
--   SELECT id
--   FROM reviews
--   WHERE order_id   = :order_id
--     AND product_id = :product_id
--     AND user_id    = :user_id
--   LIMIT 1;
--   Indexes used: ix_reviews_order_id, ix_reviews_user_id_product_id (Sprint 2)

-- US-003 (Order Status Filtering): Count orders by status
--   SELECT status, COUNT(*) AS cnt
--   FROM orders
--   GROUP BY status;
--   Index used: ix_orders_status
