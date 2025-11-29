# Архитектура Асинхронных Процессов

## Обоснование Гибридной Асинхронной Архитектуры

В среде Vercel Serverless использование только `FastAPI.BackgroundTasks` ненадежно для критически важных транзакций. Мы внедряем гибридную модель, которая разделяет обработку по уровням критичности.

## Гибридная Модель Управления Инвентарем

**Проблема:** Загрузка всего инвентаря в System Prompt для скорости создает риск перепродажи (Overselling), так как AI не знает актуальное наличие и динамическую цену.

**Решение:** Гибридная модель с двумя уровнями:

1. **System Prompt (Скорость):** Базовое описание ассортимента для быстрого диалога
2. **Real-time Validation (Надежность):** Обязательная валидация наличия и цены через прямой запрос к БД (Supabase RPC) или AI Function Calling в момент генерации действия `offer_payment`

**Реализация:**

```python
# System Prompt содержит базовое описание
SYSTEM_PROMPT = """
Available products:
- ChatGPT Plus: AI assistant with file support
- Midjourney: Image generation
- Claude Pro: Best for coding
...
"""

# При генерации offer_payment - обязательная валидация
async def validate_before_payment(product_id: str) -> dict:
    """Валидация наличия и цены в реальном времени"""
    # Валидация через прямой запрос к View available_stock_with_discounts
    result = supabase.table('available_stock_with_discounts').select('*').eq('product_id', product_id).limit(1).execute()
    
    if not result.data or len(result.data) == 0:
        raise ValueError("Product not available")
    
    return result.data[0]  # Возвращает актуальную цену со скидкой
```

## Два Уровня Обработки

### 1. Best-Effort: FastAPI.BackgroundTasks + Vercel Fluid Compute

**Использование:**
- UX и диалоги (ответы AI-консультанта)
- Логирование аналитики
- Некритичные операции

**Характеристики:**
- Быстрый отклик бота
- Нет гарантии доставки
- Подходит для операций, где потеря данных допустима

**Конфигурация Vercel Fluid Compute:**
```json
{
  "functions": {
    "api/index.py": {
      "maxDuration": 300,
      "memory": 1024
    }
  }
}
```

**Пример использования:**
```python
@app.post("/api/webhook")
async def webhook(request: Request, bg_tasks: BackgroundTasks):
    update = Update.model_validate(await request.json(), context={"bot": bot})
    bg_tasks.add_task(process_ai_response, bot, update)
    return {"ok": True}
```

### 2. Guaranteed Delivery: Upstash QStash

**Использование:**
- Платежи и выдача товара
- Начисление реферальных бонусов
- Уведомление поставщиков
- Обновление лидербордов (геймификация)
- Любые операции, требующие гарантии выполнения

## Middleman Payment Flow

**Требование:** Использование только внешних платежных шлюзов (AAIO, ЮКасса и др.). Нативные платежи Telegram (Stars) не используются.

**Поток:**
1. Пользователь инициирует оплату в Mini App
2. FastAPI создает заказ и резервирует товар через RPC
3. FastAPI генерирует ссылку на внешний платежный шлюз
4. Пользователь оплачивает через внешний шлюз
5. Платежный шлюз отправляет webhook на `/api/webhook/payment/{provider}`
6. FastAPI валидирует платеж и публикует задачу в QStash для доставки
7. QStash Worker доставляет товар пользователю

**Характеристики:**
- Гарантированная доставка
- Автоматические повторы при ошибках
- Настраиваемые таймауты
- Защита от дублирования

## Настройка QStash

### Конфигурация Очередей

```python
from upstash_qstash import QStash

qstash = QStash(
    token=os.getenv("QSTASH_TOKEN"),
    url=os.getenv("QSTASH_URL")
)
```

### Настройка Retries и Timeouts

```python
await qstash.publish_json(
    url="https://your-app.vercel.app/api/workers/deliver-goods",
    body={
        "order_id": order_id,
        "user_id": user_id,
        "stock_item_id": stock_item_id
    },
    retries=3,  # Количество повторов
    timeout=30,  # Таймаут в секундах
    delay=5  # Задержка между повторами
)
```

### Защита Эндпоинтов Worker

Все эндпоинты, обрабатываемые QStash, должны проверять подпись запроса:

```python
from upstash_qstash import verify_signature

@app.post("/api/workers/deliver-goods")
async def deliver_goods(request: Request):
    # Проверка подписи QStash
    try:
        verify_signature(request)
    except Exception as e:
        return {"error": "Invalid signature"}, 401
    
    # Обработка доставки товара
    data = await request.json()
    # ... логика доставки
```

## Сценарии Использования

### Сценарий 1: Обработка Платежа

1. Платежная система отправляет webhook на `/api/payment-callback`
2. FastAPI проверяет подпись и записывает `orders.status = 'paid'` в БД
3. FastAPI публикует задачу в QStash для доставки товара
4. QStash гарантированно доставляет задачу на `/api/workers/deliver-goods`
5. Worker обрабатывает доставку с автоматическими повторами при ошибках

### Сценарий 2: AI-Консультация

1. Пользователь отправляет сообщение
2. FastAPI возвращает `{"ok": True}` немедленно
3. `BackgroundTasks` обрабатывает запрос AI асинхронно
4. AI генерирует ответ и отправляет пользователю
5. Если AI не успел ответить (таймаут), пользователь может повторить запрос

## Мониторинг и Логирование

Все операции QStash должны логироваться:

```python
import logging

logger = logging.getLogger(__name__)

async def deliver_goods_worker(data: dict):
    try:
        # Логика доставки
        logger.info(f"Delivering goods for order {data['order_id']}")
        # ...
    except Exception as e:
        logger.error(f"Error delivering goods: {e}")
        raise  # QStash повторит автоматически
```

## Переменные Окружения

```env
QSTASH_TOKEN=your_qstash_token
QSTASH_URL=https://qstash.upstash.io/v2
```

