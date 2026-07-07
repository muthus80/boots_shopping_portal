-- =============================================================================
-- seed_data.sql  –  Reference / lookup data for the boots-shopping-app
-- Every statement uses ON CONFLICT DO NOTHING so re-runs are idempotent.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- categories  (reference table — parent rows first, children second)
-- ---------------------------------------------------------------------------
INSERT INTO categories (id, name, slug, description, image_url, is_active, parent_id, display_order, created_at, updated_at) VALUES
  ('00000000-0000-0000-0000-000000000101', 'Boots',             'boots',             'All boot styles',             NULL, true,  NULL,                                       1, '2026-01-01 00:00:00+00', '2026-01-01 00:00:00+00'),
  ('00000000-0000-0000-0000-000000000102', 'Ankle Boots',       'ankle-boots',       'Ankle-length boot styles',    NULL, true,  '00000000-0000-0000-0000-000000000101', 2, '2026-01-01 00:00:00+00', '2026-01-01 00:00:00+00'),
  ('00000000-0000-0000-0000-000000000103', 'Knee-High Boots',   'knee-high-boots',   'Knee-high boot styles',       NULL, true,  '00000000-0000-0000-0000-000000000101', 3, '2026-01-01 00:00:00+00', '2026-01-01 00:00:00+00'),
  ('00000000-0000-0000-0000-000000000104', 'Chelsea Boots',     'chelsea-boots',     'Elasticated Chelsea boots',   NULL, true,  '00000000-0000-0000-0000-000000000101', 4, '2026-01-01 00:00:00+00', '2026-01-01 00:00:00+00'),
  ('00000000-0000-0000-0000-000000000105', 'Work & Safety Boots','work-safety-boots','Heavy-duty footwear',         NULL, true,  '00000000-0000-0000-0000-000000000101', 5, '2026-01-01 00:00:00+00', '2026-01-01 00:00:00+00')
ON CONFLICT DO NOTHING;
