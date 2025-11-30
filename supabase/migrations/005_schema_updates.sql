-- Migration: Schema updates for new features
-- Adds columns for gamification, lifecycle, and AI features

-- ============================================================
-- 1. Products table updates
-- ============================================================

-- MSRP for "Money Saved" gamification
ALTER TABLE products 
    ADD COLUMN IF NOT EXISTS msrp NUMERIC(10,2);

-- Update MSRP to match price where null (baseline)
UPDATE products SET msrp = price WHERE msrp IS NULL;

-- ============================================================
-- 2. Users table updates
-- ============================================================

-- Total saved for leaderboard
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS total_saved NUMERIC(10,2) DEFAULT 0;

-- Last activity for re-engagement
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ DEFAULT NOW();

-- Last re-engagement message timestamp
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS last_reengagement_at TIMESTAMPTZ;

-- Do not disturb flag
ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS do_not_disturb BOOLEAN DEFAULT FALSE;

-- Index for inactive user queries
CREATE INDEX IF NOT EXISTS idx_users_last_activity 
    ON users(last_activity_at) 
    WHERE do_not_disturb = FALSE AND is_banned = FALSE;

-- Index for re-engagement queries
CREATE INDEX IF NOT EXISTS idx_users_reengagement 
    ON users(last_reengagement_at, last_activity_at)
    WHERE do_not_disturb = FALSE AND is_banned = FALSE;

-- ============================================================
-- 3. Orders table updates
-- ============================================================

-- Review request tracking
ALTER TABLE orders 
    ADD COLUMN IF NOT EXISTS review_requested_at TIMESTAMPTZ;

-- Cross-sell offer tracking
ALTER TABLE orders 
    ADD COLUMN IF NOT EXISTS cross_sell_offered BOOLEAN DEFAULT FALSE;

-- Index for review request cron
CREATE INDEX IF NOT EXISTS idx_orders_review_request 
    ON orders(updated_at, status, review_requested_at)
    WHERE status = 'delivered' AND review_requested_at IS NULL;

-- Index for expiring subscriptions
CREATE INDEX IF NOT EXISTS idx_orders_expires 
    ON orders(expires_at, status)
    WHERE status = 'delivered' AND expires_at IS NOT NULL;

-- ============================================================
-- 4. Wishlist table updates
-- ============================================================

-- Reminder tracking
ALTER TABLE wishlist 
    ADD COLUMN IF NOT EXISTS reminded_at TIMESTAMPTZ;

-- Index for reminder cron
CREATE INDEX IF NOT EXISTS idx_wishlist_reminder 
    ON wishlist(created_at, reminded_at)
    WHERE reminded_at IS NULL;

-- ============================================================
-- 5. Helper functions
-- ============================================================

-- Increment user's total_saved
CREATE OR REPLACE FUNCTION increment_saved(amount NUMERIC)
RETURNS NUMERIC AS $$
BEGIN
    RETURN COALESCE(total_saved, 0) + amount;
END;
$$ LANGUAGE plpgsql;

-- Increment user's balance
CREATE OR REPLACE FUNCTION increment_balance(amount NUMERIC)
RETURNS NUMERIC AS $$
BEGIN
    RETURN COALESCE(balance, 0) + amount;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 6. Update trigger for last_activity_at
-- ============================================================

-- Function to update last_activity_at
CREATE OR REPLACE FUNCTION update_last_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE users 
    SET last_activity_at = NOW()
    WHERE telegram_id = NEW.user_telegram_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: Trigger should be added to chat_history or handled in application
-- CREATE TRIGGER on_chat_message
--     AFTER INSERT ON chat_history
--     FOR EACH ROW EXECUTE FUNCTION update_last_activity();



