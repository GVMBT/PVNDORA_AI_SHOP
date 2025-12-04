-- Migration: Referral System Tables and Columns
-- Creates tables and adds columns needed for referral system

-- ============================================================
-- 1. Referral Bonuses Table - Add referrer_id column
-- ============================================================
-- Table already exists, just add missing referrer_id column

ALTER TABLE referral_bonuses 
    ADD COLUMN IF NOT EXISTS referrer_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- Update referrer_id from user_id for existing records
UPDATE referral_bonuses 
SET referrer_id = user_id 
WHERE referrer_id IS NULL;

-- Make referrer_id NOT NULL after backfill
ALTER TABLE referral_bonuses 
    ALTER COLUMN referrer_id SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_referral_bonuses_referrer ON referral_bonuses(referrer_id);

-- ============================================================
-- 2. Referral Settings Table
-- ============================================================

CREATE TABLE IF NOT EXISTS referral_settings (
    id UUID PRIMARY KEY DEFAULT '00000000-0000-0000-0000-000000000001',
    level1_threshold_usd NUMERIC(10,2) DEFAULT 0, -- Instant unlock (0)
    level2_threshold_usd NUMERIC(10,2) DEFAULT 250,
    level3_threshold_usd NUMERIC(10,2) DEFAULT 1000,
    level1_commission_percent NUMERIC(5,2) DEFAULT 20,
    level2_commission_percent NUMERIC(5,2) DEFAULT 10,
    level3_commission_percent NUMERIC(5,2) DEFAULT 5,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Insert default settings if not exists
INSERT INTO referral_settings (id, level1_threshold_usd, level2_threshold_usd, level3_threshold_usd, 
                               level1_commission_percent, level2_commission_percent, level3_commission_percent)
VALUES ('00000000-0000-0000-0000-000000000001', 0, 250, 1000, 20, 10, 5)
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- 3. Users Table - Add Referral Columns
-- ============================================================

ALTER TABLE users 
    ADD COLUMN IF NOT EXISTS referral_program_unlocked BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS turnover_usd NUMERIC(10,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_partner BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS partner_level_override INTEGER CHECK (partner_level_override IS NULL OR (partner_level_override >= 1 AND partner_level_override <= 3)),
    ADD COLUMN IF NOT EXISTS total_referral_earnings NUMERIC(10,2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS level1_unlocked_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS level2_unlocked_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS level3_unlocked_at TIMESTAMPTZ;

-- Indexes for referral queries
CREATE INDEX IF NOT EXISTS idx_users_referral_unlocked ON users(referral_program_unlocked);
CREATE INDEX IF NOT EXISTS idx_users_is_partner ON users(is_partner);
CREATE INDEX IF NOT EXISTS idx_users_turnover_usd ON users(turnover_usd DESC);

-- ============================================================
-- 4. Withdrawal Requests Table (if not exists)
-- ============================================================

CREATE TABLE IF NOT EXISTS withdrawal_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(10,2) NOT NULL,
    method TEXT NOT NULL, -- card, phone, crypto
    details TEXT, -- Payment details
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'completed')),
    admin_comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    processed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_user ON withdrawal_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_status ON withdrawal_requests(status, created_at);

-- ============================================================
-- 5. USD Exchange Rates Table (for currency conversion)
-- ============================================================

CREATE TABLE IF NOT EXISTS usd_exchange_rates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    currency_code VARCHAR(3) NOT NULL UNIQUE, -- RUB, EUR, etc.
    rate_to_usd NUMERIC(10,4) NOT NULL, -- How many units of currency = 1 USD
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Insert default RUB rate (approximate, should be updated via API)
INSERT INTO usd_exchange_rates (currency_code, rate_to_usd)
VALUES ('RUB', 100.0)
ON CONFLICT (currency_code) DO NOTHING;

-- ============================================================
-- 6. Update referral_bonuses.user_id to match referrer_id
-- ============================================================
-- For backward compatibility, ensure user_id = referrer_id

UPDATE referral_bonuses 
SET user_id = referrer_id 
WHERE user_id IS NULL OR user_id != referrer_id;

