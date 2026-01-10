# 🔨 PVNDORA Refactoring Plan - Agent 2: Monolith Splitting

**Агент:** Agent 2 (Monolith Splitting)  
**Дата:** 2026-01-27  
**Приоритет:** 🔴 Критический → 🟡 Высокий  
**Оценка:** 7-10 дней

**⚠️ ВАЖНО:** Этот документ для параллельной работы с Agent 1 и Agent 3. Начни ПОСЛЕ завершения Phase 0 Agent 1 (нужен `telegram_messaging.py`).

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
- ✅ `payments.py` упрощён (1589 → 544 строки)
- ✅ `webhooks.py` упрощён (908 → 469 строк)

**Критические монолиты (актуальные размеры 2026-01-27):**

| Файл | Строк | Проблема | Агент |
|------|-------|----------|-------|
| `core/services/notifications.py` | **1281** | Все уведомления + 20+ прямых вызовов bot.send_message | Agent 2 |
| `core/routers/workers.py` | **1271** | 5+ workers в одном файле | Agent 2 |
| `core/routers/webapp/profile.py` | **1145** | Профиль + баланс + валюта + ручная конвертация | Agent 2 |
| `core/routers/webapp/orders.py` | **1110** | Заказы + платежи + доставка | Agent 2 |

**⚠️ Примечание:** `core/routers/webapp/profile.py` содержит ручную конвертацию валют, но Agent 1 исправит это в Phase 0. После этого Agent 2 может разбивать файл.

---

## 🎯 Задачи Agent 2

### Phase 2: Split Notifications & Workers (КРИТИЧНО, 3-4 дня) 🔴

**⚠️ ЗАВИСИМОСТЬ:** Начать ПОСЛЕ завершения Phase 0 Agent 1 (нужен `telegram_messaging.py`).

#### 2.1 Разбить `core/services/notifications.py` (1281 строка)

**Текущая структура:**
- Все типы уведомлений в одном файле
- 20+ прямых вызовов `bot.send_message()` (но Agent 1 заменит на `telegram_messaging.py`)
- Методы для delivery, orders, support, referral, payments, withdrawals, misc

**Целевая структура:**
```
core/services/notifications/
├── __init__.py          # Re-exports NotificationService
├── base.py              # NotificationService class + telegram_messaging integration
├── delivery.py          # send_delivery, send_credentials
├── orders.py            # send_review_request, send_expiration_reminder
├── support.py           # send_ticket_approved, send_ticket_rejected
├── referral.py          # send_referral_unlock, send_referral_level_up, send_referral_bonus
├── payments.py          # send_cashback, send_refund, send_topup_success
├── withdrawals.py       # send_withdrawal_approved, send_withdrawal_rejected, send_withdrawal_completed
└── misc.py              # send_broadcast, send_waitlist_notification, etc.
```

**Принцип разделения:**
- `base.py` — базовый класс `NotificationService` + интеграция с `telegram_messaging.py`
- Каждый модуль — группа связанных уведомлений
- Все модули импортируются в `__init__.py` для backward compatibility

**Checklist:**
- [ ] Создать директорию `core/services/notifications/`
- [ ] Создать `base.py` с классом `NotificationService` (базовые методы, инициализация)
- [ ] Интегрировать `telegram_messaging.py` в `base.py` (Agent 1 создаст)
- [ ] Вынести методы в модули:
  - [ ] `delivery.py` — методы отправки delivery/credentials
  - [ ] `orders.py` — методы для заказов (review, expiration)
  - [ ] `support.py` — методы для support/tickets
  - [ ] `referral.py` — методы для referral системы
  - [ ] `payments.py` — методы для платежей (cashback, refund, topup)
  - [ ] `withdrawals.py` — методы для withdrawals
  - [ ] `misc.py` — методы для broadcast, waitlist, etc.
- [ ] Создать `__init__.py` с re-exports для backward compatibility
- [ ] Обновить все импорты в проекте (найти через `grep -r "from core.services.notifications import"`)
- [ ] Убедиться, что `NotificationService` работает как единый класс
- [ ] Тесты (проверить все типы уведомлений)
- [ ] Commit: `refactor: split notifications service into modules`

**Файлы для изменения:**
- `core/services/notifications.py` → `core/services/notifications/` (разбить)
- Все файлы, импортирующие `NotificationService` (обновить импорты)

#### 2.2 Разбить `core/routers/workers.py` (1271 строка)

**Текущая структура:**
- 5+ worker endpoints в одном файле
- `_deliver_items_for_order` — общая функция для доставки
- Workers: deliver-goods, deliver-batch, calculate-referral, process-replacement, process-refund, process-review-cashback, send-broadcast, notify-supplier (DEPRECATED, Agent 1 удалит)

**Целевая структура:**
```
core/routers/workers/
├── __init__.py          # Re-exports router
├── router.py            # Main router + route definitions + _deliver_items_for_order helper
├── delivery.py          # deliver-goods, deliver-batch workers
├── referral.py          # calculate-referral, process-replacement workers
├── payments.py          # process-refund, process-review-cashback workers
└── broadcast.py         # send-broadcast worker
```

**Принцип разделения:**
- `router.py` — основной router + общая функция `_deliver_items_for_order`
- Каждый модуль — группа связанных workers
- Все модули регистрируются в `router.py`

**Checklist:**
- [ ] Создать директорию `core/routers/workers/`
- [ ] Создать `router.py` с основным router и функцией `_deliver_items_for_order`
- [ ] Вынести workers в модули:
  - [ ] `delivery.py` — `worker_deliver_goods`, `worker_deliver_batch`
  - [ ] `referral.py` — `worker_calculate_referral`, `worker_process_replacement`
  - [ ] `payments.py` — `worker_process_refund`, `worker_process_review_cashback`
  - [ ] `broadcast.py` — `worker_send_broadcast`
- [ ] Удалить `worker_notify_supplier` (Agent 1 удалит в Phase 1)
- [ ] Создать `__init__.py` с re-exports router
- [ ] Обновить импорты в `api/index.py` (если нужно)
- [ ] Тесты (проверить все worker endpoints)
- [ ] Commit: `refactor: split workers router into modules`

**Файлы для изменения:**
- `core/routers/workers.py` → `core/routers/workers/` (разбить)
- `api/index.py` (обновить импорт router, если нужно)

---

### Phase 3: Split Profile Router (2-3 дня) 🟡

**⚠️ ЗАВИСИМОСТЬ:** Начать ПОСЛЕ завершения Phase 0 Agent 1 (убрана ручная конвертация валют).

#### 3.1 Разбить `core/routers/webapp/profile.py` (1145 строк)

**Текущая структура:**
- Профиль + баланс + валюта + withdrawals
- 21+ мест с `asyncio.to_thread()` (Agent 3 исправит в Phase 7)
- Ручная конвертация валют (Agent 1 исправит в Phase 0)

**Целевая структура:**
```
core/routers/webapp/profile/
├── __init__.py          # Re-exports router
├── router.py            # Main router + route definitions
├── profile.py           # get_profile, update_preferences, get_referral_info
├── balance.py           # get_balance_history, topup_balance, convert_balance
└── withdrawals.py       # calculate_withdrawal, request_withdrawal, get_withdrawal_history
```

**Принцип разделения:**
- `router.py` — основной router с маршрутами
- Каждый модуль — группа связанных endpoints
- Все модули регистрируются в `router.py`

**Checklist:**
- [ ] Создать директорию `core/routers/webapp/profile/`
- [ ] Создать `router.py` с основным router и маршрутами
- [ ] Вынести endpoints в модули:
  - [ ] `profile.py` — `get_profile`, `update_preferences`, `get_referral_info`, `get_partner_dashboard`
  - [ ] `balance.py` — `get_balance_history`, `topup_balance`, `convert_balance`
  - [ ] `withdrawals.py` — `calculate_withdrawal`, `request_withdrawal`, `get_withdrawal_history`
- [ ] Убедиться, что `CurrencyService.convert_balance()` используется (Agent 1 создаст)
- [ ] Сохранить `asyncio.to_thread()` пока (Agent 3 исправит в Phase 7)
- [ ] Создать `__init__.py` с re-exports router
- [ ] Обновить импорты в `api/index.py` (если нужно)
- [ ] Тесты (проверить все endpoints)
- [ ] Commit: `refactor: split profile router into modules`

**Файлы для изменения:**
- `core/routers/webapp/profile.py` → `core/routers/webapp/profile/` (разбить)
- `api/index.py` (обновить импорт router, если нужно)

---

### Phase 4: Split Orders Router (2 дня) 🟡

#### 4.1 Разбить `core/routers/webapp/orders.py` (1110 строк)

**Текущая структура:**
- Заказы + платежи + доставка
- CRUD операции для orders
- Payment creation logic
- Delivery verification

**Целевая структура:**
```
core/routers/webapp/orders/
├── __init__.py          # Re-exports router
├── router.py            # Main router + route definitions
├── crud.py              # get_webapp_orders, verify_and_deliver_order
└── payments.py          # create_webapp_order, payment creation logic
```

**Принцип разделения:**
- `router.py` — основной router с маршрутами
- `crud.py` — операции чтения/обновления orders
- `payments.py` — создание заказов и платежей

**Важно:** В `get_webapp_orders()` используется `o.product_id` (DEPRECATED). Agent 1 исправит это в Phase 1.

**Checklist:**
- [ ] Создать директорию `core/routers/webapp/orders/`
- [ ] Создать `router.py` с основным router и маршрутами
- [ ] Вынести endpoints в модули:
  - [ ] `crud.py` — `get_webapp_orders`, `verify_and_deliver_order`
  - [ ] `payments.py` — `create_webapp_order`, `_create_cart_order`, payment creation logic
- [ ] Убедиться, что `o.product_id` не используется (Agent 1 исправит в Phase 1)
- [ ] Создать `__init__.py` с re-exports router
- [ ] Обновить импорты в `api/index.py` (если нужно)
- [ ] Тесты (проверить все endpoints)
- [ ] Commit: `refactor: split orders router into modules`

**Файлы для изменения:**
- `core/routers/webapp/orders.py` → `core/routers/webapp/orders/` (разбить)
- `api/index.py` (обновить импорт router, если нужно)

---

## 📋 Checklist перед началом работы

- [ ] Прочитан контекст проекта (технологии, архитектура)
- [ ] Понимаю зависимости от Agent 1 (Phase 0 должен быть завершён)
- [ ] Знаю, какие файлы разбиваю (4 монолита)
- [ ] Понимаю принцип backward compatibility (re-exports в `__init__.py`)
- [ ] Готов работать параллельно с Agent 1 (Phase 1) и Agent 3

---

## ✅ Критерии готовности

**Phase 2 считается выполненной, когда:**
- ✅ `notifications.py` разбит на 8 модулей (max 300 строк)
- ✅ `workers.py` разбит на 5 модулей (max 400 строк)
- ✅ Все импорты обновлены
- ✅ Все тесты проходят
- ✅ Backward compatibility сохранена (re-exports)
- ✅ Commit сделан

**Phase 3 считается выполненной, когда:**
- ✅ `profile.py` разбит на 4 модуля (max 400 строк)
- ✅ Все импорты обновлены
- ✅ `CurrencyService.convert_balance()` используется (Agent 1 создаст)
- ✅ Все тесты проходят
- ✅ Backward compatibility сохранена
- ✅ Commit сделан

**Phase 4 считается выполненной, когда:**
- ✅ `orders.py` разбит на 3 модуля (max 400 строк)
- ✅ Все импорты обновлены
- ✅ DEPRECATED поля Order не используются (Agent 1 исправит)
- ✅ Все тесты проходят
- ✅ Backward compatibility сохранена
- ✅ Commit сделан

---

## 🔄 Координация с другими агентами

**Зависимости от Agent 1:**
- ⚠️ **КРИТИЧНО:** Phase 2 можно начать ТОЛЬКО после завершения Phase 0 Agent 1 (нужен `telegram_messaging.py`)
- Phase 3 можно начать после завершения Phase 0 Agent 1 (нужен `CurrencyService.convert_balance()`)
- Phase 4 не зависит от Agent 1 напрямую, но Agent 1 исправит чтение DEPRECATED полей

**Не пересекается с Agent 3:**
- Agent 3 работает с БД оптимизацией и async паттернами
- Agent 2 только разбивает файлы, не меняет логику запросов
- Agent 3 может работать параллельно с Agent 2

**Последовательность работы:**
1. Дождаться завершения Phase 0 Agent 1 (2-3 дня)
2. Agent 2 начинает Phase 2 (3-4 дня)
3. Agent 2 выполняет Phase 3 параллельно с Agent 1 Phase 1 и Agent 3 Phase 7 (2-3 дня)
4. Agent 2 выполняет Phase 4 (2 дня)

---

## 📝 Примечания

- Каждый phase должен быть отдельным PR
- Сохранять backward compatibility через re-exports в `__init__.py`
- Не менять логику запросов (это задача Agent 3)
- Все изменения должны быть протестированы
- Максимальный размер файла после разбиения: 400-500 строк (целевой: 200-300)

---

## 🎯 Целевые метрики

| Файл | Было | Стало | Улучшение |
|------|------|-------|-----------|
| `notifications.py` | 1281 строка | 8 модулей (max 300) | ✅ 75% |
| `workers.py` | 1271 строка | 5 модулей (max 400) | ✅ 69% |
| `profile.py` | 1145 строк | 4 модуля (max 400) | ✅ 65% |
| `orders.py` | 1110 строк | 3 модуля (max 400) | ✅ 64% |

**Итоговый результат:** Все монолиты разбиты на управляемые модули, максимальный размер файла < 500 строк.
