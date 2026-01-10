# 🧹 PVNDORA Refactoring Plan - Agent 1: Cleanup & Consolidation

**Агент:** Agent 1 (Cleanup & Consolidation)  
**Дата:** 2026-01-27  
**Приоритет:** 🔴 Критический  
**Оценка:** 2-4 дня

**⚠️ ВАЖНО:** Этот документ для параллельной работы с Agent 2 и Agent 3. Не пересекается по файлам.

---

## 📋 Контекст проекта

**Технологии:**
- Python 3.12 + FastAPI (Vercel Serverless)
- Supabase PostgreSQL (NO ORM, прямой SQL)
- OpenRouter API + LangGraph (AI агент)
- Telegram Bot API (aiogram)
- Upstash QStash (async workers)
- Upstash Redis (кэш)

**Архитектурные ограничения:**
- ✅ Single entry point: `api/index.py` (Vercel limit: 12 functions)
- ✅ QStash для критических async операций
- ✅ НЕ использовать Supabase Triggers для бизнес-логики

**Уже выполнено:**
- ✅ `core/agent/tools.py` разбит (1836 → 8 модулей)
- ✅ Старые платёжные шлюзы удалены (1Plat, Freekassa, Rukassa)
- ✅ `payments.py` упрощён (1589 → 544 строки)
- ✅ `webhooks.py` упрощён (908 → 469 строк)

---

## 🎯 Задачи Agent 1

### Phase 0: Консолидация дублирований (КРИТИЧНО, 2-3 дня) 🔴

#### Приоритет 1: Telegram Messaging Service

**Проблема:** 8+ мест с дублированной логикой отправки Telegram сообщений.

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
) -> bool:
    """
    Send Telegram message with retry logic and error handling.
    
    Args:
        chat_id: Telegram chat ID
        text: Message text (HTML or Markdown)
        parse_mode: "HTML", "Markdown", or None
        bot_token: Optional bot token (default: TELEGRAM_TOKEN)
        retries: Number of retry attempts
        
    Returns:
        True if sent successfully, False otherwise
    """
    # Implementation with retry logic, error handling, logging
```

**Checklist:**
- [ ] Создать `core/services/telegram_messaging.py` с функцией `send_telegram_message()`
- [ ] Добавить retry logic (2 попытки с exponential backoff)
- [ ] Добавить error handling (Telegram API errors, network errors)
- [ ] Добавить logging (успешные отправки, ошибки)
- [ ] Заменить все 8+ дубликатов на вызов единого сервиса:
  - [ ] `core/services/notifications.py` (20+ мест)
  - [ ] `core/routers/admin/broadcast.py:45-72`
  - [ ] `core/services/domains/offers.py:60-84`
  - [ ] `api/cron/deliver_overdue_discount.py:56-78`
  - [ ] `api/workers/deliver_discount_order.py:49-67`
  - [ ] `api/workers/process_review_cashback.py:50-67`
  - [ ] `api/cron/low_stock_alert.py:87-104`
  - [ ] `core/routers/workers.py:933, 1101+`
- [ ] Удалить старые функции `send_telegram_message()` из всех файлов
- [ ] Тесты (unit tests для retry logic, error handling)
- [ ] Commit: `refactor: consolidate telegram message sending into single service`

**Файлы для изменения:**
- `core/services/telegram_messaging.py` (новый файл)
- `core/services/notifications.py` (замена 20+ вызовов)
- `core/routers/admin/broadcast.py` (удалить функцию, использовать сервис)
- `core/services/domains/offers.py` (удалить метод, использовать сервис)
- `api/cron/deliver_overdue_discount.py` (удалить функцию, использовать сервис)
- `api/workers/deliver_discount_order.py` (удалить функцию, использовать сервис)
- `api/workers/process_review_cashback.py` (удалить функцию, использовать сервис)
- `api/cron/low_stock_alert.py` (удалить функцию, использовать сервис)
- `core/routers/workers.py` (заменить прямые вызовы)

#### Приоритет 2: Currency Conversion

**Проблема:** Ручная конвертация валют в 2 местах вместо использования `CurrencyService`.

| Место | Проблема |
|-------|----------|
| `core/services/currency.py` | ✅ Основной `CurrencyService` (но `convert_price()` только из USD) |
| `core/routers/webapp/profile.py:773-794` | ❌ Ручная конвертация баланса (RUB↔USD) через `get_exchange_rate()` |
| `core/routers/webapp/profile.py:534-542` | ❌ Ручная конвертация в topup (payment_currency → balance_currency) |

**Проблема:** `CurrencyService.convert_price()` работает только из USD, а здесь нужна конвертация между балансными валютами (только RUB↔USD).

**Решение:** Создать метод `CurrencyService.convert_balance()` для конвертации между балансными валютами (только RUB↔USD).

**Checklist:**
- [ ] Создать метод `CurrencyService.convert_balance(from_currency: str, to_currency: str, amount: float) -> float` в `core/services/currency.py`
- [ ] Реализовать логику (только RUB↔USD):
  - Если `from_currency == to_currency` → вернуть `amount`
  - Если `from_currency == "USD"` → использовать существующий `convert_price()` для конвертации в RUB
  - Если `from_currency == "RUB"` → делить на rate для конвертации в USD
- [ ] Стандартизировать округление в методе (использовать `round_money()`)
- [ ] Заменить ручную конвертацию в `profile.py:773-794` (convert_balance endpoint) на новый метод
- [ ] Заменить ручную конвертацию в `profile.py:534-542` (topup endpoint) на новый метод
- [ ] Удалить дублированный код округления из `profile.py`
- [ ] Тесты (RUB→USD, USD→RUB, RUB→RUB, USD→USD)
- [ ] Убрать EUR из `valid_currencies` в `convert_balance` endpoint (если есть)
- [ ] Commit: `refactor: add CurrencyService.convert_balance and replace manual conversion`

**Файлы для изменения:**
- `core/services/currency.py` (добавить метод `convert_balance`)
- `core/routers/webapp/profile.py:773-794` (заменить ручную конвертацию)
- `core/routers/webapp/profile.py:534-542` (заменить ручную конвертацию)

---

### Phase 1: Cleanup (1-2 дня) 🟡

#### 1.1 Удалить устаревшую документацию

**Файлы для удаления:**

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

**Checklist:**
- [ ] Удалить все 9 файлов из списка выше
- [ ] Проверить, не используются ли ссылки на эти файлы в других документах
- [ ] Обновить ссылки (если есть)
- [ ] Commit: `chore: remove outdated documentation`

#### 1.2 Удалить deprecated код

**Найдено при анализе 2026-01-27:**

**1. `core/services/notifications.py:89-200` - `fulfill_order()` (112 строк)**

```python
# DEPRECATED: Use workers._deliver_items_for_order instead
async def fulfill_order(self, order_id: str) -> bool:
    # ... 112 строк кода ...
```

**Статус:** Никто не вызывает (проверено grep)  
**Решение:** Удалить полностью

**2. `core/orders/serializer.py:39-70` - `convert_order_prices()` (32 строки)**

```python
# DEPRECATED: Use convert_order_prices_with_formatter instead
async def convert_order_prices(...):
    # ... 32 строки кода ...
```

**Статус:** Экспортируется в `__init__.py`, но НЕ используется в коде (проверено grep)  
**Решение:** Удалить функцию и экспорт из `__init__.py`

**3. `core/routers/workers.py:516-525` - `worker_notify_supplier()` endpoint**

```python
@router.post("/notify-supplier")
async def worker_notify_supplier(request: Request):
    """
    DEPRECATED: Supplier functionality is not used.
    """
    await verify_qstash(request)
    return {"deprecated": True, "message": "Supplier notifications are not used"}
```

**Статус:** Endpoint возвращает только `{"deprecated": True}`, упомянут в документации  
**Решение:** Удалить endpoint + обновить документацию

**4. Supplier функциональность (если решено удалить)**

**Статус в БД (проверено через MCP):**
- ✅ Таблица `suppliers` существует (0 строк, но структура есть)
- ✅ `products.supplier_id` → `suppliers.id` (foreign key)
- ✅ `stock_items.supplier_id` → `suppliers.id` (foreign key)
- ✅ `expenses.supplier_id` → `suppliers.id` (foreign key)
- ✅ `orders.supplier_notified_at` поле существует

**Рекомендация:** Удалить supplier функциональность полностью (endpoint DEPRECATED, таблица пустая, документация не соответствует коду).

**Checklist для supplier cleanup:**
- [ ] Удалить endpoint `worker_notify_supplier()` из `core/routers/workers.py:516-525`
- [ ] Удалить константы `NOTIFY_SUPPLIER`, `NOTIFY_SUPPLIER_PREPAID` из `core/queue.py:275-276`
- [ ] Удалить `supplier_id` из admin models:
  - [ ] `core/routers/admin/models.py:92, 99` (CreateProduct/UpdateProduct)
  - [ ] `core/routers/admin/accounting.py:53, 665` (expense models)
  - [ ] `core/routers/admin/products.py:236, 268` (создание/обновление продукта)
- [ ] Обновить документацию:
  - [ ] `docs/api-specification.md:195-210` (убрать описание `notify-supplier`)
  - [ ] `docs/api-specification.md:212-228` (убрать описание `notify-supplier-prepaid`)
  - [ ] `docs/ON_DEMAND_ORDERS.md:253, 280` (убрать упоминания supplier)
- [ ] Создать миграцию для удаления `supplier_notified_at` из orders
- [ ] Создать миграцию для удаления `supplier_id` из products, stock_items, expenses (⚠️ проверить данные)
- [ ] Удалить таблицу `suppliers` (⚠️ проверить данные, скорее всего пустая)
- [ ] Обновить SQL функцию `process_prepaid_payment` (убрать упоминания supplier)

**Checklist для deprecated кода:**
- [ ] Удалить `fulfill_order()` из `core/services/notifications.py:89-200` (112 строк)
- [ ] Удалить `convert_order_prices()` из `core/orders/serializer.py:39-70` (32 строки)
- [ ] Удалить экспорт `convert_order_prices` из `core/orders/__init__.py`
- [ ] Удалить endpoint `worker_notify_supplier()` из `core/routers/workers.py:516-525`
- [ ] (Опционально) Выполнить supplier cleanup выше
- [ ] Commit: `chore: remove deprecated code (fulfill_order, convert_order_prices, worker_notify_supplier)`

**Файлы для изменения:**
- `core/services/notifications.py` (удалить `fulfill_order`)
- `core/orders/serializer.py` (удалить `convert_order_prices`)
- `core/orders/__init__.py` (удалить экспорт)
- `core/routers/workers.py` (удалить endpoint)
- `core/queue.py` (удалить константы, если удаляем supplier)
- `core/routers/admin/models.py` (удалить supplier_id, если удаляем supplier)
- `core/routers/admin/accounting.py` (удалить supplier_id, если удаляем supplier)
- `core/routers/admin/products.py` (удалить supplier_id, если удаляем supplier)
- `docs/api-specification.md` (обновить, если удаляем supplier)
- `docs/ON_DEMAND_ORDERS.md` (обновить, если удаляем supplier)
- `supabase/migrations/` (создать миграцию для удаления supplier полей, если удаляем)

#### 1.3 Очистить unused imports

**Файлы с unused imports:**

| Файл | Unused Imports |
|------|----------------|
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

**Checklist:**
- [ ] Проверить каждый файл на unused imports (использовать `pyflakes` или `ruff`)
- [ ] Удалить unused imports из всех 10+ файлов
- [ ] Убедиться, что импорты действительно не используются
- [ ] Запустить `python -m pyflakes core/` для проверки
- [ ] Commit: `chore: remove unused imports`

**Файлы для изменения:**
- Все 10+ файлов из списка выше

#### 1.4 Исправить чтение DEPRECATED полей Order

**Проблема:** `core/routers/webapp/orders.py:373-374, 419` читает `o.product_id` (DEPRECATED), хотя есть `order_items`.

**Конкретный пример:**
```python
# core/routers/webapp/orders.py:373-374 (СТАРЫЙ паттерн)
for o in orders:
    if o.product_id:  # ⚠️ DEPRECATED поле, может быть None!
        product_ids.add(o.product_id)

# core/routers/webapp/orders.py:376 (НОВЫЙ паттерн - уже правильно)
for it in items_data:  # ✅ Правильно - order_items это источник правды
    if it.get("product_id"):
        product_ids.add(it["product_id"])
```

**Решение:** Убрать строки 373-374, использовать только `order_items` (строка 376).

**Checklist:**
- [ ] Убрать строки 373-374 из `get_webapp_orders()` (чтение `o.product_id`)
- [ ] Убрать строку 419 (использование `o.product_id` для получения product)
- [ ] Убедиться, что `product_ids` собирается только из `items_data` (строка 376)
- [ ] Убедиться, что product получается из `items_data`, а не из `o.product_id`
- [ ] Тесты (проверить, что старые заказы с `product_id` всё ещё работают через `order_items`)
- [ ] Commit: `fix: use order_items instead of deprecated Order.product_id`

**Файлы для изменения:**
- `core/routers/webapp/orders.py:373-374, 419` (убрать чтение `o.product_id`)

---

## 📋 Checklist перед началом работы

- [ ] Прочитан контекст проекта (технологии, архитектура)
- [ ] Понимаю зависимости между задачами
- [ ] Знаю, какие файлы изменяю (список выше)
- [ ] Готов работать параллельно с Agent 2 и Agent 3

---

## ✅ Критерии готовности

**Phase 0 (Консолидация) считается выполненной, когда:**
- ✅ `telegram_messaging.py` создан и все 8+ мест используют его
- ✅ `CurrencyService.convert_balance()` создан и все ручные конвертации заменены
- ✅ Все тесты проходят
- ✅ `python -m pyflakes core/` чист
- ✅ Commit сделан

**Phase 1 (Cleanup) считается выполненной, когда:**
- ✅ Устаревшая документация удалена (9 файлов)
- ✅ Deprecated код удален (3+ места)
- ✅ Unused imports очищены (10+ файлов)
- ✅ DEPRECATED поля Order больше не читаются
- ✅ (Опционально) Supplier функциональность удалена (если решено)
- ✅ Все тесты проходят
- ✅ `python -m pyflakes core/` чист
- ✅ Commit сделан

---

## 🔄 Координация с другими агентами

**Не пересекается с Agent 2:**
- Agent 2 работает с `notifications.py`, `workers.py`, `profile.py`, `orders.py` — но только с разбиением на модули
- Agent 1 работает с этими же файлами — но только с удалением/заменой кода
- ⚠️ **Важно:** Agent 1 должен закончить Phase 0 ДО того, как Agent 2 начнёт Phase 2 (так как Agent 2 будет использовать `telegram_messaging.py`)

**Не пересекается с Agent 3:**
- Agent 3 работает с БД оптимизацией и async паттернами
- Agent 1 не затрагивает эти области

**Последовательность работы:**
1. Agent 1 выполняет Phase 0 (консолидация) — **ПЕРВЫМ** (2-3 дня)
2. Agent 2 может начать Phase 2 ПОСЛЕ завершения Phase 0 Agent 1
3. Agent 1 выполняет Phase 1 (cleanup) — параллельно с Agent 2 и Agent 3

---

## 📝 Примечания

- Каждая задача должна быть отдельным PR
- Не смешивать cleanup с новой функциональностью
- Все изменения должны быть протестированы
- Backward compatibility не требуется для deprecated кода (он уже не используется)
- Supplier cleanup требует создания миграций — согласовать с командой
