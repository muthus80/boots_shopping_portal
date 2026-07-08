-- =============================================================================
-- seed_data.sql  —  reference / lookup rows
-- Idempotent: every INSERT ends with ON CONFLICT DO NOTHING.
-- Auth-entity rows are NOT here — seed.py inserts them at run-time with a
-- properly hashed password (see .elite/test-credentials.json).
-- =============================================================================

-- ---------------------------------------------------------------------------
-- categories  (reference — no inbound FKs from other reference tables)
-- ---------------------------------------------------------------------------
INSERT INTO categories (id, name, slug, description, image_url, is_active, parent_id, display_order, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000101', 'Ankle Boots',      'ankle-boots',      'Stylish ankle-height boots for everyday wear',    'https://cdn.example.com/cats/ankle-boots.jpg',   true, NULL, 1, '2026-01-01 00:00:00+00', '2026-01-01 00:00:00+00'),
  ('00000000-0000-0000-0000-000000000102', 'Chelsea Boots',    'chelsea-boots',    'Slip-on Chelsea boots with elastic side panels',  'https://cdn.example.com/cats/chelsea-boots.jpg', true, NULL, 2, '2026-01-01 00:00:00+00', '2026-01-01 00:00:00+00'),
  ('00000000-0000-0000-0000-000000000103', 'Knee-High Boots',  'knee-high-boots',  'Elegant knee-high boots for formal occasions',    'https://cdn.example.com/cats/knee-high.jpg',     true, NULL, 3, '2026-01-01 00:00:00+00', '2026-01-01 00:00:00+00'),
  ('00000000-0000-0000-0000-000000000104', 'Work Boots',       'work-boots',       'Durable safety and work boots',                   'https://cdn.example.com/cats/work-boots.jpg',    true, NULL, 4, '2026-01-01 00:00:00+00', '2026-01-01 00:00:00+00'),
  ('00000000-0000-0000-0000-000000000105', 'Winter Boots',     'winter-boots',     'Insulated boots for cold-weather protection',      'https://cdn.example.com/cats/winter-boots.jpg',  true, NULL, 5, '2026-01-01 00:00:00+00', '2026-01-01 00:00:00+00')
ON CONFLICT DO NOTHING;
