-- Миграция: Добавление поддержки модели "под заказ" (On-Demand Orders)
-- Дата: 2025-11-XX

-- 1. Обновление таблицы products
ALTER TABLE products
ADD COLUMN IF NOT EXISTS fulfillment_time_hours INTEGER DEFAULT 48,
ADD COLUMN IF NOT EXISTS requires_prepayment BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS prepayment_percent INTEGER DEFAULT 100 CHECK (prepayment_percent >= 0 AND prepayment_percent <= 100);

COMMENT ON COLUMN products.fulfillment_time_hours IS 'Время выполнения заказа в часах (для товаров под заказ)';
COMMENT ON COLUMN products.requires_prepayment IS 'Требуется ли предоплата для этого товара';
COMMENT ON COLUMN products.prepayment_percent IS 'Процент предоплаты (0-100)';

-- 2. Обновление таблицы orders
ALTER TABLE orders
ADD COLUMN IF NOT EXISTS order_type VARCHAR(20) DEFAULT 'instant' CHECK (order_type IN ('instant', 'prepaid')),
ADD COLUMN IF NOT EXISTS fulfillment_deadline TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS refund_reason TEXT,
ADD COLUMN IF NOT EXISTS refund_processed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS supplier_notified_at TIMESTAMPTZ;

-- Обновление constraint для статусов
ALTER TABLE orders 
DROP CONSTRAINT IF EXISTS orders_status_check;

ALTER TABLE orders 
ADD CONSTRAINT orders_status_check 
CHECK (status IN ('pending', 'prepaid', 'fulfilling', 'ready', 'delivered', 'cancelled', 'refunded', 'failed'));

COMMENT ON COLUMN orders.order_type IS 'Тип заказа: instant (товар в наличии) или prepaid (под заказ)';
COMMENT ON COLUMN orders.fulfillment_deadline IS 'Дедлайн выполнения заказа (для предоплатных заказов)';
COMMENT ON COLUMN orders.refund_reason IS 'Причина возврата средств';
COMMENT ON COLUMN orders.refund_processed_at IS 'Дата и время обработки возврата';
COMMENT ON COLUMN orders.supplier_notified_at IS 'Дата и время уведомления поставщика';

-- 3. Создание функции create_order_with_availability_check
CREATE OR REPLACE FUNCTION create_order_with_availability_check(
    p_product_id UUID,
    p_user_telegram_id BIGINT,
    p_order_type VARCHAR DEFAULT 'instant'
)
RETURNS TABLE(
    order_id UUID,
    order_type VARCHAR,
    status VARCHAR,
    stock_item_id UUID,
    amount NUMERIC,
    requires_prepayment BOOLEAN,
    fulfillment_deadline TIMESTAMPTZ
) AS $$
DECLARE
    v_order_id UUID;
    v_stock_item_id UUID;
    v_amount NUMERIC;
    v_product RECORD;
    v_has_stock BOOLEAN;
    v_order_type VARCHAR;
    v_status VARCHAR;
    v_fulfillment_deadline TIMESTAMPTZ;
    v_price NUMERIC;
    v_discount NUMERIC;
    v_final_price NUMERIC;
    v_expires_at TIMESTAMPTZ;
BEGIN
    -- Получение информации о товаре
    -- Разрешаем заказы для active и out_of_stock (можно заказать под заказ)
    -- discontinued и coming_soon должны блокироваться на уровне API
    SELECT 
        p.*,
        EXISTS(
            SELECT 1 FROM stock_items si 
            WHERE si.product_id = p.id 
            AND si.is_sold = false 
            AND (si.expires_at IS NULL OR si.expires_at > NOW())
        ) as has_stock
    INTO v_product
    FROM products p
    WHERE p.id = p_product_id 
    AND p.status IN ('active', 'out_of_stock');
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Product not found or unavailable for ordering (status must be active or out_of_stock)';
    END IF;
    
    -- Определение типа заказа
    IF v_product.has_stock THEN
        -- Товар есть - резервируем
        SELECT 
            stock_item_id, 
            final_price,
            original_price,
            discount_percent,
            expires_at
        INTO v_stock_item_id, v_amount, v_price, v_discount, v_expires_at
        FROM reserve_product_for_purchase(p_product_id, p_user_telegram_id);
        
        v_order_type := 'instant';
        v_status := 'pending';
        v_fulfillment_deadline := NULL;
    ELSE
        -- Товара нет - предоплата
        v_stock_item_id := NULL;
        v_amount := v_product.price;
        v_price := v_product.price;
        v_discount := 0;
        v_expires_at := NULL;
        v_order_type := 'prepaid';
        v_status := 'pending';
        
        -- Расчет дедлайна выполнения
        v_fulfillment_deadline := NOW() + 
            (v_product.fulfillment_time_hours || ' hours')::INTERVAL;
    END IF;
    
    -- Создание заказа
    INSERT INTO orders (
        user_telegram_id,
        product_id,
        stock_item_id,
        amount,
        original_price,
        discount_percent,
        status,
        order_type,
        fulfillment_deadline,
        expires_at
    ) VALUES (
        p_user_telegram_id,
        p_product_id,
        v_stock_item_id,
        v_amount,
        v_price,
        v_discount,
        v_status,
        v_order_type,
        v_fulfillment_deadline,
        v_expires_at
    )
    RETURNING id INTO v_order_id;
    
    RETURN QUERY SELECT 
        v_order_id,
        v_order_type,
        v_status,
        v_stock_item_id,
        v_amount,
        v_product.requires_prepayment,
        v_fulfillment_deadline;
END;
$$ LANGUAGE plpgsql;

-- 4. Создание функции process_prepaid_payment
CREATE OR REPLACE FUNCTION process_prepaid_payment(
    p_order_id UUID,
    p_user_telegram_id BIGINT
)
RETURNS TABLE(
    success BOOLEAN,
    status VARCHAR,
    supplier_notified BOOLEAN
) AS $$
DECLARE
    v_order RECORD;
    v_supplier_id UUID;
BEGIN
    -- Получение заказа
    SELECT o.*, p.supplier_id INTO v_order, v_supplier_id
    FROM orders o
    INNER JOIN products p ON o.product_id = p.id
    WHERE o.id = p_order_id
    AND o.user_telegram_id = p_user_telegram_id
    AND o.status = 'pending'
    AND o.order_type = 'prepaid'
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Order not found or invalid status';
    END IF;
    
    -- Обновление статуса
    UPDATE orders
    SET status = 'prepaid',
        supplier_notified_at = NOW()
    WHERE id = p_order_id;
    
    -- Уведомление поставщика будет обработано в worker endpoint через QStash
    
    RETURN QUERY SELECT 
        true,
        'prepaid',
        true;
END;
$$ LANGUAGE plpgsql;

-- 5. Создание функции fulfill_prepaid_order
CREATE OR REPLACE FUNCTION fulfill_prepaid_order(
    p_order_id UUID,
    p_content TEXT,
    p_expires_at TIMESTAMPTZ
)
RETURNS TABLE(
    success BOOLEAN,
    status VARCHAR,
    stock_item_id UUID
) AS $$
DECLARE
    v_order RECORD;
    v_stock_item_id UUID;
BEGIN
    -- Получение заказа
    SELECT * INTO v_order
    FROM orders
    WHERE id = p_order_id
    AND status IN ('prepaid', 'fulfilling')
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Order not found or invalid status';
    END IF;
    
    -- Создание stock_item для этого заказа
    INSERT INTO stock_items (
        product_id,
        content,
        expires_at,
        is_sold,
        created_at
    ) VALUES (
        v_order.product_id,
        p_content,
        p_expires_at,
        true,  -- Сразу помечаем как проданный
        NOW()
    )
    RETURNING id INTO v_stock_item_id;
    
    -- Обновление заказа
    UPDATE orders
    SET stock_item_id = v_stock_item_id,
        status = 'ready',
        expires_at = p_expires_at
    WHERE id = p_order_id;
    
    RETURN QUERY SELECT true, 'ready', v_stock_item_id;
END;
$$ LANGUAGE plpgsql;

-- 6. Создание функции process_refund
CREATE OR REPLACE FUNCTION process_refund(
    p_order_id UUID,
    p_reason TEXT
)
RETURNS TABLE(
    success BOOLEAN,
    refund_amount NUMERIC,
    refund_to_balance BOOLEAN,
    new_balance NUMERIC
) AS $$
DECLARE
    v_order RECORD;
    v_refund_amount NUMERIC;
    v_new_balance NUMERIC;
BEGIN
    -- Получение заказа
    SELECT * INTO v_order
    FROM orders
    WHERE id = p_order_id
    AND status IN ('prepaid', 'fulfilling', 'failed', 'pending')
    FOR UPDATE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Order not found or cannot be refunded';
    END IF;
    
    v_refund_amount := v_order.amount;
    
    -- Обновление заказа
    UPDATE orders
    SET status = 'refunded',
        refund_reason = p_reason,
        refund_processed_at = NOW()
    WHERE id = p_order_id;
    
    -- Начисление на баланс пользователя
    UPDATE users
    SET balance = balance + v_refund_amount
    WHERE telegram_id = v_order.user_telegram_id
    RETURNING balance INTO v_new_balance;
    
    RETURN QUERY SELECT 
        true,
        v_refund_amount,
        true,
        v_new_balance;
END;
$$ LANGUAGE plpgsql;

-- 7. Создание индексов для оптимизации
CREATE INDEX IF NOT EXISTS idx_orders_order_type_status ON orders(order_type, status);
CREATE INDEX IF NOT EXISTS idx_orders_fulfillment_deadline ON orders(fulfillment_deadline) 
    WHERE fulfillment_deadline IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_orders_status_prepaid ON orders(status) 
    WHERE status IN ('prepaid', 'fulfilling');

-- 8. Комментарии к функциям
COMMENT ON FUNCTION create_order_with_availability_check IS 'Создает заказ с проверкой наличия товара. Если товара нет - создает предоплатный заказ.';
COMMENT ON FUNCTION process_prepaid_payment IS 'Обрабатывает предоплату и переводит заказ в статус prepaid';
COMMENT ON FUNCTION fulfill_prepaid_order IS 'Выполняет предоплатный заказ: создает stock_item и переводит заказ в статус ready';
COMMENT ON FUNCTION process_refund IS 'Обрабатывает возврат средств: переводит заказ в статус refunded и начисляет деньги на баланс пользователя';

