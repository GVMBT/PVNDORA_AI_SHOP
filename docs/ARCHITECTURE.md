# Project Rules & Architecture Standards

## Tech Stack & Constraints

- **Runtime:** Vercel Serverless (Python 3.12)
- **Framework:** FastAPI (as the ASGI wrapper) + Aiogram 3.22+ (Webhook mode)
- **Database:** Supabase (PostgreSQL) + vecs (pgvector client)
- **AI:** google-genai SDK (Gemini 2.5 Flash)
- **Architecture:** Monolithic entry point (`api/index.py`) to respect Vercel's 12-function limit

## Critical Implementation Rules

### 1. Гибридная Асинхронная Архитектура

**NEVER use `bot.polling()`**

All Telegram updates must be handled via a FastAPI route `/api/webhook`.

The route MUST return `{"ok": True}` immediately.

**Two-tier processing:**

1. **Best-Effort (UX/Dialogs):** Use `fastapi.BackgroundTasks` for AI responses and non-critical operations
2. **Guaranteed Delivery (Transactions):** Use **Upstash QStash** for all critical operations (payments, delivery, bonuses)

**Example pattern:**
```python
@app.post("/api/webhook")
async def webhook(request: Request, bg_tasks: BackgroundTasks):
    update = Update.model_validate(await request.json(), context={"bot": bot})
    # Best-effort: AI responses
    bg_tasks.add_task(process_ai_response, bot, update)
    return {"ok": True}

# Guaranteed: Critical operations via QStash
async def process_payment(order_id: str):
    await qstash.publish_json(
        url="https://app.vercel.app/api/workers/deliver-goods",
        body={"order_id": order_id},
        retries=3
    )
```

**See details in:** `docs/async-architecture.md`

### 2. Vercel Fluid Compute

- Assume `maxDuration` is set to 300s
- Do not fear long-running AI tasks, but ALWAYS run them inside `BackgroundTasks`
- Memory: 1024MB

### 3. Гибридная Модель Управления Инвентарем

**Проблема:** Загрузка всего инвентаря в System Prompt создает риск перепродажи (Overselling).

**Решение:** Двухуровневая модель:
1. **System Prompt (Скорость):** Базовое описание ассортимента для быстрого диалога
2. **Real-time Validation (Надежность):** Обязательная валидация наличия и цены через Supabase RPC или Function Calling в момент генерации `offer_payment`

**Example:**
```python
# System Prompt содержит базовое описание
SYSTEM_PROMPT = "Available: ChatGPT Plus, Midjourney, Claude Pro..."

# При генерации offer_payment - обязательная валидация
if ai_response.action == "offer_payment":
    # Валидация через прямой запрос к View или через AI Function Calling
    validation = supabase.table('available_stock_with_discounts').select('*').eq('product_id', ai_response.product_id).limit(1).execute()
    
    if not validation.data or len(validation.data) == 0:
        # Товар закончился - предложить альтернативу
        pass
```

**See details in:** `docs/async-architecture.md`

### 4. Транзакционная Целостность

**Проактивное Резервирование:**
- Товар должен быть зарезервирован до начала оплаты
- Корзина хранится в Redis до checkout, заказы в БД создаются только при оплате
- Использовать Хранимые Процедуры PostgreSQL для атомарности

**Атомарные Транзакции:**
- Вся транзакционная логика (проверка наличия -> расчет скидки -> резервирование -> создание заказа) переносится внутрь Хранимых Процедур PostgreSQL
- Вызывается через `supabase.rpc()` в рамках единой транзакции

**Example:**
```python
result = supabase.rpc('reserve_product_for_purchase', {
    'p_product_id': product_id,
    'p_user_id': user_id
}).execute()
```

**See details in:** `docs/database-schema.md`

### 5. Платежный Поток (Middleman Pattern)

**Требование:** Использование только внешних платежных шлюзов (1Plat). Нативные платежи Telegram (Stars) не используются.

**Поток:**
1. Пользователь инициирует оплату в Mini App
2. FastAPI создает заказ и резервирует товар через RPC
3. FastAPI генерирует ссылку на внешний платежный шлюз
4. Пользователь оплачивает через внешний шлюз
5. Платежный шлюз отправляет webhook на `/api/webhook/payment/{provider}`
6. FastAPI валидирует платеж и публикует задачу в QStash для доставки
7. QStash Worker доставляет товар пользователю

**See details in:** `docs/async-architecture.md`

### 6. Supabase Integration

**DO NOT use realtime-py listeners** (websockets die in serverless).

**DO NOT use Supabase Triggers (pg_net) for critical operations.** Все критические операции (доставка товара, уведомления поставщиков) должны обрабатываться через QStash для гарантированной доставки.

**RAG Implementation:**
- Use `vecs` library for RAG (product search)
- Create a collection `products` with dimension 768 (Gemini embeddings)
- When admin adds product: generate embedding via Gemini
- When user queries: search nearest vector via vecs
- Gemini receives found products in context and generates response

### 7. Aiogram 3.x Specifics

- Use Dependency Injection via Middleware to pass `supabase` and `genai_client` to handlers
- Use RedisStorage (via Upstash HTTP Redis) for FSM. **Do NOT use MemoryStorage**

### 7.1. Redis Usage

**Upstash Redis используется для:**

1. **FSM Storage** - Состояния диалогов Aiogram (обязательно)
2. **Cart Management** - Временные корзины пользователей до оплаты (TTL 24 часа)
3. **Leaderboards** - Геймификация через Sorted Sets
4. **Currency Cache** - Кэширование курсов валют (TTL 1 час)

**Важно:** AI не обращается напрямую к Redis или БД. Все данные получаются через Function Calling, который абстрагирует источники данных.

### 8. AI Interaction (Gemini 2.5) - Гибридная Стратегия

**Три компонента:**

1. **RAG (Discovery):** Понимание намерений пользователя
2. **Function Calling (Accuracy):** AI обязан использовать вызовы функций для получения актуальных данных
3. **Structured Outputs (Determinism):** Все действия AI обязаны использовать Structured Outputs (Pydantic Schema-Constrained Decoding)

**Requirements:**
- Use `google.genai.Client` (v1.0+)
- Enable Grounding with Google Search only for generic queries ("What is Midjourney?")
- For product queries: RAG + Function Calling + Structured Outputs
- Use `tenacity` library for retry logic on validation errors

**See details in:** `docs/ai-strategy.md`

### 6. Web App Integration

- Web App routes (`/api/webapp/...`) must live in the same FastAPI app instance as the bot webhook

## Async Processing: QStash для Критических Операций

### Fulfillment Flow (Обновлено)

1. User pays in WebApp → Payment provider sends webhook to `/api/webhook/payment/{provider}`
2. FastAPI receives webhook, verifies signature
3. FastAPI writes to DB: `orders.status = 'paid'` и вызывает `complete_purchase()` RPC
4. **QStash:** FastAPI публикует задачу в QStash для доставки товара
5. **QStash Worker:** `/api/workers/deliver-goods` получает задачу и доставляет товар пользователю
6. **QStash Worker:** `/api/workers/update-leaderboard` обновляет лидерборд геймификации

**Benefits:**
- Гарантированная доставка через QStash (retries, timeouts)
- Атомарность через PostgreSQL RPC
- Если worker упал, QStash автоматически повторит доставку

## Performance Optimizations

### Dynamic Discounts

**DO NOT calculate in Python bot code** (unnecessary requests).

Create a **SQL View** in Supabase: `available_stock_with_discounts`.

Let SQL calculate discount on the fly:
```sql
CASE 
  WHEN NOW() - created_at > interval '30 days' THEN price * 0.9
  WHEN NOW() - created_at > interval '60 days' THEN price * 0.8
  ...
END
```

Bot queries ready price: `SELECT * FROM available_stock_with_discounts`. This is faster and cheaper for Serverless.

### Smart Product Search (RAG)

**User query:** "Need to make presentations" → Bot suggests Canva/Gamma

**Technical implementation:**
1. When admin adds product, generate vector description (Embedding) via Gemini: *"Canva Pro: tool for presentations, slides, design"*
2. When user writes "презентации", search nearest vector via vecs
3. Gemini 2.5 Flash receives found products in context and only then forms response
4. This is RAG (Retrieval Augmented Generation)

## Project Structure

```
/api
  ├── index.py           # Single entry point (FastAPI app)
  ├── bot.py             # Aiogram setup (Dispatcher, Middlewares)
  ├── handlers.py        # Bot logic (message responses)
  ├── webapp_routes.py   # API for Mini App (create order, check payment)
  └── services.py        # RAG logic, discount calculation, Gemini calls

/utils
  ├── db.py              # Supabase and Redis (Upstash) connections
  └── prompts.py         # System prompts for Gemini

pyproject.toml           # Dependencies (use uv for speed)
vercel.json              # Config with Fluid Compute enabled
```

## Vercel Configuration

**Critical `vercel.json` settings:**

```json
{
  "functions": {
    "api/index.py": {
      "maxDuration": 300,
      "memory": 1024
    }
  },
  "crons": [
    {
      "path": "/api/crons/check-expired-subs",
      "schedule": "0 10 * * *"
    }
  ]
}
```

## Environment Variables

**Telegram:**
- `TELEGRAM_WEBHOOK_URL` — URL for Telegram bot webhook
- `TELEGRAM_TOKEN` — Telegram bot token

**Supabase:**
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` — Supabase service role key for admin operations

**AI:**
- `GEMINI_API_KEY` — API key for Google Gemini 2.5 Flash

**Upstash:**
- `UPSTASH_REDIS_URL` — Upstash Redis URL for FSM storage
- `UPSTASH_REDIS_TOKEN` — Upstash Redis token
- `QSTASH_TOKEN` — Upstash QStash token for queues
- `QSTASH_URL` — Upstash QStash URL (usually https://qstash.upstash.io/v2)

**Примечание:** Upstash имеет официальную интеграцию с Vercel. Можно настроить через Vercel Dashboard → Settings → Integrations → Upstash, либо вручную через [console.upstash.com](https://console.upstash.com/). См. детали в `docs/QSTASH_EXPLAINED.md`.

**Payments:**
- `ONEPLAT_SHOP_ID` — 1Plat shop ID (x-shop)
- `ONEPLAT_SECRET_KEY` — 1Plat secret key (x-secret)
- `YUKASSA_SECRET_KEY` — ЮКасса secret key

## Key Principles

1. **Always return fast** - Use BackgroundTasks for heavy operations (Best-Effort)
2. **Guaranteed delivery** - Use QStash for all transactional operations
3. **Real-time validation** - Always validate inventory before critical actions
4. **Use database triggers** - For async processing, not Python polling
5. **Optimize with SQL** - Calculate discounts, aggregations in database
6. **RAG for search** - Use vector search for product discovery
7. **Structured outputs** - All AI actions must return typed objects
8. **Single entry point** - All routes in `api/index.py` to respect Vercel limits
9. **Middleman payments** - Only external payment gateways, no Telegram Stars
10. **Context caching** - Optimize AI costs with cached System Prompts

