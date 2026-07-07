-- ============================================================
-- Sprint 1 — Initial Database Schema
-- Engine: PostgreSQL
-- Generated for: boots-shopping-app
-- ============================================================

-- Enable pgcrypto for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- ENUM types
-- ============================================================

-- Order status enum (used by orders table)
DO $$ BEGIN
    CREATE TYPE order_status_enum AS ENUM (
        'pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Payment status enum (used by orders table)
DO $$ BEGIN
    CREATE TYPE payment_status_enum AS ENUM (
        'unpaid', 'paid', 'failed', 'refunded'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- TABLE: users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              UUID        NOT NULL DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    is_superuser    BOOLEAN     NOT NULL DEFAULT FALSE,
    email_verified  BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_users PRIMARY KEY (id),
    CONSTRAINT uq_users_email UNIQUE (email)
);

-- Index for fast email lookups (login, registration dedup)
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- Trigger: keep updated_at current on every row update
CREATE OR REPLACE FUNCTION _set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION _set_updated_at();

-- ============================================================
-- TABLE: refresh_tokens
-- ============================================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id          UUID        NOT NULL DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL,
    token       VARCHAR(512) NOT NULL,
    token_hash  VARCHAR(255),
    jti         VARCHAR(255) NOT NULL,
    is_revoked  BOOLEAN     NOT NULL DEFAULT FALSE,
    revoked     BOOLEAN     NOT NULL DEFAULT FALSE,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_refresh_tokens PRIMARY KEY (id),
    CONSTRAINT uq_refresh_tokens_token UNIQUE (token),
    CONSTRAINT uq_refresh_tokens_jti UNIQUE (jti),
    CONSTRAINT fk_refresh_tokens_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON refresh_tokens (token);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_refresh_tokens_jti ON refresh_tokens (jti);

-- ============================================================
-- TABLE: categories
-- ============================================================
CREATE TABLE IF NOT EXISTS categories (
    id            UUID        NOT NULL DEFAULT gen_random_uuid(),
    name          VARCHAR(100) NOT NULL,
    slug          VARCHAR(100) NOT NULL,
    description   TEXT,
    image_url     VARCHAR(1024),
    is_active     BOOLEAN     NOT NULL DEFAULT TRUE,
    parent_id     UUID,
    display_order INTEGER     NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_categories PRIMARY KEY (id),
    CONSTRAINT uq_categories_slug UNIQUE (slug),
    CONSTRAINT fk_categories_parent
        FOREIGN KEY (parent_id) REFERENCES categories (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_categories_slug ON categories (slug);
CREATE INDEX IF NOT EXISTS ix_categories_parent_id ON categories (parent_id);

DROP TRIGGER IF EXISTS trg_categories_updated_at ON categories;
CREATE TRIGGER trg_categories_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION _set_updated_at();

-- ============================================================
-- TABLE: products
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    id                UUID         NOT NULL DEFAULT gen_random_uuid(),
    category_id       UUID,
    name              VARCHAR(255) NOT NULL,
    slug              VARCHAR(255) NOT NULL,
    description       TEXT,
    short_description VARCHAR(500),
    brand             VARCHAR(100),
    sku               VARCHAR(100),
    base_price        NUMERIC(10, 2) NOT NULL,
    sale_price        NUMERIC(10, 2),
    currency          VARCHAR(3)   NOT NULL DEFAULT 'GBP',
    stock_quantity    INTEGER      NOT NULL DEFAULT 0,
    is_active         BOOLEAN      NOT NULL DEFAULT TRUE,
    is_featured       BOOLEAN      NOT NULL DEFAULT FALSE,
    image_url         VARCHAR(500),
    images            TEXT,
    attributes        JSONB        NOT NULL DEFAULT '{}',
    search_vector     TSVECTOR,
    average_rating    FLOAT,
    review_count      INTEGER      NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_products PRIMARY KEY (id),
    CONSTRAINT uq_products_slug UNIQUE (slug),
    CONSTRAINT uq_products_sku UNIQUE (sku),
    CONSTRAINT fk_products_category
        FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_products_category_id ON products (category_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_products_slug ON products (slug);
CREATE INDEX IF NOT EXISTS ix_products_search_vector ON products USING GIN (search_vector);

-- Trigger: maintain search_vector from name, brand, description
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

DROP TRIGGER IF EXISTS trg_products_search_vector ON products;
CREATE TRIGGER trg_products_search_vector
    BEFORE INSERT OR UPDATE OF name, brand, description ON products
    FOR EACH ROW EXECUTE FUNCTION _products_search_vector_update();

DROP TRIGGER IF EXISTS trg_products_updated_at ON products;
CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION _set_updated_at();

-- ============================================================
-- TABLE: product_variants
-- ============================================================
CREATE TABLE IF NOT EXISTS product_variants (
    id              UUID         NOT NULL DEFAULT gen_random_uuid(),
    product_id      UUID         NOT NULL,
    name            VARCHAR(255) NOT NULL,
    sku             VARCHAR(100),
    size            VARCHAR(50),
    color           VARCHAR(50),
    material        VARCHAR(100),
    price_modifier  NUMERIC(10, 2) NOT NULL DEFAULT 0,
    stock_quantity  INTEGER      NOT NULL DEFAULT 0,
    inventory_count INTEGER      NOT NULL DEFAULT 0,
    image_url       VARCHAR(500),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_product_variants PRIMARY KEY (id),
    CONSTRAINT uq_product_variants_sku UNIQUE (sku),
    CONSTRAINT chk_product_variants_inventory CHECK (inventory_count >= 0),
    CONSTRAINT fk_product_variants_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_product_variants_product_id ON product_variants (product_id);
CREATE INDEX IF NOT EXISTS ix_product_variants_size ON product_variants (size);
CREATE INDEX IF NOT EXISTS ix_product_variants_color ON product_variants (color);

DROP TRIGGER IF EXISTS trg_product_variants_updated_at ON product_variants;
CREATE TRIGGER trg_product_variants_updated_at
    BEFORE UPDATE ON product_variants
    FOR EACH ROW EXECUTE FUNCTION _set_updated_at();

-- ============================================================
-- TABLE: carts
-- ============================================================
CREATE TABLE IF NOT EXISTS carts (
    id          UUID         NOT NULL DEFAULT gen_random_uuid(),
    user_id     UUID,
    session_id  VARCHAR(255),
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_carts PRIMARY KEY (id),
    CONSTRAINT fk_carts_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_carts_user_id ON carts (user_id);
CREATE INDEX IF NOT EXISTS ix_carts_session_id ON carts (session_id);

DROP TRIGGER IF EXISTS trg_carts_updated_at ON carts;
CREATE TRIGGER trg_carts_updated_at
    BEFORE UPDATE ON carts
    FOR EACH ROW EXECUTE FUNCTION _set_updated_at();

-- ============================================================
-- TABLE: cart_items
-- ============================================================
CREATE TABLE IF NOT EXISTS cart_items (
    id                  UUID          NOT NULL DEFAULT gen_random_uuid(),
    cart_id             UUID          NOT NULL,
    product_id          UUID          NOT NULL,
    variant_id          UUID,
    quantity            INTEGER       NOT NULL DEFAULT 1,
    unit_price          NUMERIC(10, 2) NOT NULL,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_cart_items PRIMARY KEY (id),
    CONSTRAINT chk_cart_items_quantity CHECK (quantity >= 1),
    CONSTRAINT fk_cart_items_cart
        FOREIGN KEY (cart_id) REFERENCES carts (id) ON DELETE CASCADE,
    CONSTRAINT fk_cart_items_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    CONSTRAINT fk_cart_items_variant
        FOREIGN KEY (variant_id) REFERENCES product_variants (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_cart_items_cart_id ON cart_items (cart_id);

DROP TRIGGER IF EXISTS trg_cart_items_updated_at ON cart_items;
CREATE TRIGGER trg_cart_items_updated_at
    BEFORE UPDATE ON cart_items
    FOR EACH ROW EXECUTE FUNCTION _set_updated_at();

-- ============================================================
-- TABLE: orders
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
    id                     UUID          NOT NULL DEFAULT gen_random_uuid(),
    user_id                UUID,
    order_number           VARCHAR(50),
    guest_email            VARCHAR(255),
    status                 VARCHAR(50)   NOT NULL DEFAULT 'pending',
    payment_status         VARCHAR(50)   NOT NULL DEFAULT 'unpaid',
    subtotal               NUMERIC(12, 2) NOT NULL DEFAULT 0,
    shipping_cost          NUMERIC(12, 2) NOT NULL DEFAULT 0,
    tax                    NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total                  NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total_amount           NUMERIC(10, 2),
    currency               VARCHAR(8)    NOT NULL DEFAULT 'GBP',
    shipping_address       JSONB         NOT NULL DEFAULT '{}',
    shipping_name          VARCHAR(255),
    shipping_address_line1 VARCHAR(255),
    shipping_address_line2 VARCHAR(255),
    shipping_city          VARCHAR(100),
    shipping_county        VARCHAR(100),
    shipping_postcode      VARCHAR(20),
    shipping_country       VARCHAR(100),
    billing_name           VARCHAR(255),
    billing_address_line1  VARCHAR(255),
    billing_address_line2  VARCHAR(255),
    billing_city           VARCHAR(100),
    billing_county         VARCHAR(100),
    billing_postcode       VARCHAR(20),
    billing_country        VARCHAR(100),
    payment_reference      VARCHAR(255),
    stripe_payment_intent_id VARCHAR(255),
    notes                  TEXT,
    created_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_orders PRIMARY KEY (id),
    CONSTRAINT uq_orders_order_number UNIQUE (order_number),
    CONSTRAINT fk_orders_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_orders_user_id ON orders (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_order_number ON orders (order_number) WHERE order_number IS NOT NULL;

DROP TRIGGER IF EXISTS trg_orders_updated_at ON orders;
CREATE TRIGGER trg_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION _set_updated_at();

-- ============================================================
-- TABLE: order_items
-- ============================================================
CREATE TABLE IF NOT EXISTS order_items (
    id           UUID          NOT NULL DEFAULT gen_random_uuid(),
    order_id     UUID          NOT NULL,
    product_id   UUID,
    variant_id   UUID,
    product_name VARCHAR(255)  NOT NULL,
    variant_name VARCHAR(255),
    sku          VARCHAR(100),
    quantity     INTEGER       NOT NULL DEFAULT 1,
    unit_price   NUMERIC(12, 2) NOT NULL,
    line_total   NUMERIC(12, 2) NOT NULL,
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_order_items PRIMARY KEY (id),
    CONSTRAINT chk_order_items_quantity CHECK (quantity >= 1),
    CONSTRAINT fk_order_items_order
        FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
    CONSTRAINT fk_order_items_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE SET NULL,
    CONSTRAINT fk_order_items_variant
        FOREIGN KEY (variant_id) REFERENCES product_variants (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON order_items (order_id);
CREATE INDEX IF NOT EXISTS ix_order_items_product_id ON order_items (product_id);

-- ============================================================
-- TABLE: reviews
-- ============================================================
CREATE TABLE IF NOT EXISTS reviews (
    id                   UUID    NOT NULL DEFAULT gen_random_uuid(),
    product_id           UUID    NOT NULL,
    user_id              UUID    NOT NULL,
    order_id             UUID,
    rating               INTEGER NOT NULL,
    title                VARCHAR(255),
    body                 TEXT,
    is_verified_purchase BOOLEAN NOT NULL DEFAULT FALSE,
    is_approved          BOOLEAN NOT NULL DEFAULT TRUE,
    helpful_votes        INTEGER NOT NULL DEFAULT 0,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_reviews PRIMARY KEY (id),
    CONSTRAINT chk_reviews_rating CHECK (rating BETWEEN 1 AND 5),
    CONSTRAINT fk_reviews_product
        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_user
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_order
        FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_reviews_product_id ON reviews (product_id);
CREATE INDEX IF NOT EXISTS ix_reviews_user_id ON reviews (user_id);

DROP TRIGGER IF EXISTS trg_reviews_updated_at ON reviews;
CREATE TRIGGER trg_reviews_updated_at
    BEFORE UPDATE ON reviews
    FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
