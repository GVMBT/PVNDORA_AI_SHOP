<!-- 9fddf0cc-b67b-445c-bc9a-911fb63b0c50 bfa47967-8ec0-48ab-89bb-120f5521738c -->
# Исправление AI Tools и Mini App - Полный Аудит

## Критические проблемы

### 1. AI не знает UUID товаров (КРИТИЧНО)

**Проблема:** В `format_product_catalog` (prompts.py) каталог не содержит ID товаров.

**Следствие:** AI придумывает ID (`chatgpt_plus_shared`), что вызывает `invalid input syntax for type uuid`.

**Решение:** Добавить UUID в каталог и fallback-поиск по имени.

### 2. Mini App API - отсутствуют endpoints (КРИТИЧНО)

**Frontend ожидает:**

- `GET /api/webapp/products` - нет
- `GET /api/webapp/orders` - нет
- `GET /api/webapp/leaderboard` - нет
- `GET /api/webapp/faq` - нет
- `POST /api/webapp/promo/check` - нет
- `POST /api/webapp/reviews` - нет

**Есть только:** `GET /api/webapp/products/{product_id}`

Mini App полностью нефункционален!

### 3. Debug код в production (17 блоков)

Файлы: `src/ai/tools.py` (15), `src/bot/handlers.py` (2)

Все `#region agent log` блоки с записью в `debug.log` нужно удалить.

### 4. env.example - неправильные имена Redis

- Указано: `UPSTASH_REDIS_URL`, `UPSTASH_REDIS_TOKEN`
- Должно: `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`

---

## План исправлений

### Фаза 1: AI Tools (критично для бота)

**1.1 Добавить UUID в каталог товаров**

Файл: [src/ai/prompts.py](src/ai/prompts.py)

```python
# Было:
f"- {p.name}: {p.price}₽ | {p.type} | {stock_status}"

# Станет:
f"- **{p.name}** (ID: {p.id}): {p.price}₽ | {p.type} | {stock_status}"
```

**1.2 Fallback поиск по имени в tools.py**

Файл: [src/ai/tools.py](src/ai/tools.py)

Для `create_purchase_intent`, `add_to_cart`, `add_to_wishlist`:

- Проверить является ли `product_id` валидным UUID
- Если нет - искать товар по имени через `db.search_products()`

**1.3 Удалить debug код**

Удалить все 17 блоков `#region agent log` из:

- `src/ai/tools.py`
- `src/bot/handlers.py`

### Фаза 2: Mini App API endpoints

**Файл:** [api/index.py](api/index.py)

Добавить недостающие endpoints:

| Endpoint | Описание |

|----------|----------|

| `GET /api/webapp/products` | Список товаров с auth |

| `GET /api/webapp/orders` | Заказы пользователя |

| `GET /api/webapp/leaderboard` | Лидерборд savings |

| `GET /api/webapp/faq` | FAQ по языку |

| `POST /api/webapp/promo/check` | Проверка промокода |

| `POST /api/webapp/reviews` | Отправка отзыва |

### Фаза 3: Исправления конфигурации

**3.1 env.example**

Исправить названия Redis переменных:

```
UPSTASH_REDIS_REST_URL=https://xxx.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_redis_token
```

---

## Проверка переменных Vercel (уже настроены)

| Переменная | Статус |

|------------|--------|

| `SUPABASE_DB_URL` | ✅ Добавлена |

| `UPSTASH_REDIS_REST_URL` | ✅ Есть |

| `UPSTASH_REDIS_REST_TOKEN` | ✅ Есть |

| `QSTASH_TOKEN` | ✅ Есть |

| `QSTASH_CURRENT_SIGNING_KEY` | ✅ Есть |

| `QSTASH_NEXT_SIGNING_KEY` | ✅ Есть |

---

## Приоритет исправлений

1. **UUID в каталог + fallback** - решит ошибку `chatgpt_plus_shared`
2. **Удаление debug кода** - безопасность и чистота
3. **Mini App endpoints** - функциональность приложения
4. **env.example** - документация

### To-dos

- [ ] Phase 1: Create core/db.py, core/queue.py, core/cart.py modules
- [ ] Phase 2: Implement core/ai.py with Gemini Structured Outputs, Function Calling, RAG
- [ ] Phase 2: Create core/models.py with all Pydantic schemas
- [ ] Phase 3: Implement aiogram handlers (messages, callbacks, inline queries)
- [ ] Phase 4: Complete api/index.py with all endpoints (webhook, webapp, admin)
- [ ] Phase 5: Add QStash worker endpoints (delivery, notifications, processing)
- [ ] Phase 6: Implement cron jobs (lifecycle, re-engagement, reviews, wishlist)
- [ ] Phase 7: Create SQL migrations (reviews, promo_codes, faq, views, indexes)
- [ ] Добавить UUID товаров в format_product_catalog (prompts.py)
- [ ] Добавить fallback поиск по имени в create_purchase_intent (tools.py)
- [ ] Исправить названия Redis переменных в env.example
- [ ] Добавить валидацию UUID и поиск по имени в tools.py
- [ ] Проверить и задокументировать все env vars для Vercel