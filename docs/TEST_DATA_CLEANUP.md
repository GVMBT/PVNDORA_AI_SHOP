# Очистка тестовых данных перед продакшеном

Документ содержит список всех тестовых данных, которые могут появиться в режиме разработки/песочницы, и инструкции по их очистке перед запуском в продакшен.

## ⚠️ ВАЖНО

**ВСЕГДА делайте бэкап базы данных перед очисткой!**

```bash
# Создать бэкап через Supabase Dashboard или CLI
# Settings → Database → Backups → Create backup
```

---

## 📋 Список таблиц с тестовыми данными

### 1. **users** (Пользователи)
**Что очищать:**
- Тестовые пользователи (без реальных заказов)
- Пользователи с `total_saved = 0` и без заказов
- Пользователи с тестовыми username (например, содержащие "test", "demo", "admin_test")

**SQL для проверки:**
```sql
-- Найти тестовых пользователей
SELECT id, telegram_id, username, first_name, total_saved, created_at 
FROM users 
WHERE total_saved = 0 
  AND id NOT IN (SELECT DISTINCT user_id FROM orders WHERE user_id IS NOT NULL)
  AND created_at < NOW() - INTERVAL '1 day'
ORDER BY created_at DESC;
```

**SQL для очистки:**
```sql
-- ⚠️ ОСТОРОЖНО: Удаляет пользователей без заказов
DELETE FROM users 
WHERE total_saved = 0 
  AND created_at < NOW() - INTERVAL '1 day'
  AND id NOT IN (SELECT DISTINCT user_id FROM orders WHERE user_id IS NOT NULL);
```

---

### 2. **orders** (Заказы)
**Что очищать:**
- Тестовые заказы (статус `pending`, `cancelled`)
- Заказы с тестовыми суммами
- Заказы старше определенной даты (если это тестовые)

**SQL для проверки:**
```sql
-- Найти тестовые заказы
SELECT id, user_id, amount, status, payment_method, created_at 
FROM orders 
WHERE status IN ('pending', 'cancelled')
  OR amount < 1  -- Тестовые суммы
ORDER BY created_at DESC;
```

**SQL для очистки:**
```sql
-- ⚠️ Сначала удалить связанные order_items
DELETE FROM order_items WHERE order_id IN (
  SELECT id FROM orders 
  WHERE status IN ('pending', 'cancelled')
    OR amount < 1
);

-- Затем удалить заказы
DELETE FROM orders 
WHERE status IN ('pending', 'cancelled')
  OR amount < 1;
```

---

### 3. **order_items** (Элементы заказов)
**Что очищать:**
- Элементы удаленных заказов (удаляются каскадно, но лучше проверить)

**SQL для проверки:**
```sql
-- Найти "осиротевшие" элементы заказов
SELECT oi.id, oi.order_id, oi.product_id, oi.status
FROM order_items oi
LEFT JOIN orders o ON o.id = oi.order_id
WHERE o.id IS NULL;
```

**SQL для очистки:**
```sql
-- Удалить элементы несуществующих заказов
DELETE FROM order_items 
WHERE order_id NOT IN (SELECT id FROM orders);
```

---

### 4. **balance_transactions** (Транзакции баланса)
**Что очищать:**
- Транзакции связанные с тестовыми заказами
- Транзакции с тестовыми суммами
- Транзакции со статусом `failed`, `cancelled`

**SQL для проверки:**
```sql
-- Найти тестовые транзакции
SELECT bt.id, bt.user_id, bt.type, bt.amount, bt.status, bt.created_at
FROM balance_transactions bt
LEFT JOIN orders o ON o.id::text = bt.reference_id AND bt.reference_type = 'order'
WHERE bt.status IN ('failed', 'cancelled')
  OR bt.amount < 0.01  -- Тестовые суммы
  OR o.id IS NULL  -- Связанные с удаленными заказами
ORDER BY bt.created_at DESC;
```

**SQL для очистки:**
```sql
-- Удалить тестовые транзакции
DELETE FROM balance_transactions 
WHERE status IN ('failed', 'cancelled')
  OR amount < 0.01
  OR (reference_type = 'order' AND reference_id NOT IN (SELECT id::text FROM orders));
```

---

### 5. **referral_bonuses** (Реферальные бонусы)
**Что очищать:**
- Бонусы связанные с тестовыми заказами
- Бонусы для удаленных пользователей

**SQL для проверки:**
```sql
-- Найти тестовые бонусы
SELECT rb.id, rb.user_id, rb.from_user_id, rb.order_id, rb.amount, rb.created_at
FROM referral_bonuses rb
LEFT JOIN orders o ON o.id = rb.order_id
LEFT JOIN users u ON u.id = rb.user_id
WHERE o.id IS NULL  -- Связанные с удаленными заказами
  OR u.id IS NULL   -- Для удаленных пользователей
ORDER BY rb.created_at DESC;
```

**SQL для очистки:**
```sql
-- Удалить бонусы связанные с удаленными заказами/пользователями
DELETE FROM referral_bonuses 
WHERE order_id NOT IN (SELECT id FROM orders)
  OR user_id NOT IN (SELECT id FROM users)
  OR from_user_id NOT IN (SELECT id FROM users);
```

---

### 6. **withdrawal_requests** (Запросы на вывод)
**Что очищать:**
- Запросы со статусом `rejected`, `cancelled`
- Запросы от тестовых пользователей

**SQL для проверки:**
```sql
-- Найти тестовые запросы на вывод
SELECT wr.id, wr.user_id, wr.amount, wr.status, wr.created_at
FROM withdrawal_requests wr
LEFT JOIN users u ON u.id = wr.user_id
WHERE wr.status IN ('rejected', 'cancelled')
  OR u.id IS NULL
ORDER BY wr.created_at DESC;
```

**SQL для очистки:**
```sql
-- Удалить тестовые запросы
DELETE FROM withdrawal_requests 
WHERE status IN ('rejected', 'cancelled')
  OR user_id NOT IN (SELECT id FROM users);
```

---

### 7. **reviews** (Отзывы)
**Что очищать:**
- Отзывы на удаленные заказы
- Отзывы от тестовых пользователей

**SQL для проверки:**
```sql
-- Найти тестовые отзывы
SELECT r.id, r.user_id, r.order_id, r.product_id, r.rating, r.created_at
FROM reviews r
LEFT JOIN orders o ON o.id = r.order_id
LEFT JOIN users u ON u.id = r.user_id
WHERE o.id IS NULL OR u.id IS NULL
ORDER BY r.created_at DESC;
```

**SQL для очистки:**
```sql
-- Удалить отзывы связанные с удаленными заказами/пользователями
DELETE FROM reviews 
WHERE order_id NOT IN (SELECT id FROM orders)
  OR user_id NOT IN (SELECT id FROM users);
```

---

### 8. **chat_history** (История чата)
**Что очищать:**
- История чата от тестовых пользователей
- Старая история (опционально)

**SQL для проверки:**
```sql
-- Найти тестовую историю чата
SELECT ch.id, ch.user_id, ch.role, ch.message, ch.timestamp
FROM chat_history ch
LEFT JOIN users u ON u.id = ch.user_id
WHERE u.id IS NULL
  OR ch.timestamp < NOW() - INTERVAL '30 days'  -- Старая история
ORDER BY ch.timestamp DESC;
```

**SQL для очистки:**
```sql
-- Удалить историю от удаленных пользователей
DELETE FROM chat_history 
WHERE user_id NOT IN (SELECT id FROM users);

-- Опционально: удалить старую историю (старше 30 дней)
DELETE FROM chat_history 
WHERE timestamp < NOW() - INTERVAL '30 days';
```

---

### 9. **analytics_events** (События аналитики)
**Что очищать:**
- События от тестовых пользователей
- Старые события (опционально)

**SQL для проверки:**
```sql
-- Найти тестовые события
SELECT ae.id, ae.user_id, ae.event_type, ae.timestamp
FROM analytics_events ae
LEFT JOIN users u ON u.id = ae.user_id
WHERE u.id IS NULL
  OR ae.timestamp < NOW() - INTERVAL '90 days'  -- Старые события
ORDER BY ae.timestamp DESC;
```

**SQL для очистки:**
```sql
-- Удалить события от удаленных пользователей
DELETE FROM analytics_events 
WHERE user_id IS NOT NULL 
  AND user_id NOT IN (SELECT id FROM users);

-- Опционально: удалить старые события
DELETE FROM analytics_events 
WHERE timestamp < NOW() - INTERVAL '90 days';
```

---

### 10. **wishlist** (Список желаний)
**Что очищать:**
- Записи от тестовых пользователей

**SQL для проверки:**
```sql
-- Найти тестовые записи wishlist
SELECT w.id, w.user_id, w.product_id, w.created_at
FROM wishlist w
LEFT JOIN users u ON u.id = w.user_id
WHERE u.id IS NULL
ORDER BY w.created_at DESC;
```

**SQL для очистки:**
```sql
-- Удалить записи от удаленных пользователей
DELETE FROM wishlist 
WHERE user_id NOT IN (SELECT id FROM users);
```

---

### 11. **tickets** (Тикеты поддержки)
**Что очищать:**
- Тикеты от тестовых пользователей
- Закрытые тикеты (опционально)

**SQL для проверки:**
```sql
-- Найти тестовые тикеты
SELECT t.id, t.user_id, t.order_id, t.status, t.created_at
FROM tickets t
LEFT JOIN users u ON u.id = t.user_id
WHERE u.id IS NULL
  OR t.status = 'closed'  -- Закрытые тикеты
ORDER BY t.created_at DESC;
```

**SQL для очистки:**
```sql
-- Удалить тикеты от удаленных пользователей
DELETE FROM tickets 
WHERE user_id NOT IN (SELECT id FROM users);

-- Опционально: удалить закрытые тикеты
DELETE FROM tickets 
WHERE status = 'closed' 
  AND created_at < NOW() - INTERVAL '90 days';
```

---

### 12. **waitlist** (Лист ожидания)
**Что очищать:**
- Записи от тестовых пользователей

**SQL для проверки:**
```sql
-- Найти тестовые записи waitlist
SELECT w.id, w.user_id, w.product_name, w.created_at
FROM waitlist w
LEFT JOIN users u ON u.id = w.user_id
WHERE u.id IS NULL
ORDER BY w.created_at DESC;
```

**SQL для очистки:**
```sql
-- Удалить записи от удаленных пользователей
DELETE FROM waitlist 
WHERE user_id NOT IN (SELECT id FROM users);
```

---

## 🔄 Сброс счетчиков и агрегатов

После удаления данных нужно обновить агрегированные поля в таблице `users`:

```sql
-- Обновить total_saved для всех пользователей (пересчитать на основе реальных заказов)
UPDATE users u
SET total_saved = COALESCE((
  SELECT SUM(COALESCE(o.original_price, o.amount) - o.amount)
  FROM orders o
  WHERE o.user_id = u.id 
    AND o.status = 'delivered'
), 0);

-- Обновить total_referral_earnings (пересчитать на основе реальных бонусов)
UPDATE users u
SET total_referral_earnings = COALESCE((
  SELECT SUM(rb.amount)
  FROM referral_bonuses rb
  WHERE rb.user_id = u.id 
    AND rb.eligible = true
), 0);

-- Обновить turnover_usd (пересчитать на основе реальных заказов рефералов)
UPDATE users u
SET turnover_usd = COALESCE((
  SELECT SUM(o.amount)
  FROM orders o
  JOIN users r ON r.id = o.user_id
  WHERE r.referrer_id = u.id 
    AND o.status = 'delivered'
), 0);
```

---

## 📝 Полный скрипт очистки

Создайте файл `scripts/cleanup_test_data.sql` с полным скриптом:

```sql
-- ============================================
-- ОЧИСТКА ТЕСТОВЫХ ДАННЫХ ПЕРЕД ПРОДАКШЕНОМ
-- ============================================
-- ⚠️ ВНИМАНИЕ: Выполнять только после создания бэкапа!
-- ⚠️ Проверьте все запросы перед выполнением!

BEGIN;

-- 1. Удалить элементы заказов связанные с тестовыми заказами
DELETE FROM order_items 
WHERE order_id IN (
  SELECT id FROM orders 
  WHERE status IN ('pending', 'cancelled') OR amount < 1
);

-- 2. Удалить тестовые заказы
DELETE FROM orders 
WHERE status IN ('pending', 'cancelled') OR amount < 1;

-- 3. Удалить транзакции связанные с тестовыми заказами
DELETE FROM balance_transactions 
WHERE status IN ('failed', 'cancelled')
  OR amount < 0.01
  OR (reference_type = 'order' AND reference_id NOT IN (SELECT id::text FROM orders));

-- 4. Удалить бонусы связанные с удаленными заказами/пользователями
DELETE FROM referral_bonuses 
WHERE order_id NOT IN (SELECT id FROM orders)
  OR user_id NOT IN (SELECT id FROM users)
  OR from_user_id NOT IN (SELECT id FROM users);

-- 5. Удалить запросы на вывод
DELETE FROM withdrawal_requests 
WHERE status IN ('rejected', 'cancelled')
  OR user_id NOT IN (SELECT id FROM users);

-- 6. Удалить отзывы
DELETE FROM reviews 
WHERE order_id NOT IN (SELECT id FROM orders)
  OR user_id NOT IN (SELECT id FROM users);

-- 7. Удалить историю чата от удаленных пользователей
DELETE FROM chat_history 
WHERE user_id NOT IN (SELECT id FROM users);

-- 8. Удалить события аналитики
DELETE FROM analytics_events 
WHERE user_id IS NOT NULL 
  AND user_id NOT IN (SELECT id FROM users);

-- 9. Удалить wishlist
DELETE FROM wishlist 
WHERE user_id NOT IN (SELECT id FROM users);

-- 10. Удалить тикеты
DELETE FROM tickets 
WHERE user_id NOT IN (SELECT id FROM users);

-- 11. Удалить waitlist
DELETE FROM waitlist 
WHERE user_id NOT IN (SELECT id FROM users);

-- 12. Удалить тестовых пользователей (БЕЗ заказов)
DELETE FROM users 
WHERE total_saved = 0 
  AND created_at < NOW() - INTERVAL '1 day'
  AND id NOT IN (SELECT DISTINCT user_id FROM orders WHERE user_id IS NOT NULL);

-- 13. Пересчитать агрегаты
UPDATE users u
SET total_saved = COALESCE((
  SELECT SUM(COALESCE(o.original_price, o.amount) - o.amount)
  FROM orders o
  WHERE o.user_id = u.id AND o.status = 'delivered'
), 0);

UPDATE users u
SET total_referral_earnings = COALESCE((
  SELECT SUM(rb.amount)
  FROM referral_bonuses rb
  WHERE rb.user_id = u.id AND rb.eligible = true
), 0);

UPDATE users u
SET turnover_usd = COALESCE((
  SELECT SUM(o.amount)
  FROM orders o
  JOIN users r ON r.id = o.user_id
  WHERE r.referrer_id = u.id AND o.status = 'delivered'
), 0);

COMMIT;
```

---

## ✅ Чеклист перед продакшеном

- [ ] Создан бэкап базы данных
- [ ] Проверены все SQL запросы на тестовой копии
- [ ] Удалены тестовые пользователи
- [ ] Удалены тестовые заказы и order_items
- [ ] Удалены тестовые транзакции баланса
- [ ] Удалены тестовые реферальные бонусы
- [ ] Удалены тестовые запросы на вывод
- [ ] Удалены тестовые отзывы
- [ ] Очищена история чата (опционально)
- [ ] Очищены события аналитики (опционально)
- [ ] Очищены wishlist и waitlist
- [ ] Пересчитаны агрегаты (total_saved, total_referral_earnings, turnover_usd)
- [ ] Проверена целостность данных после очистки
- [ ] Обновлены счетчики в views (если нужно)

---

## 🔍 Проверка после очистки

```sql
-- Проверить количество записей в каждой таблице
SELECT 
  'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL
SELECT 'balance_transactions', COUNT(*) FROM balance_transactions
UNION ALL
SELECT 'referral_bonuses', COUNT(*) FROM referral_bonuses
UNION ALL
SELECT 'withdrawal_requests', COUNT(*) FROM withdrawal_requests
UNION ALL
SELECT 'reviews', COUNT(*) FROM reviews
UNION ALL
SELECT 'chat_history', COUNT(*) FROM chat_history
UNION ALL
SELECT 'analytics_events', COUNT(*) FROM analytics_events
UNION ALL
SELECT 'wishlist', COUNT(*) FROM wishlist
UNION ALL
SELECT 'tickets', COUNT(*) FROM tickets
UNION ALL
SELECT 'waitlist', COUNT(*) FROM waitlist
ORDER BY table_name;
```

---

## 📌 Примечания

1. **Порядок удаления важен** - сначала удаляйте зависимые таблицы (order_items, referral_bonuses), затем основные (orders, users)
2. **Каскадное удаление** - некоторые записи могут удаляться автоматически через foreign key constraints
3. **Агрегаты** - всегда пересчитывайте после удаления данных
4. **Бэкап** - обязателен перед любыми массовыми удалениями
5. **Тестирование** - сначала выполните на тестовой копии базы данных

---

## 🚀 Автоматизация

Можно создать Python скрипт для автоматической очистки:

```python
# scripts/cleanup_test_data.py
# Использовать mcp_supabase_execute_sql для выполнения запросов
```

---

**Последнее обновление:** 2025-12-15

