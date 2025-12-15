-- ============================================
-- ОЧИСТКА ТЕСТОВЫХ ДАННЫХ ПЕРЕД ПРОДАКШЕНОМ
-- ============================================
-- ⚠️ ВНИМАНИЕ: Выполнять только после создания бэкапа!
-- ⚠️ Проверьте все запросы перед выполнением!
-- 
-- Использование:
--   1. Создайте бэкап базы данных через Supabase Dashboard
--   2. Проверьте запросы на тестовой копии
--   3. Выполните скрипт через Supabase SQL Editor или MCP
--
-- ============================================

BEGIN;

-- ============================================
-- 1. УДАЛЕНИЕ ЗАВИСИМЫХ ДАННЫХ
-- ============================================

-- 1.1. Удалить элементы заказов связанные с тестовыми заказами
DELETE FROM order_items 
WHERE order_id IN (
  SELECT id FROM orders 
  WHERE status IN ('pending', 'cancelled') OR amount < 1
);

-- 1.2. Удалить транзакции связанные с тестовыми заказами
DELETE FROM balance_transactions 
WHERE status IN ('failed', 'cancelled')
  OR amount < 0.01
  OR (reference_type = 'order' AND reference_id NOT IN (SELECT id::text FROM orders));

-- 1.3. Удалить бонусы связанные с удаленными заказами/пользователями
DELETE FROM referral_bonuses 
WHERE order_id NOT IN (SELECT id FROM orders)
  OR user_id NOT IN (SELECT id FROM users)
  OR from_user_id NOT IN (SELECT id FROM users);

-- 1.4. Удалить отзывы связанные с удаленными заказами/пользователями
DELETE FROM reviews 
WHERE order_id NOT IN (SELECT id FROM orders)
  OR user_id NOT IN (SELECT id FROM users);

-- 1.5. Удалить тикеты от удаленных пользователей
DELETE FROM tickets 
WHERE user_id NOT IN (SELECT id FROM users);

-- ============================================
-- 2. УДАЛЕНИЕ ОСНОВНЫХ ДАННЫХ
-- ============================================

-- 2.1. Удалить тестовые заказы
DELETE FROM orders 
WHERE status IN ('pending', 'cancelled') OR amount < 1;

-- 2.2. Удалить запросы на вывод
DELETE FROM withdrawal_requests 
WHERE status IN ('rejected', 'cancelled')
  OR user_id NOT IN (SELECT id FROM users);

-- 2.3. Удалить историю чата от удаленных пользователей
DELETE FROM chat_history 
WHERE user_id NOT IN (SELECT id FROM users);

-- 2.4. Удалить события аналитики от удаленных пользователей
DELETE FROM analytics_events 
WHERE user_id IS NOT NULL 
  AND user_id NOT IN (SELECT id FROM users);

-- 2.5. Удалить wishlist от удаленных пользователей
DELETE FROM wishlist 
WHERE user_id NOT IN (SELECT id FROM users);

-- 2.6. Удалить waitlist от удаленных пользователей
DELETE FROM waitlist 
WHERE user_id NOT IN (SELECT id FROM users);

-- 2.7. Удалить тестовых пользователей (БЕЗ заказов)
DELETE FROM users 
WHERE total_saved = 0 
  AND created_at < NOW() - INTERVAL '1 day'
  AND id NOT IN (SELECT DISTINCT user_id FROM orders WHERE user_id IS NOT NULL);

-- ============================================
-- 3. ПЕРЕСЧЕТ АГРЕГАТОВ
-- ============================================

-- 3.1. Пересчитать total_saved на основе реальных заказов
UPDATE users u
SET total_saved = COALESCE((
  SELECT SUM(COALESCE(o.original_price, o.amount) - o.amount)
  FROM orders o
  WHERE o.user_id = u.id 
    AND o.status = 'delivered'
), 0);

-- 3.2. Пересчитать total_referral_earnings на основе реальных бонусов
UPDATE users u
SET total_referral_earnings = COALESCE((
  SELECT SUM(rb.amount)
  FROM referral_bonuses rb
  WHERE rb.user_id = u.id 
    AND rb.eligible = true
), 0);

-- 3.3. Пересчитать turnover_usd: собственные заказы + заказы рефералов
UPDATE users u
SET turnover_usd = COALESCE((
  -- Собственные доставленные заказы
  SELECT SUM(o1.amount)
  FROM orders o1
  WHERE o1.user_id = u.id AND o1.status = 'delivered'
), 0) + COALESCE((
  -- Доставленные заказы рефералов
  SELECT SUM(o2.amount)
  FROM orders o2
  JOIN users r ON r.id = o2.user_id
  WHERE r.referrer_id = u.id 
    AND o2.status = 'delivered'
), 0);

COMMIT;

-- ============================================
-- 4. ПРОВЕРКА РЕЗУЛЬТАТОВ
-- ============================================

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

