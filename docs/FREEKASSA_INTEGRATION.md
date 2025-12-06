# Freekassa Integration Guide

## Официальная документация
- **Основная документация**: https://docs.freekassa.com/
- **Документация на русском**: https://docs.freekassa.net/

## Настройка в личном кабинете Freekassa

### Необходимые данные из ЛК Freekassa:

1. **MERCHANT_ID** (ID магазина)
   - Находится в настройках магазина
   - Используется как `FREEKASSA_MERCHANT_ID` в переменных окружения

2. **SECRET_WORD_1** (Первое секретное слово)
   - Используется для формирования подписи при создании платежа
   - Используется как `FREEKASSA_SECRET_WORD_1` в переменных окружения

3. **SECRET_WORD_2** (Второе секретное слово)
   - Используется для проверки подписи в webhook уведомлениях
   - Используется как `FREEKASSA_SECRET_WORD_2` в переменных окружения

### Настройка URL в ЛК Freekassa:

1. **URL ОПОВЕЩЕНИЯ** (Notification URL)
   - URL: `https://pvndora.app/api/webhook/freekassa`
   - Метод: **POST** (поддерживается также GET для совместимости)

2. **URL УСПЕШНОЙ ОПЛАТЫ** (Success URL)
   - URL: `https://pvndora.app/checkout/success`
   - Метод: **GET**

3. **URL ВОЗВРАТА В СЛУЧАЕ НЕУДАЧИ** (Failure URL)
   - URL: `https://pvndora.app/checkout/failed`
   - Метод: **GET**

## Формирование подписи для создания платежа

Подпись формируется по формуле:
```
md5(MERCHANT_ID:AMOUNT:SECRET_WORD_1:MERCHANT_ORDER_ID)
```

Пример:
```python
import hashlib

merchant_id = "12345"
amount = "100.00"
secret_word_1 = "your_secret_word_1"
order_id = "order_123"

sign_string = f"{merchant_id}:{amount}:{secret_word_1}:{order_id}"
signature = hashlib.md5(sign_string.encode("utf-8")).hexdigest()
```

## Формирование URL платежа

```
https://pay.freekassa.ru/?m={MERCHANT_ID}&oa={AMOUNT}&o={MERCHANT_ORDER_ID}&s={SIGN}
```

Параметры:
- `m` - MERCHANT_ID (ID магазина)
- `oa` - AMOUNT (сумма платежа в рублях)
- `o` - MERCHANT_ORDER_ID (номер заказа)
- `s` - SIGN (подпись, сформированная с SECRET_WORD_1)
- `us_field1` - опционально, дополнительные данные (например, email)

## Верификация webhook уведомления

### Параметры webhook:
- `MERCHANT_ID` - ID магазина
- `AMOUNT` - сумма платежа
- `MERCHANT_ORDER_ID` - номер заказа
- `SIGN` - подпись для проверки
- `intid` - внутренний номер транзакции Freekassa
- `P_EMAIL` - email плательщика (опционально)
- `CUR_ID` - ID валюты (опционально)

### Проверка подписи:
```
md5(MERCHANT_ID:AMOUNT:SECRET_WORD_2:MERCHANT_ORDER_ID)
```

### Ответ на webhook:
После успешной обработки webhook необходимо вернуть строку `"YES"` для подтверждения получения уведомления.

## Проверка IP-адресов (рекомендуется)

Для дополнительной безопасности рекомендуется проверять IP-адреса серверов Freekassa:

- `168.119.157.136`
- `168.119.60.227`
- `178.154.197.79`
- `51.250.54.238`

## Переменные окружения

Добавьте в `.env` и Vercel:

```bash
FREEKASSA_MERCHANT_ID=your_merchant_id
FREEKASSA_SECRET_WORD_1=your_secret_word_1
FREEKASSA_SECRET_WORD_2=your_secret_word_2
FREEKASSA_API_URL=https://pay.freekassa.ru
```

## Использование в коде

### Создание платежа:
```python
payment_url = await payment_service.create_payment(
    order_id="order_123",
    amount=100.0,
    product_name="Product Name",
    method="freekassa",  # Указываем freekassa как платежный шлюз
    currency="RUB",
    user_email="user@example.com"
)
```

### Обработка webhook:
Webhook автоматически обрабатывается в `/api/webhook/freekassa` и:
1. Проверяет подпись с использованием SECRET_WORD_2
2. Отправляет задачу в QStash для доставки товаров
3. Рассчитывает реферальные бонусы
4. Возвращает "YES" для подтверждения

## Важные замечания

1. **SECRET_WORD_1** используется только для создания платежей
2. **SECRET_WORD_2** используется только для проверки webhook
3. Никогда не используйте SECRET_WORD_2 для создания платежей
4. Всегда проверяйте подпись в webhook перед обработкой платежа
5. Рекомендуется проверять IP-адреса отправителей webhook

## Тестовый режим

В личном кабинете Freekassa можно включить "Тестовый режим" для проверки интеграции без реальных платежей.
