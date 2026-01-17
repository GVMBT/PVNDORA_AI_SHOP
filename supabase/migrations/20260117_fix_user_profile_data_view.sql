-- Migration: Fix user_profile_data VIEW
-- Adds turnover_usd from referral_stats_extended
-- Adds amount_debited and balance_currency to recent_withdrawals

-- Drop and recreate the view with missing fields
DROP VIEW IF EXISTS user_profile_data;

CREATE OR REPLACE VIEW user_profile_data AS
SELECT
    u.id AS user_id,
    u.telegram_id,
    u.username,
    u.first_name,
    u.balance,
    u.balance_currency,
    u.total_referral_earnings,
    u.is_partner,
    u.partner_mode,
    u.partner_discount_percent,
    u.photo_url,
    u.language_code,
    u.created_at,
    -- From referral_stats_extended
    COALESCE(rse.level1_count, 0::bigint) AS level1_count,
    COALESCE(rse.level2_count, 0::bigint) AS level2_count,
    COALESCE(rse.level3_count, 0::bigint) AS level3_count,
    COALESCE(rse.effective_level, 0) AS effective_level,
    -- CRITICAL: Add turnover_usd (was missing!)
    COALESCE(rse.turnover_usd, 0::numeric) AS turnover_usd,
    -- Add other referral fields needed for UI
    rse.referral_program_unlocked,
    rse.partner_level_override,
    rse.level1_unlocked_at,
    rse.level2_unlocked_at,
    rse.level3_unlocked_at,
    rse.click_count,
    -- Recent bonuses
    (SELECT json_agg(json_build_object(
        'id', rb.id,
        'amount', rb.amount,
        'created_at', rb.created_at,
        'eligible', rb.eligible
    ) ORDER BY rb.created_at DESC)
    FROM referral_bonuses rb
    WHERE rb.user_id = u.id AND rb.eligible = true
    LIMIT 10) AS recent_bonuses,
    -- Recent withdrawals with FULL details for pending display
    (SELECT json_agg(json_build_object(
        'id', wr.id,
        'amount', wr.amount,
        'amount_debited', wr.amount_debited,
        'amount_to_pay', wr.amount_to_pay,
        'balance_currency', wr.balance_currency,
        'status', wr.status,
        'wallet_address', wr.wallet_address,
        'created_at', wr.created_at
    ) ORDER BY wr.created_at DESC)
    FROM withdrawal_requests wr
    WHERE wr.user_id = u.id
    LIMIT 10) AS recent_withdrawals,
    -- Recent transactions
    (SELECT json_agg(json_build_object(
        'id', bt.id,
        'amount', bt.amount,
        'type', bt.type,
        'status', bt.status,
        'description', bt.description,
        'created_at', bt.created_at
    ) ORDER BY bt.created_at DESC)
    FROM balance_transactions bt
    WHERE bt.user_id = u.id AND bt.status = 'completed'
    LIMIT 50) AS recent_transactions
FROM users u
LEFT JOIN referral_stats_extended rse ON rse.user_id = u.id;

COMMENT ON VIEW user_profile_data IS 'Aggregated user profile data with referral stats, recent withdrawals, and transactions. Includes turnover_usd for progress tracking.';
