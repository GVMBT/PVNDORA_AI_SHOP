# Анализ проблем в бухгалтерии (order_expenses)

## Найденные проблемы:

### 1. ❌ **review_cashback_amount** в `worker_process_review_cashback`
**Проблема:** UPDATE без проверки существования `order_expenses`
**Место:** `core/routers/workers/payments.py:232`
**Риск:** Если `order_expenses` не существует, UPDATE не сработает, кэшбек не попадет в бухгалтерию
**Статус:** ❌ НЕ ИСПРАВЛЕНО (только в submit_webapp_review исправлено)

### 2. ❌ **order_expenses может не существовать**
**Проблема:** `calculate_order_expenses` НЕ вызывается автоматически при создании заказа
**Место:** Проверка показала 3 заказа без `order_expenses`
**Риск:** Если `order_expenses` не создан, все UPDATE не сработают
**Поля, которые не попадут в бухгалтерию:**
- `review_cashback_amount`
- `referral_payout_amount`
- `insurance_replacement_cost`
- `promo_discount_amount`
- `partner_discount_amount`
- `acquiring_fee_amount`
- `reserve_amount`
- `cogs_amount`
**Статус:** ❌ НЕ ИСПРАВЛЕНО

### 3. ⚠️ **referral_payout_amount**
**Проблема:** Рассчитывается в `calculate_order_expenses` из таблицы `referral_bonuses`
**Риск:** Если `order_expenses` не создан, referral payouts не попадут в бухгалтерию
**Статус:** ⚠️ ЗАВИСИТ ОТ ПРОБЛЕМЫ #2

### 4. ⚠️ **insurance_replacement_cost**
**Проблема:** Рассчитывается в `calculate_order_expenses` из таблицы `insurance_replacements`
**Риск:** Если `order_expenses` не создан, insurance costs не попадут в бухгалтерию
**Статус:** ⚠️ ЗАВИСИТ ОТ ПРОБЛЕМЫ #2

### 5. ⚠️ **promo_discount_amount, partner_discount_amount**
**Проблема:** Рассчитываются в `calculate_order_expenses` из `orders.original_price - orders.amount`
**Риск:** Если `order_expenses` не создан, discounts не попадут в бухгалтерию
**Статус:** ⚠️ ЗАВИСИТ ОТ ПРОБЛЕМЫ #2

### 6. ⚠️ **acquiring_fee_amount, reserve_amount, cogs_amount**
**Проблема:** Рассчитываются в `calculate_order_expenses`
**Риск:** Если `order_expenses` не создан, эти поля не попадут в бухгалтерию
**Статус:** ⚠️ ЗАВИСИТ ОТ ПРОБЛЕМЫ #2

## Рекомендации:

1. **Исправить `worker_process_review_cashback`** - добавить проверку существования `order_expenses` (как в `submit_webapp_review`)
2. **❌ КРИТИЧНО: `calculate_order_expenses` НЕ вызывается в `mark_payment_confirmed`!**
   - Нужно добавить вызов `calculate_order_expenses` в `mark_payment_confirmed` после подтверждения оплаты
   - Иначе `order_expenses` не создается автоматически
3. **Проверить все заказы без `order_expenses`** и создать для них записи (найдено 3 заказа)
4. **После исправления #2, все поля (#3-6) будут работать автоматически**

## Приоритеты:

1. **ВЫСОКИЙ:** Добавить вызов `calculate_order_expenses` в `mark_payment_confirmed`
2. **СРЕДНИЙ:** Исправить `worker_process_review_cashback` (добавить проверку существования)
3. **НИЗКИЙ:** Исправить существующие заказы без `order_expenses`
