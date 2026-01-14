-- Migration: Referral System Views and Functions
-- Creates views for referral statistics, metrics, and analytics

-- ============================================================
-- 1. Referral Stats Extended View
-- ============================================================
-- Comprehensive view for user referral statistics including
-- network counts, earnings, unlock status, and turnover

CREATE OR REPLACE VIEW referral_stats_extended AS
WITH level1_stats AS (
    SELECT 
        u.id AS user_id,
        COUNT(DISTINCT r1.id) AS level1_count,
        COALESCE(SUM(CASE WHEN rb1.level = 1 AND rb1.eligible IS TRUE THEN rb1.amount ELSE 0 END), 0) AS level1_earnings
    FROM users u
    LEFT JOIN users r1 ON r1.referrer_id = u.id
    LEFT JOIN referral_bonuses rb1 ON rb1.referrer_id = u.id AND rb1.level = 1
    GROUP BY u.id
),
level2_stats AS (
    SELECT 
        u.id AS user_id,
        COUNT(DISTINCT r2.id) AS level2_count,
        COALESCE(SUM(CASE WHEN rb2.level = 2 AND rb2.eligible IS TRUE THEN rb2.amount ELSE 0 END), 0) AS level2_earnings
    FROM users u
    LEFT JOIN users r1 ON r1.referrer_id = u.id
    LEFT JOIN users r2 ON r2.referrer_id = r1.id
    LEFT JOIN referral_bonuses rb2 ON rb2.referrer_id = u.id AND rb2.level = 2
    GROUP BY u.id
),
level3_stats AS (
    SELECT 
        u.id AS user_id,
        COUNT(DISTINCT r3.id) AS level3_count,
        COALESCE(SUM(CASE WHEN rb3.level = 3 AND rb3.eligible IS TRUE THEN rb3.amount ELSE 0 END), 0) AS level3_earnings
    FROM users u
    LEFT JOIN users r1 ON r1.referrer_id = u.id
    LEFT JOIN users r2 ON r2.referrer_id = r1.id
    LEFT JOIN users r3 ON r3.referrer_id = r2.id
    LEFT JOIN referral_bonuses rb3 ON rb3.referrer_id = u.id AND rb3.level = 3
    GROUP BY u.id
),
active_referrals AS (
    SELECT 
        u.id AS user_id,
        COUNT(DISTINCT CASE WHEN o.status = 'delivered' THEN r.id END) AS active_referrals_count
    FROM users u
    LEFT JOIN users r ON r.referrer_id = u.id
    LEFT JOIN orders o ON o.user_id = r.id AND o.status = 'delivered'
    GROUP BY u.id
)
SELECT 
    u.id AS user_id,
    COALESCE(l1.level1_count, 0) AS level1_count,
    COALESCE(l2.level2_count, 0) AS level2_count,
    COALESCE(l3.level3_count, 0) AS level3_count,
    COALESCE(l1.level1_earnings, 0) AS level1_earnings,
    COALESCE(l2.level2_earnings, 0) AS level2_earnings,
    COALESCE(l3.level3_earnings, 0) AS level3_earnings,
    COALESCE(ar.active_referrals_count, 0) AS active_referrals_count,
    COALESCE(u.referral_program_unlocked, false) AS referral_program_unlocked,
    COALESCE(u.is_partner, false) AS is_partner,
    u.partner_level_override,
    COALESCE(u.turnover_usd, 0) AS turnover_usd,
    COALESCE(u.total_referral_earnings, 0) AS total_referral_earnings,
    u.level1_unlocked_at,
    u.level2_unlocked_at,
    u.level3_unlocked_at,
    -- Calculate effective_level based on turnover and partner status
    CASE 
        WHEN u.is_partner AND u.partner_level_override IS NOT NULL THEN u.partner_level_override
        WHEN NOT COALESCE(u.referral_program_unlocked, false) THEN 0
        WHEN COALESCE(u.turnover_usd, 0) >= 1000 THEN 3
        WHEN COALESCE(u.turnover_usd, 0) >= 250 THEN 2
        WHEN COALESCE(u.referral_program_unlocked, false) THEN 1
        ELSE 0
    END AS effective_level,
    -- Status: locked or active
    CASE 
        WHEN COALESCE(u.referral_program_unlocked, false) THEN 'active'
        ELSE 'locked'
    END AS status
FROM users u
LEFT JOIN level1_stats l1 ON l1.user_id = u.id
LEFT JOIN level2_stats l2 ON l2.user_id = u.id
LEFT JOIN level3_stats l3 ON l3.user_id = u.id
LEFT JOIN active_referrals ar ON ar.user_id = u.id;

-- ============================================================
-- 2. Referral Program Metrics View
-- ============================================================
-- Overall metrics for the referral program

CREATE OR REPLACE VIEW referral_program_metrics AS
SELECT 
    COUNT(DISTINCT CASE WHEN u.referral_program_unlocked THEN u.id END) AS active_referrers,
    COUNT(DISTINCT CASE WHEN u.is_partner THEN u.id END) AS vip_partners,
    COUNT(DISTINCT r.id) AS total_referrals,
    COUNT(DISTINCT CASE WHEN o.status = 'delivered' THEN r.id END) AS active_referrals,
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.amount ELSE 0 END), 0) AS total_referral_revenue,
    COALESCE(SUM(rb.amount), 0) AS total_payouts,
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.amount ELSE 0 END), 0) - COALESCE(SUM(rb.amount), 0) AS net_profit,
    CASE 
        WHEN COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.amount ELSE 0 END), 0) > 0 
        THEN ROUND(
            ((COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.amount ELSE 0 END), 0) - COALESCE(SUM(rb.amount), 0)) / 
             COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.amount ELSE 0 END), 0)) * 100, 
            2
        )
        ELSE 0
    END AS margin_percent
FROM users u
LEFT JOIN users r ON r.referrer_id = u.id
LEFT JOIN orders o ON o.user_id = r.id
LEFT JOIN referral_bonuses rb ON rb.referrer_id = u.id AND rb.eligible IS TRUE;

-- ============================================================
-- 3. Referral ROI Dashboard View
-- ============================================================
-- ROI metrics for admin dashboard

CREATE OR REPLACE VIEW referral_roi_dashboard AS
SELECT 
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.amount ELSE 0 END), 0) AS total_referral_revenue,
    COALESCE(SUM(rb.amount), 0) AS total_payouts,
    COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.amount ELSE 0 END), 0) - COALESCE(SUM(rb.amount), 0) AS net_profit,
    CASE 
        WHEN COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.amount ELSE 0 END), 0) > 0 
        THEN ROUND(
            ((COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.amount ELSE 0 END), 0) - COALESCE(SUM(rb.amount), 0)) / 
             COALESCE(SUM(CASE WHEN o.status = 'delivered' THEN o.amount ELSE 0 END), 0)) * 100, 
            2
        )
        ELSE 0
    END AS margin_percent,
    COUNT(DISTINCT CASE WHEN EXISTS (
        SELECT 1 FROM orders o2 
        WHERE o2.user_id = r.id AND o2.status = 'delivered'
    ) THEN u.id END) AS active_partners
FROM users u
LEFT JOIN users r ON r.referrer_id = u.id
LEFT JOIN orders o ON o.user_id = r.id
LEFT JOIN referral_bonuses rb ON rb.referrer_id = u.id AND rb.eligible IS TRUE;

-- ============================================================
-- 4. Partner Analytics View (for CRM)
-- ============================================================
-- Detailed analytics for each partner with all required fields for API

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
    WHERE u.is_partner IS TRUE OR EXISTS (SELECT 1 FROM users r2 WHERE r2.referrer_id = u.id)
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
WHERE u.is_partner IS TRUE OR EXISTS (SELECT 1 FROM users r2 WHERE r2.referrer_id = u.id);

