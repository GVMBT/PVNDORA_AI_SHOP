# 🔧 PVNDORA Refactoring Plan

**Дата:** 2026-01-27  
**Последнее обновление:** 2026-01-27 (разбиение на 3 параллельных агента)  
**Приоритет:** Критический → Высокий → Средний → Низкий

**⚡ РАЗБИТО НА 3 ПАРАЛЛЕЛЬНЫХ АГЕНТА (2026-01-27):**

Для параллельной работы создано 3 независимых документа:

1. **`REFACTORING_PLAN_AGENT_1_CLEANUP.md`** — Cleanup & Consolidation (2-4 дня)
   - Phase 0: Консолидация дублирований (Telegram messaging + Currency conversion)
   - Phase 1: Cleanup (deprecated код, unused imports, документация)
   - **Приоритет:** 🔴 Критический (нужно выполнить первым для Agent 2)

2. **`REFACTORING_PLAN_AGENT_2_SPLITTING.md`** — Monolith Splitting (7-10 дней)
   - Phase 2: Split Notifications & Workers (зависит от Phase 0 Agent 1)
   - Phase 3: Split Profile Router (зависит от Phase 0 Agent 1)
   - Phase 4: Split Orders Router
   - **Приоритет:** 🔴 Критический → 🟡 Высокий

3. **`REFACTORING_PLAN_AGENT_3_OPTIMIZATION.md`** — Database & Performance (5-7 дней)
   - Phase 7: Database Query Optimization (N+1 queries, async паттерны)
   - **Приоритет:** 🔴 Критический (для масштабирования)

**⚡ РАЗБИТО НА 3 ПАРАЛЛЕЛЬНЫХ АГЕНТА (2026-01-27):**

Для параллельной работы создано 3 независимых документа:

1. **[`REFACTORING_PLAN_AGENT_1_CLEANUP.md`](./REFACTORING_PLAN_AGENT_1_CLEANUP.md)** — Cleanup & Consolidation (2-4 дня)
   - Phase 0: Консолидация дублирований (Telegram messaging + Currency conversion)
   - Phase 1: Cleanup (deprecated код, unused imports, документация)
   - **Приоритет:** 🔴 Критический (нужно выполнить первым для Agent 2)

2. **[`REFACTORING_PLAN_AGENT_2_SPLITTING.md`](./REFACTORING_PLAN_AGENT_2_SPLITTING.md)** — Monolith Splitting (7-10 дней)
   - Phase 2: Split Notifications & Workers (зависит от Phase 0 Agent 1)
   - Phase 3: Split Profile Router (зависит от Phase 0 Agent 1)
   - Phase 4: Split Orders Router
   - **Приоритет:** 🔴 Критический → 🟡 Высокий

3. **[`REFACTORING_PLAN_AGENT_3_OPTIMIZATION.md`](./REFACTORING_PLAN_AGENT_3_OPTIMIZATION.md)** — Database & Performance (5-7 дней)
   - Phase 7: Database Query Optimization (N+1 queries, async паттерны)
   - **Приоритет:** 🔴 Критический (для масштабирования)

**Расширенное исследование (2026-01-27):**
- ✅ Проверены актуальные размеры файлов (проверено через `wc -l`)
- ✅ Найдены противоречия и наслоения логики (7 критических/средних)
- ✅ Найден лишний код: 2 неиспользуемые функции, 1 неиспользуемый endpoint
- ✅ Найдены устаревшие реализации: supplier функциональность (инфраструктура есть, логика не реализована)
- ✅ Документ разбит на 3 независимых части для параллельной работы агентов
- ✅ Документ разбит на 3 независимых части для параллельной работы агентов

---

## 📊 Анализ текущего состояния

### Статистика кодовой базы

| Метрика | Значение | Проблема |
|---------|----------|----------|
| Python файлов | ~90 | - |
| TypeScript/React | ~100 | - |
| **Крупнейшие монолиты** | 6 файлов >1000 строк | 🔴 |
| **Дублирование кода** | 8+ мест Telegram отправки | 🔴 |
| **Несогласованности** | Валютная конвертация в 3+ местах | 🟡 |
| Unused imports | 14+ файлов | 🟡 |
| TODO/FIXME/DEPRECATED | 13+ мест | 🟡 |
| Устаревшая документация | 6+ файлов | 🟡 |

### 🔴 Критические монолиты (>1000 строк) - АКТУАЛЬНЫЕ РАЗМЕРЫ (2026-01-27)

| Файл | Строк | Проблема | Статус |
|------|-------|----------|--------|
| `core/services/notifications.py` | **1281** | Все уведомления + 20+ прямых вызовов bot.send_message | ❌ Монолит |
| `core/routers/workers.py` | **1271** | 5+ workers в одном файле | ❌ Монолит |
| `core/routers/webapp/profile.py` | **1145** | Профиль + баланс + валюта + ручная конвертация | ❌ Монолит |
| `core/routers/webapp/orders.py` | **1110** | Заказы + платежи + доставка | ❌ Монолит |
| `core/bot/admin/handlers/broadcast.py` | **975** | Broadcast логика | ⚠️ Почти монолит |
| `core/services/payments.py` | **544** | Только CrystalPay (старые шлюзы удалены) | ✅ Упрощён, но ещё монолит |
| `core/routers/webhooks.py` | **469** | Только CrystalPay webhook (старые удалены) | ✅ Упрощён, но ещё монолит |

### ✅ УЖЕ ВЫПОЛНЕНО (из PROJECT_MAP.md)

| Файл | Было | Стало | Статус |
|------|------|-------|--------|
| `core/agent/tools.py` | 1836 строк (монолит) | **8 модулей** (max 567 строк) | ✅ **РАЗБИТ** |
| `core/services/payments.py` | 1589 строк (4 шлюза) | 544 строки (только CrystalPay) | ✅ **УПРОЩЁН** |
| `core/routers/webhooks.py` | 908 строк (4 webhook'а) | 469 строк (только CrystalPay) | ✅ **УПРОЩЁН** |
| 1Plat, Freekassa, Rukassa | Были | **Удалены** | ✅ **УДАЛЕНЫ** |
| Устаревшая документация | 10+ файлов | **Удалена** | ✅ **УДАЛЕНА** |

---

## 🗑️ Часть 1: Удаление устаревшего

### 1.1 Документация для удаления

| Файл | Причина |
|------|---------|
| `docs/1PLAT_DIAGNOSIS.md` | Решено / устарело |
| `docs/1PLAT_LK_CHECKLIST.md` | Решено / устарело |
| `docs/1PLAT_TROUBLESHOOTING.md` | Решено / устарело |
| `docs/CRYSTALPAY_MODERATION_RESPONSE.md` | Одноразовый документ |
| `docs/LEGAL_MODERATION_CHECKLIST.md` | Решено / устарело |
| `docs/LEGAL_TERMINOLOGY_ANALYSIS.md` | Решено / устарело |
| `docs/TEST_DATA_CLEANUP.md` | Одноразовая операция |
| `REFACTORING_ZONES.md` | Устарел (заменить на этот) |
| `REFACTORING_ROADMAP.md` | Устарел (заменить на этот) |
| `ARCHITECTURE_ANALYSIS.md` | ✅ Удалён (заменён на PROJECT_MAP) |

### 1.2 Deprecated код для удаления

**Найдено при анализе 2026-01-27 (расширено):**

```python
# core/orders/serializer.py:39-70
# DEPRECATED: Use convert_order_prices_with_formatter instead
# СТАТУС: Экспортируется в __init__.py, но НЕ используется в коде (можно удалить)

# core/services/notifications.py:89-200
# DEPRECATED: Use workers._deliver_items_for_order instead
# СТАТУС: Никто не вызывает (можно удалить полностью)

# core/routers/workers.py:516-525
# DEPRECATED: Supplier functionality is not used.
# TODO: Remove when cleaning up supplier-related tech debt.
# СТАТУС: Endpoint возвращает только {"deprecated": True}, но упомянут в документации

# core/services/models.py:111-115
# DEPRECATED fields - will be removed after migration
# СТАТУС: Поля помечены DEPRECATED, но всё ещё читаются в webapp/orders.py:373-374
```

**Дополнительные находки:**
- `notify-supplier-prepaid` endpoint упомянут в документации и `WorkerEndpoints`, но не реализован
- `supplier_id` всё ещё используется в admin/models.py, admin/accounting.py, admin/products.py
- `convert_order_prices()` экспортируется, но не используется (проверено grep)

### 1.3 Unused imports для очистки

| Файл | Imports |
|------|---------|
| `core/routers/webhooks.py` | `asyncio` |
| `core/routers/admin/accounting.py` | `decimal.Decimal` |
| `core/routers/admin/broadcast.py` | `datetime`, `timezone`, `Query` |
| `core/routers/admin/migration.py` | `Optional` |
| `core/routers/admin/replacements.py` | `UUID` |
| `core/routers/webapp/cart.py` | `Optional` |
| `core/services/admin_alerts.py` | `Decimal` |
| `core/services/domains/insurance.py` | `Dict`, `Any`, `UUID` |
| `core/services/domains/offers.py` | `Tuple` |
| `core/services/domains/support.py` | `timedelta` |

---

## 🔨 Часть 2: Разделение монолитов

### 2.1 ✅ `core/agent/tools.py` — УЖЕ РАЗБИТ (выполнено)

**Текущая структура (✅ выполнено):**
```
core/agent/tools/
├── __init__.py          # 155 строк - Re-exports all tools
├── base.py              # 54 строки - _UserContext, set_user_context, get_db
├── catalog.py           # 267 строк - Catalog & search tools
├── cart.py              # 336 строк - Cart management tools
├── checkout.py          # 567 строк - Checkout & payment tools
├── orders.py            # 186 строк - Order tools
├── profile.py           # 336 строк - Profile & referral tools
├── support.py           # 222 строки - Support & FAQ tools
└── wishlist.py          # 119 строк - Wishlist tools
```

**Максимальный файл:** checkout.py (567 строк) — вместо 1836 строк монолита ✅

### 2.2 `core/services/payments.py` (544 строки) — УПРОЩЁН, но ещё монолит

**Статус:** ✅ Старые шлюзы (1Plat, Freekassa, Rukassa) уже удалены. Остался только CrystalPay.

**Текущая структура:**
```
PaymentService (только CrystalPay)
├── CrystalPay methods (~400 lines)
├── Invoice creation (~100 lines)
└── Webhook validation (~44 lines)
```

**Целевая структура (опционально, низкий приоритет):**
```
core/services/payments/
├── __init__.py          # Re-exports PaymentService
├── base.py              # PaymentService class + common methods
└── crystalpay.py        # CrystalPay integration (все методы)
```

**Примечание:** 544 строки — приемлемый размер. Разбиение не критично, но можно для консистентности.

### 2.3 `core/routers/webhooks.py` (469 строк) — УПРОЩЁН, но ещё монолит

**Статус:** ✅ Старые webhooks (1Plat, Freekassa, Rukassa) уже удалены. Остался только CrystalPay.

**Текущая структура:**
```
Webhooks Router (только CrystalPay)
├── CrystalPay payment webhook (~250 lines)
├── CrystalPay topup webhook (~220 lines)
└── Common helpers (~20 lines)
```

**Целевая структура (опционально, низкий приоритет):**
```
core/routers/webhooks/
├── __init__.py          # Re-exports router
├── router.py            # Main router + route definitions
└── crystalpay.py        # CrystalPay webhook handlers
```

**Примечание:** 469 строк — приемлемый размер. Разбиение не критично, но можно для консистентности.

### 2.4 `core/routers/workers.py` (1271 строк) → 5 файлов

**Актуальная структура:**
- `_deliver_items_for_order` - доставка товаров
- `worker_calculate_referral` - реферальные бонусы
- `worker_deliver_batch` - батч доставка
- `worker_process_replacement` - замена аккаунтов
- `worker_process_refund` - возвраты
- `worker_process_review_cashback` - кэшбэк за отзывы
- `worker_send_broadcast` - рассылки
- И другие workers...

**Целевая структура:**
```
core/routers/workers/
├── __init__.py          # Re-exports router
├── router.py            # Main router + common helpers (_deliver_items_for_order)
├── delivery.py          # deliver-goods, deliver-batch
├── referral.py          # calculate-referral, process-replacement
├── payments.py          # process-refund, process-review-cashback
└── broadcast.py         # send-broadcast
```

### 2.6 `core/services/notifications.py` (1281 строка) → модули

**Проблема:** Все типы уведомлений в одном файле + прямые вызовы `bot.send_message()`.

**Целевая структура:**
```
core/services/notifications/
├── __init__.py          # Re-exports NotificationService
├── base.py              # NotificationService + telegram_messaging
├── delivery.py          # send_delivery, send_credentials
├── orders.py            # send_review_request, send_expiration_reminder
├── support.py           # send_ticket_approved, send_ticket_rejected
├── referral.py          # send_referral_unlock, send_referral_level_up, send_referral_bonus
├── payments.py          # send_cashback, send_refund, send_topup_success
├── withdrawals.py       # send_withdrawal_approved, send_withdrawal_rejected, send_withdrawal_completed
└── misc.py              # send_broadcast, send_waitlist_notification, etc.
```

### 2.5 `core/routers/webapp/orders.py` (1110 строк) → 3 файла

**Целевая структура:**
```
core/routers/webapp/orders/
├── __init__.py          # Re-exports router
├── router.py            # Main router + route definitions
├── crud.py              # get_webapp_orders, verify_and_deliver_order
└── payments.py          # create_webapp_order, payment creation logic
```

### 2.7 `core/routers/webapp/profile.py` (1113 строк) → модули

**Проблема:** Профиль + баланс + валюта + ручная конвертация валют.

**Целевая структура:**
```
core/routers/webapp/profile/
├── __init__.py          # Re-exports router
├── router.py            # Main router + route definitions
├── profile.py           # get_profile, update_preferences, get_referral_info
├── balance.py           # get_balance_history, topup_balance, convert_balance
└── withdrawals.py       # calculate_withdrawal, request_withdrawal, get_withdrawal_history
```

**КРИТИЧЕСКОЕ:** Убрать ручную конвертацию валют (строки 773-794, 534-542).  
**⚠️ ЗАВИСИМОСТЬ:** Phase 0 (Agent 1) должен создать `CurrencyService.convert_balance()` ДО начала Phase 3. Использовать `CurrencyService.convert_balance()` для конвертации между любыми валютами (не `convert_price()`, который работает только из USD).

---

## 🧹 Часть 3: Консолидация

### 3.1 Объединить дублирующуюся логику

**🔴 КРИТИЧЕСКОЕ ДУБЛИРОВАНИЕ: Telegram Message Sending (8+ мест)**

| Файл | Строки | Проблема |
|------|--------|----------|
| `core/services/notifications.py` | Множество | 20+ прямых вызовов `bot.send_message()` |
| `core/routers/admin/broadcast.py` | 45-72 | Функция `send_telegram_message()` |
| `core/services/domains/offers.py` | 60-84 | Метод `send_telegram_message()` |
| `api/cron/deliver_overdue_discount.py` | 56-78 | Функция `send_telegram_message()` |
| `api/workers/deliver_discount_order.py` | 49-67 | Функция `send_telegram_message()` |
| `api/workers/process_review_cashback.py` | 50-67 | Функция `send_telegram_message()` |
| `api/cron/low_stock_alert.py` | 87-104 | Функция `send_telegram_message()` |
| `core/routers/workers.py` | 933, 1101+ | Прямые вызовы `bot.send_message()` |

**Решение:** Создать единый сервис `core/services/telegram_messaging.py`:
```python
async def send_telegram_message(
    chat_id: int, 
    text: str, 
    parse_mode: str = "HTML",
    bot_token: Optional[str] = None,
    retries: int = 2
) -> bool
```

**🟡 ДУБЛИРОВАНИЕ: Currency Conversion (4+ места)**

| Место | Проблема |
|-------|----------|
| `core/services/currency.py` | ✅ Основной `CurrencyService` (но `convert_price()` только из USD) |
| `core/services/currency_response.py` | ✅ `CurrencyFormatter` (wrapper, ОК) |
| `core/routers/webapp/profile.py:773-794` | ❌ Ручная конвертация баланса (RUB→EUR, USD→RUB) через `get_exchange_rate()` |
| `core/routers/webapp/profile.py:534-542` | ❌ Ручная конвертация в topup (payment_currency → balance_currency) |
| `src/components/new/ProfileConnected.tsx:95-101` | ⚠️ Фронтенд конвертация (может быть оправдано) |

**Проблема:** `CurrencyService.convert_price()` работает только из USD, а здесь нужна конвертация между балансными валютами (RUB↔USD).

**Решение:** 
1. Создать метод `CurrencyService.convert_balance(from_currency: str, to_currency: str, amount: float) -> float` для конвертации между балансными валютами (только RUB↔USD)
2. Заменить ручную конвертацию в `profile.py:773-794` (convert_balance endpoint) на новый метод
3. Заменить ручную конвертацию в `profile.py:534-542` (topup endpoint) на новый метод
4. Стандартизировать округление в методе (убрать дублирование)

### 3.2 Несогласованности паттернов БД запросов

**Проблема:** Смешанное использование синхронных и асинхронных паттернов.

| Проблема | Пример | Решение |
|----------|--------|---------|
| `get_database()` | Используется везде одинаково | ✅ Уже единый источник |
| Прямые запросы к БД | `db.client.table()` в роутерах вместо domains | Мигрировать на domains |
| **Синхронные запросы** | `asyncio.to_thread(lambda: db.client.table()...)` в `profile.py` (20+ мест) | ⚠️ Стандартизировать на async domains |

**Найдено:** `core/routers/webapp/profile.py` использует `asyncio.to_thread()` для 20+ запросов:
- Строки 126-170: 5 запросов
- Строки 440-831: 10+ запросов  
- Все запросы обёрнуты в `lambda: db.client.table()...execute()`

**Проблема:** `supabase-py` уже async, но используется синхронно через `to_thread`. Domains уже async.

**Решение:** Заменить прямые запросы на вызовы domains методов, которые уже async.

### 3.4 Удалить `core/services/database.py` facade

**Проблема:** 398 строк wrapper'ов над repositories/domains

**Решение:**
1. Постепенно заменить `db.get_user_by_telegram_id()` на `db.users_domain.get_by_telegram_id()`
2. Удалить устаревшие методы
3. Оставить только: `client`, `users_domain`, `products_domain`, etc.

---

## 🚀 Часть 4: Оптимизация

### 4.1 Cold Start Optimization

| Проблема | Решение |
|----------|---------|
| Тяжёлые imports в `api/index.py` | Lazy imports для всех роутеров |
| `payments.py` импортирует все шлюзы | Импортировать только нужный |

### 4.2 Database Query Optimization

| Проблема | Файл | Решение |
|----------|------|---------|
| **N+1 queries в каталоге** | `repositories/product_repo.py:10-20, 22-32` | ⚠️ Для каждого продукта делается отдельный запрос stock_count |
| **Синхронные запросы через to_thread** | `routers/webapp/profile.py` (20+ мест) | Заменить на async domains |
| Multiple queries в корзине | `cart/service.py` | Single JOIN query |
| Прямые запросы вместо domains | `profile.py`, `admin/users.py` | Мигрировать на domains |

**КРИТИЧЕСКОЕ N+1:** В `ProductRepository.get_all()`, `get_by_id()`, `search()`:
```python
# Для КАЖДОГО продукта - отдельный запрос stock_count!
# Строки 16, 30, 42 - в цикле делается запрос для каждого продукта
stock = self.client.table("stock_items").select("id", count="exact")...
```

**Проблема:** Если 50 продуктов → 50 отдельных запросов stock_count.

**Решение:** 
1. Использовать VIEW `available_stock_with_discounts` (проверить, содержит ли stock_count)
2. Или использовать JOIN в SQL запросе
3. Или использовать `db.get_available_stock_count()` который уже существует, но batch loading для всех продуктов сразу

**Найдено:** `db.get_available_stock_count()` уже используется в других местах:
- `core/routers/webapp/orders.py:600, 1053`
- `core/routers/webapp/cart.py:223, 257`
- `core/agent/tools/checkout.py:153`

**Но в `ProductRepository` не используется!** ⚠️

**Дополнительные места с N+1:**
- `core/routers/admin/products.py:81-84` — цикл с запросами для каждого продукта
- `core/bot/discount/handlers/catalog.py:90-98` — цикл с запросами stock_count

**Решение (приоритетно):**

**Вариант 1: Создать VIEW `products_with_stock_summary` (РЕКОМЕНДУЕТСЯ)**
```sql
CREATE VIEW products_with_stock_summary AS
SELECT 
    p.*,
    COUNT(si.id) FILTER (
        WHERE si.status = 'available' 
        AND (si.expires_at IS NULL OR si.expires_at > NOW())
    ) AS stock_count,
    COUNT(si.id) FILTER (WHERE si.status = 'sold') AS sold_count
FROM products p
LEFT JOIN stock_items si ON p.id = si.product_id
GROUP BY p.id;
```
Затем использовать: `db.client.table("products_with_stock_summary").select("*").eq("status", status).execute()`

**Вариант 2: Batch loading через один запрос с IN фильтром**
```python
# После получения всех продуктов, сделать один запрос для всех stock counts
product_ids = [p["id"] for p in products]
stock_counts_result = await self.client.table("stock_items")
    .select("product_id", count="exact")
    .eq("status", "available")
    .in_("product_id", product_ids)
    .execute()
# Map product_id -> count
```

**Вариант 3: Использовать SQL функцию через RPC (для одного продукта уже есть)**
Функция `get_product_with_availability(product_id)` уже возвращает `available_count`, но только для одного продукта.
Можно создать функцию `get_products_with_availability(product_ids[])` для batch.

**Текущее состояние:**
- ❌ VIEW `available_stock_with_discounts` НЕ содержит stock_count (только отдельные stock_items с discount)
- ❌ Функция `get_product_with_availability` только для одного продукта (строка 253 в migrations)
- ❌ `ProductRepository` использует N+1 в `get_all()`, `get_by_id()`, `search()` (строки 16, 30, 42)
- ❌ `core/routers/admin/products.py:81-84` — N+1 для каждого продукта
- ❌ `core/bot/discount/handlers/catalog.py:90-98` — N+1 для каждого продукта
- ❌ `core/routers/webapp/public.py:182-184` — N+1 для каждого продукта (query к available_stock_with_discounts)

**КРИТИЧНО:** N+1 встречается в 5+ местах, нужно исправить везде.

### 4.3 Размер бандла Frontend

| Проблема | Решение |
|----------|---------|
| `NewApp.tsx` (495 строк) | Split into route components |
| `AudioEngine.ts` (493 строк) | Lazy load |

---

## 📅 План выполнения (РАЗБИТ НА 3 ПАРАЛЛЕЛЬНЫХ АГЕНТА)

**⚡ Для параллельной работы созданы 3 независимых документа. Детальные планы в отдельных файлах:**

1. **[Agent 1: Cleanup & Consolidation](./REFACTORING_PLAN_AGENT_1_CLEANUP.md)** — 2-4 дня
   - Phase 0: Консолидация дублирований (Telegram messaging + Currency conversion) — **ПЕРВЫЙ** (2-3 дня)
   - Phase 1: Cleanup (deprecated код, unused imports, документация) — 1-2 дня

2. **[Agent 2: Monolith Splitting](./REFACTORING_PLAN_AGENT_2_SPLITTING.md)** — 7-10 дней
   - Phase 2: Split Notifications & Workers — **ЗАВИСИТ ОТ Phase 0 Agent 1** (3-4 дня)
   - Phase 3: Split Profile Router — **ЗАВИСИТ ОТ Phase 0 Agent 1** (2-3 дня)
   - Phase 4: Split Orders Router — 2 дня

3. **[Agent 3: Database & Performance](./REFACTORING_PLAN_AGENT_3_OPTIMIZATION.md)** — 5-7 дней
   - Phase 7: Database Query Optimization (N+1 queries, async паттерны) — 3-4 дня

**Последовательность и зависимости:**
```
Day 1-3:  Agent 1 (Phase 0) — КОНСОЛИДАЦИЯ (критично, первый)
          └─> Agent 2 ждёт завершения Phase 0 (нужен telegram_messaging.py)
          └─> Agent 3 может начать параллельно (N+1 queries не пересекается)

Day 4-7:  Agent 1 (Phase 1) + Agent 2 (Phase 2) + Agent 3 (Phase 7) — ПАРАЛЛЕЛЬНО
          ├─> Agent 1: Cleanup (deprecated код, unused imports)
          ├─> Agent 2: Split Notifications & Workers (использует telegram_messaging.py)
          └─> Agent 3: N+1 queries, async паттерны (не пересекается)

Day 8-10: Agent 2 (Phase 3, Phase 4) — ЗАВЕРШЕНИЕ РАЗБИТИЯ
          └─> Agent 3 может продолжать параллельно (async паттерны в разбитых модулях)

Day 11+:  Agent 3 (завершение Phase 7) — ОПТИМИЗАЦИЯ
```

**⚠️ ВАЖНО:** Каждый агент работает по своему документу. Детальные планы, checklist и координация — в соответствующих документах выше.

---

## 📅 Детальный план (для справки)

### Phase 0: Консолидация дублирований (КРИТИЧНО, 2-3 дня) 🔴
**📄 См. детальный план в [REFACTORING_PLAN_AGENT_1_CLEANUP.md](./REFACTORING_PLAN_AGENT_1_CLEANUP.md)**

**Приоритет 1: Telegram Messaging Service**
- [ ] Создать `core/services/telegram_messaging.py` с единой функцией отправки
- [ ] Заменить все 8+ дубликатов на вызов единого сервиса
- [ ] Добавить retry logic и error handling
- [ ] Тесты
- [ ] Commit: `refactor: consolidate telegram message sending into single service`

**Приоритет 2: Currency Conversion**
- [ ] Создать метод `CurrencyService.convert_balance(from_currency, to_currency, amount)`
- [ ] Заменить ручную конвертацию в `profile.py:773-794` (convert_balance endpoint)
- [ ] Заменить ручную конвертацию в `profile.py:534-542` (topup endpoint)
- [ ] Стандартизировать округление в методе (убрать дублирование)
- [ ] Тесты (RUB→EUR, USD→RUB, EUR→USD, etc.)
- [ ] Commit: `refactor: add CurrencyService.convert_balance and replace manual conversion`

### Phase 1: Cleanup (1-2 дня)
- [ ] Удалить устаревшую документацию
- [ ] Удалить deprecated код (3 места найдено)
- [ ] Очистить unused imports (14+ файлов)
- [ ] Commit: `chore: cleanup deprecated code and docs`

### Phase 2: Split Notifications & Workers (КРИТИЧНО, 3-4 дня) 🔴

**Приоритет:** После Phase 0 (консолидация дублирований)

**Задачи:**
- [ ] Создать `core/services/notifications/` (разбить 1281 строку на модули)
- [ ] Создать `core/routers/workers/` (разбить 1271 строку на модули)
- [ ] Вынести `telegram_messaging.py` из консолидации Phase 0
- [ ] Тесты
- [ ] Commit: `refactor: split notifications and workers monoliths`

### Phase 3: Split Profile Router (2-3 дня) 🟡

**Задачи:**
- [ ] Создать `core/routers/webapp/profile/` (разбить 1145 строк)
- [ ] Убрать ручную конвертацию валют (использовать CurrencyService)
- [ ] Заменить `asyncio.to_thread()` на async domains (20+ мест)
- [ ] Тесты
- [ ] Commit: `refactor: split profile router and fix currency conversion`

### Phase 4: Split Orders Router (2 дня) 🟡

**Задачи:**
- [ ] Создать `core/routers/webapp/orders/` (разбить 1110 строк)
- [ ] Вынести CRUD операции в `crud.py`
- [ ] Вынести payment logic в `payments.py`
- [ ] Тесты
- [ ] Commit: `refactor: split orders router`

### Phase 5: Опциональные разбиения (низкий приоритет, отложено) 🟢

**Payments (544 строки — уже упрощён):**
- [ ] Разбить только если будет добавлен новый платёжный шлюз
- [ ] Commit: `refactor: split payments service` (если нужно)

**Webhooks (469 строк — уже упрощён):**
- [ ] Разбить только если будет добавлен новый webhook
- [ ] Commit: `refactor: split webhooks router` (если нужно)

**Примечание:** 544 и 469 строк — приемлемые размеры. Разбиение не критично, можно отложить.

### Phase 6: Database Facade Cleanup (низкий приоритет, отложено) 🟢

**Задачи:**
- [ ] Заменить facade calls на domain calls (где возможно)
- [ ] Удалить устаревшие методы
- [ ] Commit: `refactor: remove database facade wrapper methods`

**Примечание:** Низкий приоритет — facade работает, просто избыточен.

### Phase 7: Database Query Optimization (КРИТИЧНО для масштабирования, 3-4 дня) 🔴

**Приоритет:** После Phase 0 (критично для производительности при росте каталога)

**Важно:** Это должно быть выполнено ДО масштабирования каталога. При 50+ продуктах N+1 становится заметной проблемой.

**Задачи:**
- [ ] Создать VIEW `products_with_stock_summary` с агрегированным stock_count
- [ ] Исправить N+1 в `ProductRepository.get_all()`, `get_by_id()`, `search()` (3 метода)
- [ ] Исправить N+1 в `core/routers/admin/products.py:81-84`
- [ ] Исправить N+1 в `core/bot/discount/handlers/catalog.py:90-98`
- [ ] Исправить N+1 в `core/routers/webapp/public.py:182-184`
- [ ] Заменить `asyncio.to_thread()` на async domains в `profile.py` (20+ мест)
- [ ] Мигрировать прямые запросы `db.client.table()` на domains методы
- [ ] Тесты (проверить производительность с 50+ продуктами)
- [ ] Commit: `perf: fix N+1 queries and optimize database access patterns`

### Phase 8: Frontend Optimization (2 дня)
- [ ] Split `NewApp.tsx`
- [ ] Lazy load heavy components
- [ ] Commit: `refactor: optimize frontend bundle`

---

## 🔍 Дополнительные находки (расширенное исследование 2026-01-27)

### Циклические импорты
**Статус:** ✅ Используется lazy imports в `core/__init__.py` и `core/routers/deps.py` - проблема решена.

### Error Handling консистентность
**Найдено:** Разные паттерны обработки ошибок:
- `core/bot/handlers/helpers.py:36-62` - `safe_answer()` с обработкой Telegram ошибок ✅
- `core/services/notifications.py` - прямые try/except без централизованной логики ⚠️
- `core/routers/workers.py` - разные паттерны обработки ошибок ⚠️

**Решение:** Стандартизировать через единый error handler или использовать `safe_answer()` везде.

---

## 🚨 Противоречия и наслоения логики (обнаружено 2026-01-27)

### 🔴 ПРОТИВОРЕЧИЕ 1: DEPRECATED поля Order модели всё ещё читаются

**Проблема:** Поля `product_id`, `stock_item_id`, `delivery_content`, `delivery_instructions` помечены как DEPRECATED в модели, но код их всё ещё читает.

| Место | Строки | Проблема |
|-------|--------|----------|
| `core/services/models.py:111-115` | Order model | ✅ Поля помечены DEPRECATED |
| `core/services/repositories/order_repo.py:64-77` | create() | ✅ Проверяет и удаляет deprecated поля при создании |
| `core/routers/webapp/orders.py:373-374, 419` | get_webapp_orders() | ❌ **ЧИТАЕТ `o.product_id`** (может быть None!) |

**Конкретный пример:**
```python
# core/routers/webapp/orders.py:373-374
for o in orders:
    if o.product_id:  # ⚠️ DEPRECATED поле, может быть None!
        product_ids.add(o.product_id)
```

**Проблема:** 
- Старые заказы могут иметь `product_id` в БД (legacy данные)
- Новые заказы НЕ должны иметь `product_id` (OrderRepository.create() удаляет)
- Код читает `o.product_id`, но должен использовать `order_items` (источник правды)

**Решение:**
- Убрать чтение `o.product_id` из `get_webapp_orders()`
- Использовать только `order_items` (который уже загружается)
- `product_ids` уже собирается из `items_data` (строка 376) - достаточно

### 🔴 ПРОТИВОРЕЧИЕ 2: Синхронные запросы через `asyncio.to_thread` (наслоение старого паттерна)

**Проблема:** `supabase-py` уже async, но используется синхронно через `asyncio.to_thread` в 50+ местах.

| Файл | Количество | Проблема |
|------|-----------|----------|
| `core/routers/webapp/profile.py` | **21+ мест** | `asyncio.to_thread(lambda: db.client.table()...)` |
| `core/routers/workers.py` | **10+ мест** | То же самое |
| `core/routers/webhooks.py` | **5+ мест** | То же самое |
| `core/routers/admin/replacements.py` | **5+ мест** | То же самое |
| `core/routers/webapp/partner.py` | **3+ места** | То же самое |
| `api/cron/daily_cleanup.py` | **4 места** | То же самое |

**Почему это проблема:**
- `supabase-py` имеет async методы: `await client.table().select().execute()`
- Domains уже используют async методы правильно
- `asyncio.to_thread()` обёртывает синхронный вызов → лишняя индirection, overhead

**Пример противоречия:**
```python
# ❌ Старый паттерн (50+ мест):
result = await asyncio.to_thread(
    lambda: db.client.table("users").select("*").eq("id", user_id).execute()
)

# ✅ Правильный паттерн (используется в domains):
result = await db.client.table("users").select("*").eq("id", user_id).execute()
```

**Решение:**
- Заменить все `asyncio.to_thread(lambda: db.client.table()...)` на прямые async вызовы
- Или использовать domains методы (которые уже async)

### 🔴 ПРОТИВОРЕЧИЕ 3: Supplier функциональность — инфраструктура есть, логика не реализована

**Проблема:** Supplier инфраструктура создана (таблицы, поля, endpoint), но функциональность не работает.

| Место | Статус | Проблема |
|-------|--------|----------|
| **БД: `suppliers` таблица** | ✅ Существует | 0 строк, но структура есть (id, name, telegram_id, etc.) |
| **БД: `products.supplier_id`** | ✅ Существует | Foreign key на `suppliers.id`, используется в админке |
| **БД: `stock_items.supplier_id`** | ✅ Существует | Foreign key на `suppliers.id` |
| **БД: `expenses.supplier_id`** | ✅ Существует | Foreign key на `suppliers.id`, используется в accounting |
| **БД: `orders.supplier_notified_at`** | ✅ Существует | Поле добавлено в миграции `003_add_on_demand_orders.sql` |
| `core/routers/workers.py:516-525` | ⚠️ DEPRECATED endpoint | Возвращает `{"deprecated": True}`, но упомянут в документации |
| `docs/api-specification.md:195-210` | ❌ Устаревшая документация | Описывает `notify-supplier` endpoint |
| `docs/api-specification.md:212-228` | ❌ Устаревшая документация | Описывает **несуществующий** `notify-supplier-prepaid` endpoint |
| `docs/ON_DEMAND_ORDERS.md:253, 280` | ❌ Устаревшая документация | Упоминает `notify-supplier-prepaid` |
| `core/queue.py:275-276` | ⚠️ Константы | `NOTIFY_SUPPLIER` и `NOTIFY_SUPPLIER_PREPAID` упомянуты, но не используются |
| `core/routers/admin/models.py:92, 99` | ❌ Активен | `supplier_id: Optional[str]` в моделях CreateProduct/UpdateProduct |
| `core/routers/admin/accounting.py:53, 665` | ❌ Активен | Использует `supplier_id` в expense моделях |
| `core/routers/admin/products.py:236, 268` | ❌ Активен | Позволяет установить `supplier_id` при создании/обновлении продукта |
| `supabase/migrations/003_add_on_demand_orders.sql:164, 167` | ⚠️ SQL функция | `process_prepaid_payment` упоминает `supplier_id` и `supplier_notified_at` |

**Вывод:** Supplier функциональность была запланирована, схема БД создана (таблица `suppliers`, foreign keys), но бизнес-логика не реализована. Остался "призрачный" код в нескольких слоях (БД, admin, документация, константы).

**Статус в БД (проверено через MCP):**
- ✅ Таблица `suppliers` существует (0 строк, но структура есть)
- ✅ `products.supplier_id` → `suppliers.id` (foreign key)
- ✅ `stock_items.supplier_id` → `suppliers.id` (foreign key)
- ✅ `expenses.supplier_id` → `suppliers.id` (foreign key)
- ✅ `orders.supplier_notified_at` поле существует

**Решение (приоритетно):**
1. **Если supplier НЕ нужен** (скорее всего, так как endpoint DEPRECATED):
   - Удалить endpoint `worker_notify_supplier()` (workers.py:516-525)
   - Удалить константы `NOTIFY_SUPPLIER`, `NOTIFY_SUPPLIER_PREPAID` из `WorkerEndpoints` (queue.py:275-276)
   - Удалить `supplier_id` из admin models (models.py, accounting.py, products.py)
   - Обновить документацию (api-specification.md, ON_DEMAND_ORDERS.md)
   - Создать миграцию для удаления `supplier_notified_at` из orders
   - Создать миграцию для удаления `supplier_id` из products, stock_items, expenses (⚠️ проверить данные)
   - Удалить таблицу `suppliers` (⚠️ проверить данные, скорее всего пустая)

2. **Если supplier нужен** (маловероятно, так как endpoint DEPRECATED):
   - Реализовать `worker_notify_supplier()` (сейчас возвращает `{"deprecated": True}`)
   - Реализовать `worker_notify_supplier_prepaid()` (сейчас не существует, только в документации)
   - Добавить бизнес-логику уведомлений поставщиков

**Рекомендация:** Удалить supplier функциональность полностью (все признаки указывают на то, что она не используется: endpoint DEPRECATED, таблица пустая, документация не соответствует коду).

### 🟡 ПРОТИВОРЕЧИЕ 4: DEPRECATED функции не используются, но экспортируются

**Проблема:** DEPRECATED функции помечены, но никто их не вызывает.

| Функция | Файл | Статус | Использование |
|---------|------|--------|---------------|
| `fulfill_order()` | `core/services/notifications.py:89` | DEPRECATED | ❌ Никто не вызывает |
| `convert_order_prices()` | `core/orders/serializer.py:39` | DEPRECATED | ❌ Экспортируется в `__init__.py`, но не используется |

**Решение:**
- Удалить `fulfill_order()` (полностью заменена на `_deliver_items_for_order`)
- Проверить, используется ли `convert_order_prices()` где-то в старом коде
- Если не используется → удалить или оставить только в `__init__.py` с warning

### 🟡 ПРОТИВОРЕЧИЕ 5: Смешанные паттерны доступа к БД

**Проблема:** В одном коде используются три разных паттерна:
1. Repository pattern (правильно)
2. Domain services (правильно)
3. Прямые запросы `db.client.table()` (противоречит паттерну)

| Паттерн | Где используется | Проблема |
|---------|------------------|----------|
| Repository | `core/services/repositories/` | ✅ Правильно |
| Domain services | `core/services/domains/` | ✅ Правильно |
| Прямые запросы | Роутеры (50+ мест) | ❌ Обходит абстракции |

**Пример:**
```python
# ❌ В роутере (прямой доступ):
result = await asyncio.to_thread(
    lambda: db.client.table("orders").select("*").eq("id", order_id).execute()
)

# ✅ Через domain (правильно):
order = await db.orders_domain.get_by_id(order_id)
```

**Решение:**
- Мигрировать прямые запросы на domains методы
- Это уже запланировано в Phase 7, но стоит отметить как противоречие

---

## 🗑️ Лишний код (dead code)

### 1. Неиспользуемые DEPRECATED функции

**Можно удалить:**
- `core/services/notifications.py:89-200` - `fulfill_order()` (никто не вызывает, заменена на `_deliver_items_for_order`)
- `core/orders/serializer.py:39-70` - `convert_order_prices()` (если не используется, проверить grep)

### 2. Неиспользуемый DEPRECATED endpoint

**Можно удалить:**
- `core/routers/workers.py:516-525` - `worker_notify_supplier()` (возвращает только `{"deprecated": True}`)

**НО:** Проверить, не вызывается ли этот endpoint из QStash или других сервисов. Если нет → удалить.

### 3. Устаревшая логика чтения deprecated полей

**Код, который нужно исправить:**
- `core/routers/webapp/orders.py:373-374, 419` - чтение `o.product_id` (заменить на использование `order_items`)

---

## 📊 Итоговая таблица противоречий

| # | Противоречие | Критичность | Файлы | Решение |
|---|--------------|-------------|-------|---------|
| 1 | DEPRECATED поля Order читаются | 🔴 Высокая | `webapp/orders.py:373-374` | Использовать только `order_items` |
| 2 | Синхронные запросы через to_thread | 🔴 Высокая | 50+ мест | Заменить на async |
| 3 | Supplier частично DEPRECATED | 🟡 Средняя | `workers.py`, `admin/models.py` | Решить: удалить или использовать |
| 4 | DEPRECATED функции не используются | 🟡 Средняя | `notifications.py`, `serializer.py` | Удалить если не используются |
| 5 | Смешанные паттерны доступа к БД | 🟡 Средняя | Роутеры (50+ мест) | Мигрировать на domains (Phase 7) |
| 6 | Endpoint упомянут, но не реализован | 🟡 Средняя | `docs/`, `core/queue.py` | Удалить из документации или реализовать |
| 7 | Устаревшая документация | 🟡 Средняя | `docs/api-specification.md` | Обновить или удалить упоминания |

---

## 🚨 Критические наслоения логики

### 🔴 НАСЛОЕНИЕ 1: Старый и новый паттерн доступа к Order данным

**Проблема:** Смешиваются два источника данных для Order:
1. **Старый паттерн:** Чтение `o.product_id` из Order model (DEPRECATED)
2. **Новый паттерн:** Использование `order_items` (источник правды)

**Конкретный пример (противоречие):**
```python
# core/routers/webapp/orders.py:373-419
# СТАРЫЙ паттерн (строки 373-374):
for o in orders:
    if o.product_id:  # ⚠️ DEPRECATED поле, может быть None!
        product_ids.add(o.product_id)

# НОВЫЙ паттерн (строка 376):
for it in items_data:  # ✅ Правильно - order_items это источник правды
    if it.get("product_id"):
        product_ids.add(it["product_id"])
```

**Проблема:** Два источника данных для одного и того же (`product_id` из Order и из order_items). Старые заказы могут иметь `product_id`, новые — нет.

**Решение:**
- Убрать строки 373-374 (старый паттерн)
- Использовать только `items_data` (строка 376) — это уже делается правильно

### 🔴 НАСЛОЕНИЕ 2: Синхронные и асинхронные паттерны работы с БД

**Проблема:** В одном коде используются три разных подхода:
1. **Repository pattern** (async) — правильно
2. **Domain services** (async) — правильно  
3. **Прямые запросы через `asyncio.to_thread`** (синхронная обёртка) — противоречие

**Пример наслоения:**
```python
# ✅ Правильно (async domains):
order = await db.orders_domain.get_by_id(order_id)

# ❌ Противоречие (50+ мест):
result = await asyncio.to_thread(
    lambda: db.client.table("orders").select("*").eq("id", order_id).execute()
)
```

**Почему это наслоение:**
- `supabase-py` уже async: `await client.table().select().execute()`
- Domains уже используют async правильно
- Роутеры обёртывают async в `to_thread` → лишняя индirection, overhead

**Места наслоения:**
- `profile.py`: 21+ мест
- `workers.py`: 10+ мест
- `webhooks.py`: 5+ мест
- `admin/replacements.py`: 5+ мест
- `partner.py`: 3+ места
- `daily_cleanup.py`: 4 места
- **Всего: 50+ мест**

---

## 🗑️ Лишний код (dead code)

### 1. Неиспользуемые DEPRECATED функции

| Функция | Файл | Размер | Статус | Действие |
|---------|------|--------|--------|----------|
| `fulfill_order()` | `notifications.py:89-200` | ~112 строк | ❌ Никто не вызывает | ✅ **Удалить** |
| `convert_order_prices()` | `serializer.py:39-70` | ~32 строки | ❌ Экспортируется, но не используется | ⚠️ Проверить импорты, затем удалить |

**Проверка:**
- `fulfill_order()` — grep показал, что никто не вызывает ✅
- `convert_order_prices()` — экспортируется в `__init__.py`, но grep не нашёл использования ✅

### 2. Неиспользуемый DEPRECATED endpoint

| Endpoint | Файл | Статус | Документация | Действие |
|----------|------|--------|--------------|----------|
| `worker_notify_supplier()` | `workers.py:516-525` | Возвращает `{"deprecated": True}` | ❌ Упоминается в `docs/api-specification.md` | ⚠️ Удалить endpoint + обновить документацию |
| `notify-supplier-prepaid` | Не реализован | Нет endpoint | ❌ Упоминается в `docs/`, `WorkerEndpoints` | ⚠️ Удалить из документации или реализовать |

**Дополнительно:**
- `WorkerEndpoints.NOTIFY_SUPPLIER` упомянут в `core/queue.py:275`, но endpoint не работает
- `WorkerEndpoints.NOTIFY_SUPPLIER_PREPAID` упомянут в `core/queue.py:276`, но endpoint не существует
- Документация `docs/api-specification.md:195-210` описывает несуществующий endpoint

### 3. Устаревшая логика чтения deprecated полей

**Код, который нужно исправить:**
- `core/routers/webapp/orders.py:373-374` — чтение `o.product_id` (заменить на использование `order_items`)
- `core/routers/webapp/orders.py:419` — чтение `o.product_id` для получения product (использовать items_data)

### 4. Supplier функциональность — частично реализована

**Проблема:** Supplier упомянут в нескольких местах, но функциональность не работает.

| Место | Статус | Проблема |
|-------|--------|----------|
| `core/routers/workers.py:516-525` | DEPRECATED endpoint | Возвращает `{"deprecated": True}` |
| `docs/api-specification.md:195-210` | Устаревшая документация | Описывает несуществующий endpoint |
| `core/queue.py:275-276` | Константы в коде | Упоминают несуществующие endpoints |
| `docs/ON_DEMAND_ORDERS.md:280` | Устаревшая документация | Упоминает `notify-supplier-prepaid` |
| `core/routers/admin/models.py:92, 99` | Активен | `supplier_id: Optional[str]` в моделях |
| `core/routers/admin/accounting.py:53, 665` | Активен | Использует `supplier_id` |
| `core/routers/admin/products.py:236, 268` | Активен | Позволяет установить `supplier_id` |
| `supabase/migrations/003_add_on_demand_orders.sql:164, 167` | В БД | Упоминает `supplier_id` и `supplier_notified_at` |

**Вывод:** Supplier функциональность была запланирована, но не реализована. Остался "призрачный" код в нескольких местах.

**Решение:**
- Если supplier НЕ нужен → удалить все упоминания (admin models, документация, endpoints, константы)
- Если supplier нужен → реализовать функциональность полностью

---

## 📋 Checklist перед каждым изменением

- [ ] Все тесты проходят
- [ ] `python -m pyflakes core/` чист
- [ ] `npm run build` успешен
- [ ] Нет циклических импортов
- [ ] Backward compatibility сохранена (re-exports)

---

## 🎯 Ожидаемые результаты

| Метрика | До рефакторинга (оригинал) | Текущее состояние | После полного рефакторинга |
|---------|---------------------------|-------------------|---------------------------|
| Макс. размер файла | 1836 строк (tools.py) | ✅ tools.py разбит (max 567) | <400 строк |
| Дублирование Telegram отправки | 8+ мест | ❌ Все ещё 8+ мест | 1 сервис |
| Ручная конвертация валют | 3+ места | ❌ Все ещё в profile.py | Только CurrencyService |
| N+1 queries | В 5+ местах | ❌ Все ещё в 5+ местах | Исправлено (VIEW/batch) |
| Unused imports | 14+ файлов | ❌ Все ещё 14+ файлов | 0 |
| DEPRECATED код | 13+ мест | ❌ Все ещё 3+ места | 0 |
| Устаревшая документация | 6+ файлов | ✅ Удалена | 0 |
| Payments монолит | 1589 строк (4 шлюза) | ✅ Упрощён (544, 1 шлюз) | Опционально разбить |
| Webhooks монолит | 908 строк (4 webhook'а) | ✅ Упрощён (469, 1 webhook) | Опционально разбить |
| Agent tools монолит | 1836 строк | ✅ Разбит (8 модулей) | ✅ Выполнено |
| Cold start time | ~3s | ⚠️ Не проверено | ~2s |
| Maintainability | Средняя | 🟡 Улучшилась частично | Высокая |

---

## ⚠️ Риски

1. **Breaking changes** — минимизировать через re-exports
2. **Circular imports** — тестировать после каждого изменения (lazy imports уже есть)
3. **Vercel function limit** — не создавать новые entry points (остается один `api/index.py`)
4. **N+1 queries** — может быть не заметно при малом количестве продуктов, но критично при масштабировании

---

## 📝 Примечания

- Каждый refactoring должен быть отдельным PR
- Не смешивать refactoring с новой функциональностью
- Документировать все breaking changes в CHANGELOG
- **Phase 0 (консолидация дублирований) имеет наивысший приоритет** — это критичные архитектурные проблемы

---

## 📊 Резюме исследования и проверки актуальности (2026-01-27)

### ✅ УЖЕ ВЫПОЛНЕНО (из PROJECT_MAP.md и проверки кода)

| Рефакторинг | Было | Стало | Статус |
|-------------|------|-------|--------|
| `core/agent/tools.py` разбит | 1836 строк (монолит) | **8 модулей** (max 567 строк) | ✅ **ВЫПОЛНЕНО** |
| 1Plat, Freekassa, Rukassa удалены | 3 платёжных шлюза | **Только CrystalPay** | ✅ **ВЫПОЛНЕНО** |
| `payments.py` упрощён | 1589 строк (4 шлюза) | **544 строки** (только CrystalPay) | ✅ **ВЫПОЛНЕНО** |
| `webhooks.py` упрощён | 908 строк (4 webhook'а) | **469 строк** (только CrystalPay) | ✅ **ВЫПОЛНЕНО** |
| Устаревшая документация | 10+ файлов | **Удалена** | ✅ **ВЫПОЛНЕНО** |

**Вывод:** Частичный рефакторинг уже был выполнен! План был создан до этих изменений.

### 🔴 Критические проблемы (актуально)

1. **Дублирование Telegram отправки** — 8+ мест с одинаковой логикой (критично)
2. **Монолитные файлы** — 6 файлов >1000 строк:
   - `notifications.py`: 1281 строка
   - `workers.py`: 1271 строка
   - `profile.py`: 1145 строк (было 1113 - увеличился)
   - `orders.py`: 1110 строк
   - `broadcast.py`: 975 строк
   - `accounting.py`: 866 строк
3. **N+1 queries** — в 5+ местах:
   - `ProductRepository.get_all()`, `get_by_id()`, `search()` (3 метода)
   - `admin/products.py:81-84`
   - `discount/handlers/catalog.py:90-98`
   - `webapp/public.py:182-184`
4. **Ручная конвертация валют** — в `profile.py:786-806` вместо `CurrencyService`

### 🟡 Средние проблемы (актуально)

5. **Синхронные запросы через to_thread** — 20+ мест в `profile.py` вместо async domains
6. **Несогласованность error handling** — разные паттерны в разных файлах
7. **DEPRECATED код** — 3+ места с устаревшим кодом
8. **Unused imports** — 14+ файлов

### 🟢 Низкие проблемы (актуально)

9. **Database facade** — 437 строк wrapper'ов (работает, но избыточно)
10. **Payments/Webhooks монолиты** — 544 и 469 строк (приемлемый размер, разбиение опционально)
11. **Frontend bundle** — можно оптимизировать

### ✅ Что уже хорошо (актуально)

- ✅ Циклические импорты решены через lazy imports (`core/__init__.py`, `deps.py`)
- ✅ `get_database()` единый источник (используется везде одинаково)
- ✅ QStash правильно используется для критических операций
- ✅ LangGraph + OpenRouter архитектура соответствует правилам (обновлено 2026-01-27)
- ✅ Agent tools уже разбит на модули (8 файлов, max 567 строк)
- ✅ Старые платёжные шлюзы удалены (код упрощён: payments.py 544 строки, webhooks.py 469 строк)

---

## 🔍 Проверка актуальности плана (2026-01-27)

### ✅ Соответствует действительности:

1. **Монолиты обновлены** — актуальные размеры проверены через `wc -l`
2. **Уже выполненные рефакторинги учтены**:
   - ✅ Agent tools разбит (проверено: существует `core/agent/tools/`)
   - ✅ Старые шлюзы удалены (проверено: нет 1Plat/Freekassa/Rukassa в коде)
   - ✅ Payments/webhooks упрощены (проверено: только CrystalPay, размеры обновлены)

### ⚠️ Требует обновления:

1. **Размер profile.py** — был 1113, стал 1145 (увеличился на 32 строки)
2. **N+1 queries** — найдено дополнительное место: `webapp/public.py:182-184`
3. **Phase 2 в старом плане** — был "Split Payments", но payments уже упрощён (нужно убрать из критичных)

### ✅ План актуализирован:

- Разделы 2.1, 2.2, 2.3 обновлены (отмечено как выполненное или упрощённое)
- Добавлена таблица "УЖЕ ВЫПОЛНЕНО"
- Обновлены актуальные размеры файлов
- Phase 2 переименован в "Split Notifications & Workers" (актуально)
- Phase 7 обновлён с деталями N+1 (5+ мест вместо 3)

**Вывод:** План проверен и актуализирован. Отражает текущее состояние проекта после промежуточного рефакторинга.

**Дата проверки:** 2026-01-27  
**Проверено:**
- ✅ Размеры файлов актуализированы (проверено через `wc -l`)
- ✅ Уже выполненные рефакторинги учтены (agent/tools, payments, webhooks)
- ✅ N+1 queries найдены в 5+ местах (обновлено)
- ✅ Currency conversion проблема уточнена (нужен новый метод `convert_balance`)
- ✅ Статус выполнения рефакторингов отражён в таблице "УЖЕ ВЫПОЛНЕНО"

**Следующие шаги (РАЗБИТО НА 3 АГЕНТА):**

📄 **См. детальные планы:**
1. **[Agent 1](./REFACTORING_PLAN_AGENT_1_CLEANUP.md):** Phase 0 (Консолидация) — КРИТИЧНО, первый (2-3 дня)
2. **[Agent 1](./REFACTORING_PLAN_AGENT_1_CLEANUP.md):** Phase 1 (Cleanup) — параллельно с Agent 2, 3 (1-2 дня)
3. **[Agent 2](./REFACTORING_PLAN_AGENT_2_SPLITTING.md):** Phase 2 (Split Notifications & Workers) — после Phase 0 Agent 1 (3-4 дня)
4. **[Agent 2](./REFACTORING_PLAN_AGENT_2_SPLITTING.md):** Phase 3, 4 (Split Profile & Orders) — параллельно (2-3 дня, 2 дня)
5. **[Agent 3](./REFACTORING_PLAN_AGENT_3_OPTIMIZATION.md):** Phase 7 (Database Optimization) — параллельно (3-4 дня)

---

## 🔬 Расширенное исследование: Противоречия и наслоения (2026-01-27)

### 📊 Итоговая статистика находок

| Категория | Количество | Критичность |
|-----------|------------|-------------|
| **Противоречия в логике** | 7 находок | 🔴 2 критических, 🟡 5 средних |
| **Наслоения паттернов** | 2 критических | 🔴 Высокая |
| **Dead code (неиспользуемый)** | 3 места | 🟡 Средняя |
| **Устаревшие реализации** | 1 (supplier) | 🟡 Средняя |
| **Устаревшая документация** | 3 файла | 🟡 Средняя |

### 🔴 Критические противоречия (2)

1. **DEPRECATED поля Order читаются** — `webapp/orders.py:373-374, 419` использует `o.product_id` (DEPRECATED), хотя есть `order_items`
2. **Синхронные запросы через to_thread** — 50+ мест используют `asyncio.to_thread(lambda: db.client.table()...)` вместо async

### 🟡 Средние противоречия (5)

3. **Supplier частично DEPRECATED** — инфраструктура есть (таблица, foreign keys), но логика не работает
4. **DEPRECATED функции не используются** — `fulfill_order()`, `convert_order_prices()` помечены, но никто не вызывает
5. **Смешанные паттерны доступа к БД** — Repository/Domain + прямые запросы (50+ мест)
6. **Endpoint упомянут, но не реализован** — `notify-supplier-prepaid` в документации, но нет в коде
7. **Устаревшая документация** — описывает несуществующие endpoints

### 🔴 Критические наслоения (2)

1. **Старый и новый паттерн Order данных** — чтение `o.product_id` (DEPRECATED) + `order_items` (источник правды)
2. **Синхронные и асинхронные паттерны БД** — `supabase-py` async, но используется синхронно через `to_thread` (50+ мест)

### 🗑️ Dead code (3 места)

1. `fulfill_order()` — 112 строк, никто не вызывает (можно удалить)
2. `convert_order_prices()` — 32 строки, экспортируется, но не используется (проверить, затем удалить)
3. `worker_notify_supplier()` endpoint — возвращает только `{"deprecated": True}` (можно удалить)

### ⚠️ Устаревшие реализации (1)

**Supplier функциональность — классическое наслоение "половина реализации":**
- ✅ Таблица `suppliers` существует в БД (0 строк, но структура есть)
- ✅ Foreign keys: `products.supplier_id`, `stock_items.supplier_id`, `expenses.supplier_id` существуют
- ✅ Поле `orders.supplier_notified_at` существует
- ❌ Endpoint `worker_notify_supplier()` DEPRECATED (возвращает `{"deprecated": True}`)
- ❌ Endpoint `notify-supplier-prepaid` не реализован (только в документации)
- ⚠️ Admin models/endpoints позволяют устанавливать `supplier_id`, но логика не работает
- ⚠️ SQL функция `process_prepaid_payment` упоминает `supplier_id`, но не использует

**Вывод:** Инфраструктура готова (таблицы, поля, foreign keys), бизнес-логика не реализована. Классическое наслоение "половина реализации".

### 📋 Рекомендации по приоритетам

**Критично (следующий спринт):**
1. Исправить чтение DEPRECATED полей Order (`webapp/orders.py:373-374, 419`) — использовать только `order_items`
2. Удалить неиспользуемые DEPRECATED функции (`fulfill_order`, `convert_order_prices`)

**Высоко (в течение месяца):**
3. Заменить `asyncio.to_thread` на async (50+ мест) — улучшит производительность
4. Решить вопрос с supplier (удалить полностью или реализовать)

**Средне (технический долг):**
5. Обновить документацию (убрать упоминания несуществующих endpoints)
6. Мигрировать прямые запросы на domains (уже в Phase 7)

---

**Итог расширенного исследования:** Найдено 13+ мест противоречий и наслоений, требующих внимания. Критичные проблемы связаны с DEPRECATED полями и синхронными запросами. Supplier функциональность — классический пример незавершённой реализации (инфраструктура есть, логика не работает).

---

## 🔬 Расширенное исследование: Противоречия и наслоения (2026-01-27)

### 📊 Итоговая статистика находок

| Категория | Количество | Критичность |
|-----------|------------|-------------|
| **Противоречия в логике** | 7 находок | 🔴 2 критических, 🟡 5 средних |
| **Наслоения паттернов** | 2 критических | 🔴 Высокая |
| **Dead code (неиспользуемый)** | 3 места | 🟡 Средняя |
| **Устаревшие реализации** | 1 (supplier) | 🟡 Средняя |
| **Устаревшая документация** | 3 файла | 🟡 Средняя |

### 🔴 Критические противоречия (2)

1. **DEPRECATED поля Order читаются** — `webapp/orders.py:373-374, 419` использует `o.product_id` (DEPRECATED), хотя есть `order_items`
2. **Синхронные запросы через to_thread** — 50+ мест используют `asyncio.to_thread(lambda: db.client.table()...)` вместо async

### 🟡 Средние противоречия (5)

3. **Supplier частично DEPRECATED** — инфраструктура есть (таблица, foreign keys), но логика не работает
4. **DEPRECATED функции не используются** — `fulfill_order()`, `convert_order_prices()` помечены, но никто не вызывает
5. **Смешанные паттерны доступа к БД** — Repository/Domain + прямые запросы (50+ мест)
6. **Endpoint упомянут, но не реализован** — `notify-supplier-prepaid` в документации, но нет в коде
7. **Устаревшая документация** — описывает несуществующие endpoints

### 🔴 Критические наслоения (2)

1. **Старый и новый паттерн Order данных** — чтение `o.product_id` (DEPRECATED) + `order_items` (источник правды)
2. **Синхронные и асинхронные паттерны БД** — `supabase-py` async, но используется синхронно через `to_thread` (50+ мест)

### 🗑️ Dead code (3 места)

1. `fulfill_order()` — 112 строк, никто не вызывает (можно удалить)
2. `convert_order_prices()` — 32 строки, экспортируется, но не используется (проверить, затем удалить)
3. `worker_notify_supplier()` endpoint — возвращает только `{"deprecated": True}` (можно удалить)

### ⚠️ Устаревшие реализации (1)

**Supplier функциональность:**
- ✅ Таблица `suppliers` существует (0 строк)
- ✅ Foreign keys: `products.supplier_id`, `stock_items.supplier_id`, `expenses.supplier_id`
- ✅ Поле `orders.supplier_notified_at` существует
- ❌ Endpoint `worker_notify_supplier()` DEPRECATED
- ❌ Endpoint `notify-supplier-prepaid` не реализован (только в документации)
- ⚠️ Admin models/endpoints позволяют устанавливать `supplier_id`, но логика не работает

**Вывод:** Инфраструктура готова, бизнес-логика не реализована. Классическое наслоение "половина реализации".

### 📋 Рекомендации по приоритетам

**Критично (следующий спринт):**
1. Исправить чтение DEPRECATED полей Order (`webapp/orders.py:373-374, 419`)
2. Удалить неиспользуемые DEPRECATED функции (`fulfill_order`, `convert_order_prices`)

**Высоко (в течение месяца):**
3. Заменить `asyncio.to_thread` на async (50+ мест) — улучшит производительность
4. Решить вопрос с supplier (удалить полностью или реализовать)

**Средне (технический долг):**
5. Обновить документацию (убрать упоминания несуществующих endpoints)
6. Мигрировать прямые запросы на domains (уже в Phase 7)

---

**Итог расширенного исследования:** Найдено 13+ мест противоречий и наслоений, требующих внимания. Критичные проблемы связаны с DEPRECATED полями и синхронными запросами. Supplier функциональность — классический пример незавершённой реализации.