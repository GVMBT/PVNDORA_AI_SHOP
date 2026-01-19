-- Migration: Studio Storage Buckets
-- Purpose: Create storage buckets for Studio uploads and results
-- Date: 2026-01-19
--
-- Note: Storage buckets in Supabase are typically created via Dashboard or API.
-- This migration creates the bucket policies for RLS.

-- ============================================================
-- 1. CREATE BUCKETS (if using Supabase CLI migrations)
-- Note: In production, create buckets via Dashboard:
-- - studio-uploads (private, 10MB limit, image/video)
-- - studio-results (private, 200MB limit, image/video/audio)
-- ============================================================

-- Check if buckets exist and create them via storage API
-- This is a placeholder - actual bucket creation needs Storage API or Dashboard

DO $$
BEGIN
    -- Insert bucket if not exists (studio-uploads)
    INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
    VALUES (
        'studio-uploads',
        'studio-uploads',
        false,  -- Private bucket
        52428800,  -- 50MB limit
        ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'video/mp4', 'video/webm']
    )
    ON CONFLICT (id) DO UPDATE SET
        file_size_limit = EXCLUDED.file_size_limit,
        allowed_mime_types = EXCLUDED.allowed_mime_types;
    
    -- Insert bucket if not exists (studio-results)
    INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
    VALUES (
        'studio-results',
        'studio-results',
        false,  -- Private bucket
        209715200,  -- 200MB limit
        ARRAY['image/jpeg', 'image/png', 'image/webp', 'video/mp4', 'video/webm', 'audio/mpeg', 'audio/wav', 'audio/ogg']
    )
    ON CONFLICT (id) DO UPDATE SET
        file_size_limit = EXCLUDED.file_size_limit,
        allowed_mime_types = EXCLUDED.allowed_mime_types;
        
EXCEPTION WHEN OTHERS THEN
    -- Buckets might need to be created via Dashboard if this fails
    RAISE NOTICE 'Could not create storage buckets via SQL. Create manually via Supabase Dashboard.';
END $$;

-- ============================================================
-- 2. STORAGE POLICIES
-- ============================================================

-- Drop existing policies if any
DROP POLICY IF EXISTS "Users can upload to studio-uploads" ON storage.objects;
DROP POLICY IF EXISTS "Users can read own studio-uploads" ON storage.objects;
DROP POLICY IF EXISTS "Users can delete own studio-uploads" ON storage.objects;
DROP POLICY IF EXISTS "Users can read own studio-results" ON storage.objects;
DROP POLICY IF EXISTS "Service role can manage studio-results" ON storage.objects;

-- studio-uploads policies (user-managed)
CREATE POLICY "Users can upload to studio-uploads"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'studio-uploads'
    AND auth.role() = 'authenticated'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Users can read own studio-uploads"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'studio-uploads'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Users can delete own studio-uploads"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'studio-uploads'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- studio-results policies (service-managed, user can only read)
CREATE POLICY "Users can read own studio-results"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'studio-results'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Service role needs full access for upload/delete
-- This is handled by using service_role key in backend

-- ============================================================
-- 3. SIGNED URL FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION get_studio_result_signed_url(
    p_user_id UUID,
    p_file_path TEXT,
    p_expires_in INTEGER DEFAULT 3600  -- 1 hour default
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_full_path TEXT;
BEGIN
    -- Construct full path with user_id prefix
    v_full_path := p_user_id::text || '/' || p_file_path;
    
    -- Return signed URL (this is a placeholder - actual implementation
    -- needs to use storage.foldername() or external signing)
    RETURN 'signed_url_placeholder';
END;
$$;

COMMENT ON FUNCTION get_studio_result_signed_url IS 
    'Generate signed URL for studio result files. Actual implementation in backend.';
