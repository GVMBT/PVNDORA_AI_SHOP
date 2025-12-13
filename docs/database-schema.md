# Схема Базы Данных (ERD) и Модель Данных

## Обзор

База данных построена на Supabase (PostgreSQL) с использованием расширений:
- `uuid-ossp` для генерации UUID
- `pgvector` для векторного поиска (RAG)

**Архитектура заказов:**
- `orders` — заголовок заказа (user, payment, статус)
- `order_items` — позиции заказа (товары, delivery, stock)

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
       ▼
┌─────────────┐
│  products   │
│─────────────│
│ id (PK)     │
│ name        │
│ description │
│ price       │
│ type        │ (ai|design|dev|music)
│ supplier_id │
│ warranty_hours│
│ duration_days│
│ fulfillment_time_hours│
│ requires_prepayment│
│ prepayment_percent│
│ status      │ (active|out_of_stock|discontinued|coming_soon)
│ msrp        │
│ categories  │
│ image_url   │
└──────┬──────┘
       │
       │ 1:N
       ▼
┌─────────────┐
│ stock_items │
│─────────────│
│ id (PK)     │
│ product_id  │───► products.id
│ content     │
│ status      │ (available|reserved|sold)
│ expires_at  │
│ discount_percent│
│ reserved_at │
│ sold_at     │
│ supplier_id │
│ created_at  │
└─────────────┘


┌─────────────┐
│   users     │
│─────────────│
│ id (PK)     │
│ telegram_id │ (UNIQUE)
│ username    │
│ first_name  │
│ balance     │
│ is_admin    │
│ referrer_id │───► users.id (self-reference)
│ ...         │
└──────┬──────┘
       │
       │ 1:N
       ▼
┌─────────────────┐
│     orders      │ (Заголовок заказа)
│─────────────────│
│ id (PK)         │
│ user_id         │───► users.id
│ user_telegram_id│ (денормализация для уведомлений)
│ amount          │ (общая сумма)
│ original_price  │
│ discount_percent│
│ status          │ (pending|prepaid|partial|delivered|cancelled|refunded)
│ order_type      │ (instant|prepaid)
│ payment_method  │
│ payment_gateway │
│ payment_id      │
│ payment_url     │
│ expires_at      │
│ delivered_at    │
│ warranty_until  │
│ created_at      │
└────────┬────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐
│  order_items    │ (Позиции заказа)
│─────────────────│
│ id (PK)         │
│ order_id        │───► orders.id
│ product_id      │───► products.id
│ stock_item_id   │───► stock_items.id (nullable)
│ quantity        │
│ price           │
│ discount_percent│
│ status          │ (pending|prepaid|delivered|refund_pending|failed)
│ fulfillment_type│ (instant|preorder)
│ delivery_content│ (credentials after delivery)
│ delivery_instructions│
│ expires_at      │ (license expiration)
│ delivered_at    │
│ created_at      │
│ updated_at      │
└─────────────────┘


┌─────────────┐
│   reviews   │
│─────────────│
│ id (PK)     │
│ user_id     │───► users.id
│ order_id    │───► orders.id (UNIQUE)
│ product_id  │───► products.id
│ rating      │ (1-5)
│ text        │
│ cashback_given│
│ created_at  │
└─────────────┘

┌─────────────┐
│  tickets    │
│─────────────│
│ id (PK)     │
│ user_id     │───► users.id
│ order_id    │───► orders.id
│ status      │ (open|approved|rejected|closed)
│ issue_type  │
│ description │
│ admin_comment│
│ created_at  │
└─────────────┘
```

## SQL View: available_stock_with_discounts

View для получения доступных товаров со скидками:

```sql
CREATE OR REPLACE VIEW available_stock_with_discounts AS
SELECT 
    si.id AS stock_item_id,
    si.product_id,
    p.name AS product_name,
    p.price AS original_price,
    p.msrp,
    p.type AS product_type,
    p.warranty_hours,
    p.duration_days,
    si.discount_percent,
    ROUND(p.price * (1 - COALESCE(si.discount_percent, 0) / 100), 2) AS final_price,
    ROUND(COALESCE(p.msrp, p.price) - (p.price * (1 - COALESCE(si.discount_percent, 0) / 100)), 2) AS savings,
    si.expires_at,
    si.created_at AS stock_added_at
FROM stock_items si
JOIN products p ON si.product_id = p.id
WHERE 
    si.status = 'available'
    AND p.status = 'active'
    AND (si.expires_at IS NULL OR si.expires_at > NOW());
```

## SQL View: product_social_proof

View для социального доказательства (рейтинги, отзывы, продажи):

```sql
CREATE OR REPLACE VIEW product_social_proof AS
SELECT 
    p.id AS product_id,
    p.name AS product_name,
    COALESCE(AVG(r.rating), 0) AS avg_rating,
    COUNT(DISTINCT r.id) AS review_count,
    COUNT(DISTINCT CASE WHEN oi.status = 'delivered' THEN oi.id END) AS sales_count,
    (
        SELECT json_agg(json_build_object(
            'rating', sub_r.rating,
            'text', sub_r.text,
            'created_at', sub_r.created_at,
            'author', u.first_name
        ) ORDER BY sub_r.created_at DESC)
        FROM (
            SELECT * FROM reviews 
            WHERE product_id = p.id 
            ORDER BY created_at DESC 
            LIMIT 5
        ) sub_r
        LEFT JOIN users u ON sub_r.user_id = u.id
    ) AS recent_reviews
FROM products p
LEFT JOIN reviews r ON p.id = r.product_id
LEFT JOIN order_items oi ON p.id = oi.product_id
WHERE p.status = 'active'
GROUP BY p.id, p.name;
```

## SQL View: product_metrics

View для аналитики товаров:

```sql
CREATE OR REPLACE VIEW product_metrics AS
SELECT 
    p.id,
    p.name,
    p.price,
    p.type,
    COUNT(DISTINCT oi.order_id) AS total_orders,
    COUNT(DISTINCT CASE WHEN oi.status = 'delivered' THEN oi.order_id END) AS completed_orders,
    SUM(CASE WHEN oi.status = 'delivered' THEN oi.price ELSE 0 END) AS total_revenue,
    COUNT(DISTINCT o.user_id) AS unique_buyers,
    AVG(CASE WHEN r.rating IS NOT NULL THEN r.rating ELSE NULL END) AS avg_rating,
    COUNT(r.id) AS review_count,
    (SELECT COUNT(*) FROM stock_items si WHERE si.product_id = p.id AND si.status = 'available') AS current_stock,
    (SELECT COUNT(*) FROM wishlist w WHERE w.product_id = p.id) AS wishlist_count
FROM products p
LEFT JOIN order_items oi ON oi.product_id = p.id
LEFT JOIN orders o ON oi.order_id = o.id
LEFT JOIN reviews r ON r.product_id = p.id
GROUP BY p.id, p.name, p.price, p.type
ORDER BY total_revenue DESC NULLS LAST;
```

## Статусы

### stock_items.status
| Статус | Описание |
|--------|----------|
| `available` | Доступен для продажи |
| `reserved` | Зарезервирован (ожидает оплаты) |
| `sold` | Продан |

### orders.status
| Статус | Описание |
|--------|----------|
| `pending` | Ожидает оплаты |
| `prepaid` | Оплачен, товар под заказ |
| `partial` | Частично выдан (часть товаров доставлена) |
| `delivered` | Полностью выдан |
| `cancelled` | Отменен |
| `refunded` | Возвращен |

### order_items.status
| Статус | Описание |
|--------|----------|
| `pending` | Ожидает оплаты/выдачи |
| `prepaid` | Оплачен, ждет поставки |
| `delivered` | Выдан пользователю |
| `refund_pending` | Запрошен возврат |
| `replacement_pending` | Запрошена замена |
| `failed` | Ошибка выдачи |

## Ключевые RPC-функции

### reserve_stock_item
Атомарное резервирование товара:
```sql
CREATE OR REPLACE FUNCTION reserve_stock_item(p_stock_item_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE stock_items 
    SET status = 'reserved', reserved_at = NOW()
    WHERE id = p_stock_item_id AND status = 'available';
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;
```

## Индексы для Производительности

```sql
-- Stock items: быстрый поиск доступных
CREATE INDEX idx_stock_items_product_status 
    ON stock_items(product_id, status) 
    WHERE status = 'available';

-- Orders: поиск по пользователю и статусу
CREATE INDEX idx_orders_user_status ON orders(user_id, status);
CREATE INDEX idx_orders_created_at ON orders(created_at DESC);

-- Order items: поиск по заказу
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);

-- Products: фильтрация активных
CREATE INDEX idx_products_status ON products(status) WHERE status = 'active';
```

## Денормализация

### user_telegram_id в orders
Поле `orders.user_telegram_id` — это денормализация `users.telegram_id` для быстрого доступа в workers без JOIN. Используется для отправки уведомлений после оплаты.

## Вспомогательные таблицы

- `waitlist` — список ожидания товара
- `wishlist` — избранные товары пользователя
- `promo_codes` — промокоды на скидку
- `faq` — часто задаваемые вопросы
- `analytics_events` — события аналитики
- `chat_history` — история чата с AI
- `referral_bonuses` — начисленные реферальные бонусы
- `referral_settings` — настройки реферальной программы
- `withdrawal_requests` — запросы на вывод средств
- `partner_applications` — заявки на партнерство
