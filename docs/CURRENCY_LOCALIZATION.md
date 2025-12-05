# Валюты и Локализация Цен

## Стратегия Валют

### Основная Валюта: USD ($)

**Принцип:** Все цены в базе данных хранятся в долларах США (USD) как основная валюта.

**Причины:**
- Стабильность курса
- Международный стандарт для цифровых товаров
- Упрощение управления ценами

### Конвертация по Курсу

**Механизм:** Все остальные валюты конвертируются из USD по актуальному курсу в момент отображения.

**Реализация:**

```python
# Пример структуры для конвертации
CURRENCY_RATES = {
    "USD": 1.0,      # Базовая валюта
    "RUB": 95.0,     # Примерный курс (обновляется)
    "EUR": 0.92,     # Примерный курс
    "UAH": 38.0,     # Примерный курс
    # ... для всех поддерживаемых валют
}

def convert_price(price_usd: float, target_currency: str) -> float:
    """Конвертация цены из USD в целевую валюту"""
    rate = CURRENCY_RATES.get(target_currency, 1.0)
    return price_usd * rate

def format_price(price: float, currency: str) -> str:
    """Форматирование цены с символом валюты"""
    symbols = {
        "USD": "$",
        "RUB": "₽",
        "EUR": "€",
        "UAH": "₴",
        "GBP": "£",
        "TRY": "₺",
        "INR": "₹",
        "AED": "د.إ"
    }
    symbol = symbols.get(currency, currency)
    return f"{price:.2f} {symbol}"
```

## Определение Валюты по Языку

### Маппинг Язык → Валюта

```python
LANGUAGE_TO_CURRENCY = {
    "ru": "RUB",      # Русский → Рубли
    "uk": "UAH",      # Украинский → Гривны
    "en": "USD",      # Английский → Доллары
    "de": "EUR",      # Немецкий → Евро
    "fr": "EUR",      # Французский → Евро
    "es": "EUR",      # Испанский → Евро
    "tr": "TRY",      # Турецкий → Лиры
    "ar": "AED",      # Арабский → Дирхамы (или USD)
    "hi": "INR"       # Хинди → Рупии
}
```

### Логика Определения

1. **Извлечение языка пользователя:**
   ```python
   user_language = update.message.from_user.language_code  # "ru", "en", etc.
   ```

2. **Определение валюты:**
   ```python
   currency = LANGUAGE_TO_CURRENCY.get(user_language, "USD")  # По умолчанию USD
   ```

3. **Конвертация и форматирование:**
   ```python
   price_usd = product.price  # Из БД в USD
   price_local = convert_price(price_usd, currency)
   formatted_price = format_price(price_local, currency)
   ```

## Хранение в Базе Данных

### Структура Таблицы products

```sql
CREATE TABLE products (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    price NUMERIC NOT NULL,  -- Цена в USD
    -- ... другие поля
);
```

**Важно:** Поле `price` всегда хранит цену в USD.

### Пример Данных

```sql
INSERT INTO products (name, price) VALUES
    ('ChatGPT Plus', 20.00),  -- $20 USD
    ('Midjourney', 10.00),     -- $10 USD
    ('Claude Pro', 25.00);     -- $25 USD
```

## Отображение в AI-Ответах

### Форматирование в System Prompt

```python
SYSTEM_PROMPT = """
...
## Price Display Rules
- Always show price in user's local currency
- Format: "{price} {currency_symbol}"
- Examples:
  - Russian: "300₽/мес"
  - English: "$20/month"
  - Arabic: "75 د.إ/شهر"
- If discount applies, show both: "270₽ ~~300₽~~ (скидка 10%)"

## Language and Currency
User language: {user_language}
Currency: {currency}
Exchange rate: 1 USD = {exchange_rate} {currency}
"""
```

### Пример AI-Ответа

**Для русского пользователя:**
```
ChatGPT Plus — 1900₽/мес
(скидка 5% за простой 1 месяц)
Итого: 1805₽
```

**Для английского пользователя:**
```
ChatGPT Plus — $20/month
(discount 5% for 1 month in stock)
Total: $19
```

**Для арабского пользователя:**
```
ChatGPT Plus — 75 د.إ/شهر
(خصم 5% لمدة شهر في المخزن)
الإجمالي: 71.25 د.إ
```

## Обновление Курсов Валют

### Источники Курсов

1. **Внешний API** (рекомендуется):
   - ExchangeRate API
   - OpenExchangeRates
   - CurrencyLayer

2. **Кэширование:**
   - Обновление курсов раз в час
   - Хранение в Redis для быстрого доступа

### Реализация

```python
import httpx
from datetime import datetime, timedelta

async def update_currency_rates():
    """Обновление курсов валют"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.exchangerate-api.com/v4/latest/USD"
        )
        rates = response.json()["rates"]
        
        # Сохранение в Redis с TTL 1 час
        redis.setex(
            "currency_rates",
            3600,
            json.dumps(rates)
        )

async def get_currency_rate(target_currency: str) -> float:
    """Получение актуального курса"""
    rates_json = redis.get("currency_rates")
    if not rates_json:
        await update_currency_rates()
        rates_json = redis.get("currency_rates")
    
    rates = json.loads(rates_json)
    return rates.get(target_currency, 1.0)
```

## Интеграция с Платежными Системами

### Выбор Платежной Системы

```python
def get_payment_provider(currency: str, language: str) -> str:
    """Определение платежного провайдера"""
    # Используется только 1Plat для всех регионов
    return "1plat"
```

### Конвертация для Платежа

```python
async def create_payment(order: dict, user_language: str):
    """Создание платежа с правильной валютой"""
    currency = LANGUAGE_TO_CURRENCY.get(user_language, "USD")
    rate = await get_currency_rate(currency)
    
    price_usd = order["amount"]
    price_local = price_usd * rate
    
    # Округление до 2 знаков
    price_local = round(price_local, 2)
    
    # Создание платежа в локальной валюте
    payment = await payment_provider.create_payment(
        amount=price_local,
        currency=currency
    )
    
    return payment
```

## Особые Случаи

### Округление Цен

```python
def round_price(price: float, currency: str) -> float:
    """Округление цены в зависимости от валюты"""
    # Для рублевой зоны - до целых
    if currency in ["RUB", "UAH"]:
        return round(price)
    
    # Для долларов/евро - до 2 знаков
    if currency in ["USD", "EUR"]:
        return round(price, 2)
    
    # Для других - по умолчанию 2 знака
    return round(price, 2)
```

### Отображение Скидок

```python
def format_discount_price(original_usd: float, discount_percent: float, currency: str) -> str:
    """Форматирование цены со скидкой"""
    rate = get_currency_rate(currency)
    
    original_local = original_usd * rate
    final_local = original_local * (1 - discount_percent / 100)
    
    original_formatted = format_price(round_price(original_local, currency), currency)
    final_formatted = format_price(round_price(final_local, currency), currency)
    
    return f"{final_formatted} ~~{original_formatted}~~ (скидка {discount_percent}%)"
```

## Рекомендации по Реализации

1. **Хранение цен:** Всегда в USD в базе данных
2. **Конвертация:** В момент отображения/оплаты
3. **Кэширование курсов:** Redis с TTL 1 час
4. **Обновление курсов:** Cron job или при первом запросе
5. **Форматирование:** В зависимости от языка и валюты
6. **Округление:** По правилам валюты (рубли - целые, доллары - 2 знака)

## Пример Полной Реализации

```python
class CurrencyService:
    def __init__(self):
        self.redis = get_redis_client()
        self.language_to_currency = LANGUAGE_TO_CURRENCY
    
    async def get_user_currency(self, language_code: str) -> str:
        """Получить валюту пользователя по языку"""
        return self.language_to_currency.get(language_code, "USD")
    
    async def convert_and_format(self, price_usd: float, language_code: str) -> str:
        """Конвертировать и отформатировать цену"""
        currency = await self.get_user_currency(language_code)
        rate = await self.get_currency_rate(currency)
        
        price_local = price_usd * rate
        price_rounded = self.round_price(price_local, currency)
        
        return self.format_price(price_rounded, currency)
    
    async def get_currency_rate(self, currency: str) -> float:
        """Получить актуальный курс валюты"""
        # Реализация с кэшированием
        pass
```

