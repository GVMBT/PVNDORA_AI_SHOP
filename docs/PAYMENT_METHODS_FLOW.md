# User Flow для методов оплаты 1Plat

## Проблема

Методы оплаты 1Plat не работают. Нужно разобраться в user flow и исправить проблемы.

## Текущий User Flow

### 1. Загрузка методов оплаты

**Frontend (`useCheckoutFlow.js`):**
```javascript
getPaymentMethods()
  .then((data) => {
    if (data && Array.isArray(data.systems)) {
      setAvailableMethods(data.systems.map((s) => s.system_group))
      setPaymentMethod(data.systems[0]?.system_group || 'card')
    } else {
      setAvailableMethods(['card', 'sbp', 'qr', 'crypto'])
    }
  })
```

**Backend (`/api/webapp/payments/methods`):**
- Вызывает `payment_service.list_payment_methods()`
- Запрашивает у 1Plat API: `GET /api/merchant/payments/methods/by-api`
- Возвращает ответ как есть

**Проблема:** Неизвестна структура ответа от 1Plat API. Нужно проверить, что именно возвращается.

### 2. Отображение методов на фронтенде

**CheckoutPage.jsx:**
```javascript
{(availableMethods?.length ? availableMethods : ['card', 'sbp', 'qr', 'crypto']).map((m) => (
  <button onClick={() => setPaymentMethod(m)}>
    {m.toUpperCase()}
  </button>
))}
```

Пользователь видит кнопки: CARD, SBP, QR, CRYPTO

### 3. Создание заказа

**Frontend (`useCheckoutFlow.js`):**
```javascript
const result = await createOrderFromCart(
  promoResult?.is_valid ? promoCode : null,
  paymentMethod  // 'card', 'sbp', 'qr', 'crypto'
)
```

**Backend (`/api/webapp/orders`):**
```python
payment_method = request.payment_method or "card"
payment_url = await payment_service.create_payment(
    method=payment_gateway,  # "1plat"
    payment_method=payment_method  # "card", "sbp", "qr", "crypto"
)
```

**PaymentService (`_create_1plat_payment`):**
```python
method = self._normalize_method(method_override)  # Проверяет, что метод в {"card", "sbp", "qr", "crypto"}
payload = {
    "merchant_order_id": order_id,
    "user_id": user_id_int,
    "amount": amount_kopecks,
    "method": method,  # Передается в 1Plat API
}
```

## Проблемы

1. **Неизвестна структура ответа от 1Plat API** для `/api/merchant/payments/methods/by-api`
   - Нужно проверить, что именно возвращается
   - Возможно, структура отличается от ожидаемой `data.systems[].system_group`

2. **Маппинг методов может быть неправильным**
   - 1Plat может возвращать другие названия методов
   - Нужно правильно маппить на поддерживаемые: `card`, `sbp`, `qr`, `crypto`

3. **Метод может не передаваться правильно**
   - Нужно убедиться, что выбранный метод доходит до 1Plat API

## Правильный User Flow

### 1. Пользователь открывает страницу оплаты
- Загружаются доступные методы оплаты с 1Plat API
- Если загрузка не удалась - показываются дефолтные: card, sbp, qr, crypto

### 2. Пользователь выбирает метод оплаты
- Нажимает на кнопку (CARD, SBP, QR, CRYPTO)
- Метод сохраняется в state: `paymentMethod`

### 3. Пользователь нажимает "Оплатить"
- Создается заказ через `/api/webapp/orders`
- Передается `payment_method: "card"` (или выбранный метод)
- Бэкенд создает платеж в 1Plat с указанным методом
- Возвращается `payment_url` для редиректа

### 4. Редирект на страницу оплаты 1Plat
- Пользователь перенаправляется на `payment_url`
- На странице 1Plat отображаются реквизиты для выбранного метода
- После оплаты - webhook обрабатывает платеж

## Исправления (выполнено)

1. ✅ **Улучшена обработка ответа от 1Plat API**
   - Добавлено логирование ответа для отладки
   - Обработка разных форматов ответа (data.systems, массив, data.data, data.result)
   - Нормализация ответа для фронтенда

2. ✅ **Исправлен маппинг методов**
   - Маппинг различных названий методов на стандартные: card, sbp, qr, crypto
   - Фильтрация только поддерживаемых методов
   - Удаление дубликатов

3. ✅ **Добавлена обработка ошибок**
   - При ошибке загрузки методов - возвращаются дефолтные методы
   - Логирование ошибок для отладки

4. ⚠️ **UX улучшения (требуют доработки на фронтенде)**
   - Показывать загрузку методов (можно добавить loading state)
   - Показывать ошибки, если методы не загрузились (сейчас используются дефолтные)
   - Валидация выбранного метода (уже есть в _normalize_method)

## Правильный User Flow (после исправлений)

### 1. Пользователь открывает страницу оплаты
- ✅ Загружаются доступные методы оплаты с 1Plat API
- ✅ Если загрузка не удалась - показываются дефолтные: card, sbp, qr, crypto
- ✅ Методы нормализуются и фильтруются

### 2. Пользователь выбирает метод оплаты
- ✅ Нажимает на кнопку (CARD, SBP, QR, CRYPTO)
- ✅ Метод сохраняется в state: `paymentMethod`

### 3. Пользователь нажимает "Оплатить"
- ✅ Создается заказ через `/api/webapp/orders`
- ✅ Передается `payment_method: "card"` (или выбранный метод)
- ✅ Бэкенд валидирует метод через `_normalize_method`
- ✅ Бэкенд создает платеж в 1Plat с указанным методом
- ✅ Возвращается `payment_url` для редиректа

### 4. Редирект на страницу оплаты 1Plat
- ✅ Пользователь перенаправляется на `payment_url`
- ✅ На странице 1Plat отображаются реквизиты для выбранного метода
- ✅ После оплаты - webhook обрабатывает платеж

## Отладка

Если методы не работают, проверьте логи:
1. Логи загрузки методов: `1Plat payment methods response: ...`
2. Логи создания платежа: `1Plat payment created for order ...`
3. Логи ошибок: `Failed to fetch 1Plat payment methods: ...`

## Возможные проблемы

1. **1Plat API возвращает неожиданный формат**
   - Решение: добавлена обработка разных форматов
   - Логи покажут реальную структуру ответа

2. **Метод не поддерживается 1Plat**
   - Решение: `_normalize_method` валидирует метод перед отправкой
   - Если метод не поддерживается - возвращается ошибка

3. **Метод не передается при создании платежа**
   - Решение: проверьте, что `paymentMethod` передается в `createOrderFromCart`
   - Проверьте логи создания платежа
