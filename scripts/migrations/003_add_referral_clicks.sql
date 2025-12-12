-- Migration: Add Referral Click Tracking
-- Version: 003
-- Date: December 2024
-- Description: Adds click_count tracking for referral links

-- 1. Add column to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS referral_clicks_count INTEGER DEFAULT 0;

-- 2. Create atomic increment function
CREATE OR REPLACE FUNCTION increment_referral_click(user_id_param UUID)
RETURNS VOID AS $$
BEGIN
    UPDATE users
    SET referral_clicks_count = referral_clicks_count + 1
    WHERE id = user_id_param;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3. Create or replace the extended referral stats view
CREATE OR REPLACE VIEW referral_stats_extended AS
SELECT 
    u.id as user_id,
    u.referral_clicks_count as click_count,
    COUNT(DISTINCT r1.id) as level1_count,
    COUNT(DISTINCT r2.id) as level2_count,
    COUNT(DISTINCT r3.id) as level3_count,
    COALESCE(SUM(CASE WHEN rb.level = 1 THEN rb.amount ELSE 0 END), 0) as level1_earnings,
    COALESCE(SUM(CASE WHEN rb.level = 2 THEN rb.amount ELSE 0 END), 0) as level2_earnings,
    COALESCE(SUM(CASE WHEN rb.level = 3 THEN rb.amount ELSE 0 END), 0) as level3_earnings,
    COUNT(DISTINCT CASE WHEN r1.id IS NOT NULL AND EXISTS(
        SELECT 1 FROM orders o WHERE o.user_id = r1.id AND o.status IN ('delivered', 'completed')
    ) THEN r1.id END) as active_referrals,
    CASE 
        WHEN u.referral_clicks_count > 0 
        THEN ROUND((COUNT(DISTINCT r1.id)::numeric / u.referral_clicks_count * 100), 2)
        ELSE 0 
    END as conversion_rate
FROM users u
LEFT JOIN users r1 ON r1.referrer_id = u.id
LEFT JOIN users r2 ON r2.referrer_id = r1.id
LEFT JOIN users r3 ON r3.referrer_id = r2.id
LEFT JOIN referral_bonuses rb ON rb.referrer_id = u.id
GROUP BY u.id, u.referral_clicks_count;

-- 4. Grant permissions (adjust role as needed)
GRANT SELECT ON referral_stats_extended TO authenticated;
GRANT EXECUTE ON FUNCTION increment_referral_click TO authenticated;

-- 5. Create index for performance
CREATE INDEX IF NOT EXISTS idx_users_referrer_id ON users(referrer_id);

-- Verification query (run after migration)
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'users' AND column_name = 'referral_clicks_count';


