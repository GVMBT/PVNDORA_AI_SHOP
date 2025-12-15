# Статусы Заказов (Order Statuses)

Упрощённый список статусов заказов в системе PVNDORA.

## Статусы (7 штук)

| Статус | Описание | Переходы |
|--------|----------|----------|
| `pending` | Создан, ожидает оплаты | → paid, prepaid, cancelled |
| `paid` | Оплачен + сток есть | → delivered, partial, cancelled, refunded |
| `prepaid` | Оплачен + стока нет (предзаказ) | → paid, partial, delivered, cancelled, refunded |
| `partial` | Часть товаров доставлена | → delivered, cancelled, refunded |
| `delivered` | Все товары доставлены | *(финальный)* |
| `cancelled` | Заказ отменён | *(финальный)* |
| `refunded` | Средства возвращены | *(финальный)* |

## Диаграмма переходов

```
pending
  ├─→ paid (оплата + сток есть)
  │     ├─→ delivered
  │     ├─→ partial → delivered
  │     ├─→ cancelled
  │     └─→ refunded
  │
  ├─→ prepaid (оплата + стока нет)
  │     ├─→ paid (сток появился)
  │     ├─→ partial → delivered
  │     ├─→ delivered (напрямую)
  │     ├─→ cancelled
  │     └─→ refunded
  │
  └─→ cancelled (истёк срок / пользователь отменил)
```

## Финальные статусы

- `delivered` — заказ выполнен
- `cancelled` — заказ отменён (причина в поле `cancellation_reason`)
- `refunded` — средства возвращены

## Код

**Определение:** `core/payments/constants.py` → `OrderStatus`

```python
class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    PREPAID = "prepaid"
    PARTIAL = "partial"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
```

**Переходы:** `core/orders/status_service.py` → `can_transition_to()`

## Удалённые статусы (legacy)

Следующие статусы были удалены в рефакторинге:

- `fulfilling`, `ready` — не используются (нет физических поставщиков)
- `expired` — объединён с `cancelled`
- `failed` — объединён с `cancelled`
- `fulfilled`, `completed` — синонимы `delivered`
- `error`, `refund_pending` — не статусы заказа
