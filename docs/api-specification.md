# Спецификация API (OpenAPI/Swagger)

## Базовый URL

```
Production: https://your-app.vercel.app
```

## Аутентификация

### Telegram Mini App (initData)

Все эндпоинты Mini App требуют валидации `initData` от Telegram через проверку подписи.

## Эндпоинты для Mini App

### 1. GET /api/webapp/products/{product_id}

Получить информацию о товаре с актуальной ценой и скидкой.

**Request:** `GET /api/webapp/products/{product_id}` с `Authorization: Bearer {initData}`

**Response:** JSON с полями: `id`, `name`, `description`, `original_price`, `discount_percent`, `final_price`, `warranty_days`, `duration_days`, `available`

### 2. POST /api/webapp/orders

Создать заказ и получить ссылку на оплату.

**Request:** `POST /api/webapp/orders` с `{"product_id": "uuid"}`

**Response:** JSON с полями: `order_id`, `amount`, `payment_url`, `reserved_until`

### 3. GET /api/webapp/orders

Получить историю заказов пользователя.

**Request:** `GET /api/webapp/orders?limit=10&offset=0`

**Response:** JSON с массивом `orders` (поля: `id`, `product_name`, `amount`, `status`, `created_at`, `expires_at`) и `total`

## Эндпоинты для QStash Workers

### 1. POST /api/workers/deliver-goods

Доставка товара после оплаты (вызывается через QStash).

**Request:**
```http
POST /api/workers/deliver-goods
X-QStash-Signature: {signature}
Content-Type: application/json

{
  "order_id": "456e7890-e89b-12d3-a456-426614174001",
  "user_id": "789e0123-e89b-12d3-a456-426614174002",
  "stock_item_id": "012e3456-e89b-12d3-a456-426614174003"
}
```

**Response:**
```json
{
  "success": true,
  "message_sent": true
}
```

### 2. POST /api/workers/calculate-referral

Начисление реферального бонуса (вызывается через QStash).

**Request:**
```http
POST /api/workers/calculate-referral
X-QStash-Signature: {signature}
Content-Type: application/json

{
  "order_id": "456e7890-e89b-12d3-a456-426614174001",
  "user_id": "789e0123-e89b-12d3-a456-426614174002",
  "amount": 268.50
}
```

## Вебхуки

### 1. POST /api/webhook/telegram

Webhook от Telegram для обновлений бота.

**Request:**
```http
POST /api/webhook/telegram
Content-Type: application/json

{
  "update_id": 123456789,
  "message": {
    "message_id": 1,
    "from": {...},
    "text": "Привет"
  }
}
```

**Response:**
```json
{
  "ok": true
}
```

### 2. POST /api/webhook/payment/aaio

Webhook от платежной системы AAIO.

**Request:**
```http
POST /api/webhook/payment/aaio
Content-Type: application/json

{
  "order_id": "456e7890-e89b-12d3-a456-426614174001",
  "status": "paid",
  "signature": "..."
}
```

### 3. POST /api/webhook/payment/stripe

Webhook от Stripe.

**Request:**
```http
POST /api/webhook/payment/stripe
Stripe-Signature: {signature}
Content-Type: application/json

{
  "type": "checkout.session.completed",
  "data": {
    "object": {
      "client_reference_id": "456e7890-e89b-12d3-a456-426614174001",
      "amount_total": 26850
    }
  }
}
```

## Эндпоинты для Геймификации

### GET /api/webapp/leaderboard

Получить лидерборд по экономии (Money Saved).

**Request:**
```http
GET /api/webapp/leaderboard?limit=10&offset=0
Authorization: Bearer {initData}
```

**Response:**
```json
{
  "leaderboard": [
    {
      "user_id": "789e0123-e89b-12d3-a456-426614174002",
      "username": "@user1",
      "first_name": "Иван",
      "total_saved": 1500.50,
      "rank": 1
    },
    {
      "user_id": "012e3456-e89b-12d3-a456-426614174003",
      "username": "@user2",
      "first_name": "Мария",
      "total_saved": 1200.00,
      "rank": 2
    }
  ],
  "user_rank": 5,
  "user_saved": 800.25
}
```

## Эндпоинты для QStash Workers

### POST /api/workers/deliver-goods

Доставка товара после оплаты (вызывается через QStash).

**Request:**
```http
POST /api/workers/deliver-goods
X-QStash-Signature: {signature}
Content-Type: application/json

{
  "order_id": "456e7890-e89b-12d3-a456-426614174001",
  "user_id": "789e0123-e89b-12d3-a456-426614174002",
  "stock_item_id": "012e3456-e89b-12d3-a456-426614174003"
}
```

**Response:**
```json
{
  "success": true,
  "message_sent": true
}
```

### POST /api/workers/notify-supplier

Уведомление поставщика о продаже (вызывается через QStash).

**Request:**
```http
POST /api/workers/notify-supplier
X-QStash-Signature: {signature}
Content-Type: application/json

{
  "order_id": "456e7890-e89b-12d3-a456-426614174001",
  "product_id": "123e4567-e89b-12d3-a456-426614174000",
  "supplier_id": "789e0123-e89b-12d3-a456-426614174002"
}
```

### POST /api/workers/notify-supplier-prepaid

Уведомление поставщика о необходимости изготовления товара для предоплатного заказа (вызывается через QStash).

**Request:**
```http
POST /api/workers/notify-supplier-prepaid
X-QStash-Signature: {signature}
Content-Type: application/json

{
  "order_id": "456e7890-e89b-12d3-a456-426614174001",
  "product_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_telegram_id": 123456789,
  "fulfillment_deadline": "2025-11-15T10:00:00Z"
}
```

### POST /api/workers/check-fulfillment-timeout

Проверка заказов на таймаут выполнения (вызывается через Cron или QStash).

**Request:**
```http
POST /api/workers/check-fulfillment-timeout
X-QStash-Signature: {signature}
Content-Type: application/json

{}
```

**Response:**
```json
{
  "checked_orders": 5,
  "refunded_orders": 2,
  "refunded_orders_ids": ["...", "..."]
}
```

### POST /api/workers/process-refund

Обработка возврата средств (вызывается через QStash).

**Request:**
```http
POST /api/workers/process-refund
X-QStash-Signature: {signature}
Content-Type: application/json

{
  "order_id": "456e7890-e89b-12d3-a456-426614174001",
  "reason": "Fulfillment timeout" | "Supplier unavailable" | "User request"
}
```

**Response:**
```json
{
  "success": true,
  "refund_amount": 300.00,
  "refund_to_balance": true,
  "new_balance": 300.00
}
```

### POST /api/workers/update-leaderboard

Обновление лидерборда после покупки (вызывается через QStash).

**Request:**
```http
POST /api/workers/update-leaderboard
X-QStash-Signature: {signature}
Content-Type: application/json

{
  "user_id": "789e0123-e89b-12d3-a456-426614174002",
  "savings": 150.50
}
```

## OpenAPI Схема

Полная OpenAPI спецификация доступна в файле `openapi.yaml`:

```yaml
openapi: 3.0.0
info:
  title: PVNDORA API
  version: 1.0.0
servers:
  - url: https://your-app.vercel.app
paths:
  /api/webapp/products/{product_id}:
    get:
      summary: Get product information
      parameters:
        - name: product_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Product information
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Product'
components:
  schemas:
    Product:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        original_price:
          type: number
        discount_percent:
          type: number
        final_price:
          type: number
```

