-- Fix product_social_proof view: add sales_count alias and recent_reviews
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

COMMENT ON VIEW product_social_proof IS 'Product social proof metrics with reviews and sales count';

-- Add function to automatically set fulfillment_deadline for prepaid orders
-- This will be called by the backend when payment is confirmed for prepaid items
CREATE OR REPLACE FUNCTION set_fulfillment_deadline_for_prepaid_order(
    p_order_id UUID,
    p_hours_from_now INTEGER DEFAULT 48
) RETURNS VOID AS $$
DECLARE
    v_order_status TEXT;
    v_has_prepaid_items BOOLEAN;
BEGIN
    -- Check if order has prepaid items
    SELECT EXISTS(
        SELECT 1 FROM order_items 
        WHERE order_id = p_order_id 
        AND fulfillment_type = 'preorder'
        AND status = 'prepaid'
    ) INTO v_has_prepaid_items;
    
    -- Check order status
    SELECT status INTO v_order_status FROM orders WHERE id = p_order_id;
    
    -- Only set deadline for prepaid/partial orders with preorder items
    IF v_has_prepaid_items AND v_order_status IN ('prepaid', 'partial', 'paid') THEN
        UPDATE orders 
        SET fulfillment_deadline = NOW() + (p_hours_from_now || ' hours')::INTERVAL
        WHERE id = p_order_id
        AND fulfillment_deadline IS NULL; -- Only if not already set
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION set_fulfillment_deadline_for_prepaid_order IS 'Set fulfillment deadline for prepaid orders (called after payment confirmation)';

-- Backfill fulfillment_deadline for existing prepaid/partial orders
-- Set deadline to 48 hours from created_at for orders without deadline
UPDATE orders
SET fulfillment_deadline = created_at + INTERVAL '48 hours'
WHERE status IN ('prepaid', 'partial', 'paid')
AND fulfillment_deadline IS NULL
AND EXISTS (
    SELECT 1 FROM order_items 
    WHERE order_items.order_id = orders.id 
    AND fulfillment_type = 'preorder'
    AND status = 'prepaid'
);
