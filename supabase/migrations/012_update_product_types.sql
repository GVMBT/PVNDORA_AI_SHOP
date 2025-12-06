-- Update product types to new AI-centric categories
-- Removes legacy "shared/student/trial/key" typing and introduces:
-- ai, design, dev, music

-- Drop old constraint
ALTER TABLE products DROP CONSTRAINT IF EXISTS products_type_check;

-- Re-map existing products to new categories
UPDATE products SET type = 'music'
WHERE id IN (
  'bce7f8ba-a21c-4d78-8e58-e19432857d31', -- 11Labs Vol 1
  '60b420cf-cf53-4b54-875a-24c6d3a211c2'  -- Eleven Labs (3 month)
);

UPDATE products SET type = 'design'
WHERE id IN (
  '2ac81d43-7a12-4c9a-a091-ba0fb9e6b928'  -- Midjourney V7
);

UPDATE products SET type = 'dev'
WHERE id IN (
  '551aabf7-8d7b-416f-8656-f7d00a8298db'  -- Cursor IDE (7 day)
);

-- Everything else defaults to core AI
UPDATE products
SET type = 'ai'
WHERE type IN ('shared', 'student', 'trial', 'key')
  AND id NOT IN (
    'bce7f8ba-a21c-4d78-8e58-e19432857d31',
    '60b420cf-cf53-4b54-875a-24c6d3a211c2',
    '2ac81d43-7a12-4c9a-a091-ba0fb9e6b928',
    '551aabf7-8d7b-416f-8656-f7d00a8298db'
  );

-- Add new constraint
ALTER TABLE products
  ADD CONSTRAINT products_type_check
  CHECK (type = ANY (ARRAY['ai', 'design', 'dev', 'music']));
