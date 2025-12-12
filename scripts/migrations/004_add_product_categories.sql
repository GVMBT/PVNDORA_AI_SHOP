-- Migration: Add Product Categories
-- Version: 004
-- Date: December 2024
-- Description: Adds categories array for product content filtering (text/video/image/code/audio)

-- 1. Add categories column to products table
ALTER TABLE products
ADD COLUMN IF NOT EXISTS categories TEXT[] DEFAULT '{}'::TEXT[];

-- 2. Create GIN index for efficient array queries
CREATE INDEX IF NOT EXISTS idx_products_categories_gin ON products USING GIN (categories);

-- 3. Populate categories based on existing type field (optional - manual update preferred)
-- You can run this to auto-populate based on type:
-- UPDATE products SET categories = ARRAY['text'] WHERE type IN ('ai', 'dev');
-- UPDATE products SET categories = ARRAY['code'] WHERE type = 'dev';
-- UPDATE products SET categories = ARRAY['image'] WHERE type = 'design';
-- UPDATE products SET categories = ARRAY['audio'] WHERE type = 'music';

-- 4. Comment on column
COMMENT ON COLUMN products.categories IS 'Content categories for filtering: text, video, image, code, audio. Multiple allowed.';

-- Verification query (run after migration)
-- SELECT id, name, categories FROM products;

