# Схема Базы Данных (ERD) и Модель Данных

## Обзор

База данных построена на Supabase (PostgreSQL) с использованием расширений:
- `uuid-ossp` для генерации UUID
- `pgvector` для векторного поиска (RAG)

## ERD Диаграмма

```
┌─────────────┐
│  suppliers  │
│─────────────│
│ id (PK)     │
│ name        │
│ telegram_id │
└──────┬──────┘
       │
       │ 1:N
       │
┌──────▼──────┐
│  products   │
│─────────────│
│ id (PK)     │
│ name        │
│ description │
│ price       │
│ type        │
│ supplier_id │◄──┐
│ warranty_days│  │
│ duration_days│  │
│ fulfillment_time_hours│
│ requires_prepayment│
│ prepayment_percent│
│ status      │   │
└──────┬──────┘   │
       │          │
       │ 1:N      │
       │          │
┌──────▼──────┐   │
│ stock_items │   │
│─────────────│   │
│ id (PK)     │   │
│ product_id  │───┘
│ content     │
│ expires_at  │
│ is_sold     │
│ created_at  │
└─────────────┘

┌─────────────┐
│   users     │
│─────────────│
│ telegram_id (PK) │
│ referrer_telegram_id │◄──┐ (self-reference)
│ balance     │   │
│ is_admin    │   │
└──────┬──────┘   │
       │          │
       │ 1:N      │
       │          │
┌──────▼──────┐   │
│   orders    │   │
│─────────────│   │
│ id (PK)     │   │
│ user_telegram_id │───┘
│ product_id  │
│ stock_item_id│
│ amount      │
│ original_price│
│ discount_percent│
│ status      │ (pending|prepaid|fulfilling|ready|delivered|cancelled|refunded|failed)
│ order_type  │ (instant|prepaid)
│ fulfillment_deadline│
│ refund_reason│
│ refund_processed_at│
│ expires_at  │
└─────────────┘

┌─────────────┐
│  tickets    │
│─────────────│
│ id (PK)     │
│ user_id     │
│ order_id    │
│ status      │
└─────────────┘
```

## SQL View: available_stock_with_discounts

Критически важный View для оптимизации производительности:

```sql
CREATE OR REPLACE VIEW available_stock_with_discounts AS
SELECT 
    si.id as stock_item_id,
    p.id as product_id,
    p.name,
    p.price as original_price,
    p.duration_days,
    si.expires_at,
    si.created_at as stock_created_at,
    CASE 
        WHEN p.duration_days IS NOT NULL THEN
            LEAST(
                20.0,  -- Максимальная скидка 20%
                GREATEST(
                    0.0,
                    (EXTRACT(EPOCH FROM (NOW() - si.created_at)) / 86400.0) / 
                    NULLIF(p.duration_days, 0) * 100.0 * 0.5  -- Коэффициент 0.5
                )
            )
        WHEN si.expires_at IS NOT NULL THEN
            LEAST(
                20.0,
                GREATEST(
                    0.0,
                    (EXTRACT(EPOCH FROM (NOW() - si.created_at)) / 86400.0) / 
                    NULLIF(EXTRACT(EPOCH FROM (si.expires_at - si.created_at)) / 86400.0, 0) * 100.0 * 0.5
                )
            )
        ELSE 0.0
    END as discount_percent,
    (p.price * (1 - 
        CASE 
            WHEN p.duration_days IS NOT NULL THEN
                LEAST(20.0, GREATEST(0.0, 
                    (EXTRACT(EPOCH FROM (NOW() - si.created_at)) / 86400.0) / 
                    NULLIF(p.duration_days, 0) * 100.0 * 0.5)) / 100.0
            WHEN si.expires_at IS NOT NULL THEN
                LEAST(20.0, GREATEST(0.0,
                    (EXTRACT(EPOCH FROM (NOW() - si.created_at)) / 86400.0) / 
                    NULLIF(EXTRACT(EPOCH FROM (si.expires_at - si.created_at)) / 86400.0, 0) * 100.0 * 0.5)) / 100.0
            ELSE 0.0
        END
    )) as final_price
FROM stock_items si
INNER JOIN products p ON si.product_id = p.id
WHERE 
    si.is_sold = false
    AND p.status = 'active'
    AND (
        si.expires_at IS NULL 
        OR si.expires_at > NOW()
    );
```

## Хранимые Процедуры (RPC)

### 1. reserve_product_for_purchase

Атомарная процедура для резервирования товара:

```sql
CREATE OR REPLACE FUNCTION reserve_product_for_purchase(
    p_product_id UUID,
    p_user_telegram_id BIGINT,
    p_reservation_ttl INTERVAL DEFAULT '15 minutes'
)
RETURNS TABLE(
    order_id UUID,
    stock_item_id UUID,
    original_price NUMERIC,
    discount_percent NUMERIC,
    final_price NUMERIC,
    expires_at TIMESTAMPTZ
) AS $$
DECLARE
    v_stock_item_id UUID;
    v_price NUMERIC;
    v_discount NUMERIC;
    v_final_price NUMERIC;
    v_expires_at TIMESTAMPTZ;
    v_order_id UUID;
    v_user_id BIGINT;
BEGIN
    -- Получение user_id (если пользователь не существует, создается автоматически через триггер)
    SELECT telegram_id INTO v_user_id FROM users WHERE telegram_id = p_user_telegram_id;
    
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'User not found';
    END IF;
    
    -- Блокировка строки напрямую в stock_items для надежности
    SELECT si.id, 
           (p.price * (1 - COALESCE(v.discount_percent, 0) / 100.0)),
           COALESCE(v.discount_percent, 0),
           p.price,
           si.expires_at
    INTO v_stock_item_id, v_final_price, v_discount, v_price, v_expires_at
    FROM stock_items si
    INNER JOIN products p ON si.product_id = p.id
    LEFT JOIN LATERAL (
        SELECT discount_percent 
        FROM available_stock_with_discounts 
        WHERE stock_item_id = si.id
    ) v ON true
    WHERE si.product_id = p_product_id
    AND si.is_sold = false
    AND p.status = 'active'
    AND (si.expires_at IS NULL OR si.expires_at > NOW())
    FOR UPDATE SKIP LOCKED
    LIMIT 1;
    
    IF v_stock_item_id IS NULL THEN
        RAISE EXCEPTION 'Product not available';
    END IF;
    
    -- Создание заказа со статусом pending в рамках той же транзакции
    INSERT INTO orders (
        user_telegram_id,
        product_id,
        stock_item_id,
        amount,
        original_price,
        discount_percent,
        status,
        expires_at
    ) VALUES (
        p_user_telegram_id,
        p_product_id,
        v_stock_item_id,
        v_final_price,
        v_price,
        v_discount,
        'pending',
        v_expires_at
    )
    RETURNING id INTO v_order_id;
    
    RETURN QUERY SELECT 
        v_order_id,
        v_stock_item_id,
        v_price,
        v_discount,
        v_final_price,
        v_expires_at;
END;
$$ LANGUAGE plpgsql;
```

### 2. complete_purchase

Атомарная процедура для завершения покупки:

```sql
CREATE OR REPLACE FUNCTION complete_purchase(
    p_order_id UUID,
    p_stock_item_id UUID,
    p_user_telegram_id BIGINT
)
RETURNS TABLE(
    success BOOLEAN,
    content TEXT,
    expires_at TIMESTAMPTZ
) AS $$
DECLARE
    v_content TEXT;
    v_expires_at TIMESTAMPTZ;
BEGIN
    -- Атомарная транзакция: пометить товар как проданный и получить контент
    UPDATE stock_items
    SET is_sold = true
    WHERE id = p_stock_item_id
    AND is_sold = false
    RETURNING content, expires_at INTO v_content, v_expires_at;
    
    IF v_content IS NULL THEN
        RAISE EXCEPTION 'Stock item already sold or not found';
    END IF;
    
    -- Обновление статуса заказа
    UPDATE orders
    SET status = 'paid',
        stock_item_id = p_stock_item_id
    WHERE id = p_order_id
    AND user_telegram_id = p_user_telegram_id
    AND status = 'pending';
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Order not found or already processed';
    END IF;
    
    RETURN QUERY SELECT true, v_content, v_expires_at;
END;
$$ LANGUAGE plpgsql;
```

## Векторная Коллекция (vecs)

### Создание Коллекции

```python
import vecs

vx = vecs.create_client(SUPABASE_CONNECTION_STRING)

# Создание коллекции для товаров
products_collection = vx.create_collection(
    name="products",
    dimension=768,  # Gemini embedding dimension
    metric=vecs.distance.cosine
)
```

### Структура Векторных Данных

```python
# Метаданные для каждого вектора
metadata = {
    "product_id": "uuid",
    "name": "ChatGPT Plus",
    "type": "shared",
    "status": "active"
}
```

## Геймификация: Поля для "Money Saved"

**Добавление полей для расчета экономии:**

```sql
-- Добавить поле msrp в products (если еще не добавлено)
ALTER TABLE products ADD COLUMN IF NOT EXISTS msrp NUMERIC;

-- Добавить поле total_saved в users (если еще не добавлено)
ALTER TABLE users ADD COLUMN IF NOT EXISTS total_saved NUMERIC DEFAULT 0;

-- Обновление total_saved при покупке
CREATE OR REPLACE FUNCTION update_user_savings()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'paid' AND OLD.status != 'paid' THEN
        UPDATE users
        SET total_saved = total_saved + COALESCE(
            (SELECT msrp - NEW.amount FROM products WHERE id = NEW.product_id),
            0
        )
        WHERE telegram_id = NEW.user_telegram_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_savings
AFTER UPDATE ON orders
FOR EACH ROW
WHEN (NEW.status = 'paid' AND OLD.status != 'paid')
EXECUTE FUNCTION update_user_savings();
```

## Redis Sorted Sets для Лидербордов

**Структура данных в Redis:**

```python
# Ключ для лидерборда
LEADERBOARD_KEY = "leaderboard:money_saved"

# Добавление/обновление пользователя в лидерборде
redis.zadd(LEADERBOARD_KEY, {user_id: total_saved})

# Получение топ-10
top_users = redis.zrevrange(LEADERBOARD_KEY, 0, 9, withscores=True)
```

## Индексы для Производительности

```sql
-- Индексы для быстрого поиска
CREATE INDEX idx_stock_items_product_sold ON stock_items(product_id, is_sold) WHERE is_sold = false;
CREATE INDEX idx_orders_user_status ON orders(user_telegram_id, status);
CREATE INDEX idx_orders_created_at ON orders(created_at);
CREATE INDEX idx_products_status ON products(status) WHERE status = 'active';
CREATE INDEX idx_users_total_saved ON users(total_saved DESC); -- Для лидерборда

-- Индекс для векторного поиска (pgvector)
CREATE INDEX idx_products_embedding ON products USING ivfflat (embedding vector_cosine_ops);
```

## Триггеры

### Триггер для уведомления о продаже

```sql
-- Уведомление поставщиков обрабатывается через QStash, а не через триггеры
-- Триггер удален для обеспечения надежности через специализированную очередь
```

