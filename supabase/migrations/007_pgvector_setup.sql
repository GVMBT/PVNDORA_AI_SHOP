-- Migration: pgvector setup for RAG
-- Enables vector search for product discovery

-- ============================================================
-- 1. Enable pgvector extension
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- 2. Add embedding column to products
-- ============================================================

ALTER TABLE products 
    ADD COLUMN IF NOT EXISTS embedding vector(768);

-- ============================================================
-- 3. Create index for vector similarity search
-- ============================================================

-- HNSW index for fast approximate nearest neighbor search
CREATE INDEX IF NOT EXISTS idx_products_embedding 
    ON products 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================
-- 4. Function to search products by embedding
-- ============================================================

CREATE OR REPLACE FUNCTION search_products_by_embedding(
    query_embedding vector(768),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE(
    product_id UUID,
    name VARCHAR,
    description TEXT,
    price NUMERIC,
    product_type VARCHAR,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id AS product_id,
        p.name,
        p.description,
        p.price,
        p.type AS product_type,
        1 - (p.embedding <=> query_embedding) AS similarity
    FROM products p
    WHERE 
        p.status = 'active'
        AND p.embedding IS NOT NULL
        AND 1 - (p.embedding <=> query_embedding) > match_threshold
    ORDER BY p.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 5. Function to find similar products
-- ============================================================

CREATE OR REPLACE FUNCTION find_similar_products(
    p_product_id UUID,
    match_count INT DEFAULT 5
)
RETURNS TABLE(
    product_id UUID,
    name VARCHAR,
    price NUMERIC,
    similarity FLOAT
) AS $$
DECLARE
    v_embedding vector(768);
BEGIN
    -- Get the product's embedding
    SELECT embedding INTO v_embedding
    FROM products
    WHERE id = p_product_id;
    
    IF v_embedding IS NULL THEN
        RETURN;
    END IF;
    
    RETURN QUERY
    SELECT 
        p.id AS product_id,
        p.name,
        p.price,
        1 - (p.embedding <=> v_embedding) AS similarity
    FROM products p
    WHERE 
        p.id != p_product_id
        AND p.status = 'active'
        AND p.embedding IS NOT NULL
    ORDER BY p.embedding <=> v_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- 6. Trigger to clear embedding when product text changes
-- ============================================================

CREATE OR REPLACE FUNCTION clear_product_embedding()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.name != OLD.name 
        OR NEW.description != OLD.description 
        OR NEW.instructions != OLD.instructions THEN
        NEW.embedding := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER product_text_changed
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION clear_product_embedding();

-- ============================================================
-- Note: To populate embeddings, run:
-- 
-- from core.rag import get_product_search
-- search = get_product_search()
-- 
-- # For each product:
-- await search.index_product(
--     product_id=str(product['id']),
--     name=product['name'],
--     description=product['description'],
--     product_type=product['type'],
--     instructions=product.get('instructions')
-- )
-- ============================================================


