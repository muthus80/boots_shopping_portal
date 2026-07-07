-- =============================================================================
-- demo_data.sql  –  Transactional demo rows for the boots-shopping-app
-- Depends on: seed_data.sql (categories already inserted)
-- Auth-entity user row is inserted by seed.py (not here) to keep the hash live.
-- Every statement uses ON CONFLICT DO NOTHING so re-runs are idempotent.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- products  (FK → categories)
-- ---------------------------------------------------------------------------
INSERT INTO products (id, category_id, name, slug, description, short_description, brand, sku, base_price, sale_price, currency, stock_quantity, is_active, is_featured, image_url, images, attributes, average_rating, review_count, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000201',
   '00000000-0000-0000-0000-000000000102',
   'Classic Leather Ankle Boot', 'classic-leather-ankle-boot',
   'Timeless leather ankle boot with side zip and block heel.',
   'Side-zip leather ankle boot.',
   'Heritage Co', 'SKU-AB-001', 89.99, 74.99, 'GBP', 50, true, true,
   'https://cdn.example.com/boots/ab-001.jpg',
   '[]', '{}', 4.5, 12,
   '2026-01-10 09:00:00+00', '2026-01-10 09:00:00+00'),

  ('00000000-0000-0000-0000-000000000202',
   '00000000-0000-0000-0000-000000000103',
   'Suede Knee-High Boot', 'suede-knee-high-boot',
   'Soft suede knee-high boot with hidden elastic side panels.',
   'Suede knee-high with elastic panels.',
   'Eleganza', 'SKU-KH-001', 129.99, NULL, 'GBP', 30, true, false,
   'https://cdn.example.com/boots/kh-001.jpg',
   '[]', '{}', 4.2, 7,
   '2026-01-11 10:00:00+00', '2026-01-11 10:00:00+00'),

  ('00000000-0000-0000-0000-000000000203',
   '00000000-0000-0000-0000-000000000104',
   'Chelsea Boot Tan', 'chelsea-boot-tan',
   'Classic pull-on Chelsea boot in smooth tan leather.',
   'Smooth tan leather Chelsea boot.',
   'Heritage Co', 'SKU-CH-001', 99.99, 84.99, 'GBP', 60, true, true,
   'https://cdn.example.com/boots/ch-001.jpg',
   '[]', '{}', 4.7, 23,
   '2026-01-12 11:00:00+00', '2026-01-12 11:00:00+00'),

  ('00000000-0000-0000-0000-000000000204',
   '00000000-0000-0000-0000-000000000105',
   'Steel-Toe Safety Boot', 'steel-toe-safety-boot',
   'Waterproof safety boot with steel toe cap and anti-slip sole.',
   'Steel toe, waterproof, anti-slip.',
   'Titan Works', 'SKU-WB-001', 74.99, NULL, 'GBP', 45, true, false,
   'https://cdn.example.com/boots/wb-001.jpg',
   '[]', '{}', 4.0, 5,
   '2026-01-13 12:00:00+00', '2026-01-13 12:00:00+00'),

  ('00000000-0000-0000-0000-000000000205',
   '00000000-0000-0000-0000-000000000102',
   'Patent Block-Heel Ankle Boot', 'patent-block-heel-ankle-boot',
   'Eye-catching patent finish ankle boot with chunky block heel.',
   'Patent ankle boot, block heel.',
   'Eleganza', 'SKU-AB-002', 109.99, 89.99, 'GBP', 25, true, true,
   'https://cdn.example.com/boots/ab-002.jpg',
   '[]', '{}', 4.3, 9,
   '2026-01-14 13:00:00+00', '2026-01-14 13:00:00+00')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- product_variants  (FK → products)
-- ---------------------------------------------------------------------------
INSERT INTO product_variants (id, product_id, name, sku, size, color, material, price_modifier, stock_quantity, inventory_count, image_url, is_active, created_at, updated_at) VALUES
  -- Classic Leather Ankle Boot variants
  ('00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-000000000201', 'UK 5 / Black', 'SKU-AB-001-5-BLK', '5', 'Black',  'Leather', 0.00, 10, 10, NULL, true, '2026-01-10 09:00:00+00', '2026-01-10 09:00:00+00'),
  ('00000000-0000-0000-0000-000000000302', '00000000-0000-0000-0000-000000000201', 'UK 6 / Black', 'SKU-AB-001-6-BLK', '6', 'Black',  'Leather', 0.00, 15, 15, NULL, true, '2026-01-10 09:00:00+00', '2026-01-10 09:00:00+00'),
  ('00000000-0000-0000-0000-000000000303', '00000000-0000-0000-0000-000000000201', 'UK 7 / Tan',   'SKU-AB-001-7-TAN', '7', 'Tan',    'Leather', 5.00, 10, 10, NULL, true, '2026-01-10 09:00:00+00', '2026-01-10 09:00:00+00'),
  -- Chelsea Boot Tan variants
  ('00000000-0000-0000-0000-000000000304', '00000000-0000-0000-0000-000000000203', 'UK 5 / Tan',   'SKU-CH-001-5-TAN', '5', 'Tan',    'Leather', 0.00, 20, 20, NULL, true, '2026-01-12 11:00:00+00', '2026-01-12 11:00:00+00'),
  ('00000000-0000-0000-0000-000000000305', '00000000-0000-0000-0000-000000000203', 'UK 6 / Tan',   'SKU-CH-001-6-TAN', '6', 'Tan',    'Leather', 0.00, 25, 25, NULL, true, '2026-01-12 11:00:00+00', '2026-01-12 11:00:00+00'),
  ('00000000-0000-0000-0000-000000000306', '00000000-0000-0000-0000-000000000203', 'UK 7 / Black', 'SKU-CH-001-7-BLK', '7', 'Black',  'Leather', 0.00, 15, 15, NULL, true, '2026-01-12 11:00:00+00', '2026-01-12 11:00:00+00'),
  -- Safety Boot variants
  ('00000000-0000-0000-0000-000000000307', '00000000-0000-0000-0000-000000000204', 'UK 8 / Brown', 'SKU-WB-001-8-BRN', '8', 'Brown',  'Leather', 0.00, 15, 15, NULL, true, '2026-01-13 12:00:00+00', '2026-01-13 12:00:00+00'),
  ('00000000-0000-0000-0000-000000000308', '00000000-0000-0000-0000-000000000204', 'UK 9 / Brown', 'SKU-WB-001-9-BRN', '9', 'Brown',  'Leather', 0.00, 15, 15, NULL, true, '2026-01-13 12:00:00+00', '2026-01-13 12:00:00+00'),
  -- Patent Block-Heel variants
  ('00000000-0000-0000-0000-000000000309', '00000000-0000-0000-0000-000000000205', 'UK 4 / Red',   'SKU-AB-002-4-RED', '4', 'Red',    'Patent', 0.00, 8,  8,  NULL, true, '2026-01-14 13:00:00+00', '2026-01-14 13:00:00+00'),
  ('00000000-0000-0000-0000-000000000310', '00000000-0000-0000-0000-000000000205', 'UK 5 / Black', 'SKU-AB-002-5-BLK', '5', 'Black',  'Patent', 0.00, 10, 10, NULL, true, '2026-01-14 13:00:00+00', '2026-01-14 13:00:00+00')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- users  (demo users)
-- NOTE: hashed_password is NOT emitted here as a literal hash value.
--       All user rows (test login user + demo users alice/bob/carol) are
--       inserted by seed.py, which calls app.core.security.hash_password()
--       at seed-time to produce valid bcrypt hashes from known plaintexts.
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- carts  (FK → users; also one guest/anonymous cart)
-- ---------------------------------------------------------------------------
INSERT INTO carts (id, user_id, session_id, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000501', '00000000-0000-0000-0000-000000000401', NULL,            '2026-02-01 10:00:00+00', '2026-02-01 10:05:00+00'),
  ('00000000-0000-0000-0000-000000000502', '00000000-0000-0000-0000-000000000402', NULL,            '2026-02-02 11:00:00+00', '2026-02-02 11:10:00+00'),
  ('00000000-0000-0000-0000-000000000503', NULL,                                   'guest-sess-abc', '2026-02-03 12:00:00+00', '2026-02-03 12:05:00+00')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- cart_items  (FK → carts, products, product_variants)
-- ---------------------------------------------------------------------------
INSERT INTO cart_items (id, cart_id, product_id, variant_id, quantity, unit_price, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000601',
   '00000000-0000-0000-0000-000000000501',
   '00000000-0000-0000-0000-000000000201',
   '00000000-0000-0000-0000-000000000301',
   1, 74.99,
   '2026-02-01 10:05:00+00', '2026-02-01 10:05:00+00'),

  ('00000000-0000-0000-0000-000000000602',
   '00000000-0000-0000-0000-000000000501',
   '00000000-0000-0000-0000-000000000203',
   '00000000-0000-0000-0000-000000000304',
   2, 84.99,
   '2026-02-01 10:06:00+00', '2026-02-01 10:06:00+00'),

  ('00000000-0000-0000-0000-000000000603',
   '00000000-0000-0000-0000-000000000502',
   '00000000-0000-0000-0000-000000000205',
   '00000000-0000-0000-0000-000000000310',
   1, 89.99,
   '2026-02-02 11:05:00+00', '2026-02-02 11:05:00+00'),

  ('00000000-0000-0000-0000-000000000604',
   '00000000-0000-0000-0000-000000000503',
   '00000000-0000-0000-0000-000000000204',
   '00000000-0000-0000-0000-000000000307',
   1, 74.99,
   '2026-02-03 12:05:00+00', '2026-02-03 12:05:00+00')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- orders  (FK → users — alice and bob each have one delivered order)
-- ---------------------------------------------------------------------------
INSERT INTO orders (id, user_id, order_number, guest_email, status, payment_status, subtotal, shipping_cost, tax, total, total_amount, currency, shipping_address, shipping_name, shipping_address_line1, shipping_city, shipping_postcode, shipping_country, billing_name, billing_address_line1, billing_city, billing_postcode, billing_country, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000701',
   '00000000-0000-0000-0000-000000000401',
   'ORD-20260201-0001', NULL,
   'delivered', 'paid',
   159.98, 4.99, 19.20, 184.17, 184.17, 'GBP',
   '{"line1":"10 Baker Street","city":"London","postcode":"W1U 3BJ","country":"GB"}',
   'Alice Johnson', '10 Baker Street', 'London', 'W1U 3BJ', 'GB',
   'Alice Johnson', '10 Baker Street', 'London', 'W1U 3BJ', 'GB',
   '2026-02-10 14:00:00+00', '2026-02-15 11:00:00+00'),

  ('00000000-0000-0000-0000-000000000702',
   '00000000-0000-0000-0000-000000000402',
   'ORD-20260202-0002', NULL,
   'processing', 'paid',
   89.99, 4.99, 10.80, 105.78, 105.78, 'GBP',
   '{"line1":"25 High Street","city":"Manchester","postcode":"M1 1AE","country":"GB"}',
   'Bob Smith', '25 High Street', 'Manchester', 'M1 1AE', 'GB',
   'Bob Smith', '25 High Street', 'Manchester', 'M1 1AE', 'GB',
   '2026-02-12 09:00:00+00', '2026-02-12 12:00:00+00'),

  ('00000000-0000-0000-0000-000000000703',
   '00000000-0000-0000-0000-000000000401',
   'ORD-20260220-0003', NULL,
   'pending', 'unpaid',
   74.99, 0.00, 9.00, 83.99, 83.99, 'GBP',
   '{"line1":"10 Baker Street","city":"London","postcode":"W1U 3BJ","country":"GB"}',
   'Alice Johnson', '10 Baker Street', 'London', 'W1U 3BJ', 'GB',
   'Alice Johnson', '10 Baker Street', 'London', 'W1U 3BJ', 'GB',
   '2026-02-20 16:00:00+00', '2026-02-20 16:00:00+00'),

  ('00000000-0000-0000-0000-000000000704',
   NULL,
   'ORD-20260222-0004', 'guest.buyer@demo.local',
   'confirmed', 'paid',
   109.99, 4.99, 13.20, 128.18, 128.18, 'GBP',
   '{"line1":"5 Elm Road","city":"Birmingham","postcode":"B1 1BB","country":"GB"}',
   'Guest Buyer', '5 Elm Road', 'Birmingham', 'B1 1BB', 'GB',
   'Guest Buyer', '5 Elm Road', 'Birmingham', 'B1 1BB', 'GB',
   '2026-02-22 14:00:00+00', '2026-02-22 15:00:00+00'),

  ('00000000-0000-0000-0000-000000000705',
   '00000000-0000-0000-0000-000000000403',
   'ORD-20260301-0005', NULL,
   'shipped', 'paid',
   129.99, 4.99, 15.60, 150.58, 150.58, 'GBP',
   '{"line1":"3 Maple Close","city":"Edinburgh","postcode":"EH1 1AA","country":"GB"}',
   'Carol White', '3 Maple Close', 'Edinburgh', 'EH1 1AA', 'GB',
   'Carol White', '3 Maple Close', 'Edinburgh', 'EH1 1AA', 'GB',
   '2026-03-01 10:00:00+00', '2026-03-03 14:00:00+00')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- order_items  (FK → orders, products, product_variants)
-- ---------------------------------------------------------------------------
INSERT INTO order_items (id, order_id, product_id, variant_id, product_name, variant_name, sku, quantity, unit_price, line_total, created_at) VALUES
  -- ORD-0001 (Alice — two items)
  ('00000000-0000-0000-0000-000000000801',
   '00000000-0000-0000-0000-000000000701',
   '00000000-0000-0000-0000-000000000201',
   '00000000-0000-0000-0000-000000000301',
   'Classic Leather Ankle Boot', 'UK 5 / Black', 'SKU-AB-001-5-BLK',
   1, 74.99, 74.99,
   '2026-02-10 14:00:00+00'),

  ('00000000-0000-0000-0000-000000000802',
   '00000000-0000-0000-0000-000000000701',
   '00000000-0000-0000-0000-000000000203',
   '00000000-0000-0000-0000-000000000304',
   'Chelsea Boot Tan', 'UK 5 / Tan', 'SKU-CH-001-5-TAN',
   1, 84.99, 84.99,
   '2026-02-10 14:00:00+00'),

  -- ORD-0002 (Bob — one item)
  ('00000000-0000-0000-0000-000000000803',
   '00000000-0000-0000-0000-000000000702',
   '00000000-0000-0000-0000-000000000201',
   '00000000-0000-0000-0000-000000000302',
   'Classic Leather Ankle Boot', 'UK 6 / Black', 'SKU-AB-001-6-BLK',
   1, 89.99, 89.99,
   '2026-02-12 09:00:00+00'),

  -- ORD-0003 (Alice — one item, pending)
  ('00000000-0000-0000-0000-000000000804',
   '00000000-0000-0000-0000-000000000703',
   '00000000-0000-0000-0000-000000000204',
   '00000000-0000-0000-0000-000000000307',
   'Steel-Toe Safety Boot', 'UK 8 / Brown', 'SKU-WB-001-8-BRN',
   1, 74.99, 74.99,
   '2026-02-20 16:00:00+00'),

  -- ORD-0004 (guest — one item)
  ('00000000-0000-0000-0000-000000000805',
   '00000000-0000-0000-0000-000000000704',
   '00000000-0000-0000-0000-000000000205',
   '00000000-0000-0000-0000-000000000309',
   'Patent Block-Heel Ankle Boot', 'UK 4 / Red', 'SKU-AB-002-4-RED',
   1, 109.99, 109.99,
   '2026-02-22 14:00:00+00'),

  -- ORD-0005 (Carol — one item)
  ('00000000-0000-0000-0000-000000000806',
   '00000000-0000-0000-0000-000000000705',
   '00000000-0000-0000-0000-000000000202',
   NULL,
   'Suede Knee-High Boot', NULL, 'SKU-KH-001',
   1, 129.99, 129.99,
   '2026-03-01 10:00:00+00')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- reviews  (FK → products, users, orders)
-- Only inserted for delivered/shipped orders so is_verified_purchase = true.
-- ---------------------------------------------------------------------------
INSERT INTO reviews (id, product_id, user_id, order_id, rating, title, body, is_verified_purchase, is_approved, helpful_votes, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000901',
   '00000000-0000-0000-0000-000000000201',
   '00000000-0000-0000-0000-000000000401',
   '00000000-0000-0000-0000-000000000701',
   5, 'Beautifully crafted!',
   'These ankle boots are exactly as described — supple leather, easy zip and a heel height that is both stylish and comfortable. Highly recommend.',
   true, true, 4,
   '2026-02-18 10:00:00+00', '2026-02-18 10:00:00+00'),

  ('00000000-0000-0000-0000-000000000902',
   '00000000-0000-0000-0000-000000000203',
   '00000000-0000-0000-0000-000000000401',
   '00000000-0000-0000-0000-000000000701',
   4, 'Great everyday boot',
   'Comfortable Chelsea boot, looks great with both jeans and a dress. Sized true to UK, delivery was fast.',
   true, true, 2,
   '2026-02-19 11:00:00+00', '2026-02-19 11:00:00+00'),

  ('00000000-0000-0000-0000-000000000903',
   '00000000-0000-0000-0000-000000000202',
   '00000000-0000-0000-0000-000000000403',
   '00000000-0000-0000-0000-000000000705',
   4, 'Very elegant knee-high',
   'Gorgeous suede finish and fits perfectly. Slightly narrow calf but manageable. Would buy again.',
   true, true, 1,
   '2026-03-08 09:00:00+00', '2026-03-08 09:00:00+00'),

  ('00000000-0000-0000-0000-000000000904',
   '00000000-0000-0000-0000-000000000201',
   '00000000-0000-0000-0000-000000000402',
   '00000000-0000-0000-0000-000000000702',
   5, 'Best boots I have owned',
   'Excellent quality leather and the block heel makes them very stable. Perfect for a full day at the office.',
   true, true, 6,
   '2026-02-20 14:00:00+00', '2026-02-20 14:00:00+00'),

  ('00000000-0000-0000-0000-000000000905',
   '00000000-0000-0000-0000-000000000205',
   '00000000-0000-0000-0000-000000000403',
   NULL,
   3, 'Nice but runs small',
   'Loved the patent finish and colour. Unfortunately runs about half a size small — order up.',
   false, true, 0,
   '2026-03-10 15:00:00+00', '2026-03-10 15:00:00+00')
ON CONFLICT DO NOTHING;
