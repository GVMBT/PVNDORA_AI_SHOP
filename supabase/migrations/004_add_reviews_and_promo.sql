-- Migration: Add reviews, promo codes, and FAQ tables
-- Part of Phase 7: Database completion

-- ============================================================
-- 1. Reviews table
-- ============================================================

CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
    text TEXT,
    cashback_paid BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- One review per order
    UNIQUE(order_id)
);

-- Indexes for reviews
CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user ON reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_created ON reviews(created_at DESC);

-- ============================================================
-- 2. Promo codes table
-- ============================================================

CREATE TABLE IF NOT EXISTS promo_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(50) NOT NULL UNIQUE,
    discount_percent NUMERIC(5,2) DEFAULT 0,
    discount_amount NUMERIC(10,2) DEFAULT 0,
    min_order_amount NUMERIC(10,2) DEFAULT 0,
    usage_limit INTEGER,
    usage_count INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Either percent or amount, not both
    CHECK (
        (discount_percent > 0 AND discount_amount = 0) OR
        (discount_percent = 0 AND discount_amount > 0) OR
        (discount_percent = 0 AND discount_amount = 0)
    )
);

-- Index for promo lookups
CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code);
CREATE INDEX IF NOT EXISTS idx_promo_codes_active ON promo_codes(is_active, expires_at);

-- ============================================================
-- 3. FAQ table
-- ============================================================

CREATE TABLE IF NOT EXISTS faq (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(100) DEFAULT 'general',
    language_code VARCHAR(10) DEFAULT 'en',
    priority INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for FAQ lookups
CREATE INDEX IF NOT EXISTS idx_faq_language ON faq(language_code, is_active);
CREATE INDEX IF NOT EXISTS idx_faq_category ON faq(category, language_code);

-- ============================================================
-- 4. Product recommendations table
-- ============================================================

CREATE TABLE IF NOT EXISTS product_recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    recommended_product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    weight NUMERIC(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- No self-recommendations
    CHECK (product_id != recommended_product_id),
    UNIQUE(product_id, recommended_product_id)
);

-- Index for recommendations
CREATE INDEX IF NOT EXISTS idx_recommendations_product ON product_recommendations(product_id);

-- ============================================================
-- 5. User notifications table (rate limiting)
-- ============================================================

CREATE TABLE IF NOT EXISTS user_notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    last_sent_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, notification_type)
);

-- Index for notification checks
CREATE INDEX IF NOT EXISTS idx_user_notifications_lookup 
    ON user_notifications(user_id, notification_type, last_sent_at);

-- ============================================================
-- 6. Enable Row Level Security
-- ============================================================

ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE promo_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE faq ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_recommendations ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_notifications ENABLE ROW LEVEL SECURITY;

-- Reviews: users can read all, write own
CREATE POLICY "Reviews are viewable by all" ON reviews
    FOR SELECT USING (true);

CREATE POLICY "Users can insert own reviews" ON reviews
    FOR INSERT WITH CHECK (
        auth.uid() IS NOT NULL
    );

-- Promo codes: read only for users
CREATE POLICY "Promo codes are viewable by all" ON promo_codes
    FOR SELECT USING (is_active = true);

-- FAQ: read only
CREATE POLICY "FAQ is viewable by all" ON faq
    FOR SELECT USING (is_active = true);

-- Product recommendations: read only
CREATE POLICY "Recommendations are viewable by all" ON product_recommendations
    FOR SELECT USING (true);


