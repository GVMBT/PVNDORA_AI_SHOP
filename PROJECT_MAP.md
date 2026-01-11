# 🗺️ PVNDORA Project Map

**Обновлено:** 2026-01-06  
**Назначение:** Быстрая навигация по проекту

---

## 📁 Структура проекта

```
pvndora/
├── 🔵 api/                     # Vercel Serverless Entry Points
├── 🟢 core/                    # Python Backend
├── 🟡 src/                     # React Frontend  
├── 🟣 docs/                    # Документация
├── 🔴 supabase/                # Миграции БД
├── 🟤 scripts/                 # Локальные скрипты
└── 🟠 locales/                 # Переводы (JSON)
```

---

## 🔵 API Layer (`api/`)

**Точки входа Vercel Serverless**

| Файл | Назначение | Вызывается |
|------|-----------|------------|
| `index.py` | FastAPI monolith | Все `/api/*` кроме cron/og/workers |
| `cron/*.py` | Cron jobs | По расписанию (vercel.json) |
| `workers/*.py` | QStash workers | QStash delayed tasks |
| `og/*.js` | OG Image Generation | Social sharing |

### Cron Jobs

| Файл | Расписание | Назначение |
|------|-----------|------------|
| `check_pending_payments.py` | `* * * * *` | Проверка оплаты CrystalPay |
| `deliver_overdue_discount.py` | `*/5 * * * *` | Fallback доставка discount |
| `expire_orders.py` | `*/5 * * * *` | Отмена просроченных заказов |
| `auto_alloc.py` | `*/5 * * * *` | Авто-аллокация PVNDORA |
| `discount_offers.py` | `0 12 * * *` | Офферы перелива |
| `reengagement.py` | `0 12 * * *` | Re-engagement PVNDORA |
| `low_stock_alert.py` | `*/30 * * * *` | Алерты о стоке |
| `update_exchange_rates.py` | `0 */6 * * *` | Курсы валют |
| `daily_cleanup.py` | `0 3 * * *` | Очистка старых данных |

---

## 🟢 Core Backend (`core/`)

### Роутеры (`core/routers/`)

**API endpoints по доменам**

| Директория/Файл | Endpoints | Назначение |
|-----------------|-----------|------------|
| `admin/` | `/api/admin/*` | Админ-панель |
| `webapp/` | `/api/webapp/*` | Mini App API |
| `webhooks.py` | `/api/webhook/*` | Платежные вебхуки |
| `workers.py` | `/api/workers/*` | QStash workers |
| `user.py` | `/api/user/*` | Wishlist, reviews |
| `deps.py` | - | DI (Dependency Injection) |

### Admin Routers (`core/routers/admin/`)

| Файл | Назначение |
|------|-----------|
| `accounting.py` | Бухгалтерия, расходы |
| `analytics.py` | Аналитика, статистика |
| `broadcast.py` | Массовые рассылки |
| `migration.py` | Миграция discount→PVNDORA |
| `orders.py` | Управление заказами |
| `products.py` | Каталог товаров |
| `promo.py` | Промокоды |
| `rag.py` | RAG поиск |
| `referral.py` | Партнёрка |
| `replacements.py` | Модерация замен |
| `tickets.py` | Тикеты поддержки |
| `users.py` | Пользователи |

### WebApp Routers (`core/routers/webapp/`)

| Файл/Модуль | Назначение |
|-------------|-----------|
| `auth.py` | Авторизация TMA |
| `cart.py` | Корзина |
| `orders/` | Заказы пользователя (CRUD + Payments) |
| `partner.py` | Партнёрка |
| `profile/` | Профиль (Profile + Balance + Withdrawals) |
| `public.py` | Публичные endpoints |
| `ai_chat.py` | AI консультант |
| `misc/` | Прочее (FAQ + Promo + Reviews + Leaderboard + Support) |

---

### Сервисы (`core/services/`)

**Бизнес-логика**

| Категория | Файлы | Назначение |
|-----------|-------|-----------|
| **Infrastructure** | `database.py`, `payments.py`, `notifications.py`, `currency.py` | Внешние интеграции |
| **Domain Services** | `domains/*.py` | Бизнес-правила |
| **Repositories** | `repositories/*.py` | Доступ к данным |
| **Models** | `models.py` | Pydantic модели |

### Domain Services (`core/services/domains/`)

| Файл | Назначение | Связанные роутеры |
|------|-----------|-------------------|
| `users.py` | Пользователи | `admin/users.py`, `webapp/profile.py` |
| `products.py` | Товары | `admin/products.py`, `webapp/public.py` |
| `orders.py` | Заказы | `admin/orders.py`, `webapp/orders.py` |
| `catalog.py` | Каталог + фильтры | `webapp/public.py` |
| `stock.py` | Сток товаров | `admin/products.py` |
| `insurance.py` | Страховка (discount) | `bot/discount/*` |
| `discount_orders.py` | Отложенная доставка | `webhooks.py`, cron |
| `offers.py` | Офферы перелива | `cron/discount_offers.py` |
| `promo.py` | Промокоды | `admin/promo.py` |
| `referral.py` | Партнёрка | `admin/referral.py`, `webapp/partner.py` |
| `support.py` | Тикеты | `admin/tickets.py` |
| `wishlist.py` | Избранное | `user.py` |
| `chat.py` | История чата | `webapp/ai_chat.py` |

---

### Bot (`core/bot/`)

**Telegram Bot handlers**

| Директория | Назначение |
|------------|-----------|
| `handlers/` | PVNDORA bot handlers |
| `discount/` | Discount bot handlers |
| `keyboards.py` | Inline клавиатуры |
| `middlewares.py` | Middleware (auth, rate limit) |
| `states.py` | FSM states |

### Discount Bot (`core/bot/discount/`)

| Файл | Назначение |
|------|-----------|
| `handlers/start.py` | /start, терминология |
| `handlers/catalog.py` | Каталог товаров |
| `handlers/purchase.py` | Покупка, оплата |
| `handlers/issues.py` | Проблемы, замены |
| `keyboards.py` | Клавиатуры discount |
| `middlewares.py` | Auth middleware |

---

### Прочие модули (`core/`)

| Модуль | Назначение |
|--------|-----------|
| `agent/` | AI Agent (Gemini + modular tools) |
| `auth/` | Авторизация (Telegram, JWT) |
| `cart/` | Корзина (Redis) |
| `i18n/` | Локализация |
| `orders/` | Order status management |
| `payments/` | Payment gateway config |
| `db.py` | Supabase + Redis clients |
| `queue.py` | QStash integration |
| `rag.py` | Vector search |
| `logging.py` | Centralized logging |

---

## 🟡 Frontend (`src/`)

### Компоненты (`src/components/`)

| Директория | Назначение |
|------------|-----------|
| `admin/` | Admin панель |
| `new/` | Основные UI компоненты |
| `profile/` | Страница профиля |
| `app/` | App layout, router |

### Hooks (`src/hooks/`)

| Файл | Назначение |
|------|-----------|
| `api/*.ts` | API hooks (useOrders, useProducts) |
| `use*.ts` | UI hooks (useTheme, useSound) |

### Adapters (`src/adapters/`)

**API → Component data transformers**

| Файл | Назначение |
|------|-----------|
| `order.ts` | Order API → UI |
| `product.ts` | Product API → UI |
| `user.ts` | User API → UI |

---

## 🔍 Что где искать

### "Хочу изменить..."

| Задача | Где смотреть |
|--------|-------------|
| Логику покупки в discount боте | `core/bot/discount/handlers/purchase.py` |
| Доставку заказов | `api/workers/deliver_discount_order.py`, `core/routers/workers.py` |
| Страховку | `core/services/domains/insurance.py`, `core/bot/discount/handlers/issues.py` |
| Офферы перелива | `core/services/domains/offers.py`, `api/cron/discount_offers.py` |
| AI консультанта | `core/agent/agent.py`, `core/agent/tools/` (модульный пакет) |
| Партнёрку | `core/services/domains/referral.py`, `src/components/profile/` |
| Корзину | `core/cart/`, `core/routers/webapp/cart.py` |
| Админку | `core/routers/admin/`, `src/components/admin/` |
| Платежи | `core/services/payments.py`, `core/routers/webhooks.py` |
| Локализацию | `locales/*.json`, `core/i18n/` |

### "Получаю ошибку в..."

| Симптом | Где смотреть |
|---------|-------------|
| Webhook не работает | `core/routers/webhooks.py`, Vercel logs |
| Заказ не доставляется | `api/workers/`, `api/cron/deliver_overdue_discount.py` |
| AI не отвечает | `core/agent/agent.py`, `core/routers/webapp/ai_chat.py` |
| Корзина пустая | `core/cart/storage.py`, Redis |
| Админка не грузит | `core/routers/admin/`, frontend network tab |

---

## 📊 Статистика проекта

| Слой | Файлов | ~Строк кода |
|------|--------|-------------|
| API (`api/`) | 14 | ~2,000 |
| Backend (`core/`) | ~95 | ~13,500 |
| Frontend (`src/`) | ~132 | ~18,000 |
| Docs (`docs/`) | 10 | ~2,000 |
| Scripts (`scripts/`) | 21 | ~2,500 |
| **Всего** | **~272** | **~38,000** |

**Последний рефакторинг:**
- Удалено ~3,700 строк (1Plat, Freekassa, Rukassa; устаревшая документация)
- `agent/tools.py` → модульный пакет `agent/tools/` (8 файлов)
- `payments.py` упрощён: 1610 → 450 строк
- `webhooks.py` упрощён: 930 → 350 строк

---

## 🔗 Связи между модулями

```
[Telegram] → [api/index.py] → [core/bot/handlers/]
                           → [core/routers/webapp/] → [core/services/domains/]
                           → [core/routers/admin/]  → [core/services/domains/]
                                                    → [core/services/repositories/]
                                                    → [core/db.py] → [Supabase]
                                                                  → [Redis]

[QStash] → [api/workers/] → [core/services/]
[Vercel Cron] → [api/cron/] → [core/services/]
[CrystalPay] → [core/routers/webhooks.py] → [core/services/payments.py]
```

---

## 🎯 Приоритеты рефакторинга

### ✅ Выполнено

1. ~~Workers routing в vercel.json~~ ✅
2. ~~Страховка фильтрация~~ ✅  
3. ~~Split agent/tools.py в модули~~ ✅
4. ~~Удалены 1Plat, Freekassa, Rukassa~~ ✅
5. ~~Очистка устаревшей документации~~ ✅

### 🟡 Средние (следующий этап)

6. Объединить `core/services/domains/` и `core/services/repositories/` в единую структуру
7. Убрать дублирование между `core/services/database.py` и repositories
8. Стандартизировать error handling

### 🟢 Низкие

9. Добавить barrel exports в frontend (`src/utils/index.ts`)
10. Унифицировать lazy imports pattern
11. Улучшить типизацию в frontend

---

## 📝 Примечания

- **Lazy imports**: Критически важны для Vercel cold start
- **Monolithic entry**: `api/index.py` — соответствует ограничениям Vercel
- **Repository Pattern**: Абстракция для возможной смены БД
- **Domain Services**: Бизнес-логика отделена от инфраструктуры
