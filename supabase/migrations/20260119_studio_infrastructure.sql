-- Migration: Studio Infrastructure
-- Purpose: Tables for AI generation studio (video, image, audio)
-- Date: 2026-01-19
-- 
-- This migration creates:
-- 1. studio_model_prices - AI model pricing (RUB)
-- 2. studio_sessions - User projects/canvases
-- 3. studio_generations - Generated content
-- 4. users.studio_referral_bonus_paid - Referral flag

-- ============================================================
-- 1. STUDIO MODEL PRICES (AI model pricing in RUB)
-- ============================================================

CREATE TABLE IF NOT EXISTS studio_model_prices (
    id TEXT PRIMARY KEY,  -- 'veo-3.1', 'kling-1.6', etc.
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('video', 'image', 'audio')),
    
    -- Base price in RUB (RUB-only system)
    base_price NUMERIC NOT NULL,
    
    -- Multipliers for options (resolution, duration, etc.)
    price_multipliers JSONB DEFAULT '{}',
    
    -- Cost price in RUB (for margin calculation)
    cost_price NUMERIC,
    
    -- Model limits
    max_duration_seconds INTEGER,
    supported_resolutions TEXT[],
    
    -- Capabilities for Dynamic UI
    capabilities JSONB DEFAULT '{}',
    
    is_active BOOLEAN DEFAULT true,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE studio_model_prices IS 'AI model pricing in RUB. Part of RUB-only system.';
COMMENT ON COLUMN studio_model_prices.base_price IS 'Base price in RUB';
COMMENT ON COLUMN studio_model_prices.price_multipliers IS 'Multipliers: {"resolution": {"720p": 1.0, "1080p": 1.5}}';
COMMENT ON COLUMN studio_model_prices.capabilities IS 'Dynamic UI capabilities: {"supports_audio": true, "custom_options": [...]}';

-- Initial pricing data (RUB, approximate rate 78₽/$)
INSERT INTO studio_model_prices (id, name, type, base_price, price_multipliers, cost_price, max_duration_seconds, supported_resolutions, capabilities, is_active, sort_order) VALUES
-- Video models
('veo-3.1', 'VEO 3.1', 'video', 200, 
 '{"resolution": {"720p": 1.0, "1080p": 1.5, "4k": 2.5}, "duration": {"4s": 0.8, "6s": 1.0, "8s": 1.2}}',
 65, 8, ARRAY['720p', '1080p', '4k'],
 '{"supports_audio": true, "custom_options": [{"id": "audio_sync", "type": "boolean", "label": "Генерировать звук"}]}',
 true, 1),
('veo-fast', 'VEO FAST', 'video', 80, '{}', 25, 6, ARRAY['720p'], '{}', true, 2),
('kling-1.6', 'KLING 1.6', 'video', 160,
 '{"resolution": {"720p": 1.0, "1080p": 1.3}, "duration": {"5s": 1.0, "10s": 1.8}}',
 50, 10, ARRAY['720p', '1080p'],
 '{"custom_options": [{"id": "camera_motion", "type": "select", "label": "Движение камеры", "options": ["static", "pan_left", "pan_right", "zoom_in", "orbit"]}]}',
 true, 3),
-- Audio models
('suno-v4', 'SUNO V4', 'audio', 80,
 '{"duration": {"30s": 1.0, "60s": 1.5, "120s": 2.5}}',
 28, 120, NULL,
 '{"custom_options": [{"id": "style", "type": "text", "label": "Стиль (теги)"}, {"id": "instrumental", "type": "boolean", "label": "Только инструментал"}]}',
 true, 10),
('elevenlabs', 'ELEVENLABS', 'audio', 40, '{}', 12, NULL, NULL, 
 '{"custom_options": [{"id": "voice_id", "type": "select", "label": "Голос"}]}',
 true, 11),
-- Image models
('imagen-3', 'IMAGEN 3', 'image', 40, '{}', 12, NULL, NULL, '{}', true, 20),
('flux-1.1', 'FLUX 1.1', 'image', 25, '{}', 8, NULL, NULL, '{}', true, 21),
('midjourney', 'MIDJOURNEY', 'image', 50, '{}', 16, NULL, NULL, '{}', false, 22)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    base_price = EXCLUDED.base_price,
    price_multipliers = EXCLUDED.price_multipliers,
    cost_price = EXCLUDED.cost_price,
    capabilities = EXCLUDED.capabilities,
    is_active = EXCLUDED.is_active;

-- ============================================================
-- 2. STUDIO SESSIONS (Projects/Canvases)
-- ============================================================

CREATE TABLE IF NOT EXISTS studio_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Project name (editable)
    name TEXT DEFAULT 'Новый проект',
    
    -- Statistics (updated by trigger)
    total_generations INTEGER DEFAULT 0,
    total_spent NUMERIC DEFAULT 0,  -- In RUB
    
    -- Flags
    is_archived BOOLEAN DEFAULT false,
    is_default BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_studio_sessions_user ON studio_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_studio_sessions_active ON studio_sessions(user_id) 
    WHERE is_archived = false;

COMMENT ON TABLE studio_sessions IS 'User projects/canvases for organizing generations';
COMMENT ON COLUMN studio_sessions.is_default IS 'One session per user marked as default (for newcomers)';

-- ============================================================
-- 3. STUDIO GENERATIONS (Generated content)
-- ============================================================

CREATE TABLE IF NOT EXISTS studio_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES studio_sessions(id) ON DELETE CASCADE,
    
    -- Content type
    type TEXT NOT NULL CHECK (type IN ('video', 'image', 'audio')),
    model TEXT NOT NULL,  -- References studio_model_prices.id
    prompt TEXT,
    
    -- Generation config (resolution, duration, custom_params, etc.)
    config JSONB DEFAULT '{}',
    
    -- Status
    status TEXT NOT NULL DEFAULT 'queued' 
        CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'expired')),
    progress INTEGER DEFAULT 0,  -- 0-100
    error_message TEXT,
    
    -- Result
    result_url TEXT,  -- URL in Supabase Storage
    thumbnail_url TEXT,
    duration_seconds NUMERIC,
    file_size_bytes BIGINT,
    has_audio BOOLEAN DEFAULT false,  -- For Veo native audio
    
    -- Canvas links
    parent_id UUID REFERENCES studio_generations(id) ON DELETE SET NULL,
    linked_audio_id UUID REFERENCES studio_generations(id) ON DELETE SET NULL,
    linked_image_id UUID REFERENCES studio_generations(id) ON DELETE SET NULL,
    
    -- Canvas position (desktop uses, mobile ignores)
    position_x INTEGER,
    position_y INTEGER,
    
    -- Cost in RUB
    cost_amount NUMERIC NOT NULL DEFAULT 0,
    
    -- Reference to balance transaction
    balance_transaction_id UUID REFERENCES balance_transactions(id),
    
    -- External job tracking
    external_job_id TEXT,  -- Provider's job ID for status polling
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ  -- Auto-calculated: created_at + 30 days
);

CREATE INDEX IF NOT EXISTS idx_studio_generations_user ON studio_generations(user_id);
CREATE INDEX IF NOT EXISTS idx_studio_generations_session ON studio_generations(session_id);
CREATE INDEX IF NOT EXISTS idx_studio_generations_status ON studio_generations(status);
CREATE INDEX IF NOT EXISTS idx_studio_generations_expires ON studio_generations(expires_at) 
    WHERE status = 'completed';
CREATE INDEX IF NOT EXISTS idx_studio_generations_external_job ON studio_generations(external_job_id)
    WHERE external_job_id IS NOT NULL;

COMMENT ON TABLE studio_generations IS 'AI-generated content (video, image, audio)';
COMMENT ON COLUMN studio_generations.has_audio IS 'True for Veo videos with native audio';
COMMENT ON COLUMN studio_generations.external_job_id IS 'Provider job ID for webhook/polling';

-- ============================================================
-- 4. TRIGGERS
-- ============================================================

-- 4.1 Auto-set expires_at on insert
CREATE OR REPLACE FUNCTION set_generation_expires_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.expires_at := NEW.created_at + INTERVAL '30 days';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_set_generation_expires_at ON studio_generations;
CREATE TRIGGER trg_set_generation_expires_at
    BEFORE INSERT ON studio_generations
    FOR EACH ROW
    EXECUTE FUNCTION set_generation_expires_at();

-- 4.2 Update session stats on generation insert
CREATE OR REPLACE FUNCTION update_session_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE studio_sessions 
    SET 
        total_generations = total_generations + 1,
        total_spent = total_spent + NEW.cost_amount,
        updated_at = NOW()
    WHERE id = NEW.session_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_session_stats ON studio_generations;
CREATE TRIGGER trg_update_session_stats
    AFTER INSERT ON studio_generations
    FOR EACH ROW
    EXECUTE FUNCTION update_session_stats();

-- 4.3 Update updated_at on generation update
CREATE OR REPLACE FUNCTION update_generation_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_generation_updated_at ON studio_generations;
CREATE TRIGGER trg_update_generation_updated_at
    BEFORE UPDATE ON studio_generations
    FOR EACH ROW
    EXECUTE FUNCTION update_generation_updated_at();

-- ============================================================
-- 5. USER FLAG FOR STUDIO REFERRAL BONUS
-- ============================================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS studio_referral_bonus_paid BOOLEAN DEFAULT false;

COMMENT ON COLUMN users.studio_referral_bonus_paid IS 
    'True if referrer already received 80₽ bonus for this user first studio generation';

-- ============================================================
-- 6. HELPER FUNCTION: Get or create default session
-- ============================================================

CREATE OR REPLACE FUNCTION get_or_create_default_studio_session(p_user_id UUID)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_session_id UUID;
BEGIN
    -- Try to find existing default session
    SELECT id INTO v_session_id
    FROM studio_sessions
    WHERE user_id = p_user_id AND is_default = true
    LIMIT 1;
    
    IF v_session_id IS NOT NULL THEN
        RETURN v_session_id;
    END IF;
    
    -- Try to find any session
    SELECT id INTO v_session_id
    FROM studio_sessions
    WHERE user_id = p_user_id AND is_archived = false
    ORDER BY created_at DESC
    LIMIT 1;
    
    IF v_session_id IS NOT NULL THEN
        RETURN v_session_id;
    END IF;
    
    -- Create new default session
    INSERT INTO studio_sessions (user_id, name, is_default)
    VALUES (p_user_id, 'Мой первый проект', true)
    RETURNING id INTO v_session_id;
    
    RETURN v_session_id;
END;
$$;

COMMENT ON FUNCTION get_or_create_default_studio_session IS 
    'Get existing default session or create new one for user';

-- ============================================================
-- 7. HELPER FUNCTION: Calculate generation price
-- ============================================================

CREATE OR REPLACE FUNCTION calculate_studio_generation_price(
    p_model_id TEXT,
    p_config JSONB DEFAULT '{}'
)
RETURNS NUMERIC
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_model RECORD;
    v_price NUMERIC;
    v_option_key TEXT;
    v_option_value TEXT;
    v_multiplier NUMERIC;
BEGIN
    -- Get model pricing
    SELECT base_price, price_multipliers INTO v_model
    FROM studio_model_prices
    WHERE id = p_model_id AND is_active = true;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Model not found or inactive: %', p_model_id;
    END IF;
    
    v_price := v_model.base_price;
    
    -- Apply multipliers from config
    IF v_model.price_multipliers IS NOT NULL AND v_model.price_multipliers != '{}' THEN
        FOR v_option_key, v_option_value IN
            SELECT key, value::text FROM jsonb_each_text(p_config)
            WHERE key IN (SELECT jsonb_object_keys(v_model.price_multipliers))
        LOOP
            v_multiplier := (v_model.price_multipliers -> v_option_key ->> v_option_value)::numeric;
            IF v_multiplier IS NOT NULL THEN
                v_price := v_price * v_multiplier;
            END IF;
        END LOOP;
    END IF;
    
    RETURN ROUND(v_price);
END;
$$;

COMMENT ON FUNCTION calculate_studio_generation_price IS 
    'Calculate generation price in RUB based on model and config';

-- ============================================================
-- 8. RLS POLICIES
-- ============================================================

ALTER TABLE studio_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE studio_generations ENABLE ROW LEVEL SECURITY;

-- Sessions: users can only see their own
CREATE POLICY "Users can view own sessions" ON studio_sessions
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can insert own sessions" ON studio_sessions
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own sessions" ON studio_sessions
    FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "Users can delete own sessions" ON studio_sessions
    FOR DELETE USING (user_id = auth.uid());

-- Generations: users can only see their own
CREATE POLICY "Users can view own generations" ON studio_generations
    FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can insert own generations" ON studio_generations
    FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update own generations" ON studio_generations
    FOR UPDATE USING (user_id = auth.uid());

-- Model prices: everyone can read (public pricing)
CREATE POLICY "Anyone can view model prices" ON studio_model_prices
    FOR SELECT USING (true);
