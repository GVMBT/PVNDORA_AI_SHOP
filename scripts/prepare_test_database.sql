-- ============================================
-- ПОДГОТОВКА БД ДЛЯ ТЕСТИРОВАНИЯ
-- ============================================
-- ⚠️ ВНИМАНИЕ: Выполнять только после создания бэкапа!
-- ⚠️ Этот скрипт удаляет ВСЕ финансовые данные и историю заказов
-- ⚠️ Оставляет: пользователей, товары, сток, настройки
-- 
-- Использование:
--   1. Создайте бэкап базы данных через Supabase Dashboard
--   2. Проверьте запросы на тестовой копии
--   3. Выполните скрипт через Supabase SQL Editor или MCP
--
-- ============================================

BEGIN;

-- ============================================
-- 1. УДАЛЕНИЕ ФИНАНСОВЫХ ДАННЫХ
-- ============================================

-- 1.1. Удалить все транзакции баланса (история операций)
DELETE FROM balance_transactions;

-- 1.2. Удалить все элементы заказов (зависит от orders)
DELETE FROM order_items;

-- 1.3. Удалить все заказы (включая delivered, paid, prepaid)
DELETE FROM orders;

-- 1.4. Удалить все бонусы реферальной программы
DELETE FROM referral_bonuses;

-- 1.5. Удалить все запросы на вывод средств
DELETE FROM withdrawal_requests;

-- 1.6. Удалить все расходы (expenses)
DELETE FROM expenses;

-- 1.7. Удалить все расчеты расходов по заказам
DELETE FROM order_expenses;

-- 1.8. Удалить все доходы от страховок
DELETE FROM insurance_revenue;

-- 1.9. Удалить все замены по страховке
DELETE FROM insurance_replacements;

-- ============================================
-- 2. УДАЛЕНИЕ ИСТОРИИ И АКТИВНОСТИ
-- ============================================

-- 2.1. Удалить все тикеты (поддержка/замены)
DELETE FROM tickets;

-- 2.2. Удалить все отзывы
DELETE FROM reviews;

-- 2.3. Удалить всю историю чата с AI
DELETE FROM chat_history;

-- 2.4. Удалить все события аналитики
DELETE FROM analytics_events;

-- 2.5. Удалить все избранное (wishlist)
DELETE FROM wishlist;

-- 2.6. Удалить все листы ожидания (waitlist)
DELETE FROM waitlist;

-- 2.7. Удалить историю рассылок
DELETE FROM broadcast_recipients;
DELETE FROM broadcast_messages;

-- 2.8. Удалить заявки на партнерство (опционально - можно оставить)
DELETE FROM partner_applications;

-- 2.9. Удалить ограничения пользователей (опционально - можно оставить)
DELETE FROM user_restrictions;

-- 2.10. Удалить сессии и сообщения чата (если используются в PVNDORA)
-- Если эти таблицы относятся к другому проекту, пропустите эти строки
DELETE FROM chat_messages;
DELETE FROM chat_sessions;
DELETE FROM processed_messages;

-- ============================================
-- 3. ОБНУЛЕНИЕ СТАТИСТИКИ ПОЛЬЗОВАТЕЛЕЙ
-- ============================================
-- Оставляем всех пользователей, но обнуляем финансовые агрегаты

UPDATE users
SET 
  balance = 0,
  balance_currency = 'USD', -- или 'RUB' в зависимости от языка
  total_saved = 0,
  total_referral_earnings = 0,
  total_purchases_amount = 0,
  turnover_usd = 0,
  referral_level = 1,
  referral_program_unlocked = false,
  referral_unlocked_at = NULL,
  level1_unlocked_at = NULL,
  level2_unlocked_at = NULL,
  level3_unlocked_at = NULL,
  referral_clicks_count = 0,
  warnings_count = 0,
  is_banned = false,
  do_not_disturb = false,
  -- Оставляем: telegram_id, username, first_name, referrer_id, is_admin, created_at, language_code, preferred_currency, interface_language
  -- Оставляем: photo_url, last_activity_at, last_reengagement_at, bot_blocked_at, terms_accepted, terms_accepted_at
  -- Оставляем: is_partner, partner_level_override, partner_mode, partner_discount_percent, discount_tier_source
  -- Оставляем: personal_ref_percent
;

-- ============================================
-- 4. ВОССТАНОВЛЕНИЕ СТОКА
-- ============================================
-- Возвращаем весь сток в статус "available" для тестирования

UPDATE stock_items
SET 
  status = 'available',
  reserved_at = NULL,
  sold_at = NULL
WHERE status IN ('reserved', 'sold');

-- ============================================
-- 5. ОЧИСТКА ПРОМОКОДОВ (опционально)
-- ============================================
-- Обнуляем счетчики использований промокодов (сами промокоды оставляем)

UPDATE promo_codes
SET 
  usage_count = 0
WHERE usage_count > 0;

-- ============================================
-- 6. ТАБЛИЦЫ, КОТОРЫЕ ОСТАВЛЯЕМ БЕЗ ИЗМЕНЕНИЙ
-- ============================================
-- ✅ products - товары (оставляем)
-- ✅ stock_items - сток (уже обновлен выше)
-- ✅ suppliers - поставщики (оставляем)
-- ✅ users - пользователи (уже обновлены выше)
-- ✅ referral_settings - настройки реферальной программы (оставляем)
-- ✅ exchange_rates - курсы валют (оставляем, обновляются автоматически)
-- ✅ accounting_settings - настройки учета (оставляем)
-- ✅ payment_gateway_fees - комиссии платежных систем (оставляем)
-- ✅ insurance_options - опции страховки (оставляем)
-- ✅ faq - часто задаваемые вопросы (оставляем)
-- ✅ product_embeddings - векторные представления для поиска (оставляем)

COMMIT;

-- ============================================
-- 8. ПРОВЕРКА РЕЗУЛЬТАТОВ
-- ============================================

SELECT 
  'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'stock_items', COUNT(*) FROM stock_items
UNION ALL
SELECT 'stock_items_available', COUNT(*) FROM stock_items WHERE status = 'available'
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
SELECT 'tickets', COUNT(*) FROM tickets
UNION ALL
SELECT 'reviews', COUNT(*) FROM reviews
UNION ALL
SELECT 'chat_history', COUNT(*) FROM chat_history
UNION ALL
SELECT 'analytics_events', COUNT(*) FROM analytics_events
UNION ALL
SELECT 'expenses', COUNT(*) FROM expenses
UNION ALL
SELECT 'order_expenses', COUNT(*) FROM order_expenses
ORDER BY table_name;

-- Проверка балансов пользователей (должны быть 0)
SELECT 
  telegram_id, 
  username, 
  balance, 
  total_saved, 
  total_referral_earnings,
  turnover_usd
FROM users
WHERE balance != 0 
   OR total_saved != 0 
   OR total_referral_earnings != 0
   OR turnover_usd != 0;
