-- Migration: Anchor Currency System
-- Purpose: Implement fixed pricing (RUB/USD anchors) and transaction snapshots
-- Date: 2026-01-09

-- ============================================================
-- 1. Products: Add anchor prices column
-- ============================================================

-- Add JSONB column for fixed prices in different currencies
-- Example: {"RUB": 990, "USD": 10.50}
ALTER TABLE products ADD COLUMN IF NOT EXISTS prices jsonb DEFAULT '{}';

COMMENT ON COLUMN products.prices IS 'Anchor prices in different currencies. Format: {"RUB": 990, "USD": 10.50}. If set, takes priority over dynamic conversion.';

-- ============================================================
-- 2. Orders: Add currency snapshot columns
-- ============================================================

-- fiat_amount = what user saw/paid in their currency
ALTER TABLE orders ADD COLUMN IF NOT EXISTS fiat_amount numeric;

-- fiat_currency = user's payment currency (RUB, USD, etc.)
ALTER TABLE orders ADD COLUMN IF NOT EXISTS fiat_currency varchar(3);

-- exchange_rate_snapshot = rate at order creation (1 USD = X fiat_currency)
ALTER TABLE orders ADD COLUMN IF NOT EXISTS exchange_rate_snapshot numeric;

COMMENT ON COLUMN orders.fiat_amount IS 'Amount in user currency (what they saw/paid)';
COMMENT ON COLUMN orders.fiat_currency IS 'Currency code user paid in (RUB, USD, EUR, etc.)';
COMMENT ON COLUMN orders.exchange_rate_snapshot IS 'Exchange rate at order creation: 1 USD = X fiat_currency';

-- Migrate historical data: assume USD for existing orders
UPDATE orders SET 
    fiat_currency = 'USD',
    fiat_amount = amount,
    exchange_rate_snapshot = 1.0
WHERE fiat_currency IS NULL;

-- ============================================================
-- 3. Users: Add balance currency column
-- ============================================================

-- Add balance_currency column
ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_currency varchar(3) DEFAULT 'USD';

COMMENT ON COLUMN users.balance_currency IS 'Currency of user balance. Determined by language_code on first transaction. RUB for ru/be/kk, USD for others.';

-- Migrate existing users: ru/be/kk → RUB, others → USD
UPDATE users SET balance_currency = 
    CASE 
        WHEN language_code IN ('ru', 'be', 'kk') THEN 'RUB' 
        ELSE 'USD' 
    END
WHERE balance_currency IS NULL OR balance_currency = 'USD';

-- For users with existing RUB balance (from Russian language), keep as is
-- For users with USD balance, keep as is

-- ============================================================
-- 4. Update calculate_order_expenses function
-- Remove hardcoded /80 exchange rate
-- ============================================================

CREATE OR REPLACE FUNCTION public.calculate_order_expenses(p_order_id uuid)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
  v_order RECORD;
  v_cogs NUMERIC := 0;
  v_acquiring_fee NUMERIC := 0;
  v_referral_payout NUMERIC := 0;
  v_reserve NUMERIC := 0;
  v_review_cashback NUMERIC := 0;
  v_replacement_cost NUMERIC := 0;
  v_promo_discount NUMERIC := 0;
  v_partner_discount NUMERIC := 0;
  v_fee_record RECORD;
  v_settings RECORD;
  v_details JSONB := '{}';
  v_exchange_rate NUMERIC;
BEGIN
  SELECT * INTO v_order FROM orders WHERE id = p_order_id;
  IF NOT FOUND THEN RETURN; END IF;
  
  SELECT * INTO v_settings FROM accounting_settings LIMIT 1;
  
  -- Get exchange rate: prefer snapshot, fallback to current rate, then hardcoded
  v_exchange_rate := COALESCE(
    v_order.exchange_rate_snapshot,
    (SELECT rate FROM exchange_rates WHERE currency = COALESCE(v_order.fiat_currency, 'RUB') LIMIT 1),
    80.0  -- Last resort fallback
  );
  
  -- 1. COGS
  SELECT COALESCE(SUM(p.cost_price * oi.quantity), 0)
  INTO v_cogs
  FROM order_items oi
  JOIN products p ON oi.product_id = p.id
  WHERE oi.order_id = p_order_id;
  
  -- 2. Acquiring fee
  SELECT * INTO v_fee_record 
  FROM payment_gateway_fees 
  WHERE gateway = LOWER(COALESCE(v_order.payment_gateway, 'rukassa'))
  AND (payment_method IS NULL OR payment_method = LOWER(v_order.payment_method))
  ORDER BY payment_method NULLS LAST
  LIMIT 1;
  
  IF FOUND THEN
    v_acquiring_fee := (v_order.amount * v_fee_record.fee_percent / 100);
    IF v_fee_record.fee_fixed_amount > 0 THEN
      IF v_fee_record.fee_currency IN ('USD', 'USDT') THEN
        v_acquiring_fee := v_acquiring_fee + v_fee_record.fee_fixed_amount;
      ELSE
        -- Use snapshot rate instead of hardcoded 80
        v_acquiring_fee := v_acquiring_fee + (v_fee_record.fee_fixed_amount / v_exchange_rate);
      END IF;
    END IF;
  ELSE
    v_acquiring_fee := v_order.amount * COALESCE(v_settings.default_acquiring_fee_pct, 5) / 100;
  END IF;
  
  -- 3. Referral payouts (ALL 3 levels)
  SELECT COALESCE(SUM(amount), 0)
  INTO v_referral_payout
  FROM referral_bonuses
  WHERE order_id = p_order_id AND eligible = true;
  
  -- 4. Reserves
  v_reserve := v_order.amount * (
    COALESCE(v_settings.reserve_marketing_pct, 5) +
    COALESCE(v_settings.reserve_unforeseen_pct, 3) +
    COALESCE(v_settings.reserve_tax_pct, 0)
  ) / 100;
  
  -- 5. Review cashback (5% of order if review exists)
  SELECT COALESCE(SUM(bt.amount::numeric), 0)
  INTO v_review_cashback
  FROM balance_transactions bt
  WHERE bt.reference_id = p_order_id::text 
    AND bt.type = 'cashback'
    AND (bt.description ILIKE '%отзыв%' OR bt.description ILIKE '%review%');
  
  -- 6. Insurance replacement costs
  SELECT COALESCE(SUM(p.cost_price), 0)
  INTO v_replacement_cost
  FROM insurance_replacements ir
  JOIN order_items oi ON ir.order_item_id = oi.id
  JOIN products p ON oi.product_id = p.id
  WHERE oi.order_id = p_order_id
    AND ir.status IN ('approved', 'auto_approved');
  
  -- 7. Promo code discount (difference between original and final price)
  v_promo_discount := COALESCE(v_order.original_price, v_order.amount) - v_order.amount;
  IF v_promo_discount < 0 THEN v_promo_discount := 0; END IF;
  
  -- Build details
  v_details := jsonb_build_object(
    'cogs_breakdown', (
      SELECT COALESCE(jsonb_agg(jsonb_build_object(
        'product', p.name,
        'cost_price', p.cost_price,
        'quantity', oi.quantity,
        'subtotal', p.cost_price * oi.quantity
      )), '[]'::jsonb)
      FROM order_items oi
      JOIN products p ON oi.product_id = p.id
      WHERE oi.order_id = p_order_id
    ),
    'acquiring', jsonb_build_object(
      'gateway', v_order.payment_gateway,
      'method', v_order.payment_method,
      'fee_percent', COALESCE(v_fee_record.fee_percent, COALESCE(v_settings.default_acquiring_fee_pct, 5)),
      'exchange_rate_used', v_exchange_rate
    ),
    'reserves', jsonb_build_object(
      'marketing_pct', COALESCE(v_settings.reserve_marketing_pct, 5),
      'unforeseen_pct', COALESCE(v_settings.reserve_unforeseen_pct, 3),
      'tax_pct', COALESCE(v_settings.reserve_tax_pct, 0)
    ),
    'currency_snapshot', jsonb_build_object(
      'fiat_currency', v_order.fiat_currency,
      'fiat_amount', v_order.fiat_amount,
      'exchange_rate', v_exchange_rate
    ),
    'review_cashback', v_review_cashback,
    'replacement_cost', v_replacement_cost
  );
  
  -- Insert/Update
  INSERT INTO order_expenses (
    order_id, revenue_amount, cogs_amount, acquiring_fee_amount, 
    referral_payout_amount, reserve_amount, 
    review_cashback_amount, insurance_replacement_cost,
    promo_discount_amount, partner_discount_amount,
    details
  ) VALUES (
    p_order_id, v_order.amount, v_cogs, v_acquiring_fee,
    v_referral_payout, v_reserve,
    v_review_cashback, v_replacement_cost,
    v_promo_discount, v_partner_discount,
    v_details
  )
  ON CONFLICT (order_id) DO UPDATE SET
    revenue_amount = EXCLUDED.revenue_amount,
    cogs_amount = EXCLUDED.cogs_amount,
    acquiring_fee_amount = EXCLUDED.acquiring_fee_amount,
    referral_payout_amount = EXCLUDED.referral_payout_amount,
    reserve_amount = EXCLUDED.reserve_amount,
    review_cashback_amount = EXCLUDED.review_cashback_amount,
    insurance_replacement_cost = EXCLUDED.insurance_replacement_cost,
    promo_discount_amount = EXCLUDED.promo_discount_amount,
    partner_discount_amount = EXCLUDED.partner_discount_amount,
    details = EXCLUDED.details;
    
END;
$function$;

-- ============================================================
-- 5. Helper function to get anchor price for a product
-- ============================================================

CREATE OR REPLACE FUNCTION get_anchor_price(
    p_product_id uuid,
    p_currency varchar(3)
)
RETURNS numeric
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    v_product RECORD;
    v_anchor_price numeric;
    v_rate numeric;
BEGIN
    SELECT id, price, prices INTO v_product
    FROM products
    WHERE id = p_product_id;
    
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;
    
    -- Check if anchor price exists for this currency
    IF v_product.prices IS NOT NULL AND v_product.prices ? p_currency THEN
        v_anchor_price := (v_product.prices ->> p_currency)::numeric;
        RETURN v_anchor_price;
    END IF;
    
    -- Fallback: convert from USD
    IF p_currency = 'USD' THEN
        RETURN v_product.price;
    END IF;
    
    -- Get exchange rate
    SELECT rate INTO v_rate FROM exchange_rates WHERE currency = p_currency;
    IF v_rate IS NULL THEN
        v_rate := 1.0;
    END IF;
    
    RETURN ROUND(v_product.price * v_rate, 2);
END;
$function$;

COMMENT ON FUNCTION get_anchor_price IS 'Get product price in specified currency. Returns anchor price if set, otherwise converts from USD.';

-- ============================================================
-- 6. Index for faster currency lookups
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_orders_fiat_currency ON orders(fiat_currency);
CREATE INDEX IF NOT EXISTS idx_users_balance_currency ON users(balance_currency);
