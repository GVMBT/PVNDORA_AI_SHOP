# 🔧 PVNDORA Refactoring Plan

**Дата:** 2026-01-27  
**Последнее обновление:** 2026-01-27  
**Приоритет:** Критический → Высокий → Средний → Низкий

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

### 🔴 Критические монолиты (>1000 строк) - АКТУАЛЬНЫЕ РАЗМЕРЫ

| Файл | Строк | Проблема |
|------|-------|----------|
| `core/services/notifications.py` | **1281** | Все уведомления + 20+ прямых вызовов bot.send_message |
| `core/routers/workers.py` | **1271** | 5+ workers в одном файле |
| `core/routers/webapp/profile.py` | **1113** | Профиль + баланс + валюта + ручная конвертация |
| `core/routers/webapp/orders.py` | **1110** | Заказы + платежи + доставка |
| `core/bot/admin/handlers/broadcast.py` | **975** | Broadcast логика |
| `core/services/payments.py` | **~1589** | ⚠️ Проверить актуальный размер (возможно изменился) |
| `core/agent/tools.py` | **~1836** | ⚠️ Проверить актуальный размер (возможно разбит) |

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

**Найдено при анализе 2026-01-27:**

```python
# core/orders/serializer.py:48
# DEPRECATED: Use convert_order_prices_with_formatter instead

# core/services/notifications.py:93
# DEPRECATED: Use workers._deliver_items_for_order instead

# core/routers/workers.py:519-525
# DEPRECATED: Supplier functionality is not used.
# TODO: Remove when cleaning up supplier-related tech debt.

# core/services/models.py:105-109 (если существует)
# DEPRECATED fields - will be removed after migration
```

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

### 2.1 `core/services/payments.py` (1589 строк) → 5 файлов

**Текущая структура:**
```
PaymentService
├── 1Plat methods (~300 lines)
├── Freekassa methods (~150 lines)  
├── RuKassa methods (~300 lines)
├── CrystalPay methods (~400 lines)
└── Common methods (~400 lines)
```

**Целевая структура:**
```
core/services/payments/
├── __init__.py          # Re-exports PaymentService
├── base.py              # PaymentService class + common methods
├── oneplat.py           # 1Plat integration
├── freekassa.py         # Freekassa integration
├── rukassa.py           # RuKassa integration
└── crystalpay.py        # CrystalPay integration
```

### 2.2 `core/agent/tools.py` (1836 строк) → 6 файлов

**Текущая структура:**
```
tools.py
├── Catalog tools (get_catalog, search_products, etc)
├── Cart tools (add_to_cart, remove_from_cart, etc)
├── Order tools (get_orders, checkout_cart, etc)
├── Profile tools (get_profile, get_referral_stats, etc)
├── Support tools (create_support_ticket, etc)
└── Utility tools (get_faq, etc)
```

**Целевая структура:**
```
core/agent/tools/
├── __init__.py          # Re-exports all tools
├── context.py           # _UserContext, set_user_context, get_db
├── catalog.py           # Catalog & search tools
├── cart.py              # Cart management tools
├── orders.py            # Order & checkout tools
├── profile.py           # Profile & referral tools
└── support.py           # Support & FAQ tools
```

### 2.3 `core/routers/webhooks.py` (908 строк) → 5 файлов

**Целевая структура:**
```
core/routers/webhooks/
├── __init__.py          # Re-exports router
├── router.py            # Main router
├── oneplat.py           # 1Plat webhook
├── freekassa.py         # Freekassa webhook
├── rukassa.py           # RuKassa webhook
└── crystalpay.py        # CrystalPay webhook
```

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

**КРИТИЧЕСКОЕ:** Убрать ручную конвертацию валют (строки 786-806), использовать `CurrencyService.convert_price()`.

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

**🟡 ДУБЛИРОВАНИЕ: Currency Conversion (3+ места)**

| Место | Проблема |
|-------|----------|
| `core/services/currency.py` | ✅ Основной `CurrencyService` |
| `core/services/currency_response.py` | ✅ `CurrencyFormatter` (wrapper, ОК) |
| `core/routers/webapp/profile.py:786-806` | ❌ Ручная конвертация вместо `CurrencyService.convert_price()` |
| `src/components/new/ProfileConnected.tsx:95-101` | ⚠️ Фронтенд конвертация (может быть оправдано) |

**Решение:** Убрать ручную конвертацию в `profile.py`, использовать `CurrencyService`.

### 3.3 Несогласованности паттернов БД запросов

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

### 4.3 Размер бандла Frontend

| Проблема | Решение |
|----------|---------|
| `NewApp.tsx` (495 строк) | Split into route components |
| `AudioEngine.ts` (493 строк) | Lazy load |

---

## 📅 План выполнения (ОБНОВЛЁН)

### Phase 0: Консолидация дублирований (КРИТИЧНО, 2-3 дня) 🔴

**Приоритет 1: Telegram Messaging Service**
- [ ] Создать `core/services/telegram_messaging.py` с единой функцией отправки
- [ ] Заменить все 8+ дубликатов на вызов единого сервиса
- [ ] Добавить retry logic и error handling
- [ ] Тесты
- [ ] Commit: `refactor: consolidate telegram message sending into single service`

**Приоритет 2: Currency Conversion**
- [ ] Убрать ручную конвертацию из `core/routers/webapp/profile.py:786-806`
- [ ] Использовать `CurrencyService.convert_price()` везде
- [ ] Тесты
- [ ] Commit: `refactor: unify currency conversion using CurrencyService`

### Phase 1: Cleanup (1-2 дня)
- [ ] Удалить устаревшую документацию
- [ ] Удалить deprecated код (3 места найдено)
- [ ] Очистить unused imports (14+ файлов)
- [ ] Commit: `chore: cleanup deprecated code and docs`

### Phase 2: Split Payments (2-3 дня)
- [ ] Создать `core/services/payments/`
- [ ] Вынести 1Plat в отдельный файл
- [ ] Вынести Freekassa в отдельный файл
- [ ] Вынести RuKassa в отдельный файл
- [ ] Вынести CrystalPay в отдельный файл
- [ ] Тесты
- [ ] Commit: `refactor: split payments monolith into modules`

### Phase 3: Split Agent Tools (2-3 дня)
- [ ] Создать `core/agent/tools/`
- [ ] Вынести по категориям
- [ ] Тесты
- [ ] Commit: `refactor: split agent tools into modules`

### Phase 4: Split Notifications & Workers (3-4 дня)
- [ ] Создать `core/services/notifications/` (разбить 1281 строку)
- [ ] Создать `core/routers/workers/` (разбить 1271 строку)
- [ ] Вынести `telegram_messaging.py` в отдельный модуль
- [ ] Тесты
- [ ] Commit: `refactor: split notifications and workers monoliths`

### Phase 4b: Split Webhooks (1-2 дня)
- [ ] Создать `core/routers/webhooks/`
- [ ] Тесты
- [ ] Commit: `refactor: split webhooks`

### Phase 5: Split Profile Router (2 дня)
- [ ] Создать `core/routers/webapp/profile/` (разбить 1113 строк)
- [ ] Убрать ручную конвертацию валют
- [ ] Тесты
- [ ] Commit: `refactor: split profile router and fix currency conversion`

### Phase 6: Database Facade Cleanup (1-2 дня)
- [ ] Заменить facade calls на domain calls (где возможно)
- [ ] Удалить устаревшие методы
- [ ] Commit: `refactor: remove database facade wrapper methods`

### Phase 7: Database Query Optimization (2-3 дня)
- [ ] Исправить N+1 queries в `ProductRepository` (использовать VIEW или JOIN)
- [ ] Заменить `asyncio.to_thread()` на async domains в `profile.py`
- [ ] Мигрировать прямые запросы `db.client.table()` на domains методы
- [ ] Тесты
- [ ] Commit: `perf: optimize database queries - fix N+1 and async patterns`

### Phase 8: Frontend Optimization (2 дня)
- [ ] Split `NewApp.tsx`
- [ ] Lazy load heavy components
- [ ] Commit: `refactor: optimize frontend bundle`

---

## 🔍 Дополнительные находки

### Циклические импорты
**Статус:** ✅ Используется lazy imports в `core/__init__.py` и `core/routers/deps.py` - проблема решена.

### Error Handling консистентность
**Найдено:** Разные паттерны обработки ошибок:
- `core/bot/handlers/helpers.py:36-62` - `safe_answer()` с обработкой Telegram ошибок ✅
- `core/services/notifications.py` - прямые try/except без централизованной логики ⚠️
- `core/routers/workers.py` - разные паттерны обработки ошибок ⚠️

**Решение:** Стандартизировать через единый error handler или использовать `safe_answer()` везде.

---

## 📋 Checklist перед каждым изменением

- [ ] Все тесты проходят
- [ ] `python -m pyflakes core/` чист
- [ ] `npm run build` успешен
- [ ] Нет циклических импортов
- [ ] Backward compatibility сохранена (re-exports)

---

## 🎯 Ожидаемые результаты

| Метрика | До | После |
|---------|----|----|
| Макс. размер файла | 1281 строк | <400 строк |
| Дублирование Telegram отправки | 8+ мест | 1 сервис |
| Ручная конвертация валют | 3+ места | Только CurrencyService |
| Unused imports | 14+ файлов | 0 |
| DEPRECATED код | 13+ мест | 0 |
| Устаревшая документация | 6+ файлов | 0 |
| Cold start time | ~3s | ~2s |
| Maintainability | Средняя | Высокая |

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

## 📊 Резюме исследования (2026-01-27)

### Критические проблемы (🔴)
1. **Дублирование Telegram отправки** — 8+ мест с одинаковой логикой
2. **Монолитные файлы** — 6 файлов >1000 строк (максимум 1281 строка)
3. **N+1 queries** — в `ProductRepository` для каждого продукта отдельный запрос stock_count
4. **Ручная конвертация валют** — в `profile.py` вместо использования `CurrencyService`

### Средние проблемы (🟡)
5. **Синхронные запросы через to_thread** — 20+ мест в `profile.py` вместо async domains
6. **Несогласованность error handling** — разные паттерны в разных файлах
7. **DEPRECATED код** — 3+ места с устаревшим кодом
8. **Unused imports** — 14+ файлов

### Низкие проблемы (🟢)
9. **Database facade** — 398 строк wrapper'ов (работает, но избыточно)
10. **Frontend bundle** — можно оптимизировать

### ✅ Что уже хорошо
- Циклические импорты решены через lazy imports
- `get_database()` единый источник
- QStash правильно используется для критических операций
- LangGraph + OpenRouter архитектура соответствует правилам