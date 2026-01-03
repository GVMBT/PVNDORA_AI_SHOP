-- Migration: Discount Funnel Schema
-- Description: Adds tables and columns for discount channel and insurance system
-- Date: 2026-01-03

-- ============================================
-- 1. Extend products table
-- ============================================

ALTER TABLE products ADD COLUMN IF NOT EXISTS discount_price NUMERIC(10,2);
COMMENT ON COLUMN products.discount_price IS 'Price in USD for discount channel (lower than main price)';

-- ============================================
-- 2. Extend orders table
-- ============================================

ALTER TABLE orders ADD COLUMN IF NOT EXISTS source_channel TEXT DEFAULT 'premium';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'orders_source_channel_check'
    ) THEN
        ALTER TABLE orders ADD CONSTRAINT orders_source_channel_check 
            CHECK (source_channel IN ('discount', 'premium', 'migrated'));
    END IF;
END $$;

COMMENT ON COLUMN orders.source_channel IS 'Order origin: discount bot, premium PVNDORA, or migrated user';

-- ============================================
-- 3. Extend users table
-- ============================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS discount_tier_source BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ;

COMMENT ON COLUMN users.discount_tier_source IS 'TRUE if user first interacted via discount bot';
COMMENT ON COLUMN users.terms_accepted IS 'Whether user accepted terms in discount bot';
COMMENT ON COLUMN users.terms_accepted_at IS 'When user accepted terms';

-- ============================================
-- 4. Extend promo_codes table
-- ============================================

ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS target_user_id UUID REFERENCES users(id);
ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS is_personal BOOLEAN DEFAULT FALSE;
ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS source_trigger TEXT;

COMMENT ON COLUMN promo_codes.target_user_id IS 'User this personal promo code was created for (NULL = public)';
COMMENT ON COLUMN promo_codes.is_personal IS 'TRUE if this is a personal one-time promo code';
COMMENT ON COLUMN promo_codes.source_trigger IS 'Event that triggered creation: issue_no_insurance, loyal_3_purchases, etc.';

CREATE INDEX IF NOT EXISTS idx_promo_codes_target_user ON promo_codes(target_user_id) 
WHERE target_user_id IS NOT NULL;

-- ============================================
-- 5. New table: insurance_options
-- ============================================

CREATE TABLE IF NOT EXISTS insurance_options (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    duration_days INT NOT NULL CHECK (duration_days > 0),
    price_percent NUMERIC(5,2) NOT NULL CHECK (price_percent >= 50),
    replacements_count INT NOT NULL DEFAULT 1 CHECK (replacements_count > 0),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE insurance_options IS 'Insurance options for discount channel products';
COMMENT ON COLUMN insurance_options.duration_days IS 'Insurance validity period in days';
COMMENT ON COLUMN insurance_options.price_percent IS 'Insurance price as percentage of product discount_price (min 50%)';
COMMENT ON COLUMN insurance_options.replacements_count IS 'Number of replacements allowed during insurance period';

CREATE INDEX IF NOT EXISTS idx_insurance_options_product ON insurance_options(product_id) 
WHERE is_active = TRUE;

ALTER TABLE insurance_options ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "insurance_options_select_all" ON insurance_options;
CREATE POLICY "insurance_options_select_all" ON insurance_options FOR SELECT USING (true);

-- ============================================
-- 6. Extend order_items table
-- ============================================

ALTER TABLE order_items ADD COLUMN IF NOT EXISTS insurance_id UUID REFERENCES insurance_options(id);
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS insurance_expires_at TIMESTAMPTZ;

COMMENT ON COLUMN order_items.insurance_id IS 'Insurance option purchased with this item';
COMMENT ON COLUMN order_items.insurance_expires_at IS 'When insurance expires (calculated from delivery + duration_days)';

-- ============================================
-- 7. New table: insurance_replacements
-- ============================================

CREATE TABLE IF NOT EXISTS insurance_replacements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_item_id UUID NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
    insurance_id UUID NOT NULL REFERENCES insurance_options(id),
    old_stock_item_id UUID REFERENCES stock_items(id),
    new_stock_item_id UUID REFERENCES stock_items(id),
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'auto_approved')),
    rejection_reason TEXT,
    processed_by UUID REFERENCES users(id),
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE insurance_replacements IS 'Tracks replacement requests under insurance';
COMMENT ON COLUMN insurance_replacements.status IS 'pending=awaiting review, approved=replacement issued, rejected=denied, auto_approved=passed abuse check';
COMMENT ON COLUMN insurance_replacements.processed_by IS 'Admin who processed the request (NULL for auto)';

CREATE INDEX IF NOT EXISTS idx_replacements_order_item ON insurance_replacements(order_item_id);
CREATE INDEX IF NOT EXISTS idx_replacements_status ON insurance_replacements(status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_replacements_created ON insurance_replacements(created_at DESC);

ALTER TABLE insurance_replacements ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "replacements_select_all" ON insurance_replacements;
CREATE POLICY "replacements_select_all" ON insurance_replacements FOR SELECT USING (true);

-- ============================================
-- 8. New table: user_restrictions
-- ============================================

CREATE TABLE IF NOT EXISTS user_restrictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    restriction_type TEXT NOT NULL CHECK (restriction_type IN (
        'replacement_blocked',
        'insurance_blocked',
        'purchase_blocked'
    )),
    reason TEXT,
    expires_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE user_restrictions IS 'User restrictions for abuse prevention';
COMMENT ON COLUMN user_restrictions.expires_at IS 'NULL means permanent restriction';

CREATE INDEX IF NOT EXISTS idx_user_restrictions_user ON user_restrictions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_restrictions_type ON user_restrictions(restriction_type);

ALTER TABLE user_restrictions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "restrictions_select_all" ON user_restrictions;
CREATE POLICY "restrictions_select_all" ON user_restrictions FOR SELECT USING (true);

-- ============================================
-- 9. View: low_stock_alert
-- ============================================

CREATE OR REPLACE VIEW low_stock_alert AS
SELECT 
    p.id,
    p.name,
    p.discount_price,
    COUNT(si.id) as available_count,
    CASE 
        WHEN COUNT(si.id) = 0 THEN 'prepaid_only'
        WHEN COUNT(si.id) < 3 THEN 'critical'
        WHEN COUNT(si.id) < 5 THEN 'low'
        ELSE 'ok'
    END as stock_status
FROM products p
LEFT JOIN stock_items si ON si.product_id = p.id 
    AND si.status = 'available' 
    AND si.sold_at IS NULL
WHERE p.status = 'active'
GROUP BY p.id, p.name, p.discount_price
HAVING COUNT(si.id) < 5
ORDER BY COUNT(si.id) ASC;

COMMENT ON VIEW low_stock_alert IS 'Products with low stock (<5) for admin alerts';

-- ============================================
-- 10. View: discount_migration_stats
-- ============================================

CREATE OR REPLACE VIEW discount_migration_stats AS
SELECT 
    COUNT(DISTINCT CASE WHEN discount_tier_source THEN id END) AS total_discount_users,
    COUNT(DISTINCT CASE 
        WHEN discount_tier_source 
        AND EXISTS (
            SELECT 1 FROM orders o 
            WHERE o.user_id = users.id 
            AND o.source_channel = 'premium'
        ) 
        THEN id 
    END) AS migrated_users,
    ROUND(
        COUNT(DISTINCT CASE 
            WHEN discount_tier_source 
            AND EXISTS (
                SELECT 1 FROM orders o 
                WHERE o.user_id = users.id 
                AND o.source_channel = 'premium'
            ) 
            THEN id 
        END)::numeric / 
        NULLIF(COUNT(DISTINCT CASE WHEN discount_tier_source THEN id END), 0) * 100,
        2
    ) AS migration_rate_percent,
    COUNT(DISTINCT CASE 
        WHEN discount_tier_source 
        AND EXISTS (SELECT 1 FROM orders o WHERE o.user_id = users.id AND o.source_channel = 'discount')
        THEN id 
    END) AS users_with_discount_orders,
    SUM(CASE WHEN discount_tier_source THEN 1 ELSE 0 END) AS total_from_discount
FROM users;

COMMENT ON VIEW discount_migration_stats IS 'Statistics for discount to premium migration funnel';

-- ============================================
-- 11. Function: count_replacements
-- ============================================

CREATE OR REPLACE FUNCTION count_replacements(p_order_item_id UUID)
RETURNS INT AS $$
BEGIN
    RETURN (
        SELECT COUNT(*) 
        FROM insurance_replacements 
        WHERE order_item_id = p_order_item_id
        AND status IN ('approved', 'auto_approved')
    );
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION count_replacements IS 'Count approved replacements for an order item';

-- ============================================
-- 12. Function: can_request_replacement
-- ============================================

CREATE OR REPLACE FUNCTION can_request_replacement(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN NOT EXISTS (
        SELECT 1 FROM user_restrictions
        WHERE user_id = p_user_id
        AND restriction_type = 'replacement_blocked'
        AND (expires_at IS NULL OR expires_at > NOW())
    );
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION can_request_replacement IS 'Check if user is allowed to request replacements';

-- ============================================
-- 13. Function: get_user_abuse_score
-- ============================================

CREATE OR REPLACE FUNCTION get_user_abuse_score(p_telegram_id BIGINT)
RETURNS INT AS $$
DECLARE
    v_score INT := 0;
    v_recent_replacements INT;
    v_total_purchases INT;
    v_replacement_rate NUMERIC;
    v_account_age_days INT;
BEGIN
    SELECT EXTRACT(DAY FROM NOW() - created_at)::INT
    INTO v_account_age_days
    FROM users WHERE telegram_id = p_telegram_id;
    
    IF v_account_age_days IS NULL THEN
        RETURN 0;
    END IF;
    
    SELECT COUNT(*)
    INTO v_recent_replacements
    FROM insurance_replacements ir
    JOIN order_items oi ON oi.id = ir.order_item_id
    JOIN orders o ON o.id = oi.order_id
    JOIN users u ON u.id = o.user_id
    WHERE u.telegram_id = p_telegram_id
    AND ir.created_at > NOW() - INTERVAL '30 days'
    AND ir.status IN ('approved', 'auto_approved');
    
    SELECT COUNT(*)
    INTO v_total_purchases
    FROM orders o
    JOIN users u ON u.id = o.user_id
    WHERE u.telegram_id = p_telegram_id
    AND o.status = 'delivered';
    
    v_replacement_rate := v_recent_replacements::NUMERIC / GREATEST(v_total_purchases, 1);
    
    IF v_recent_replacements > 3 THEN
        v_score := v_score + 30;
    ELSIF v_recent_replacements > 1 THEN
        v_score := v_score + 15;
    END IF;
    
    IF v_replacement_rate > 0.5 THEN
        v_score := v_score + 40;
    ELSIF v_replacement_rate > 0.3 THEN
        v_score := v_score + 20;
    END IF;
    
    IF v_account_age_days < 7 THEN
        v_score := v_score + 20;
    ELSIF v_account_age_days < 30 THEN
        v_score := v_score + 10;
    END IF;
    
    RETURN LEAST(v_score, 100);
END;
$$ LANGUAGE plpgsql STABLE;

COMMENT ON FUNCTION get_user_abuse_score IS 'Calculate abuse risk score (0-100) for a user';

-- ============================================
-- 14. Indexes
-- ============================================

CREATE INDEX IF NOT EXISTS idx_orders_source_channel ON orders(source_channel);
CREATE INDEX IF NOT EXISTS idx_users_discount_tier ON users(discount_tier_source) WHERE discount_tier_source = TRUE;
