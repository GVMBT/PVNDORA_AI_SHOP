-- Migration: Fix Referral Bonus Multi-Currency Conversion
-- 
-- Problem: Referral bonuses are calculated in USD (orders.amount) and directly 
-- added to referrer's balance without considering referrer's balance_currency.
-- This causes incorrect balances when referrer's balance_currency is not USD.
--
-- Solution:
-- 1. Calculate bonus from fiat_amount (buyer's payment currency)
-- 2. Convert bonus from buyer's fiat_currency to referrer's balance_currency
-- 3. Use exchange_rates table for conversion (via USD)
--
-- Logic:
-- - If buyer pays in currency X, referrer has balance in currency Y:
--   - Bonus in X: bonus_x = fiat_amount * (percent / 100.0)
--   - Convert via USD: bonus_y = bonus_x * (rate_y / rate_x)
--   - Where rate_x = exchange rate for currency X (1 USD = rate_x X)
--   - Where rate_y = exchange rate for currency Y (1 USD = rate_y Y)
-- - Fallback: If fiat_amount is NULL, use p_order_amount (USD)

-- ============================================================
-- 1. Update process_referral_bonus function
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
    v_bonus_currency varchar(3);  -- Currency of calculated bonus
    v_referrer_balance_currency varchar(3);
    v_buyer_rate numeric;  -- Exchange rate for buyer's currency (1 USD = rate)
    v_referrer_rate numeric;  -- Exchange rate for referrer's currency (1 USD = rate)
    v_converted_bonus numeric;
BEGIN
    -- Загружаем динамические настройки
    SELECT * INTO v_settings FROM referral_settings LIMIT 1;
    
    -- Получаем заказ с fiat_amount и fiat_currency
    SELECT * INTO v_order FROM orders WHERE id = p_order_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'Order not found');
    END IF;
    
    -- Определяем валюту для расчета бонуса
    -- Приоритет: fiat_amount (что реально заплатил покупатель) > USD amount
    IF v_order.fiat_amount IS NOT NULL AND v_order.fiat_currency IS NOT NULL THEN
        v_order_fiat_amount := v_order.fiat_amount;
        v_order_fiat_currency := v_order.fiat_currency;
        v_bonus_currency := v_order.fiat_currency;
    ELSE
        -- Fallback: используем USD
        v_order_fiat_amount := p_order_amount;
        v_order_fiat_currency := 'USD';
        v_bonus_currency := 'USD';
    END IF;
    
    -- Получаем курс валюты покупателя (1 USD = rate)
    SELECT rate INTO v_buyer_rate FROM exchange_rates WHERE currency = v_order_fiat_currency;
    IF v_buyer_rate IS NULL THEN
        -- Fallback: если курс не найден, считаем что это USD
        v_buyer_rate := 1.0;
        IF v_order_fiat_currency != 'USD' THEN
            RAISE WARNING 'Exchange rate not found for currency %, using 1.0', v_order_fiat_currency;
        END IF;
    END IF;
    
    -- Получаем покупателя
    SELECT * INTO v_buyer FROM users WHERE id = p_buyer_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'error', 'Buyer not found');
    END IF;
    
    -- Проверяем есть ли реферер (level 1)
    v_level1_referrer_id := v_buyer.referrer_id;
    IF v_level1_referrer_id IS NULL THEN
        RETURN jsonb_build_object('success', true, 'bonuses', '[]'::jsonb, 'message', 'No referrer');
    END IF;
    
    -- ============== LEVEL 1 BONUS ==============
    SELECT * INTO v_referrer FROM users WHERE id = v_level1_referrer_id;
    IF FOUND THEN
        v_turnover := COALESCE(v_referrer.turnover_usd, 0);
        v_referrer_balance_currency := COALESCE(v_referrer.balance_currency, 'USD');
        
        -- Level 1 открыт СРАЗУ после любой покупки (threshold = 0)
        -- Или партнёр с override
        v_effective_level := CASE 
            WHEN v_referrer.is_partner AND v_referrer.partner_level_override IS NOT NULL THEN v_referrer.partner_level_override
            WHEN NOT v_referrer.referral_program_unlocked THEN 0
            WHEN v_turnover >= v_settings.level3_threshold_usd THEN 3
            WHEN v_turnover >= v_settings.level2_threshold_usd THEN 2
            WHEN v_referrer.referral_program_unlocked THEN 1  -- Сразу Level 1!
            ELSE 0
        END;
        
        IF v_effective_level >= 1 THEN
            -- Рассчитываем бонус в валюте покупателя
            v_bonus_amount := v_order_fiat_amount * (v_settings.level1_commission_percent / 100.0);
            
            -- Конвертируем бонус в валюту баланса реферера
            SELECT rate INTO v_referrer_rate FROM exchange_rates WHERE currency = v_referrer_balance_currency;
            IF v_referrer_rate IS NULL THEN
                v_referrer_rate := 1.0;
                IF v_referrer_balance_currency != 'USD' THEN
                    RAISE WARNING 'Exchange rate not found for currency %, using 1.0', v_referrer_balance_currency;
                END IF;
            END IF;
            
            -- Конвертация: bonus_referrer_currency = bonus_buyer_currency * (referrer_rate / buyer_rate)
            v_converted_bonus := v_bonus_amount * (v_referrer_rate / v_buyer_rate);
            
            -- Округляем для целочисленных валют (RUB, JPY, KRW и т.д.)
            IF v_referrer_balance_currency IN ('RUB', 'JPY', 'KRW', 'UAH', 'TRY', 'INR', 'CNY', 'BRL') THEN
                v_converted_bonus := ROUND(v_converted_bonus);
            ELSE
                v_converted_bonus := ROUND(v_converted_bonus, 2);
            END IF;
            
            INSERT INTO referral_bonuses (user_id, from_user_id, order_id, amount, level, eligible)
            VALUES (v_level1_referrer_id, p_buyer_id, p_order_id, v_converted_bonus, 1, true);
            
            UPDATE users 
            SET balance = balance + v_converted_bonus,
                total_referral_earnings = COALESCE(total_referral_earnings, 0) + v_converted_bonus
            WHERE id = v_level1_referrer_id;
            
            v_result := v_result || jsonb_build_object('level1', v_converted_bonus);
        ELSE
            -- Рассчитываем бонус для записи (но не начисляем)
            v_bonus_amount := v_order_fiat_amount * (v_settings.level1_commission_percent / 100.0);
            INSERT INTO referral_bonuses (user_id, from_user_id, order_id, amount, level, eligible, ineligible_reason)
            VALUES (v_level1_referrer_id, p_buyer_id, p_order_id, 
                    v_bonus_amount, 1, false, 
                    'Program not unlocked');
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
                    -- Рассчитываем бонус в валюте покупателя
                    v_bonus_amount := v_order_fiat_amount * (v_settings.level2_commission_percent / 100.0);
                    
                    -- Конвертируем бонус в валюту баланса реферера
                    SELECT rate INTO v_referrer_rate FROM exchange_rates WHERE currency = v_referrer_balance_currency;
                    IF v_referrer_rate IS NULL THEN
                        v_referrer_rate := 1.0;
                        IF v_referrer_balance_currency != 'USD' THEN
                            RAISE WARNING 'Exchange rate not found for currency %, using 1.0', v_referrer_balance_currency;
                        END IF;
                    END IF;
                    
                    -- Конвертация
                    v_converted_bonus := v_bonus_amount * (v_referrer_rate / v_buyer_rate);
                    
                    -- Округляем для целочисленных валют
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
                    
                    v_result := v_result || jsonb_build_object('level2', v_converted_bonus);
                ELSE
                    -- Рассчитываем бонус для записи (но не начисляем)
                    v_bonus_amount := v_order_fiat_amount * (v_settings.level2_commission_percent / 100.0);
                    INSERT INTO referral_bonuses (user_id, from_user_id, order_id, amount, level, eligible, ineligible_reason)
                    VALUES (v_level2_referrer_id, p_buyer_id, p_order_id,
                            v_bonus_amount, 2, false,
                            'Level 2 not reached (turnover: ' || v_turnover || ')');
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
                            ELSE 
                                CASE WHEN v_turnover >= v_settings.level2_threshold_usd THEN 2 ELSE 1 END
                        END;
                        
                        IF v_effective_level >= 3 THEN
                            -- Рассчитываем бонус в валюте покупателя
                            v_bonus_amount := v_order_fiat_amount * (v_settings.level3_commission_percent / 100.0);
                            
                            -- Конвертируем бонус в валюту баланса реферера
                            SELECT rate INTO v_referrer_rate FROM exchange_rates WHERE currency = v_referrer_balance_currency;
                            IF v_referrer_rate IS NULL THEN
                                v_referrer_rate := 1.0;
                                IF v_referrer_balance_currency != 'USD' THEN
                                    RAISE WARNING 'Exchange rate not found for currency %, using 1.0', v_referrer_balance_currency;
                                END IF;
                            END IF;
                            
                            -- Конвертация
                            v_converted_bonus := v_bonus_amount * (v_referrer_rate / v_buyer_rate);
                            
                            -- Округляем для целочисленных валют
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
                            
                            v_result := v_result || jsonb_build_object('level3', v_converted_bonus);
                        ELSE
                            -- Рассчитываем бонус для записи (но не начисляем)
                            v_bonus_amount := v_order_fiat_amount * (v_settings.level3_commission_percent / 100.0);
                            INSERT INTO referral_bonuses (user_id, from_user_id, order_id, amount, level, eligible, ineligible_reason)
                            VALUES (v_level3_referrer_id, p_buyer_id, p_order_id,
                                    v_bonus_amount, 3, false,
                                    'Level 3 not reached (turnover: ' || v_turnover || ')');
                        END IF;
                    END IF;
                END IF;
            END IF;
        END IF;
    END IF;
    
    RETURN jsonb_build_object('success', true) || v_result;
END;
$function$;

-- ============================================================
-- 2. Update rollback_user_turnover function
-- ============================================================

CREATE OR REPLACE FUNCTION public.rollback_user_turnover(
    p_user_id uuid, 
    p_amount_rub numeric, 
    p_usd_rate numeric DEFAULT 100, 
    p_order_id uuid DEFAULT NULL::uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $function$
DECLARE
    v_amount_usd NUMERIC;
    v_bonuses_revoked INTEGER := 0;
    v_referrer_id UUID;
    v_order orders%ROWTYPE;
    v_order_fiat_amount numeric;
    v_order_fiat_currency varchar(3);
    v_buyer_rate numeric;
    v_referrer_balance_currency varchar(3);
    v_referrer_rate numeric;
    v_revoked_bonus numeric;
    v_converted_revoked_bonus numeric;
BEGIN
    v_amount_usd := p_amount_rub / p_usd_rate;
    
    -- Get referrer_id if exists (needed to recalculate referrer's turnover)
    SELECT referrer_id INTO v_referrer_id FROM users WHERE id = p_user_id;
    
    -- Mark order as refunded (if status allows)
    IF p_order_id IS NOT NULL THEN
        -- Update order status to refunded (if not already)
        UPDATE orders 
        SET status = 'refunded'
        WHERE id = p_order_id AND status NOT IN ('refunded', 'cancelled');
        
        -- Получаем заказ для определения валюты
        SELECT * INTO v_order FROM orders WHERE id = p_order_id;
        
        -- Определяем валюту заказа
        IF v_order.fiat_amount IS NOT NULL AND v_order.fiat_currency IS NOT NULL THEN
            v_order_fiat_amount := v_order.fiat_amount;
            v_order_fiat_currency := v_order.fiat_currency;
        ELSE
            -- Fallback: USD
            v_order_fiat_currency := 'USD';
        END IF;
        
        -- Получаем курс валюты покупателя
        SELECT rate INTO v_buyer_rate FROM exchange_rates WHERE currency = v_order_fiat_currency;
        IF v_buyer_rate IS NULL THEN
            v_buyer_rate := 1.0;
        END IF;
    END IF;
    
    -- Recalculate buyer's turnover (now it will exclude the refunded order)
    PERFORM recalculate_user_turnover(p_user_id);
    
    -- If buyer has a referrer, also recalculate referrer's turnover
    IF v_referrer_id IS NOT NULL THEN
        PERFORM recalculate_user_turnover(v_referrer_id);
    END IF;
    
    -- Revoke referral bonuses paid for this order
    IF p_order_id IS NOT NULL THEN
        -- Mark bonuses as ineligible
        UPDATE referral_bonuses 
        SET eligible = false, ineligible_reason = 'Order refunded'
        WHERE order_id = p_order_id AND eligible = true;
        
        GET DIAGNOSTICS v_bonuses_revoked = ROW_COUNT;
        
        -- Rollback balance and earnings of bonus recipients
        -- Для каждого реферера конвертируем сумму в его валюту баланса
        FOR v_referrer_id, v_revoked_bonus IN 
            SELECT rb.user_id, rb.amount
            FROM referral_bonuses rb
            WHERE rb.order_id = p_order_id 
              AND rb.eligible = false
        LOOP
            -- Получаем валюту баланса реферера
            SELECT balance_currency INTO v_referrer_balance_currency 
            FROM users WHERE id = v_referrer_id;
            
            v_referrer_balance_currency := COALESCE(v_referrer_balance_currency, 'USD');
            
            -- Получаем курс валюты реферера
            SELECT rate INTO v_referrer_rate FROM exchange_rates WHERE currency = v_referrer_balance_currency;
            IF v_referrer_rate IS NULL THEN
                v_referrer_rate := 1.0;
            END IF;
            
            -- Конвертируем откатываемую сумму из валюты заказа в валюту баланса реферера
            -- v_revoked_bonus уже в валюте баланса реферера (был сохранен так при начислении)
            -- Но для правильного отката нужно использовать ту же сумму (она уже сконвертирована)
            v_converted_revoked_bonus := v_revoked_bonus;
            
            -- Откатываем баланс и earnings
            UPDATE users
            SET balance = GREATEST(0, balance - v_converted_revoked_bonus),
                total_referral_earnings = GREATEST(0, COALESCE(total_referral_earnings, 0) - v_converted_revoked_bonus)
            WHERE id = v_referrer_id;
        END LOOP;
    END IF;
    
    -- Update total_purchases_amount (subtract the refunded amount)
    UPDATE users 
    SET total_purchases_amount = GREATEST(0, COALESCE(total_purchases_amount, 0) - p_amount_rub)
    WHERE id = p_user_id;
    
    RETURN jsonb_build_object(
        'success', true,
        'amount_usd_revoked', v_amount_usd,
        'bonuses_revoked', v_bonuses_revoked
    );
END;
$function$;

-- ============================================================
-- Comments
-- ============================================================

COMMENT ON FUNCTION process_referral_bonus IS 
'Calculates and applies referral bonuses with multi-currency conversion. 
Bonus is calculated from buyer''s fiat_amount (payment currency) and converted 
to referrer''s balance_currency using exchange_rates table.';

COMMENT ON FUNCTION rollback_user_turnover IS 
'Rolls back user turnover and revokes referral bonuses for refunded orders.
Revoked bonuses are deducted from referrer''s balance in their balance_currency.';
