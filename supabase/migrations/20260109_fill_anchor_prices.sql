-- Migration: Fill Anchor Prices for Existing Products
-- Purpose: Populate products.prices JSONB with calculated RUB prices
-- Date: 2026-01-09

-- ============================================================
-- Fill anchor prices for existing products
-- ============================================================

-- Function to round price to "beautiful" number (990, 1990, 2990, etc.)
CREATE OR REPLACE FUNCTION round_to_beautiful_price(price_usd numeric, rate_rub numeric)
RETURNS integer
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    price_rub numeric;
    rounded integer;
BEGIN
    -- Convert USD to RUB
    price_rub := price_usd * rate_rub;
    
    -- Round to nearest "beautiful" price:
    -- - If < 1000: round to nearest 10 (990, 1990, etc.)
    -- - If >= 1000: round to nearest 50 (1950, 2990, etc.)
    IF price_rub < 1000 THEN
        rounded := ROUND(price_rub / 10) * 10;
    ELSE
        rounded := ROUND(price_rub / 50) * 50;
    END IF;
    
    -- Ensure minimum price
    IF rounded < 10 THEN
        rounded := 10;
    END IF;
    
    RETURN rounded;
END;
$$;

-- Get current RUB rate (fallback to 80 if not found)
DO $$
DECLARE
    v_rate_rub numeric;
    v_product RECORD;
    v_price_rub integer;
BEGIN
    -- Get current RUB exchange rate
    SELECT rate INTO v_rate_rub 
    FROM exchange_rates 
    WHERE currency = 'RUB' 
    ORDER BY updated_at DESC 
    LIMIT 1;
    
    -- Fallback to 80 if rate not found
    IF v_rate_rub IS NULL THEN
        v_rate_rub := 80.0;
        RAISE NOTICE 'RUB rate not found, using fallback: 80.0';
    ELSE
        RAISE NOTICE 'Using RUB rate: %', v_rate_rub;
    END IF;
    
    -- Update each product with anchor price
    FOR v_product IN 
        SELECT id, name, price 
        FROM products 
        WHERE status = 'active'
        AND (prices IS NULL OR prices = '{}'::jsonb)
    LOOP
        -- Calculate beautiful RUB price
        v_price_rub := round_to_beautiful_price(v_product.price, v_rate_rub);
        
        -- Update product with anchor price
        UPDATE products 
        SET prices = jsonb_build_object('RUB', v_price_rub)
        WHERE id = v_product.id;
        
        RAISE NOTICE 'Updated product %: % USD -> % RUB (rate: %)', 
            v_product.name, v_product.price, v_price_rub, v_rate_rub;
    END LOOP;
    
    RAISE NOTICE 'Anchor prices filled successfully';
END $$;

-- Cleanup: drop helper function (optional, can keep for future use)
-- DROP FUNCTION IF EXISTS round_to_beautiful_price(numeric, numeric);
