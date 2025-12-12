-- Migration: Add referral click tracking
-- Run this in Supabase SQL Editor

-- 1. Add referral_clicks column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_clicks INTEGER DEFAULT 0;

-- 2. Create RPC function to increment click count atomically
CREATE OR REPLACE FUNCTION increment_referral_click(referrer_user_id UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE users 
    SET referral_clicks = COALESCE(referral_clicks, 0) + 1 
    WHERE id = referrer_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. Create product_social_proof table if not exists (for sales_count)
CREATE TABLE IF NOT EXISTS product_social_proof (
    product_id UUID PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    sales_count INTEGER DEFAULT 0,
    recent_reviews JSONB DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create trigger to update sales_count when order is delivered
CREATE OR REPLACE FUNCTION update_product_sales_count()
RETURNS TRIGGER AS $$
BEGIN
    -- When order status changes to delivered, increment sales count
    IF NEW.status IN ('delivered', 'completed', 'ready') AND 
       (OLD.status IS NULL OR OLD.status NOT IN ('delivered', 'completed', 'ready')) THEN
        
        INSERT INTO product_social_proof (product_id, sales_count)
        VALUES (NEW.product_id, 1)
        ON CONFLICT (product_id) 
        DO UPDATE SET 
            sales_count = product_social_proof.sales_count + 1,
            updated_at = NOW();
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS trigger_update_sales_count ON orders;

-- Create trigger
CREATE TRIGGER trigger_update_sales_count
AFTER INSERT OR UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION update_product_sales_count();

-- 5. Initialize product_social_proof with existing data
INSERT INTO product_social_proof (product_id, sales_count)
SELECT 
    product_id, 
    COUNT(*) as sales_count
FROM orders 
WHERE status IN ('delivered', 'completed', 'ready')
GROUP BY product_id
ON CONFLICT (product_id) 
DO UPDATE SET sales_count = EXCLUDED.sales_count;

-- 6. Add index for performance
CREATE INDEX IF NOT EXISTS idx_users_referral_clicks ON users(referral_clicks DESC);

-- 7. Update referral_stats_extended view to include click_count
CREATE OR REPLACE VIEW referral_stats_extended AS
SELECT 
    u.id as user_id,
    u.referral_program_unlocked,
    u.is_partner,
    u.partner_level_override,
    u.turnover_usd,
    u.referral_clicks as click_count,
    -- Level 1 (direct referrals)
    (SELECT COUNT(*) FROM users r1 WHERE r1.referrer_id = u.id) as level1_count,
    -- Level 2 (referrals of referrals)
    (SELECT COUNT(*) FROM users r2 
     WHERE r2.referrer_id IN (SELECT r1.id FROM users r1 WHERE r1.referrer_id = u.id)
    ) as level2_count,
    -- Level 3
    (SELECT COUNT(*) FROM users r3 
     WHERE r3.referrer_id IN (
         SELECT r2.id FROM users r2 
         WHERE r2.referrer_id IN (SELECT r1.id FROM users r1 WHERE r1.referrer_id = u.id)
     )
    ) as level3_count,
    -- Earnings by level
    (SELECT COALESCE(SUM(amount), 0) FROM referral_bonuses rb 
     WHERE rb.referrer_id = u.id AND rb.level = 1 AND rb.eligible = true
    ) as level1_earnings,
    (SELECT COALESCE(SUM(amount), 0) FROM referral_bonuses rb 
     WHERE rb.referrer_id = u.id AND rb.level = 2 AND rb.eligible = true
    ) as level2_earnings,
    (SELECT COALESCE(SUM(amount), 0) FROM referral_bonuses rb 
     WHERE rb.referrer_id = u.id AND rb.level = 3 AND rb.eligible = true
    ) as level3_earnings,
    -- Active referrals (made at least one purchase)
    (SELECT COUNT(DISTINCT o.user_id) FROM orders o 
     INNER JOIN users r ON o.user_id = r.id 
     WHERE r.referrer_id = u.id AND o.status IN ('delivered', 'completed', 'ready')
    ) as active_referrals_count,
    -- Unlock timestamps (from referral_level_unlocks if exists)
    NULL::timestamptz as level1_unlocked_at,
    NULL::timestamptz as level2_unlocked_at,
    NULL::timestamptz as level3_unlocked_at
FROM users u;

COMMENT ON VIEW referral_stats_extended IS 'Extended referral statistics with click tracking';


