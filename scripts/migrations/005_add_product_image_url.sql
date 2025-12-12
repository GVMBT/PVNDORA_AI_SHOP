-- Migration: Add image_url to products
-- Version: 005
-- Description: Adds image_url field so frontend can use backend-provided images instead of placeholders.

-- 1) Add column
ALTER TABLE products
ADD COLUMN IF NOT EXISTS image_url TEXT;

-- 2) Optional index (not usually needed for simple text url, skipped)

-- 3) Comment
COMMENT ON COLUMN products.image_url IS 'Direct image URL for product card/detail';

-- Verification
-- SELECT id, name, image_url FROM products LIMIT 10;

