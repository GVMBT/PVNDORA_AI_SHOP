-- Delete all test stock items
-- Test items identified by content containing 'test' (case insensitive)
DELETE FROM stock_items
WHERE content ILIKE '%test%' 
   OR content ILIKE '%_test_%'
   OR content ILIKE '%тест%';
