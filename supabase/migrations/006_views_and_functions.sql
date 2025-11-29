-- Migration: SQL Views and RPC Functions
-- Critical views for inventory, social proof, and business logic

-- ============================================================
-- 1. Available Stock with Discounts View
-- ============================================================

CREATE OR REPLACE VIEW available_stock_with_discounts AS
SELECT 
    si.id AS stock_item_id,
    si.product_id,
    p.name AS product_name,
    p.price AS original_price,
    p.msrp,
    p.type AS product_type,
    p.warranty_days,
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

-- ============================================================
-- 2. Product Social Proof View
-- ============================================================

CREATE OR REPLACE VIEW product_social_proof AS
SELECT 
    p.id AS product_id,
    p.name AS product_name,
    COALESCE(AVG(r.rating), 0) AS avg_rating,
    COUNT(DISTINCT r.id) AS review_count,
    COUNT(DISTINCT CASE WHEN o.status = 'delivered' THEN o.id END) AS sales_count,
    (
        SELECT json_agg(json_build_object(
            'rating', sub_r.rating,
            'text', sub_r.text,
            'created_at', sub_r.created_at,
            'author', u.first_name
        ) ORDER BY sub_r.created_at DESC)
        FROM (
            SELECT * FROM reviews 
            WHERE product_id = p.id 
            ORDER BY created_at DESC 
            LIMIT 5
        ) sub_r
        LEFT JOIN users u ON sub_r.user_id = u.id
    ) AS recent_reviews
FROM products p
LEFT JOIN reviews r ON p.id = r.product_id
LEFT JOIN orders o ON p.id = o.product_id
WHERE p.status = 'active'
GROUP BY p.id, p.name;

-- ============================================================
-- 3. Reserve Product for Purchase (Instant)
-- ============================================================

CREATE OR REPLACE FUNCTION reserve_product_for_purchase(
    p_product_id UUID,
    p_user_telegram_id BIGINT
)
RETURNS TABLE(
    order_id UUID,
    stock_item_id UUID,
    amount NUMERIC,
    status VARCHAR
) AS $$
DECLARE
    v_stock_item_id UUID;
    v_order_id UUID;
    v_amount NUMERIC;
    v_user_id UUID;
BEGIN
    -- Get user ID
    SELECT id INTO v_user_id 
    FROM users 
    WHERE telegram_id = p_user_telegram_id;
    
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'User not found';
    END IF;
    
    -- Lock and get available stock item
    SELECT 
        si.id,
        ROUND(p.price * (1 - COALESCE(si.discount_percent, 0) / 100), 2)
    INTO v_stock_item_id, v_amount
    FROM stock_items si
    JOIN products p ON si.product_id = p.id
    WHERE 
        si.product_id = p_product_id
        AND si.status = 'available'
        AND (si.expires_at IS NULL OR si.expires_at > NOW())
    ORDER BY si.created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED;
    
    IF v_stock_item_id IS NULL THEN
        RAISE EXCEPTION 'No stock available';
    END IF;
    
    -- Reserve the stock item
    UPDATE stock_items 
    SET status = 'reserved', reserved_at = NOW()
    WHERE id = v_stock_item_id;
    
    -- Create order
    INSERT INTO orders (
        user_id,
        user_telegram_id,
        product_id,
        stock_item_id,
        amount,
        original_price,
        status,
        order_type
    )
    SELECT 
        v_user_id,
        p_user_telegram_id,
        p_product_id,
        v_stock_item_id,
        v_amount,
        p.price,
        'pending',
        'instant'
    FROM products p
    WHERE p.id = p_product_id
    RETURNING id INTO v_order_id;
    
    RETURN QUERY SELECT 
        v_order_id AS order_id,
        v_stock_item_id AS stock_item_id,
        v_amount AS amount,
        'pending'::VARCHAR AS status;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 4. Complete Purchase
-- ============================================================

CREATE OR REPLACE FUNCTION complete_purchase(
    p_order_id UUID
)
RETURNS TABLE(
    success BOOLEAN,
    status VARCHAR,
    content TEXT
) AS $$
DECLARE
    v_order RECORD;
    v_content TEXT;
    v_expires_at TIMESTAMPTZ;
BEGIN
    -- Get order with stock item
    SELECT 
        o.*,
        si.content AS stock_content,
        si.expires_at AS stock_expires,
        p.duration_days,
        p.warranty_days
    INTO v_order
    FROM orders o
    JOIN stock_items si ON o.stock_item_id = si.id
    JOIN products p ON o.product_id = p.id
    WHERE o.id = p_order_id
    FOR UPDATE;
    
    IF v_order IS NULL THEN
        RAISE EXCEPTION 'Order not found';
    END IF;
    
    IF v_order.status NOT IN ('pending', 'prepaid') THEN
        RAISE EXCEPTION 'Invalid order status: %', v_order.status;
    END IF;
    
    -- Calculate expiration
    v_expires_at := COALESCE(
        v_order.stock_expires,
        CASE WHEN v_order.duration_days IS NOT NULL 
            THEN NOW() + (v_order.duration_days || ' days')::INTERVAL 
            ELSE NULL 
        END
    );
    
    -- Update stock item
    UPDATE stock_items 
    SET status = 'sold', sold_at = NOW()
    WHERE id = v_order.stock_item_id;
    
    -- Update order
    UPDATE orders 
    SET 
        status = 'delivered',
        expires_at = v_expires_at,
        warranty_until = NOW() + (v_order.warranty_days || ' days')::INTERVAL,
        updated_at = NOW()
    WHERE id = p_order_id;
    
    v_content := v_order.stock_content;
    
    RETURN QUERY SELECT 
        TRUE AS success,
        'delivered'::VARCHAR AS status,
        v_content AS content;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 5. Increment usage count for promo codes
-- ============================================================

CREATE OR REPLACE FUNCTION use_promo_code(
    p_code VARCHAR
)
RETURNS BOOLEAN AS $$
DECLARE
    v_promo RECORD;
BEGIN
    SELECT * INTO v_promo
    FROM promo_codes
    WHERE code = UPPER(p_code)
    AND is_active = TRUE
    AND (expires_at IS NULL OR expires_at > NOW())
    AND (usage_limit IS NULL OR usage_count < usage_limit)
    FOR UPDATE;
    
    IF v_promo IS NULL THEN
        RETURN FALSE;
    END IF;
    
    UPDATE promo_codes 
    SET usage_count = COALESCE(usage_count, 0) + 1
    WHERE id = v_promo.id;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 6. Get product with availability summary
-- ============================================================

CREATE OR REPLACE FUNCTION get_product_with_availability(
    p_product_id UUID
)
RETURNS TABLE(
    product_id UUID,
    name VARCHAR,
    description TEXT,
    price NUMERIC,
    msrp NUMERIC,
    product_type VARCHAR,
    warranty_days INTEGER,
    duration_days INTEGER,
    available_count BIGINT,
    min_price NUMERIC,
    max_discount NUMERIC,
    avg_rating NUMERIC,
    review_count BIGINT,
    sales_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id AS product_id,
        p.name,
        p.description,
        p.price,
        p.msrp,
        p.type AS product_type,
        p.warranty_days,
        p.duration_days,
        COUNT(si.id) AS available_count,
        MIN(ROUND(p.price * (1 - COALESCE(si.discount_percent, 0) / 100), 2)) AS min_price,
        MAX(si.discount_percent) AS max_discount,
        COALESCE(AVG(r.rating), 0) AS avg_rating,
        COUNT(DISTINCT r.id) AS review_count,
        COUNT(DISTINCT CASE WHEN o.status = 'delivered' THEN o.id END) AS sales_count
    FROM products p
    LEFT JOIN stock_items si ON p.id = si.product_id 
        AND si.status = 'available'
        AND (si.expires_at IS NULL OR si.expires_at > NOW())
    LEFT JOIN reviews r ON p.id = r.product_id
    LEFT JOIN orders o ON p.id = o.product_id
    WHERE p.id = p_product_id
    GROUP BY p.id;
END;
$$ LANGUAGE plpgsql;

