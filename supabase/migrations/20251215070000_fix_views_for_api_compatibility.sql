-- Fix views to match API expectations
-- This migration fixes column mismatches between database views and API code

-- ============================================================
-- 1. Fix available_stock_with_discounts view
-- ============================================================
-- The API code queries by product_id, but the current view doesn't have this column
DROP VIEW IF EXISTS available_stock_with_discounts CASCADE;

CREATE OR REPLACE VIEW available_stock_with_discounts AS
SELECT 
    si.id AS stock_item_id,
    si.product_id,
    p.name AS product_name,
    p.price AS original_price,
    p.msrp,
    p.type AS product_type,
    CASE WHEN p.warranty_hours IS NOT NULL THEN p.warranty_hours / 24 ELSE NULL END AS warranty_days,
    p.duration_days,
    si.discount_percent,
    ROUND(p.price * (1 - COALESCE(si.discount_percent, 0) / 100), 2) AS final_price,
    ROUND(COALESCE(p.msrp, p.price) - (p.price * (1 - COALESCE(si.discount_percent, 0) / 100)), 2) AS savings,
    si.expires_at,
    si.created_at AS stock_added_at
FROM stock_items si
JOIN products p ON si.product_id = p.id
WHERE 
    si.status = 'available'
    AND p.status = 'active'
    AND (si.expires_at IS NULL OR si.expires_at > NOW());

COMMENT ON VIEW available_stock_with_discounts IS 'Available stock items with discount calculations, includes product_id for API queries';

-- ============================================================
-- 2. Fix product_social_proof view
-- ============================================================
-- The API code expects sales_count, review_count, avg_rating, and recent_reviews
DROP VIEW IF EXISTS product_social_proof CASCADE;

CREATE OR REPLACE VIEW product_social_proof AS
SELECT 
    p.id AS product_id,
    COALESCE(r.review_count, 0) AS review_count,
    COALESCE(r.avg_rating, 0) AS avg_rating,
    COALESCE(o.order_count, 0) AS order_count,
    COALESCE(o.order_count, 0) AS sales_count, -- Alias for frontend compatibility
    COALESCE(r.recent_reviews, '[]'::jsonb) AS recent_reviews
FROM products p
LEFT JOIN (
    SELECT 
        oi.product_id,
        COUNT(DISTINCT rev.id) AS review_count,
        AVG(rev.rating) AS avg_rating,
        jsonb_agg(
            jsonb_build_object(
                'user_name', COALESCE(u.first_name, u.username, 'Anonymous'),
                'rating', rev.rating,
                'text', COALESCE(rev.text, ''),
                'created_at', rev.created_at
            ) 
            ORDER BY rev.created_at DESC
        ) FILTER (WHERE rev.id IS NOT NULL) AS recent_reviews
    FROM order_items oi
    LEFT JOIN reviews rev ON rev.order_id = oi.order_id
    LEFT JOIN orders ord ON ord.id = oi.order_id
    LEFT JOIN users u ON u.id = ord.user_id
    GROUP BY oi.product_id
) r ON r.product_id = p.id
LEFT JOIN (
    SELECT 
        oi.product_id,
        COUNT(DISTINCT oi.order_id) AS order_count
    FROM order_items oi
    JOIN orders ord ON ord.id = oi.order_id
    WHERE ord.status IN ('paid', 'delivered', 'completed', 'partial')
    GROUP BY oi.product_id
) o ON o.product_id = p.id;

COMMENT ON VIEW product_social_proof IS 'Product social proof metrics with reviews and sales count for API compatibility';

