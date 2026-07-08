-- =============================================================================
-- demo_data.sql  —  transactional / demo rows
-- Idempotent: every INSERT ends with ON CONFLICT DO NOTHING.
-- Depends on seed_data.sql having been applied first.
-- Auth-entity (test.user@demo.local) is inserted by seed.py — NOT here.
-- All user_id references below use the UUID seed.py reserves for that user:
--   00000000-0000-0000-0000-000000000001
-- =============================================================================

-- ---------------------------------------------------------------------------
-- products  (FK → categories seeded in seed_data.sql)
-- ---------------------------------------------------------------------------
INSERT INTO products (id, category_id, name, slug, description, short_description, brand, sku, base_price, sale_price, currency, stock_quantity, is_active, is_featured, image_url, images, attributes, average_rating, review_count, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000101',
   'Classic Leather Ankle Boot',   'classic-leather-ankle-boot',
   'Timeless leather ankle boot with a block heel and side zip.',
   'Block-heel leather ankle boot', 'Clarks', 'CLK-ANK-001',
   89.99, 74.99, 'GBP', 50, true, true,
   'https://cdn.example.com/products/clk-ank-001.jpg',
   '["https://cdn.example.com/products/clk-ank-001.jpg","https://cdn.example.com/products/clk-ank-001-b.jpg"]',
   '{"heel_height":"5cm","lining":"leather","sole":"rubber"}',
   4.5, 12, '2026-01-10 09:00:00+00', '2026-01-10 09:00:00+00'),

  ('00000000-0000-0000-0000-000000000202', '00000000-0000-0000-0000-000000000102',
   'Suede Chelsea Boot',            'suede-chelsea-boot',
   'Smooth suede Chelsea boot with elastic gussets and a low stacked heel.',
   'Slip-on suede Chelsea boot', 'Dr. Martens', 'DM-CHE-001',
   119.99, NULL, 'GBP', 35, true, false,
   'https://cdn.example.com/products/dm-che-001.jpg',
   '["https://cdn.example.com/products/dm-che-001.jpg"]',
   '{"heel_height":"3cm","lining":"fabric","sole":"air-cushioned"}',
   4.2, 8, '2026-01-11 10:00:00+00', '2026-01-11 10:00:00+00'),

  ('00000000-0000-0000-0000-000000000203', '00000000-0000-0000-0000-000000000103',
   'Tall Riding Boot',              'tall-riding-boot',
   'Full-length leather riding boot with side zip and low block heel.',
   'Classic leather riding boot', 'Dubarry', 'DUB-KH-001',
   249.00, 199.00, 'GBP', 20, true, true,
   'https://cdn.example.com/products/dub-kh-001.jpg',
   '["https://cdn.example.com/products/dub-kh-001.jpg"]',
   '{"shaft_height":"40cm","heel_height":"4cm","lining":"leather","sole":"rubber"}',
   4.8, 5, '2026-01-12 11:00:00+00', '2026-01-12 11:00:00+00'),

  ('00000000-0000-0000-0000-000000000204', '00000000-0000-0000-0000-000000000104',
   'Steel-Toe Work Boot',           'steel-toe-work-boot',
   'Heavy-duty water-resistant work boot with steel toe cap.',
   'Safety-rated steel-toe boot', 'Timberland Pro', 'TBL-WRK-001',
   149.99, NULL, 'GBP', 80, true, false,
   'https://cdn.example.com/products/tbl-wrk-001.jpg',
   '["https://cdn.example.com/products/tbl-wrk-001.jpg"]',
   '{"toe_cap":"steel","waterproof":true,"sole":"anti-slip composite"}',
   4.6, 22, '2026-01-13 12:00:00+00', '2026-01-13 12:00:00+00'),

  ('00000000-0000-0000-0000-000000000205', '00000000-0000-0000-0000-000000000105',
   'Insulated Snow Boot',           'insulated-snow-boot',
   'Waterproof snow boot with Thinsulate lining rated to -30°C.',
   'Waterproof winter snow boot', 'Sorel', 'SOR-WIN-001',
   129.99, 99.99, 'GBP', 60, true, false,
   'https://cdn.example.com/products/sor-win-001.jpg',
   '["https://cdn.example.com/products/sor-win-001.jpg"]',
   '{"insulation":"Thinsulate 200g","waterproof":true,"sole":"rubber lug"}',
   4.3, 17, '2026-01-14 13:00:00+00', '2026-01-14 13:00:00+00'),

  ('00000000-0000-0000-0000-000000000206', '00000000-0000-0000-0000-000000000101',
   'Patent Ankle Boot',             'patent-ankle-boot',
   'Sleek patent leather ankle boot with pointed toe and stiletto heel.',
   'Patent stiletto ankle boot', 'Kurt Geiger', 'KG-PAT-001',
   95.00, NULL, 'GBP', 30, true, false,
   'https://cdn.example.com/products/kg-pat-001.jpg',
   '["https://cdn.example.com/products/kg-pat-001.jpg"]',
   '{"heel_height":"9cm","toe":"pointed","finish":"patent"}',
   3.9, 6, '2026-01-15 14:00:00+00', '2026-01-15 14:00:00+00'),

  ('00000000-0000-0000-0000-000000000207', '00000000-0000-0000-0000-000000000102',
   'Tan Leather Chelsea',           'tan-leather-chelsea',
   'Premium tan leather Chelsea boot with contrasting elastic panel.',
   'Premium tan Chelsea boot', 'Red Wing', 'RW-CHE-002',
   220.00, 185.00, 'GBP', 25, true, true,
   'https://cdn.example.com/products/rw-che-002.jpg',
   '["https://cdn.example.com/products/rw-che-002.jpg"]',
   '{"heel_height":"3cm","lining":"leather","sole":"leather"}',
   4.7, 9, '2026-01-16 09:00:00+00', '2026-01-16 09:00:00+00')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- product_variants  (FK → products)
-- ---------------------------------------------------------------------------
INSERT INTO product_variants (id, product_id, name, sku, size, color, material, price_modifier, stock_quantity, inventory_count, image_url, is_active, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000301', '00000000-0000-0000-0000-000000000201', 'UK 4 / Black',  'CLK-ANK-001-4-BLK',  '4',  'Black',  'Leather', 0.00, 10, 10, NULL, true, '2026-01-10 09:00:00+00', '2026-01-10 09:00:00+00'),
  ('00000000-0000-0000-0000-000000000302', '00000000-0000-0000-0000-000000000201', 'UK 5 / Black',  'CLK-ANK-001-5-BLK',  '5',  'Black',  'Leather', 0.00, 10, 10, NULL, true, '2026-01-10 09:00:00+00', '2026-01-10 09:00:00+00'),
  ('00000000-0000-0000-0000-000000000303', '00000000-0000-0000-0000-000000000201', 'UK 6 / Black',  'CLK-ANK-001-6-BLK',  '6',  'Black',  'Leather', 0.00, 10, 10, NULL, true, '2026-01-10 09:00:00+00', '2026-01-10 09:00:00+00'),
  ('00000000-0000-0000-0000-000000000304', '00000000-0000-0000-0000-000000000201', 'UK 5 / Tan',    'CLK-ANK-001-5-TAN',  '5',  'Tan',    'Leather', 5.00, 10, 10, NULL, true, '2026-01-10 09:00:00+00', '2026-01-10 09:00:00+00'),
  ('00000000-0000-0000-0000-000000000305', '00000000-0000-0000-0000-000000000202', 'UK 5 / Black',  'DM-CHE-001-5-BLK',   '5',  'Black',  'Suede',   0.00,  8,  8, NULL, true, '2026-01-11 10:00:00+00', '2026-01-11 10:00:00+00'),
  ('00000000-0000-0000-0000-000000000306', '00000000-0000-0000-0000-000000000202', 'UK 6 / Black',  'DM-CHE-001-6-BLK',   '6',  'Black',  'Suede',   0.00,  7,  7, NULL, true, '2026-01-11 10:00:00+00', '2026-01-11 10:00:00+00'),
  ('00000000-0000-0000-0000-000000000307', '00000000-0000-0000-0000-000000000204', 'UK 8 / Brown',  'TBL-WRK-001-8-BRN',  '8',  'Brown',  'Leather', 0.00, 20, 20, NULL, true, '2026-01-13 12:00:00+00', '2026-01-13 12:00:00+00'),
  ('00000000-0000-0000-0000-000000000308', '00000000-0000-0000-0000-000000000205', 'UK 5 / Grey',   'SOR-WIN-001-5-GRY',  '5',  'Grey',   'Rubber',  0.00, 15, 15, NULL, true, '2026-01-14 13:00:00+00', '2026-01-14 13:00:00+00'),
  ('00000000-0000-0000-0000-000000000309', '00000000-0000-0000-0000-000000000205', 'UK 6 / Black',  'SOR-WIN-001-6-BLK',  '6',  'Black',  'Rubber',  0.00, 15, 15, NULL, true, '2026-01-14 13:00:00+00', '2026-01-14 13:00:00+00')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- users  (additional demo users — the E2E test user is inserted by seed.py)
-- ---------------------------------------------------------------------------
-- NOTE: hashed_password values here are NOT real bcrypt hashes.
-- These rows are for demo data only and are not used for auth login tests.
-- seed.py inserts the real test user (test.user@demo.local) with a proper hash.
-- We skip demo user rows that have a password field by inserting placeholder
-- demo users who are not used in auth tests; their passwords are irrelevant.
INSERT INTO users (id, email, hashed_password, full_name, is_active, is_superuser, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000002', 'alice.smith@example.com', '$2b$12$demoplaceholderhashAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', 'Alice Smith', true, false, '2026-01-05 08:00:00+00', '2026-01-05 08:00:00+00'),
  ('00000000-0000-0000-0000-000000000003', 'bob.jones@example.com',   '$2b$12$demoplaceholderhashBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB', 'Bob Jones',   true, false, '2026-01-06 09:00:00+00', '2026-01-06 09:00:00+00')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- orders  (FK → users; user_id = NULL allowed for guest orders)
-- ---------------------------------------------------------------------------
INSERT INTO orders (id, user_id, order_number, guest_email, status, payment_status, subtotal, shipping_cost, tax, total, total_amount, currency, shipping_address, shipping_name, shipping_address_line1, shipping_address_line2, shipping_city, shipping_county, shipping_postcode, shipping_country, billing_name, billing_address_line1, billing_address_line2, billing_city, billing_county, billing_postcode, billing_country, payment_reference, notes, created_at, updated_at) VALUES
  -- Alice's completed order
  ('00000000-0000-0000-0000-000000000401', '00000000-0000-0000-0000-000000000002',
   'ORD-2026-0001', NULL,
   'delivered', 'paid',
   89.99, 4.99, 9.50, 104.48, 104.48, 'GBP',
   '{"name":"Alice Smith","line1":"12 Baker Street","city":"London","postcode":"W1U 3BH","country":"United Kingdom"}',
   'Alice Smith', '12 Baker Street', NULL, 'London', 'Greater London', 'W1U 3BH', 'United Kingdom',
   'Alice Smith', '12 Baker Street', NULL, 'London', 'Greater London', 'W1U 3BH', 'United Kingdom',
   'pi_test_alice_001',
   NULL, '2026-02-01 10:00:00+00', '2026-02-03 14:00:00+00'),

  -- Bob's pending order
  ('00000000-0000-0000-0000-000000000402', '00000000-0000-0000-0000-000000000003',
   'ORD-2026-0002', NULL,
   'confirmed', 'paid',
   249.00, 0.00, 24.90, 273.90, 273.90, 'GBP',
   '{"name":"Bob Jones","line1":"45 High Street","city":"Manchester","postcode":"M1 1AD","country":"United Kingdom"}',
   'Bob Jones', '45 High Street', 'Apt 3', 'Manchester', 'Greater Manchester', 'M1 1AD', 'United Kingdom',
   'Bob Jones', '45 High Street', 'Apt 3', 'Manchester', 'Greater Manchester', 'M1 1AD', 'United Kingdom',
   'pi_test_bob_001',
   'Please leave with neighbour', '2026-02-10 11:00:00+00', '2026-02-10 11:30:00+00'),

  -- Guest checkout order
  ('00000000-0000-0000-0000-000000000403', NULL,
   'ORD-2026-0003', 'guest.shopper@example.com',
   'pending', 'unpaid',
   129.99, 4.99, 13.50, 148.48, 148.48, 'GBP',
   '{"name":"Guest Shopper","line1":"7 Station Road","city":"Bristol","postcode":"BS1 4AD","country":"United Kingdom"}',
   'Guest Shopper', '7 Station Road', NULL, 'Bristol', 'Bristol', 'BS1 4AD', 'United Kingdom',
   'Guest Shopper', '7 Station Road', NULL, 'Bristol', 'Bristol', 'BS1 4AD', 'United Kingdom',
   NULL,
   NULL, '2026-02-15 16:00:00+00', '2026-02-15 16:00:00+00'),

  -- Test user's delivered order (user_id reserved for seed.py test user)
  ('00000000-0000-0000-0000-000000000404', '00000000-0000-0000-0000-000000000001',
   'ORD-2026-0004', NULL,
   'delivered', 'paid',
   119.99, 0.00, 12.00, 131.99, 131.99, 'GBP',
   '{"name":"Test User","line1":"1 Demo Lane","city":"London","postcode":"EC1A 1BB","country":"United Kingdom"}',
   'Test User', '1 Demo Lane', NULL, 'London', 'Greater London', 'EC1A 1BB', 'United Kingdom',
   'Test User', '1 Demo Lane', NULL, 'London', 'Greater London', 'EC1A 1BB', 'United Kingdom',
   'pi_test_user_001',
   NULL, '2026-03-01 10:00:00+00', '2026-03-03 12:00:00+00'),

  -- Test user's processing order
  ('00000000-0000-0000-0000-000000000405', '00000000-0000-0000-0000-000000000001',
   'ORD-2026-0005', NULL,
   'processing', 'paid',
   89.99, 4.99, 9.50, 104.48, 104.48, 'GBP',
   '{"name":"Test User","line1":"1 Demo Lane","city":"London","postcode":"EC1A 1BB","country":"United Kingdom"}',
   'Test User', '1 Demo Lane', NULL, 'London', 'Greater London', 'EC1A 1BB', 'United Kingdom',
   'Test User', '1 Demo Lane', NULL, 'London', 'Greater London', 'EC1A 1BB', 'United Kingdom',
   'pi_test_user_002',
   NULL, '2026-03-10 09:00:00+00', '2026-03-10 09:30:00+00')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- order_items  (FK → orders, products, product_variants)
-- ---------------------------------------------------------------------------
INSERT INTO order_items (id, order_id, product_id, variant_id, product_name, variant_name, sku, quantity, unit_price, line_total, created_at) VALUES
  ('00000000-0000-0000-0000-000000000501', '00000000-0000-0000-0000-000000000401',
   '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000302',
   'Classic Leather Ankle Boot', 'UK 5 / Black', 'CLK-ANK-001-5-BLK', 1, 74.99, 74.99, '2026-02-01 10:00:00+00'),

  ('00000000-0000-0000-0000-000000000502', '00000000-0000-0000-0000-000000000402',
   '00000000-0000-0000-0000-000000000203', NULL,
   'Tall Riding Boot', NULL, 'DUB-KH-001', 1, 249.00, 249.00, '2026-02-10 11:00:00+00'),

  ('00000000-0000-0000-0000-000000000503', '00000000-0000-0000-0000-000000000403',
   '00000000-0000-0000-0000-000000000205', '00000000-0000-0000-0000-000000000308',
   'Insulated Snow Boot', 'UK 5 / Grey', 'SOR-WIN-001-5-GRY', 1, 99.99, 99.99, '2026-02-15 16:00:00+00'),

  ('00000000-0000-0000-0000-000000000504', '00000000-0000-0000-0000-000000000404',
   '00000000-0000-0000-0000-000000000202', '00000000-0000-0000-0000-000000000305',
   'Suede Chelsea Boot', 'UK 5 / Black', 'DM-CHE-001-5-BLK', 1, 119.99, 119.99, '2026-03-01 10:00:00+00'),

  ('00000000-0000-0000-0000-000000000505', '00000000-0000-0000-0000-000000000405',
   '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000302',
   'Classic Leather Ankle Boot', 'UK 5 / Black', 'CLK-ANK-001-5-BLK', 1, 74.99, 74.99, '2026-03-10 09:00:00+00'),

  ('00000000-0000-0000-0000-000000000506', '00000000-0000-0000-0000-000000000401',
   '00000000-0000-0000-0000-000000000205', '00000000-0000-0000-0000-000000000309',
   'Insulated Snow Boot', 'UK 6 / Black', 'SOR-WIN-001-6-BLK', 1, 99.99, 99.99, '2026-02-01 10:00:00+00')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- carts  (FK → users; may also be guest carts with session_id)
-- ---------------------------------------------------------------------------
INSERT INTO carts (id, user_id, session_id, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000601', '00000000-0000-0000-0000-000000000001', NULL,                  '2026-04-01 10:00:00+00', '2026-04-01 10:30:00+00'),
  ('00000000-0000-0000-0000-000000000602', '00000000-0000-0000-0000-000000000002', NULL,                  '2026-04-02 11:00:00+00', '2026-04-02 11:15:00+00'),
  ('00000000-0000-0000-0000-000000000603', NULL,                                   'guest-sess-abc12345', '2026-04-03 14:00:00+00', '2026-04-03 14:20:00+00')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- cart_items  (FK → carts, products, product_variants)
-- ---------------------------------------------------------------------------
INSERT INTO cart_items (id, cart_id, product_id, variant_id, quantity, unit_price, created_at, updated_at) VALUES
  -- Test user's cart
  ('00000000-0000-0000-0000-000000000701', '00000000-0000-0000-0000-000000000601',
   '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000302',
   2, 74.99, '2026-04-01 10:15:00+00', '2026-04-01 10:30:00+00'),

  ('00000000-0000-0000-0000-000000000702', '00000000-0000-0000-0000-000000000601',
   '00000000-0000-0000-0000-000000000207', NULL,
   1, 185.00, '2026-04-01 10:20:00+00', '2026-04-01 10:30:00+00'),

  -- Alice's cart
  ('00000000-0000-0000-0000-000000000703', '00000000-0000-0000-0000-000000000602',
   '00000000-0000-0000-0000-000000000204', '00000000-0000-0000-0000-000000000307',
   1, 149.99, '2026-04-02 11:05:00+00', '2026-04-02 11:15:00+00'),

  -- Guest cart
  ('00000000-0000-0000-0000-000000000704', '00000000-0000-0000-0000-000000000603',
   '00000000-0000-0000-0000-000000000205', '00000000-0000-0000-0000-000000000308',
   1, 99.99, '2026-04-03 14:10:00+00', '2026-04-03 14:20:00+00')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------------------------
-- reviews  (FK → products, users, orders; UNIQUE(user_id, product_id))
-- ---------------------------------------------------------------------------
INSERT INTO reviews (id, product_id, user_id, order_id, rating, title, body, is_verified_purchase, is_approved, helpful_votes, created_at, updated_at) VALUES
  -- Alice reviews the Classic Ankle Boot (verified, from ORD-0001)
  ('00000000-0000-0000-0000-000000000801',
   '00000000-0000-0000-0000-000000000201',
   '00000000-0000-0000-0000-000000000002',
   '00000000-0000-0000-0000-000000000401',
   5, 'Absolutely love these!', 'Incredibly comfortable from day one. Great quality leather and the heel height is perfect.', true, true, 7, '2026-02-05 12:00:00+00', '2026-02-05 12:00:00+00'),

  -- Alice reviews the Snow Boot (unverified)
  ('00000000-0000-0000-0000-000000000802',
   '00000000-0000-0000-0000-000000000205',
   '00000000-0000-0000-0000-000000000002',
   NULL,
   4, 'Warm and waterproof', 'Kept my feet dry and warm all winter. A little stiff at first but broken in nicely.', false, true, 3, '2026-02-20 09:00:00+00', '2026-02-20 09:00:00+00'),

  -- Bob reviews the Tall Riding Boot (verified, from ORD-0002)
  ('00000000-0000-0000-0000-000000000803',
   '00000000-0000-0000-0000-000000000203',
   '00000000-0000-0000-0000-000000000003',
   '00000000-0000-0000-0000-000000000402',
   5, 'Premium quality', 'These are the finest riding boots I have owned. Supple leather and excellent construction.', true, true, 4, '2026-02-12 15:00:00+00', '2026-02-12 15:00:00+00'),

  -- Test user reviews the Chelsea Boot (verified, from ORD-0004)
  ('00000000-0000-0000-0000-000000000804',
   '00000000-0000-0000-0000-000000000202',
   '00000000-0000-0000-0000-000000000001',
   '00000000-0000-0000-0000-000000000404',
   4, 'Great everyday boot', 'Slip on and off easily, look great with jeans or smart trousers. Very pleased.', true, true, 2, '2026-03-05 10:00:00+00', '2026-03-05 10:00:00+00'),

  -- Test user reviews the Work Boot (unverified)
  ('00000000-0000-0000-0000-000000000805',
   '00000000-0000-0000-0000-000000000204',
   '00000000-0000-0000-0000-000000000001',
   NULL,
   4, 'Solid safety boot', 'Very sturdy. Takes a week to break in but after that very comfortable for long shifts.', false, true, 1, '2026-03-15 11:00:00+00', '2026-03-15 11:00:00+00')
ON CONFLICT DO NOTHING;
