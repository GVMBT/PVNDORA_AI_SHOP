# Сводка по платежным системам

## Всего платежных систем: **2**

---

## 1. **1Plat** (основная, используется по умолчанию)

### Статус: ✅ Настроена и работает

### Требуемые переменные окружения:
- `ONEPLAT_SHOP_ID` - ID магазина (x-shop)
- `ONEPLAT_SECRET_KEY` - Секретный ключ (x-secret)

### Опциональные переменные:
- `ONEPLAT_API_URL` - URL API (по умолчанию: `https://1plat.cash`)
- `ONEPLAT_MERCHANT_ID` - для обратной совместимости (deprecated)
- `ONEPLAT_API_KEY` - для обратной совместимости (deprecated)

### Webhook endpoint:
- `POST /api/webhook/1plat`
- `POST /webhook/1plat`

### Поддерживаемые методы оплаты:
- `card` - Банковская карта
- `sbp` - СБП (Система быстрых платежей)
- `qr` - QR-код
- `crypto` - Криптовалюта

### Особенности:
- Используется по умолчанию (если `DEFAULT_PAYMENT_GATEWAY` не указан)
- Имеет кулдаун на создание платежей (90 секунд)
- Проверка на дубликаты pending заказов
- Улучшенная обработка ошибок с понятными сообщениями

---

## 2. **Freekassa** (новая, добавлена недавно)

### Статус: ⚠️ Требует настройки переменных окружения

### Требуемые переменные окружения:
- `FREEKASSA_MERCHANT_ID` - ID магазина (API ключ кассы)
- `FREEKASSA_SECRET_WORD_1` - Первое секретное слово (для создания платежей)
- `FREEKASSA_SECRET_WORD_2` - Второе секретное слово (для проверки webhook)

### Опциональные переменные:
- `FREEKASSA_API_URL` - URL API (по умолчанию: `https://pay.freekassa.ru`)

### Webhook endpoint:
- `POST /api/webhook/freekassa`
- `POST /webhook/freekassa`
- `GET /api/webhook/freekassa` (для совместимости)
- `GET /webhook/freekassa` (для совместимости)

### Особенности:
- Поддержка GET и POST для webhook
- Возвращает "YES" для подтверждения получения webhook
- Использует SECRET_WORD_1 для создания платежей
- Использует SECRET_WORD_2 для проверки webhook

### Настройка в ЛК Freekassa:
1. **URL ОПОВЕЩЕНИЯ**: `https://pvndora.app/api/webhook/freekassa` (POST)
2. **URL УСПЕШНОЙ ОПЛАТЫ**: `https://pvndora.app/checkout/success` (GET)
3. **URL ВОЗВРАТА**: `https://pvndora.app/checkout/failed` (GET)

---

## Использование в коде

### Выбор платежного шлюза:
```python
# По умолчанию используется 1Plat
payment_gateway = request.payment_gateway or os.environ.get("DEFAULT_PAYMENT_GATEWAY", "1plat")

# Можно явно указать:
# - "1plat" для 1Plat
# - "freekassa" для Freekassa
```

### Создание платежа:
```python
payment_url = await payment_service.create_payment(
    order_id=order.id,
    amount=payable_amount,
    product_name=product_names,
    method=payment_gateway,  # "1plat" или "freekassa"
    payment_method=payment_method,  # "card", "sbp", "qr", "crypto"
    user_email=f"{user.id}@telegram.user",
    user_id=user.id
)
```

---

## Проверка конфигурации

### 1Plat:
- ✅ Проверяется наличие `ONEPLAT_SHOP_ID` или `ONEPLAT_MERCHANT_ID`
- ✅ Проверяется наличие `ONEPLAT_SECRET_KEY`
- ✅ Если не настроено - возвращается ошибка 500

### Freekassa:
- ✅ Проверяется наличие `FREEKASSA_MERCHANT_ID`
- ✅ Проверяется наличие `FREEKASSA_SECRET_WORD_1`
- ✅ Проверяется наличие `FREEKASSA_SECRET_WORD_2`
- ✅ Если не настроено - возвращается ошибка 500 с понятным сообщением

---

## Рекомендации

1. **Для продакшена**: Настроить обе платежные системы для резервирования
2. **По умолчанию**: Использовать 1Plat (уже настроен и работает)
3. **Для тестирования Freekassa**: Включить тестовый режим в ЛК Freekassa
4. **Мониторинг**: Проверять логи webhook'ов для обеих систем

---

## Документация

- **1Plat**: Встроена в код, см. `src/services/payments.py`
- **Freekassa**: См. `docs/FREEKASSA_INTEGRATION.md`
- **Официальная документация Freekassa**: https://docs.freekassa.com/
