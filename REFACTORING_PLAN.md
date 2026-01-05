# 🔧 PVNDORA Refactoring Plan

**Дата:** 2026-01-05  
**Приоритет:** Критический → Высокий → Средний → Низкий

---

## 📊 Анализ текущего состояния

### Статистика кодовой базы

| Метрика | Значение | Проблема |
|---------|----------|----------|
| Python файлов | ~90 | - |
| TypeScript/React | ~100 | - |
| **Крупнейшие монолиты** | 5 файлов >1000 строк | 🔴 |
| Unused imports | 14+ файлов | 🟡 |
| TODO/FIXME | 8 мест | 🟡 |
| Устаревшая документация | 6+ файлов | 🟡 |

### 🔴 Критические монолиты (>800 строк)

| Файл | Строк | Проблема |
|------|-------|----------|
| `core/agent/tools.py` | **1836** | Все AI tools в одном файле |
| `core/services/payments.py` | **1589** | 4 платёжных шлюза в одном файле |
| `core/routers/webapp/orders.py` | **1087** | Заказы + платежи + доставка |
| `core/routers/webhooks.py` | **908** | 4 webhook'а + CrystalPay |
| `core/routers/workers.py` | **840** | 5+ workers в одном файле |

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
| `ARCHITECTURE_ANALYSIS.md` | Устарел (заменить на PROJECT_MAP) |

### 1.2 Deprecated код для удаления

```python
# core/orders/serializer.py:48
# DEPRECATED: Use convert_order_prices_with_formatter instead

# core/services/notifications.py:39
# DEPRECATED: Use workers._deliver_items_for_order instead

# core/services/models.py:105-109
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

### 2.4 `core/routers/workers.py` (840 строк) → 5 файлов

**Целевая структура:**
```
core/routers/workers/
├── __init__.py          # Re-exports router
├── router.py            # Main router + common helpers
├── delivery.py          # deliver-goods, deliver-batch
├── notifications.py     # notify-*, alerts
├── referral.py          # referral bonus workers
└── misc.py              # other workers
```

### 2.5 `core/routers/webapp/orders.py` (1087 строк) → 3 файла

**Целевая структура:**
```
core/routers/webapp/orders/
├── __init__.py          # Re-exports router
├── router.py            # Main router
├── crud.py              # Get orders, order details
└── payments.py          # Payment creation, processing
```

---

## 🧹 Часть 3: Консолидация

### 3.1 Объединить дублирующуюся логику

| Дублирование | Файлы | Решение |
|--------------|-------|---------|
| `get_database()` | `core/services/database.py`, `core/routers/deps.py` | Один источник |
| Currency conversion | 5+ мест | Единый сервис |
| Telegram message sending | `notifications.py`, `offers.py`, workers | Общий helper |

### 3.2 Удалить `core/services/database.py` facade

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
| N+1 queries в каталоге | `domains/catalog.py` | Batch loading |
| Multiple queries в корзине | `cart/service.py` | Single JOIN query |

### 4.3 Размер бандла Frontend

| Проблема | Решение |
|----------|---------|
| `NewApp.tsx` (495 строк) | Split into route components |
| `AudioEngine.ts` (493 строк) | Lazy load |

---

## 📅 План выполнения

### Phase 1: Cleanup (1-2 дня) ✅
- [ ] Удалить устаревшую документацию
- [ ] Удалить deprecated код
- [ ] Очистить unused imports
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

### Phase 4: Split Webhooks & Workers (2 дня)
- [ ] Создать `core/routers/webhooks/`
- [ ] Создать `core/routers/workers/`
- [ ] Тесты
- [ ] Commit: `refactor: split webhooks and workers`

### Phase 5: Database Facade Cleanup (1-2 дня)
- [ ] Заменить facade calls на domain calls
- [ ] Удалить устаревшие методы
- [ ] Commit: `refactor: remove database facade wrapper methods`

### Phase 6: Frontend Optimization (2 дня)
- [ ] Split `NewApp.tsx`
- [ ] Lazy load heavy components
- [ ] Commit: `refactor: optimize frontend bundle`

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
| Макс. размер файла | 1836 строк | <400 строк |
| Unused imports | 14+ файлов | 0 |
| Устаревшая документация | 10+ файлов | 0 |
| Cold start time | ~3s | ~2s |
| Maintainability | Средняя | Высокая |

---

## ⚠️ Риски

1. **Breaking changes** — минимизировать через re-exports
2. **Circular imports** — тестировать после каждого изменения
3. **Vercel function limit** — не создавать новые entry points

---

## 📝 Примечания

- Каждый refactoring должен быть отдельным PR
- Не смешивать refactoring с новой функциональностью
- Документировать все breaking changes в CHANGELOG
