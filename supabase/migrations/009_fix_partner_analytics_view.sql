-- Migration: Fix partner_analytics view to match API expectations
-- This view is used by /api/admin/referral/partners-crm endpoint

CREATE OR REPLACE VIEW partner_analytics AS
WITH referral_stats AS (
    SELECT 
        u.id AS user_id,
        COUNT(DISTINCT r.id) AS total_referrals,
        COUNT(DISTINCT CASE WHEN o.status = 'delivered' THEN r.id END) AS paying_referrals,
        COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.amount ELSE 0 END), 0) AS referral_revenue,
        CASE 
            WHEN COUNT(DISTINCT r.id) > 0 
            THEN ROUND((COUNT(DISTINCT CASE WHEN o.status = 'delivered' THEN r.id END)::numeric / COUNT(DISTINCT r.id)::numeric) * 100, 2)
            ELSE 0
        END AS conversion_rate
    FROM users u
    LEFT JOIN users r ON r.referrer_id = u.id
    LEFT JOIN orders o ON o.user_id = r.id
    WHERE u.is_partner = true OR EXISTS (SELECT 1 FROM users r2 WHERE r2.referrer_id = u.id)
    GROUP BY u.id
),
level_counts AS (
    SELECT 
        u.id AS user_id,
        COUNT(DISTINCT r1.id) AS level1_referrals,
        COUNT(DISTINCT r2.id) AS level2_referrals,
        COUNT(DISTINCT r3.id) AS level3_referrals
    FROM users u
    LEFT JOIN users r1 ON r1.referrer_id = u.id
    LEFT JOIN users r2 ON r2.referrer_id = r1.id
    LEFT JOIN users r3 ON r3.referrer_id = r2.id
    WHERE u.is_partner = true OR EXISTS (SELECT 1 FROM users r4 WHERE r4.referrer_id = u.id)
    GROUP BY u.id
)
SELECT 
    u.id AS user_id,
    u.telegram_id,
    u.username,
    u.first_name,
    COALESCE(u.is_partner, false) AS is_partner,
    COALESCE(u.partner_level_override, 0) AS partner_level_override,
    u.created_at AS joined_at,
    -- From referral_stats_extended
    COALESCE(rse.effective_level, 0) AS effective_level,
    -- From referral_stats CTE
    COALESCE(rs.total_referrals, 0) AS total_referrals,
    COALESCE(rs.paying_referrals, 0) AS paying_referrals,
    COALESCE(rs.conversion_rate, 0) AS conversion_rate,
    COALESCE(rs.referral_revenue, 0) AS referral_revenue,
    -- Financial
    COALESCE(u.total_referral_earnings, 0) AS total_earned,
    COALESCE(u.balance, 0) AS current_balance,
    -- Level counts
    COALESCE(lc.level1_referrals, 0) AS level1_referrals,
    COALESCE(lc.level2_referrals, 0) AS level2_referrals,
    COALESCE(lc.level3_referrals, 0) AS level3_referrals
FROM users u
LEFT JOIN referral_stats_extended rse ON rse.user_id = u.id
LEFT JOIN referral_stats rs ON rs.user_id = u.id
LEFT JOIN level_counts lc ON lc.user_id = u.id
WHERE u.is_partner = true OR EXISTS (SELECT 1 FROM users r2 WHERE r2.referrer_id = u.id);

