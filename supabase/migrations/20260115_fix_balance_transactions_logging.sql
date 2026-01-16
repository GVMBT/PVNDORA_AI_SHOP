-- Migration: Fix Balance Transactions Logging & Turnover Tracking
-- Date: 2026-01-15
-- 
-- Problems fixed:
-- 1. add_to_user_balance was not defined in migrations (created in Supabase directly)
-- 2. Balance purchases logged as generic "credit"/"debit" instead of "purchase"
-- 3. Referral bonuses not logged in balance_transactions
-- 4. Refunds through RPC have no metadata
-- 5. Descriptions not informative
-- 6. update_user_turnover was missing - turnover not tracked

-- ============================================================
-- 1. Create/Replace add_to_user_balance function
-- ============================================================

CREATE OR REPLACE FUNCTION public.add_to_user_balance(
    p_user_id uuid,
    p_amount numeric,
    p_reason text DEFAULT NULL,
    p_reference_type text DEFAULT NULL,
    p_reference_id text DEFAULT NULL,
    p_metadata jsonb DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
    v_user users%ROWTYPE;
    v_new_balance numeric;
    v_tx_type text;
    v_description text;
    v_final_metadata jsonb;
BEGIN
    -- Get user with lock
    SELECT * INTO v_user FROM users WHERE id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'User not found');
    END IF;
    
    -- Calculate new balance
    v_new_balance := COALESCE(v_user.balance, 0) + p_amount;
    
    -- Prevent negative balance (optional - can be disabled for admin)
    IF v_new_balance < 0 THEN
        RETURN jsonb_build_object('success', false, 'error', 'Insufficient balance');
    END IF;
    
    -- Determine transaction type based on amount and reason
    IF p_amount < 0 THEN
        -- Debit (money leaving)
        IF p_reason ILIKE '%payment for order%' OR p_reason ILIKE '%оплата заказа%' THEN
            v_tx_type := 'purchase';
            v_description := p_reason;
        ELSIF p_reason ILIKE '%withdrawal%' OR p_reason ILIKE '%вывод%' THEN
            v_tx_type := 'withdrawal';
            v_description := p_reason;
        ELSE
            v_tx_type := 'debit';
            v_description := COALESCE(p_reason, 'Списание с баланса');
        END IF;
    ELSE
        -- Credit (money coming in)
        IF p_reason ILIKE '%refund%' OR p_reason ILIKE '%возврат%' THEN
            v_tx_type := 'refund';
            v_description := p_reason;
        ELSIF p_reason ILIKE '%cashback%' OR p_reason ILIKE '%кэшбек%' THEN
            v_tx_type := 'cashback';
            v_description := p_reason;
        ELSIF p_reason ILIKE '%referral%' OR p_reason ILIKE '%реферал%' OR p_reason ILIKE '%bonus%' OR p_reason ILIKE '%бонус%' THEN
            v_tx_type := 'bonus';
            v_description := p_reason;
        ELSIF p_reason ILIKE '%topup%' OR p_reason ILIKE '%пополнение%' THEN
            v_tx_type := 'topup';
            v_description := p_reason;
        ELSIF p_reason ILIKE '%admin%' OR p_reason ILIKE '%adjustment%' OR p_reason ILIKE '%корректировка%' THEN
            v_tx_type := 'bonus';  -- Admin adjustments as bonus
            v_description := p_reason;
        ELSE
            v_tx_type := 'credit';
            v_description := COALESCE(p_reason, 'Зачисление на баланс');
        END IF;
    END IF;
    
    -- Build metadata
    v_final_metadata := COALESCE(p_metadata, '{}'::jsonb);
    IF p_reference_id IS NOT NULL THEN
        v_final_metadata := v_final_metadata || jsonb_build_object('reference_id', p_reference_id);
    END IF;
    IF p_reference_type IS NOT NULL THEN
        v_final_metadata := v_final_metadata || jsonb_build_object('reference_type', p_reference_type);
    END IF;
    
    -- Update user balance
    UPDATE users SET balance = v_new_balance WHERE id = p_user_id;
    
    -- Create balance transaction record
    INSERT INTO balance_transactions (
        user_id,
        type,
        amount,
        currency,
        balance_before,
        balance_after,
        status,
        description,
        reference_type,
        reference_id,
        metadata
    ) VALUES (
        p_user_id,
        v_tx_type,
        ABS(p_amount),  -- Store absolute amount, type indicates direction
        COALESCE(v_user.balance_currency, 'RUB'),
        COALESCE(v_user.balance, 0),
        v_new_balance,
        'completed',
        v_description,
        p_reference_type,
        p_reference_id,
        v_final_metadata
    );
    
    RETURN jsonb_build_object(
        'success', true,
        'new_balance', v_new_balance,
        'transaction_type', v_tx_type
    );
END;
$function$;

COMMENT ON FUNCTION add_to_user_balance IS 'Atomically update user balance and create balance_transaction record. Automatically determines transaction type based on amount and reason.';

-- ============================================================
-- 2. Update process_referral_bonus to log in balance_transactions
-- ============================================================

CREATE OR REPLACE FUNCTION public.process_referral_bonus(
    p_buyer_id uuid, 
    p_order_id uuid, 
    p_order_amount numeric
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
    v_settings referral_settings%ROWTYPE;
    v_referrer users%ROWTYPE;
    v_buyer users%ROWTYPE;
    v_order orders%ROWTYPE;
    v_level1_referrer_id uuid;
    v_level2_referrer_id uuid;
    v_level3_referrer_id uuid;
    v_bonus_amount numeric;
    v_result jsonb := '{"bonuses": []}'::jsonb;
    v_turnover numeric;
    v_effective_level integer;
    -- Multi-currency variables
    v_order_fiat_amount numeric;
    v_order_fiat_currency varchar(3);
    v_bonus_currency varchar(3);
    v_referrer_balance_currency varchar(3);
    v_buyer_rate numeric;
    v_referrer_rate numeric;
    v_converted_bonus numeric;
    -- For buyer info
    v_buyer_name text;
BEGIN
    -- Load settings
    SELECT * INTO v_settings FROM referral_settings LIMIT 1;
    
    -- Get order with fiat_amount and fiat_currency
    SELECT * INTO v_order FROM orders WHERE id = p_order_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'Order not found');
    END IF;
    
    -- Determine currency for bonus calculation
    IF v_order.fiat_amount IS NOT NULL AND v_order.fiat_currency IS NOT NULL THEN
        v_order_fiat_amount := v_order.fiat_amount;
        v_order_fiat_currency := v_order.fiat_currency;
        v_bonus_currency := v_order.fiat_currency;
    ELSE
        v_order_fiat_amount := p_order_amount;
        v_order_fiat_currency := 'USD';
        v_bonus_currency := 'USD';
    END IF;
    
    -- Get buyer exchange rate
    SELECT rate INTO v_buyer_rate FROM exchange_rates WHERE currency = v_order_fiat_currency;
    IF v_buyer_rate IS NULL THEN
        v_buyer_rate := 1.0;
    END IF;
    
    -- Get buyer
    SELECT * INTO v_buyer FROM users WHERE id = p_buyer_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'Buyer not found');
    END IF;
    
    v_buyer_name := COALESCE(v_buyer.username, v_buyer.first_name, 'Пользователь');
    
    -- Check for referrer (level 1)
    v_level1_referrer_id := v_buyer.referrer_id;
    IF v_level1_referrer_id IS NULL THEN
        RETURN jsonb_build_object('success', true, 'bonuses', '[]'::jsonb, 'message', 'No referrer');
    END IF;
    
    -- ============== LEVEL 1 BONUS ==============
    SELECT * INTO v_referrer FROM users WHERE id = v_level1_referrer_id;
    IF FOUND THEN
        v_turnover := COALESCE(v_referrer.turnover_usd, 0);
        v_referrer_balance_currency := COALESCE(v_referrer.balance_currency, 'USD');
        
        v_effective_level := CASE 
            WHEN v_referrer.is_partner AND v_referrer.partner_level_override IS NOT NULL THEN v_referrer.partner_level_override
            WHEN NOT v_referrer.referral_program_unlocked THEN 0
            WHEN v_turnover >= v_settings.level3_threshold_usd THEN 3
            WHEN v_turnover >= v_settings.level2_threshold_usd THEN 2
            WHEN v_referrer.referral_program_unlocked THEN 1
            ELSE 0
        END;
        
        IF v_effective_level >= 1 THEN
            -- Calculate bonus in buyer's currency
            v_bonus_amount := v_order_fiat_amount * (v_settings.level1_commission_percent / 100.0);
            
            -- Convert to referrer's balance currency
            SELECT rate INTO v_referrer_rate FROM exchange_rates WHERE currency = v_referrer_balance_currency;
            IF v_referrer_rate IS NULL THEN
                v_referrer_rate := 1.0;
            END IF;
            
            v_converted_bonus := v_bonus_amount * (v_referrer_rate / v_buyer_rate);
            
            -- Round for integer currencies
            IF v_referrer_balance_currency IN ('RUB', 'JPY', 'KRW', 'UAH', 'TRY', 'INR', 'CNY', 'BRL') THEN
                v_converted_bonus := ROUND(v_converted_bonus);
            ELSE
                v_converted_bonus := ROUND(v_converted_bonus, 2);
            END IF;
            
            -- Insert into referral_bonuses
            INSERT INTO referral_bonuses (user_id, from_user_id, order_id, amount, level, eligible)
            VALUES (v_level1_referrer_id, p_buyer_id, p_order_id, v_converted_bonus, 1, true);
            
            -- Update user balance
            UPDATE users 
            SET balance = balance + v_converted_bonus,
                total_referral_earnings = COALESCE(total_referral_earnings, 0) + v_converted_bonus
            WHERE id = v_level1_referrer_id;
            
            -- *** NEW: Create balance_transaction record ***
            INSERT INTO balance_transactions (
                user_id,
                type,
                amount,
                currency,
                balance_before,
                balance_after,
                status,
                description,
                reference_type,
                reference_id,
                metadata
            ) VALUES (
                v_level1_referrer_id,
                'bonus',
                v_converted_bonus,
                v_referrer_balance_currency,
                v_referrer.balance,
                v_referrer.balance + v_converted_bonus,
                'completed',
                'Реферальный бонус L1 (' || v_settings.level1_commission_percent || '%) от ' || v_buyer_name,
                'referral',
                p_order_id::text,
                jsonb_build_object(
                    'level', 1,
                    'percent', v_settings.level1_commission_percent,
                    'from_user_id', p_buyer_id,
                    'from_username', v_buyer_name,
                    'order_amount', v_order_fiat_amount,
                    'order_currency', v_order_fiat_currency
                )
            );
            
            v_result := v_result || jsonb_build_object('level1', v_converted_bonus);
        ELSE
            v_bonus_amount := v_order_fiat_amount * (v_settings.level1_commission_percent / 100.0);
            INSERT INTO referral_bonuses (user_id, from_user_id, order_id, amount, level, eligible, ineligible_reason)
            VALUES (v_level1_referrer_id, p_buyer_id, p_order_id, v_bonus_amount, 1, false, 'Program not unlocked');
        END IF;
        
        -- ============== LEVEL 2 BONUS ==============
        v_level2_referrer_id := v_referrer.referrer_id;
        IF v_level2_referrer_id IS NOT NULL THEN
            SELECT * INTO v_referrer FROM users WHERE id = v_level2_referrer_id;
            IF FOUND THEN
                v_turnover := COALESCE(v_referrer.turnover_usd, 0);
                v_referrer_balance_currency := COALESCE(v_referrer.balance_currency, 'USD');
                
                v_effective_level := CASE 
                    WHEN v_referrer.is_partner AND v_referrer.partner_level_override IS NOT NULL THEN v_referrer.partner_level_override
                    WHEN NOT v_referrer.referral_program_unlocked THEN 0
                    WHEN v_turnover >= v_settings.level3_threshold_usd THEN 3
                    WHEN v_turnover >= v_settings.level2_threshold_usd THEN 2
                    ELSE 1
                END;
                
                IF v_effective_level >= 2 THEN
                    v_bonus_amount := v_order_fiat_amount * (v_settings.level2_commission_percent / 100.0);
                    
                    SELECT rate INTO v_referrer_rate FROM exchange_rates WHERE currency = v_referrer_balance_currency;
                    IF v_referrer_rate IS NULL THEN
                        v_referrer_rate := 1.0;
                    END IF;
                    
                    v_converted_bonus := v_bonus_amount * (v_referrer_rate / v_buyer_rate);
                    
                    IF v_referrer_balance_currency IN ('RUB', 'JPY', 'KRW', 'UAH', 'TRY', 'INR', 'CNY', 'BRL') THEN
                        v_converted_bonus := ROUND(v_converted_bonus);
                    ELSE
                        v_converted_bonus := ROUND(v_converted_bonus, 2);
                    END IF;
                    
                    INSERT INTO referral_bonuses (user_id, from_user_id, order_id, amount, level, eligible)
                    VALUES (v_level2_referrer_id, p_buyer_id, p_order_id, v_converted_bonus, 2, true);
                    
                    UPDATE users 
                    SET balance = balance + v_converted_bonus,
                        total_referral_earnings = COALESCE(total_referral_earnings, 0) + v_converted_bonus
                    WHERE id = v_level2_referrer_id;
                    
                    -- *** NEW: Create balance_transaction record ***
                    INSERT INTO balance_transactions (
                        user_id,
                        type,
                        amount,
                        currency,
                        balance_before,
                        balance_after,
                        status,
                        description,
                        reference_type,
                        reference_id,
                        metadata
                    ) VALUES (
                        v_level2_referrer_id,
                        'bonus',
                        v_converted_bonus,
                        v_referrer_balance_currency,
                        v_referrer.balance,
                        v_referrer.balance + v_converted_bonus,
                        'completed',
                        'Реферальный бонус L2 (' || v_settings.level2_commission_percent || '%) от ' || v_buyer_name,
                        'referral',
                        p_order_id::text,
                        jsonb_build_object(
                            'level', 2,
                            'percent', v_settings.level2_commission_percent,
                            'from_user_id', p_buyer_id,
                            'from_username', v_buyer_name,
                            'order_amount', v_order_fiat_amount,
                            'order_currency', v_order_fiat_currency
                        )
                    );
                    
                    v_result := v_result || jsonb_build_object('level2', v_converted_bonus);
                ELSE
                    v_bonus_amount := v_order_fiat_amount * (v_settings.level2_commission_percent / 100.0);
                    INSERT INTO referral_bonuses (user_id, from_user_id, order_id, amount, level, eligible, ineligible_reason)
                    VALUES (v_level2_referrer_id, p_buyer_id, p_order_id, v_bonus_amount, 2, false, 'Level 2 not reached');
                END IF;
                
                -- ============== LEVEL 3 BONUS ==============
                v_level3_referrer_id := v_referrer.referrer_id;
                IF v_level3_referrer_id IS NOT NULL THEN
                    SELECT * INTO v_referrer FROM users WHERE id = v_level3_referrer_id;
                    IF FOUND THEN
                        v_turnover := COALESCE(v_referrer.turnover_usd, 0);
                        v_referrer_balance_currency := COALESCE(v_referrer.balance_currency, 'USD');
                        
                        v_effective_level := CASE 
                            WHEN v_referrer.is_partner AND v_referrer.partner_level_override IS NOT NULL THEN v_referrer.partner_level_override
                            WHEN NOT v_referrer.referral_program_unlocked THEN 0
                            WHEN v_turnover >= v_settings.level3_threshold_usd THEN 3
                            ELSE CASE WHEN v_turnover >= v_settings.level2_threshold_usd THEN 2 ELSE 1 END
                        END;
                        
                        IF v_effective_level >= 3 THEN
                            v_bonus_amount := v_order_fiat_amount * (v_settings.level3_commission_percent / 100.0);
                            
                            SELECT rate INTO v_referrer_rate FROM exchange_rates WHERE currency = v_referrer_balance_currency;
                            IF v_referrer_rate IS NULL THEN
                                v_referrer_rate := 1.0;
                            END IF;
                            
                            v_converted_bonus := v_bonus_amount * (v_referrer_rate / v_buyer_rate);
                            
                            IF v_referrer_balance_currency IN ('RUB', 'JPY', 'KRW', 'UAH', 'TRY', 'INR', 'CNY', 'BRL') THEN
                                v_converted_bonus := ROUND(v_converted_bonus);
                            ELSE
                                v_converted_bonus := ROUND(v_converted_bonus, 2);
                            END IF;
                            
                            INSERT INTO referral_bonuses (user_id, from_user_id, order_id, amount, level, eligible)
                            VALUES (v_level3_referrer_id, p_buyer_id, p_order_id, v_converted_bonus, 3, true);
                            
                            UPDATE users 
                            SET balance = balance + v_converted_bonus,
                                total_referral_earnings = COALESCE(total_referral_earnings, 0) + v_converted_bonus
                            WHERE id = v_level3_referrer_id;
                            
                            -- *** NEW: Create balance_transaction record ***
                            INSERT INTO balance_transactions (
                                user_id,
                                type,
                                amount,
                                currency,
                                balance_before,
                                balance_after,
                                status,
                                description,
                                reference_type,
                                reference_id,
                                metadata
                            ) VALUES (
                                v_level3_referrer_id,
                                'bonus',
                                v_converted_bonus,
                                v_referrer_balance_currency,
                                v_referrer.balance,
                                v_referrer.balance + v_converted_bonus,
                                'completed',
                                'Реферальный бонус L3 (' || v_settings.level3_commission_percent || '%) от ' || v_buyer_name,
                                'referral',
                                p_order_id::text,
                                jsonb_build_object(
                                    'level', 3,
                                    'percent', v_settings.level3_commission_percent,
                                    'from_user_id', p_buyer_id,
                                    'from_username', v_buyer_name,
                                    'order_amount', v_order_fiat_amount,
                                    'order_currency', v_order_fiat_currency
                                )
                            );
                            
                            v_result := v_result || jsonb_build_object('level3', v_converted_bonus);
                        ELSE
                            v_bonus_amount := v_order_fiat_amount * (v_settings.level3_commission_percent / 100.0);
                            INSERT INTO referral_bonuses (user_id, from_user_id, order_id, amount, level, eligible, ineligible_reason)
                            VALUES (v_level3_referrer_id, p_buyer_id, p_order_id, v_bonus_amount, 3, false, 'Level 3 not reached');
                        END IF;
                    END IF;
                END IF;
            END IF;
        END IF;
    END IF;
    
    RETURN jsonb_build_object('success', true) || v_result;
END;
$function$;

COMMENT ON FUNCTION process_referral_bonus IS 'Calculates and applies referral bonuses with multi-currency conversion. Now also creates balance_transaction records for audit trail.';

-- ============================================================
-- 3. Add index for faster transaction lookups
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_balance_transactions_reference 
ON balance_transactions(reference_type, reference_id) 
WHERE reference_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_balance_transactions_user_type 
ON balance_transactions(user_id, type, created_at DESC);

-- ============================================================
-- 4. Create update_user_turnover function (was missing!)
-- ============================================================

CREATE OR REPLACE FUNCTION public.update_user_turnover(
    p_user_id uuid,
    p_amount_rub numeric,
    p_usd_rate numeric DEFAULT 100.0
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO 'public'
AS $function$
DECLARE
    v_user users%ROWTYPE;
    v_settings referral_settings%ROWTYPE;
    v_old_turnover numeric;
    v_new_turnover numeric;
    v_old_level integer;
    v_new_level integer;
    v_level_up boolean := false;
BEGIN
    -- Get user with lock
    SELECT * INTO v_user FROM users WHERE id = p_user_id FOR UPDATE;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'User not found');
    END IF;
    
    -- Get settings for thresholds
    SELECT * INTO v_settings FROM referral_settings LIMIT 1;
    
    -- Calculate old level
    v_old_turnover := COALESCE(v_user.turnover_usd, 0);
    v_old_level := CASE
        WHEN v_user.is_partner AND v_user.partner_level_override IS NOT NULL THEN v_user.partner_level_override
        WHEN NOT COALESCE(v_user.referral_program_unlocked, false) THEN 0
        WHEN v_old_turnover >= COALESCE(v_settings.level3_threshold_usd, 80000) THEN 3
        WHEN v_old_turnover >= COALESCE(v_settings.level2_threshold_usd, 20000) THEN 2
        WHEN v_user.referral_program_unlocked THEN 1
        ELSE 0
    END;
    
    -- Update turnover (p_amount_rub is in RUB, but field is named _usd for legacy reasons)
    -- After RUB migration, we store RUB values directly
    v_new_turnover := v_old_turnover + p_amount_rub;
    
    UPDATE users 
    SET turnover_usd = v_new_turnover,
        total_purchases_amount = COALESCE(total_purchases_amount, 0) + p_amount_rub
    WHERE id = p_user_id;
    
    -- Calculate new level
    v_new_level := CASE
        WHEN v_user.is_partner AND v_user.partner_level_override IS NOT NULL THEN v_user.partner_level_override
        WHEN NOT COALESCE(v_user.referral_program_unlocked, false) THEN 0
        WHEN v_new_turnover >= COALESCE(v_settings.level3_threshold_usd, 80000) THEN 3
        WHEN v_new_turnover >= COALESCE(v_settings.level2_threshold_usd, 20000) THEN 2
        WHEN v_user.referral_program_unlocked THEN 1
        ELSE 0
    END;
    
    -- Check for level up
    IF v_new_level > v_old_level THEN
        v_level_up := true;
        
        -- Update level unlock timestamps
        IF v_new_level >= 2 AND v_old_level < 2 THEN
            UPDATE users SET level2_unlocked_at = NOW() WHERE id = p_user_id;
        END IF;
        IF v_new_level >= 3 AND v_old_level < 3 THEN
            UPDATE users SET level3_unlocked_at = NOW() WHERE id = p_user_id;
        END IF;
    END IF;
    
    RETURN jsonb_build_object(
        'success', true,
        'old_turnover', v_old_turnover,
        'new_turnover', v_new_turnover,
        'old_level', v_old_level,
        'new_level', v_new_level,
        'level_up', v_level_up
    );
END;
$function$;

COMMENT ON FUNCTION update_user_turnover IS 'Updates user turnover after purchase and checks for level progression. Thresholds: L2=20000 RUB, L3=80000 RUB.';

-- ============================================================
-- 5. Update referral_settings thresholds (RUB migration)
-- ============================================================

-- Update thresholds to RUB values (if still in USD)
UPDATE referral_settings 
SET level2_threshold_usd = 20000,
    level3_threshold_usd = 80000
WHERE level2_threshold_usd < 1000 OR level3_threshold_usd < 5000;

COMMENT ON TABLE referral_settings IS 'Referral program settings. Note: threshold fields named _usd but contain RUB values after migration.';
