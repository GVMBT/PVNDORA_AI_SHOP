# Спецификация UX, Deep Linking и Локализации

## Разделение Ответственности: Чат vs Mini App

### Чат (Консьерж)
**Назначение:** Консультации, уведомления

**Функции:**
- AI-консультации и диалоги
- Уведомления о статусе заказов
- Быстрые действия (добавить в wishlist, создать тикет)

### Mini App (Витрина)
**Назначение:** Каталог, профиль, оплата

**Функции:**
- Просмотр каталога товаров
- История покупок
- Профиль пользователя
- Оплата товаров
- Лидерборд геймификации

## Бесшовный Deep Linking

### Протокол Кодирования startapp

**Требование:** Обязательная передача контекста через `startapp` параметр.

**Ограничение:** Telegram ограничивает длину `startapp` до 512 символов.

**Решение:** Использование Base64url для кодирования сложных параметров.

### Формат startapp

```
https://t.me/bot/app?startapp={base64url_encoded_params}
```

### Структура Параметров

```python
from base64 import urlsafe_b64encode, urlsafe_b64decode
import json

def encode_startapp_params(params: dict) -> str:
    """Кодирование параметров для startapp"""
    json_str = json.dumps(params, separators=(',', ':'))
    encoded = urlsafe_b64encode(json_str.encode()).decode().rstrip('=')
    return encoded

def decode_startapp_params(encoded: str) -> dict:
    """Декодирование параметров из startapp"""
    # Добавление padding если нужно
    padding = 4 - len(encoded) % 4
    if padding != 4:
        encoded += '=' * padding
    
    decoded = urlsafe_b64decode(encoded)
    return json.loads(decoded.decode())
```

### Примеры Использования

#### Переход к товару из чата

```python
# В чате AI предлагает товар
product_id = "123e4567-e89b-12d3-a456-426614174000"
params = {
    "action": "view_product",
    "product_id": product_id,
    "source": "chat"
}

startapp = encode_startapp_params(params)
webapp_url = f"https://t.me/bot/app?startapp={startapp}"

# AI отправляет кнопку
await message.answer(
    "Отличный выбор! Перейдите в витрину для оплаты:",
    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="💳 Оплатить", web_app=WebAppInfo(url=webapp_url))
    ]])
)
```

#### Переход к оплате с контекстом

```python
params = {
    "action": "checkout",
    "order_id": order_id,
    "product_id": product_id,
    "amount": 268.50,
    "discount_percent": 10.5
}

startapp = encode_startapp_params(params)
```

#### Возврат в чат из Mini App

```python
# В Mini App после оплаты
back_to_chat_url = f"https://t.me/bot?start=order_{order_id}"
```

## Сценарии Перехода с Сохранением Контекста

### Сценарий 1: Покупка из Чата

1. Пользователь в чате: "Хочу ChatGPT Plus"
2. AI предлагает товар с кнопкой "Оплатить"
3. Кнопка открывает Mini App с предзаполненной формой оплаты
4. После оплаты Mini App закрывается, пользователь возвращается в чат
5. Бот отправляет подтверждение и данные доступа

### Сценарий 2: История Покупок

1. Пользователь в чате: "Что я покупал?"
2. AI показывает краткий список последних покупок
3. AI предлагает кнопку "Открыть полную историю"
4. Mini App открывается на странице истории покупок

## Локализация

### RTL (Right-to-Left) Поддержка

**Требование:** Поддержка RTL интерфейсов для арабского языка.

**Реализация в Mini App:**

```jsx
// React компонент с RTL поддержкой
import { useTelegram } from '../hooks/useTelegram';

const ProductCard = ({ product }) => {
  const { language } = useTelegram();
  const isRTL = language === 'ar' || language === 'he';
  
  return (
    <div dir={isRTL ? 'rtl' : 'ltr'} className="product-card">
      <h3>{product.name}</h3>
      <p>{product.description}</p>
    </div>
  );
};
```

**CSS для RTL:**

```css
[dir="rtl"] {
  text-align: right;
}

[dir="rtl"] .product-card {
  direction: rtl;
}

[dir="rtl"] .price {
  float: left;
}
```

### Культурная Адаптация Тона AI

**Требование:** Адаптация тона AI под культурные особенности.

**Реализация:**

```python
CULTURAL_TONES = {
    "ru": {
        "formality": "casual",
        "emoji_usage": "moderate",
        "directness": "high"
    },
    "ar": {
        "formality": "formal",
        "emoji_usage": "low",
        "directness": "medium",
        "greeting": "السلام عليكم"
    },
    "en": {
        "formality": "friendly",
        "emoji_usage": "high",
        "directness": "medium"
    }
    # ... для всех 9 языков
}

def get_cultural_prompt(language: str) -> str:
    """Получить культурно адаптированный промпт"""
    tone = CULTURAL_TONES.get(language, CULTURAL_TONES["en"])
    
    return f"""
    Respond in {language} language with:
    - Formality level: {tone['formality']}
    - Emoji usage: {tone['emoji_usage']}
    - Directness: {tone['directness']}
    - Cultural context: {tone.get('greeting', 'Hello')}
    """
```

## Виральность (Viral Sharing)

### Нативный Шеринг через switchInlineQuery

**Требование:** Использование `switchInlineQuery` вместо копирования ссылок.

**Реализация:**

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Кнопка для шеринга предложения
share_button = InlineKeyboardButton(
    text="Поделиться предложением",
    switch_inline_query=f"product_{product_id}"
)

# Обработка inline query
@dp.inline_query()
async def handle_inline_query(query: InlineQuery):
    if query.query.startswith("product_"):
        product_id = query.query.split("_")[1]
        # Генерация inline результата с товаром
        result = InlineQueryResultArticle(
            id=product_id,
            title="Смотри, что нашел!",
            description="Отличное предложение",
            input_message_content=InputTextMessageContent(
                message_text=f"Нашел отличный товар: {product_name}!"
            )
        )
        await query.answer([result])
```

## Human Handoff UX

### Процесс Эскалации

1. **Триггер:** Пользователь запрашивает оператора или AI не может помочь
2. **AI Предложение:** "Создать запрос в поддержку?"
3. **Создание Тикета:** AI создает тикет в БД
4. **Уведомление:** Оператор получает уведомление
5. **Ответ Оператора:** Оператор отвечает через админ-панель
6. **Уведомление Пользователя:** Бот отправляет ответ оператора

### UI для Human Handoff

```python
# Кнопка для эскалации
escalate_keyboard = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(
        text="Связаться с оператором",
        callback_data=f"escalate_{ticket_id}"
    )
]])

await message.answer(
    "Я не могу решить эту проблему. Хотите связаться с оператором?",
    reply_markup=escalate_keyboard
)
```

