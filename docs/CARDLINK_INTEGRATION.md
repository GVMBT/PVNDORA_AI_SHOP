# Интеграция CardLink

## Данные для заявки на cardlink.link

### Основная информация проекта

**Название проекта:** PVNDORA AI Shop

**Вид деятельности:** 
- Продажа цифровых товаров
- Подписки на AI-сервисы
- Доступы к платным сервисам

**Описание магазина:**
```
PVNDORA - AI-маркетплейс цифровых товаров в Telegram. 
Продаем доступы к платным нейросетям и сервисам: 
ChatGPT Plus, Midjourney, Claude Pro, GitHub Copilot, 
Canva Pro и другие. Формат выдачи: Login:Pass или инвайт-ссылки.
```

**URL магазина:** 
```
https://pvndora.app
```

### URL для обработки платежей

**Success URL (URL успешной оплаты):**
```
https://pvndora.app/payment/success?order_id={order_id}
```
*URL адрес, на который будет перенаправлен пользователь в случае успешного прохождения платежа*

**Fail URL (URL неуспешной оплаты):**
```
https://pvndora.app/payment/fail?order_id={order_id}
```
*URL адрес, на который будет перенаправлен пользователь в случае неуспешного прохождения платежа*

**Result URL (Webhook для обработки ответа):**
```
https://pvndora.app/api/webhook/cardlink
```
*URL адрес, по которому будет приходить обработка ответа о статусе платежа*

**Refund URL (Webhook для возвратов):**
```
https://pvndora.app/api/webhook/cardlink/refund
```
*URL адрес, по которому будет приходить обработка возврата*

**Chargeback URL (Webhook для чарджбэков):**
```
https://pvndora.app/api/webhook/cardlink/chargeback
```
*URL адрес, по которому будет приходить обработка чарджбэка*

## Шаги для подключения

1. **Регистрация на cardlink.link**
   - Перейти на https://cardlink.link/
   - Нажать "Получить ссылку"
   - Зарегистрироваться (email + пароль)
   - Привязать банковскую карту (спишется и вернется 100₽)

2. **Добавление магазина**
   - В личном кабинете: "Магазины" → "Добавить магазин"
   - Заполнить все поля из раздела выше
   - Подтвердить владение доменом:
     - **Вариант 1 (DNS):** Добавить TXT-запись в DNS
     - **Вариант 2 (Файл):** Загрузить файл в корень сайта
   - Нажать "Верифицировать"

3. **Ожидание модерации**
   - Статус изменится на "На модерации"
   - Обычно до 48 часов

4. **Получение API-данных**
   - После одобрения получить:
     - **API Token** (Bearer токен)
     - **Shop ID** (ID магазина)
   - Добавить в Vercel Environment Variables:
     - `CARDLINK_API_TOKEN`
     - `CARDLINK_SHOP_ID`

5. **Тестирование**
   - Создать тестовый платеж
   - Проверить webhook обработку
   - Убедиться в корректной доставке товаров

## Техническая интеграция

### API Endpoints

CardLink использует REST API с Bearer токеном:
```
Authorization: Bearer {CARDLINK_API_TOKEN}
```

### Создание платежа

```python
POST https://api.cardlink.link/v1/payments
Headers:
  Authorization: Bearer {token}
  Content-Type: application/json
Body:
{
  "shop_id": "{shop_id}",
  "amount": 1000.00,
  "currency": "RUB",
  "order_id": "unique_order_id",
  "description": "Оплата товара",
  "success_url": "https://pvndora.app/payment/success?order_id={order_id}",
  "fail_url": "https://pvndora.app/payment/fail?order_id={order_id}"
}
```

### Webhook формат

CardLink отправляет POST запросы на Result URL с данными о статусе платежа.

## Переменные окружения

Добавить в Vercel:
```
CARDLINK_API_TOKEN=your_api_token_here
CARDLINK_SHOP_ID=your_shop_id_here
```

