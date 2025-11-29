# Стратегия AI и Спецификация Моделей

## Архитектура AI-Ядра

AI-система использует гибридную стратегию для обеспечения точности, детерминизма и надежности коммерческих операций.

**Ключевые принципы:**
- **Детерминизм:** Обязательное использование Structured Outputs
- **Оптимизация:** Context Caching для снижения стоимости и задержки
- **Персонализация:** "Vibe Coding" для эмоционально окрашенных ответов

## Три Компонента AI Стратегии

### 1. RAG (Retrieval Augmented Generation) - Discovery

**Назначение:** Понимание намерений пользователя и поиск релевантных товаров.

**Реализация:**
- Использование библиотеки `vecs` для векторного поиска
- Collection `products` с dimension 768 (Gemini embeddings)
- При добавлении товара: генерация embedding через Gemini
- При запросе пользователя: поиск ближайших векторов

**Паттерн:**
- Генерация embedding через `genai.models.embed_content()` при добавлении товара
- Поиск через `vecs.create_client()` и `collection.query()` с фильтрами
- Использование dimension 768 (Gemini embeddings)

### 2. Function Calling - Accuracy

**Назначение:** Получение актуальных данных о наличии и динамических скидках в реальном времени.

**Обязательное требование:** AI обязан использовать вызовы функций для всех коммерческих операций.

**Доступные функции для AI:**

1. **`check_product_availability(product_id: str)`** - Проверить наличие, цену со скидкой, возможность изготовления под заказ
2. **`get_user_cart()`** - Получить корзину пользователя из Redis
3. **`add_to_cart(product_id: str, quantity: int)`** - Добавить товар в корзину (автоматически разделяет на instant + prepaid)
4. **`update_cart(operation: str, product_id?: str, quantity?: int)`** - Изменить корзину (update_quantity, remove_item, clear)

**Примечание:** `reserve_product` и `create_purchase_intent` удалены. Резервирование и создание заказа выполняются бэкендом на основе
# структурированного ответа AI (action: "offer_payment") при checkout.
# Это обеспечивает атомарность транзакций через PostgreSQL RPC.
# 
# Корзина хранится в Redis до оплаты, заказы в БД создаются только при checkout.
```

**Реализация функций backend:**

Все функции абстрагируют источники данных:
- `check_product_availability` - проверяет Supabase (БД) для наличия
- `get_user_cart` - читает из Redis
- `add_to_cart` - проверяет БД для наличия, автоматически разделяет на instant + prepaid, сохраняет в Redis
- `update_cart` - обновляет Redis корзину

AI не знает о различиях между БД и Redis - все абстрагировано через функции.
<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>
grep

### 3. Structured Outputs - Determinism

**Назначение:** Гарантировать структурированный, типизированный ответ от AI.

**Требование:** Все действия AI обязаны использовать Structured Outputs через Pydantic Schema-Constrained Decoding.

**Pydantic Модели:**

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class IntentType(str, Enum):
    DISCOVERY = "discovery"
    PURCHASE = "purchase"
    SUPPORT = "support"
    COMPARISON = "comparison"
    FAQ = "faq"

class PurchaseIntent(BaseModel):
    """Намерение пользователя на покупку"""
    intent_type: IntentType = Field(description="Тип намерения")
    product_id: Optional[str] = Field(None, description="UUID товара, если определен")
    product_name: Optional[str] = Field(None, description="Название товара")
    confidence: float = Field(ge=0.0, le=1.0, description="Уверенность в намерении")
    user_message: str = Field(description="Исходное сообщение пользователя")
    suggested_products: List[str] = Field(default_factory=list, description="Список UUID предложенных товаров")

class CartItem(BaseModel):
    """Элемент корзины"""
    product_id: str = Field(description="UUID товара")
    quantity: int = Field(description="Общее количество")
    instant_quantity: int = Field(description="Количество в наличии (instant)")
    prepaid_quantity: int = Field(description="Количество под заказ (prepaid)")
    price: float = Field(description="Цена за единицу")

class AIResponse(BaseModel):
    """Структурированный ответ AI (финальный формат)"""
    thought: str = Field(description="Внутренние размышления AI (для логирования)")
    reply_text: str = Field(description="Текст ответа для пользователя")
    action: Optional[str] = Field(None, description="Действие: 'offer_payment', 'add_to_cart', 'update_cart', 'add_to_waitlist', 'show_catalog', None")
    product_id: Optional[str] = Field(None, description="UUID товара, если действие связано с товаром")
    cart_items: Optional[List[CartItem]] = Field(None, description="Список товаров в корзине (для множественных покупок)")
    total_amount: Optional[float] = Field(None, description="Общая сумма корзины")
    requires_validation: bool = Field(False, description="Требуется ли валидация наличия перед действием")
```

**Использование в Gemini:**

```python
from google.genai import Client
from tenacity import retry, stop_after_attempt, wait_exponential

genai = Client(api_key=GEMINI_API_KEY)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def get_ai_response(
    user_message: str,
    context: str,
    response_schema: type[BaseModel]
) -> BaseModel:
    """Получить структурированный ответ от AI с retry логикой"""
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": response_schema
        }
    )
    
    prompt = f"""
    {context}
    
    User message: {user_message}
    
    Respond according to the schema.
    """
    
    try:
        response = await model.generate_content_async(prompt)
        return response_schema.model_validate_json(response.text)
    except ValidationError as e:
        # Retry при ошибках валидации
        raise
```

## System Prompts и Локализация

### Базовая Структура System Prompt

**Ключевые элементы:**
- Роль: AI Sales Consultant для AI сервисов и подписок
- Правила: ALWAYS use function calling, ALWAYS return structured responses, NEVER recommend without checking availability
- Каталог товаров: Инжектируется из базы данных
- Язык: Динамически определяется из `user_language` (9 языков)

{additional_context}
"""
```

### Локализация Промптов

Все системные промпты должны быть локализованы для 9 языков:

```python
LOCALIZED_PROMPTS = {
    "ru": SYSTEM_PROMPT_TEMPLATE.format(
        language="русском",
        additional_context="Используй неформальный стиль общения."
    ),
    "en": SYSTEM_PROMPT_TEMPLATE.format(
        language="English",
        additional_context="Use a friendly, conversational tone."
    ),
    # ... для всех 9 языков
}
```

## RAG Пайплайн

### 1. Индексация Товаров

```python
async def index_product(product: dict):
    """Индексировать товар в векторной БД"""
    # Генерация embedding
    embedding = await generate_embedding(
        f"{product['name']}: {product['description']} {product['instructions']}"
    )
    
    # Сохранение в vecs
    products_collection.upsert(
        vectors=[(product['id'], embedding, {"product_id": product['id']})]
    )
```

### 2. Поиск Релевантных Товаров

```python
async def search_products(query: str, limit: int = 5) -> List[dict]:
    """Поиск товаров по запросу пользователя"""
    # Генерация embedding запроса
    query_embedding = await generate_embedding(query)
    
    # Поиск в vecs
    results = products_collection.query(
        data=query_embedding,
        limit=limit,
        filters={"status": "active"}
    )
    
    # Получение полной информации о товарах из Supabase
    product_ids = [r.id for r in results]
    products = supabase.table("products").select("*").in_("id", product_ids).execute()
    
    return products.data
```

## Полный Процесс AI-Консультации

1. **Получение запроса пользователя**
2. **RAG поиск:** Поиск релевантных товаров через vecs
3. **Формирование контекста:** Добавление найденных товаров в System Prompt
4. **Function Calling:** AI вызывает функции для работы с данными:
   - `check_product_availability` - проверка наличия в БД (Supabase)
   - `get_user_cart` - получение корзины из Redis
   - `add_to_cart` - добавление в корзину (проверяет БД, автоматически разделяет на instant + prepaid, сохраняет в Redis)
   - `update_cart` - изменение корзины в Redis
5. **Structured Output:** AI возвращает типизированный ответ с действиями

**Важно:** AI не знает о различиях между БД и Redis. Все абстрагировано через Function Calling. Backend сам решает, откуда брать данные.
5. **Structured Output:** AI возвращает типизированный ответ (AIResponse с полями: thought, reply_text, action, product_id)
6. **Обработка ответа:** Бэкенд обрабатывает структурированный ответ и выполняет действия (резервирование через RPC, если action="offer_payment")

## Обработка Ошибок

Использование `tenacity` для retry при ошибках валидации:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import ValidationError

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(ValidationError)
)
async def get_validated_response(...):
    # Логика с автоматическим retry при ValidationError
    pass

## Context Caching

**Назначение:** Снижение стоимости и задержки обработки System Prompt.

**Реализация:**
- Кэширование System Prompt с базовым инвентарем
- Обновление кэша только при изменении ассортимента
- Использование Gemini Context Caching API

```python
from google.genai import Client

genai = Client(api_key=GEMINI_API_KEY)

**Паттерн:**
- Создание кэша через `genai.cached_content.create()` с System Prompt
- Использование `cached_content` параметра в `generate_content_async()`
- Кэш переиспользуется для всех запросов с тем же System Prompt
```

## Vibe Coding (Персонализация)

**Назначение:** Генерация эмоционально окрашенных, контекстных ответов для повышения вовлеченности.

**Реализация:**
- Анализ тона сообщения пользователя
- Адаптация стиля ответа под контекст
- Использование эмодзи и культурных особенностей

```python
VIBE_PROMPT = """
Analyze user's message tone and respond in matching style:
- Excited → Enthusiastic response
- Frustrated → Empathetic, helpful
- Casual → Friendly, informal
- Formal → Professional but warm

Use appropriate emojis and cultural context for {language}.
"""
```

## Human Handoff

**Назначение:** Структурированный процесс поддержки с эскалацией на оператора.

**Триггеры:**
- Пользователь явно запрашивает оператора
- AI не может решить проблему после 3 попыток
- Критическая ошибка в системе

**Процесс:**
1. AI предлагает создать тикет
2. Создание тикета в БД со статусом `escalated`
3. Уведомление оператора через Telegram
4. Оператор получает контекст диалога

