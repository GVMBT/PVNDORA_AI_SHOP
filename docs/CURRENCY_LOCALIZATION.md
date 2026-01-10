# Валюты и Локализация Цен

## Обзор

PVNDORA использует **Multi-Currency Anchor Architecture** для стабильного ценообразования в международном сервисе.

**Принципы:**
- **Anchor Prices**: Фиксированные цены для каждой валюты (RUB, USD)
- **Transaction Snapshots**: Фиксация курса на момент транзакции
- **Balance Currency**: Баланс пользователя в его валюте (определяется по Telegram language_code)
- **Snapshot Architecture**: Заморозка курсов для точной бухгалтерии

---

## Архитектура "Якорных Валют" (Currency Anchors)

### 1. Anchor Prices для Товаров

**Таблица `products`:**
- `price` (NUMERIC) - базовая цена в USD (для обратной совместимости)
- `prices` (JSONB) - фиксированные цены по валютам: `{"RUB": 990, "USD": 10.5}`

**Логика:**
- Если есть anchor price в валюте пользователя → используется он
- Если нет anchor price → конвертация из USD по текущему курсу
- Anchor prices задаются вручную через админку

### 2. Balance Currency (Валюта Баланса)

**Таблица `users`:**
- `balance` (NUMERIC) - баланс в валюте `balance_currency`
- `balance_currency` (VARCHAR) - валюта баланса (RUB | USD)

**Определение валюты:**
```python
LANGUAGE_TO_CURRENCY: Dict[str, str] = {
    "ru": "RUB",  # Русский → Рубли
    "be": "RUB",  # Белорусский → Рубли
    "kk": "RUB",  # Казахский → Рубли
    # Остальные → USD (по умолчанию)
}

# При регистрации:
balance_currency = LANGUAGE_TO_CURRENCY.get(language_code, "USD")
```

**Смена валюты баланса:**
- Пользователь может конвертировать баланс через `POST /profile/convert-balance`
- При конвертации баланс пересчитывается по текущему курсу
- Логируется в `balance_transactions` как транзакция типа "conversion"

### 3. Transaction Snapshots (Снимки Транзакций)

**Таблица `orders`:**
- `amount` (NUMERIC) - базовая сумма в USD (для отчетности)
- `fiat_amount` (NUMERIC) - сумма в валюте оплаты (snapshot)
- `fiat_currency` (VARCHAR) - валюта оплаты (snapshot)
- `exchange_rate_snapshot` (NUMERIC) - курс на момент покупки (snapshot)

**Таблица `withdrawal_requests`:**
- `amount_debited` (NUMERIC) - сумма списания в валюте баланса
- `amount_to_pay` (NUMERIC) - фиксированная сумма USDT к выплате (snapshot)
- `exchange_rate` (NUMERIC) - курс на момент создания заявки (RUB → USDT)
- `usdt_rate` (NUMERIC) - курс USDT/USD на момент заявки (snapshot)
- `network_fee` (NUMERIC) - комиссия сети TRC20 (1.5 USDT)

**Принцип:**
- Курс фиксируется в момент создания заказа/заявки
- Бухгалтерия использует snapshot курсы, а не текущие
- Это гарантирует точность P&L отчетов

---

## CurrencyService

**Файл:** `core/services/currency.py`

### Основные методы:

```python
class CurrencyService:
    async def get_anchor_price(product_id: str, currency: str) -> Optional[Decimal]:
        """Получить anchor price товара в валюте, если есть"""
        
    async def convert_balance(from_currency: str, to_currency: str, amount: Decimal) -> Decimal:
        """Конвертировать баланс между RUB и USD (с правильным округлением)"""
        
    async def get_user_currency(telegram_id: int) -> str:
        """Определить валюту баланса пользователя по Telegram language_code"""
        
    async def calculate_withdrawal_usdt(
        amount_in_balance_currency: Decimal,
        balance_currency: str
    ) -> Dict[str, Decimal]:
        """Рассчитать сумму USDT для вывода с учётом комиссии сети"""
```

---

## Использование в Коде

### Backend (FastAPI)

**Checkout Flow:**
```python
# 1. Получить anchor price или конвертировать из USD
price_decimal = await currency_service.get_anchor_price(product.id, user_currency)
if not price_decimal:
    rate = await currency_service.get_exchange_rate(user_currency)
    price_decimal = product.price * rate

# 2. Фиксировать snapshot при создании заказа
order = await orders_domain.create_order(
    product_id=product.id,
    user_id=user.id,
    amount=price_decimal,
    currency=user_currency,
    exchange_rate_snapshot=rate  # Фиксируем курс!
)
```

**Withdrawal Flow:**
```python
# 1. Рассчитать USDT с учётом комиссии
result = await currency_service.calculate_withdrawal_usdt(
    amount_in_balance_currency=request.amount,
    balance_currency=user.balance_currency
)

# 2. Фиксировать snapshot при создании заявки
withdrawal = await withdrawals_domain.create_withdrawal(
    user_id=user.id,
    amount_debited=request.amount,
    amount_to_pay=result["usdt_amount"],
    exchange_rate=result["rate"],
    usdt_rate=result["usdt_rate"],
    network_fee=result["network_fee"]
)
```

### Frontend (React)

**Отображение цен:**
- Frontend получает готовые цены из API (anchor или конвертированные)
- НЕ делает конвертацию на клиенте
- Использует `Intl.NumberFormat` для форматирования

**Отображение баланса:**
- Backend возвращает баланс в `balance_currency` пользователя
- Если пользователь меняет валюту интерфейса → вызывается `POST /profile/convert-balance`

---

## Бухгалтерия и Отчетность

### Принцип Snapshot для Точности

**Проблема старой модели:**
- Использование текущих курсов для исторических транзакций
- Хардкод `/80` в SQL функциях
- Неточные P&L отчеты

**Решение:**
- Все заказы хранят `exchange_rate_snapshot`
- SQL функция `calculate_order_expenses` использует snapshot курсы
- Точные отчеты по прибыли/убыткам

**Пример SQL:**
```sql
-- Старая модель (неправильно):
acquiring_fee_rub / 80  -- Хардкод!

-- Новая модель (правильно):
acquiring_fee_rub / order.exchange_rate_snapshot  -- Используем snapshot!
```

---

## Обновление Курсов Валют

**Крон:** `api/cron/update_exchange_rates.py`

**Расписание:** Каждые 6 часов

**Таблица:** `exchange_rates`
- Хранит текущие курсы для конвертации новых транзакций
- Исторические транзакции используют snapshot (не зависят от обновлений)

---

## Примеры Использования

### Создание Товара с Anchor Price

```python
# В админке:
product = await create_product(
    name="ChatGPT Plus",
    price=10.0,  # USD (базовая)
    prices={"RUB": 990, "USD": 10.0}  # Anchor prices
)
```

### Покупка (Anchor Price доступен)

```python
# Пользователь с balance_currency = RUB
price = await currency_service.get_anchor_price(product.id, "RUB")
# price = 990 (фиксированная цена, не меняется при колебаниях курса)

# Создаём заказ с snapshot:
order = await create_order(
    fiat_amount=990,
    fiat_currency="RUB",
    exchange_rate_snapshot=current_usd_rate  # Для бухгалтерии
)
```

### Покупка (Anchor Price отсутствует)

```python
# Пользователь с balance_currency = EUR (нет anchor price)
rate = await currency_service.get_exchange_rate("EUR")
price = product.price * rate  # Конвертация из USD

# Создаём заказ с snapshot:
order = await create_order(
    fiat_amount=price,
    fiat_currency="EUR",
    exchange_rate_snapshot=rate  # Фиксируем для бухгалтерии
)
```

### Вывод (USDT)

```python
# Пользователь хочет вывести 5000 RUB
result = await currency_service.calculate_withdrawal_usdt(
    amount_in_balance_currency=5000,
    balance_currency="RUB"
)

# result = {
#     "usdt_amount": 54.30,  # Фиксированная сумма USDT
#     "rate": 92.08,         # RUB → USDT курс
#     "usdt_rate": 1.0,      # USDT → USD курс
#     "network_fee": 1.5     # Комиссия TRC20
# }

# Создаём заявку с snapshot:
withdrawal = await create_withdrawal(
    amount_debited=5000,      # RUB (списываем)
    amount_to_pay=54.30,      # USDT (выплачиваем)
    exchange_rate=92.08,      # Snapshot
    usdt_rate=1.0,            # Snapshot
    network_fee=1.5           # Snapshot
)
```

---

## Рекомендации

1. **Всегда используйте CurrencyService** - не делайте ручную конвертацию в роутерах
2. **Фиксируйте snapshot при транзакциях** - для точной бухгалтерии
3. **Anchor prices для популярных валют** - RUB, USD (стабильность цен)
4. **Конвертация для редких валют** - автоматически из USD
5. **Используйте `convert_balance()` для балансов** - правильное округление

---

## Миграция со Старой Модели

**Старая модель (устарела):**
- Все цены в USD
- Конвертация на клиенте "на лету"
- Плавающие цены (меняются каждые 15 минут)
- Хардкод курсов в SQL

**Новая модель (текущая):**
- Anchor prices для стабильности
- Конвертация на бэкенде с snapshot
- Фиксированные цены для пользователей
- Динамические курсы в SQL функциях (snapshot)

**Как мигрировать:**
1. Заполнить `products.prices` для существующих товаров (см. миграцию `20260109_fill_anchor_prices.sql`)
2. Обновить `users.balance_currency` на основе `language_code`
3. Конвертировать существующие балансы при необходимости
