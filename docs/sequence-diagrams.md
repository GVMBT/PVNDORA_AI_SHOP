# Диаграммы Последовательности

## Процесс Покупки (Instant - товар в наличии)

```
User          Bot           FastAPI        Gemini         Supabase RPC    QStash        Payment
  |            |               |               |                |            |              |
  |--"Купить"->|               |               |                |            |              |
  |            |--Webhook----->|               |                |            |              |
  |            |<--{"ok": true}|               |                |            |              |
  |            |               |               |                |            |              |
  |            |               |--AI Process->|                |            |              |
  |            |               |               |                |            |              |
  |            |               |<--AIResponse (action=offer_payment, product_id)            |
  |            |               |               |                |            |              |
  |            |               |--Real-time Validation-------->|            |              |
  |            |               |               |                |            |              |
  |            |               |<--Query available_stock_with_discounts View|            |              |
  |            |               |<--available, price, discount--|            |              |
  |            |               |               |                |            |              |
  |            |               |--reserve_product_for_purchase()-->|         |              |
  |            |               |<--Reservation Success----------|            |              |
  |            |               |               |                |            |              |
  |<--Payment URL + Product Info             |                |            |              |
  |            |               |               |                |            |              |
  |--Pay------>|               |               |                |            |--Pay------->|
  |            |               |<--Payment Webhook             |            |              |
  |            |               |--complete_purchase()---------->|            |              |
  |            |               |<--Order completed             |            |              |
  |            |               |--Publish to QStash---------->|            |              |
  |            |               |                |            |--Deliver Goods-->|
  |<--Product Delivered        |               |                |            |              |
```

## Процесс Покупки (Prepaid - товар под заказ)

```
User          Bot           FastAPI        Gemini         Supabase RPC    QStash        Payment    Supplier
  |            |               |               |                |            |              |            |
  |--"Хочу X"->|               |               |                |            |              |            |
  |            |--Webhook----->|               |                |            |              |            |
  |            |<--{"ok": true}|               |                |            |              |            |
  |            |               |               |                |            |              |            |
  |            |               |--AI Process->|                |            |              |            |
  |            |               |--Function Call: check_product_availability-->|            |              |            |
  |            |               |<--available: false, can_fulfill: true, fulfillment_time: 48h|            |              |            |
  |            |               |               |                |            |              |            |
  |<--"Товара нет, можем сделать под заказ за 2 дня. Предоплата 100%"      |            |              |            |
  |            |               |               |                |            |              |            |
  |--"Согласен"->|             |               |                |            |              |            |
  |            |               |--create_order_with_availability_check(prepaid)-->|         |              |            |
  |            |               |<--Order created (status=prepaid, order_type=prepaid)        |              |            |
  |            |               |               |                |            |              |            |
  |<--Payment URL (Prepaid)    |               |                |            |              |            |
  |            |               |               |                |            |              |            |
  |--Pay------>|               |               |                |            |--Pay------->|            |
  |            |               |<--Payment Webhook             |            |              |            |
  |            |               |--process_prepaid_payment()---->|            |              |            |
  |            |               |<--Status: prepaid              |            |              |            |
  |            |               |--Publish to QStash---------->|            |              |            |
  |            |               |                |            |--Notify Supplier-->|            |
  |            |               |                |            |              |--Get Product->|
  |            |               |                |            |              |<--Product Ready|
  |            |               |<--Supplier updates order (fulfill_prepaid_order)            |              |            |
  |            |               |<--Status: ready               |            |              |            |
  |            |               |--Publish to QStash---------->|            |              |            |
  |            |               |                |            |--Deliver Goods-->|
  |<--Product Delivered         |               |                |            |              |            |
```

## Процесс Возврата (Refund)

```
Cron/QStash   Worker        FastAPI        Supabase RPC    User
  |               |             |                |            |
  |--Check Timeout->|           |                |            |
  |               |--Find expired prepaid orders-->|         |
  |               |<--Orders list----------------|            |
  |               |             |                |            |
  |               |--process_refund()---------->|            |
  |               |<--Refund processed           |            |
  |               |             |                |            |
  |               |--Update user balance------->|            |
  |               |             |                |            |
  |               |--Send notification--------->|            |
  |               |             |                |--Refund notification->|
  |               |             |                |            |
  |<--Success      |             |                |            |
```

## Процесс AI-Консультации (с Context Caching)

```
User          Bot           FastAPI        Gemini         vecs          Supabase
  |            |               |               |            |                |
  |--"Нужны презентации"->|     |               |            |                |
  |            |--Webhook----->|               |            |                |
  |            |<--{"ok": true}|               |            |                |
  |            |               |               |            |                |
  |            |               |--RAG Search----------------->|                |
  |            |               |<--Relevant Products----------|                |
  |            |               |               |            |                |
  |            |               |--Get Cached Context-------->|                |
  |            |               |<--Cached System Prompt-------|                |
  |            |               |               |            |                |
  |            |               |--Generate with Cache------->|                |
  |            |               |<--AIResponse (thought, reply_text, action)     |
  |            |               |               |            |                |
  |            |               |--Function Call: check_product_availability-->|   |
  |            |               |<--Real-time Validation (via View)------|                |
  |            |               |               |            |                |
  |<--AI Response (Vibe Coded) |               |            |                |
```


## Процесс Резервирования и Оплаты (Детальный)

```
User          Mini App      FastAPI        Supabase RPC    QStash        Payment
  |               |             |                |            |              |
  |--Click Buy--->|             |                |            |              |
  |               |--POST /orders->|             |            |              |
  |               |             |--reserve_product_for_purchase()-->|         |
  |               |             |                |            |              |
  |               |             |<--Reservation Success (Order created)--------|             |
  |               |<--Order + Payment URL-------|            |              |
  |               |             |                |            |              |
  |--Redirect to Payment------->|                |            |              |
  |               |             |                |            |--Process---->|
  |               |             |                |            |              |
  |<--Payment Success-----------|                |            |              |
  |               |             |                |            |--Webhook----->|
  |               |             |<--Payment Callback-----------|              |
  |               |             |--complete_purchase()-------->|             |
  |               |             |<--Product Content-----------|              |
  |               |             |--Publish to QStash--------->|             |
  |               |             |                |            |              |
  |               |             |                |--Deliver------------->|
  |               |             |                |            |              |
  |<--Notification: Goods Delivered             |            |              |
```

## Процесс Обработки Ошибок и Retry

```
QStash        Worker        Supabase      Telegram Bot
  |               |              |              |
  |--Deliver----->|              |              |
  |               |--Get Order->|              |
  |               |<--Order Data-|              |
  |               |              |              |
  |               |--Send Message-------->|     |
  |               |<--Error (Rate Limit)--|     |
  |               |              |              |
  |<--Retry Request (after delay)          |     |
  |               |              |              |
  |--Deliver (retry)---------->|              |
  |               |--Send Message-------->|     |
  |               |<--Success-------------|     |
  |               |              |              |
  |<--Success Response----------|              |
```

