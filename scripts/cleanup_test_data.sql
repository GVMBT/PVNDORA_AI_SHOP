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

-- 1.1. Удалить ВСЕ элементы заказов (тестовые данные)
-- Удаляем сначала элементы, потом заказы (из-за внешних ключей)
DELETE FROM order_items;

-- 1.2. Удалить ВСЕ транзакции баланса (тестовые данные)
-- SYSTEM_LOGS формируется из balance_transactions, поэтому очищаем все
DELETE FROM balance_transactions;

-- 1.3. Удалить ВСЕ бонусы (тестовые данные, все заказы удалены)
DELETE FROM referral_bonuses;

-- 1.4. Удалить ВСЕ отзывы (тестовые данные, все заказы удалены)
DELETE FROM reviews;

-- 1.5. Удалить тикеты от удаленных пользователей
DELETE FROM tickets 
WHERE user_id NOT IN (SELECT id FROM users);

-- ============================================
-- 2. УДАЛЕНИЕ ОСНОВНЫХ ДАННЫХ
-- ============================================

-- 2.1. Удалить ВСЕ тестовые заказы (включая delivered)
-- Все заказы считаются тестовыми для полной очистки
DELETE FROM orders;

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
-- 3. ОБНУЛЕНИЕ АГРЕГАТОВ (все заказы удалены)
-- ============================================

-- 3.1. Обнулить все агрегаты пользователей (тестовые данные)
-- Все заказы, бонусы и транзакции удалены, поэтому обнуляем все
UPDATE users
SET 
  balance = 0,
  total_saved = 0,
  total_referral_earnings = 0,
  turnover_usd = 0;

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

