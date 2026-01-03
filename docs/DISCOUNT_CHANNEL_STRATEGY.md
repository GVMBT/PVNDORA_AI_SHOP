# Стратегия дискаунт-канала и перелива в PVNDORA

## Оглавление

1. [Концепция](#концепция)
2. [Архитектура экосистемы](#архитектура-экосистемы)
3. [Ценообразование](#ценообразование)
4. [Механика страховки](#механика-страховки)
5. [Обработка проблем](#обработка-проблем)
6. [Офферы для перелива](#офферы-для-перелива)
7. [Партнерская программа PVNDORA](#партнерская-программа-pvndora)
8. [Техническая реализация](#техническая-реализация)
9. [Метрики успеха](#метрики-успеха)
10. [Зацикленность экосистемы](#зацикленность-экосистемы)

---

## Концепция

### Проблема
- PVNDORA продает по цене x5 выше рыночной (60$ vs 10$ на маркетплейсах)
- Трафик утекает на Авито/Plati к конкурентам
- Конкуренты покупают у нас и перепродают дешевле

### Решение: Матрица захвата рынка
Создать двухуровневую систему, где клиент в любом случае взаимодействует с нами:

```
┌─────────────────────────────────────────────────────────────┐
│  ДИСКАУНТ-БОТ (@ai_discount_bot)                           │
│  • Цены на уровне/ниже рынка (8-10$)                       │
│  • Автовыдача без гарантий                                 │
│  • Кнопочный интерфейс                                     │
│  • Опциональная платная страховка                          │
│  • Рычаги перелива в PVNDORA                               │
└─────────────────────────────┬───────────────────────────────┘
                              │
                    [Перелив трафика]
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  PVNDORA (@pvndora_ai_bot)                                          │
│  • Премиум цены (60$)                                                      │
│  • Гарантия на все аккаунты                                                   │
│  • 3-уровневая партнерская программа                                                  │
│  • Поддержка 24/7                                                          │
│  • Mini App + AI-агент                                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Архитектура экосистемы

### Общая БД
- Единая база данных Supabase для обоих ботов
- Единый пользователь (идентификация по telegram_id)
- История покупок сохраняется при переходе

### Разделение по source_channel
```sql
-- Поле в orders для отслеживания источника
source_channel: 'discount' | 'premium' | 'migrated'

-- Поле в users для отслеживания происхождения
discount_tier_source: BOOLEAN  -- TRUE если начинал в дисконте
```

### Интерфейсы
| Параметр | Дискаунт | PVNDORA |
|----------|----------|---------|
| Интерфейс | Кнопочный бот | Mini App + AI |
| Цены | discount_price | price |
| Гарантия | Нет (платная страховка) | Включена |
| Поддержка | Минимальная | 24/7 |
| Партнерка | Нет | 3 уровня |

---

## Ценообразование

### Структура цен в БД (products)
```
msrp           — оригинальная цена сервиса (Google/OpenAI/etc)
price          — цена в PVNDORA (USD)
discount_price — цена в дискаунте (USD) [НОВОЕ ПОЛЕ]
```

### Пример (Gemini Ultra)
```
msrp           = 250$  (цена Google)
price          = 60$   (PVNDORA)
discount_price = 8-10$ (дискаунт)
```

### Стратегия ценообразования дисконта
- На уровне рынка или ниже для захвата трафика
- Возможен демпинг в ноль для вытеснения конкурентов
- Прибыль формируется за счет:
  - Продажи страховок
  - Перелива в PVNDORA (высокий LTV)

---

## Механика страховки

### Концепция
Платная опция в дисконте — право на замену при отлете аккаунта.

### Варианты страховки

**Правило:** Страховка ≥ 50% от стоимости аккаунта (защита от каннибализации).

| Тип | Срок | Цена | Замены |
|-----|------|------|--------|
| Базовая | 7 дней | +50% от цены | 1 |
| Расширенная | 14 дней | +80% от цены | 2 |

### Пример
```
ChatGPT Plus — 950₽

[Купить без страховки]

[+] Страховка 7 дней — 475₽ (1 замена)
    Итого: 1,425₽

[+] Страховка 14 дней — 760₽ (2 замены)
    Итого: 1,710₽

[Купить со страховкой]
```

### Сравнение с PVNDORA
```
Дискаунт без страховки:     950₽ (0 замен)
Дискаунт + базовая:       1,425₽ (1 замена, 7 дней)
Дискаунт + расширенная:   1,710₽ (2 замены, 14 дней)
PVNDORA:                  4,500₽ (∞ замен, полный срок, 24/7 поддержка)
```

Разница в ~2.6-4.7x оправдана качеством сервиса и партнеркой.

### Зачем страховка
1. Дополнительный доход с дисконта
2. Клиент привыкает к ценности гарантий
3. Мост к PVNDORA (там гарантия включена)

---

## Обработка проблем

### Механика через кнопку в боте

После покупки клиент получает сообщение с кнопкой:

```
Заказ #abc123 выполнен

Данные аккаунта:
login: user@example.com
password: xxxxxxxx

Страховка: 7 дней (до 15.01.2026)
────────────────────
[Проблема с аккаунтом]
```

### Обработка нажатия кнопки

```
Что случилось?

[Аккаунт заблокирован]
[Неверный логин/пароль]
[Не могу войти]
[Другое]
```

### Логика обработки

```python
async def handle_issue_report(user_id, order_id, issue_type):
    order = await db.get_order(order_id)
    
    if order.insurance_id:
        insurance = await db.get_insurance(order.insurance_id)
        days_since = (now - order.delivered_at).days
        
        if days_since <= insurance.duration_days:
            replacements_used = await db.count_replacements(order_id)
            
            if replacements_used < insurance.replacements_count:
                # Автоматическая замена
                new_item = await deliver_replacement(order_id)
                return send_replacement_success(user_id, new_item)
            else:
                # Лимит замен исчерпан
                return send_offer_limit_exhausted(user_id)
        else:
            # Страховка истекла
            return send_offer_insurance_expired(user_id)
    else:
        # Нет страховки
        return send_offer_no_insurance(user_id)
```

### Таблица решений

| Ситуация | Действие |
|----------|----------|
| Есть страховка, срок активен, есть замены | Автоматическая замена |
| Есть страховка, срок активен, лимит исчерпан | Оффер PVNDORA |
| Есть страховка, срок истек | Оффер PVNDORA |
| Нет страховки | Оффер PVNDORA или покупка со страховкой |

---

## Офферы для перелива

### Таблица промокодов

| Код | Скидка | Сценарий | Срок действия |
|-----|--------|----------|---------------|
| REPLACE50 | 50% | Проблема с аккаунтом | 7 дней |
| LOYAL30 | 30% | После 3 покупок | 14 дней |
| UPGRADE40 | 40% | Через 7 дней | 7 дней |
| MIGRATE50 | 50% | Первый переход | 30 дней |

---

### Оффер 1: После успешной покупки

**Цель:** Показать ценность партнерки

```
Заказ выполнен. Данные выше.

Хочешь зарабатывать на AI-аккаунтах?

В PVNDORA — партнерская программа:
• 10% с каждого приведенного клиента
• 7% с клиентов твоих рефералов
• 3% с третьей линии

Пример: 10 рефералов купили на 50,000₽ = 5,000₽ тебе

Вывод от 1,000₽

[Подключить партнерку]
```

---

### Оффер 2: Нет страховки

**Цель:** Конвертировать боль в переход

```
В дисконте замены не предусмотрены.

Варианты:
1. Купить новый аккаунт со страховкой
2. Перейти в PVNDORA — гарантия включена

В PVNDORA:
• Гарантия на все аккаунты
• Бесплатная замена при проблемах
• Поддержка 24/7

Промокод REPLACE50 — скидка 50%

[Купить в PVNDORA]
[Купить здесь со страховкой]
```

---

### Оффер 3: Страховка истекла

**Цель:** Показать преимущество включенной гарантии

```
Срок страховки истек.

В PVNDORA гарантия включена в цену — не нужно следить за сроками.

• Гарантия на весь срок действия аккаунта
• Бесплатные замены
• Поддержка 24/7

Промокод REPLACE50 — скидка 50%

[Купить в PVNDORA]
```

---

### Оффер 4: Лимит замен исчерпан

**Цель:** Показать преимущество неограниченных замен

```
Лимит замен по страховке исчерпан.

В PVNDORA — неограниченные замены в период гарантии.

Промокод REPLACE50 — скидка 50%

[Купить в PVNDORA]
```

---

### Оффер 5: Через 7 дней (информационный)

**Цель:** Напомнить о партнерке без давления

```
Новые позиции в PVNDORA:

• Claude 3.5 Sonnet — 45$
• Cursor Pro — 25$
• Midjourney V7 — 35$

Гарантия включена. Партнерка 10%/7%/3%.

[Смотреть каталог]
```

---

### Оффер 6: После 3 покупок (лояльность)

**Цель:** Персональный оффер для постоянного клиента

```
3 покупки в дисконте — ты постоянный клиент.

Персональное предложение:
• Скидка 30% на первый заказ в PVNDORA
• Партнерка 10%/7%/3%
• Гарантия на все аккаунты

Промокод LOYAL30

[Активировать]
```

---

### Оффер 7: Разблокировка партнерки

**Цель:** Вовлечь в экосистему через заработок

```
Бонус за покупку — партнерка разблокирована!

Зарабатывай в PVNDORA:
• 10% с первой линии
• 7% со второй
• 3% с третьей

Твоя ссылка:
t.me/pvndora_ai_bot?start=ref_{telegram_id}

[Подробнее о партнерке]
```

---

## Партнерская программа PVNDORA

### Как это работает

Партнерская программа — это возможность зарабатывать на рекомендациях. Каждый клиент PVNDORA получает персональную реферальную ссылку и зарабатывает процент с покупок приведенных клиентов.

### Карьерные уровни

| Уровень | Название | Порог | Что открывается |
|---------|----------|-------|-----------------|
| 0 | LOCKED | — | Партнерка заблокирована |
| 1 | PROXY | Первая покупка | Линия 1 (10%) |
| 2 | OPERATOR | Оборот 250$ | Линия 2 (7%) |
| 3 | ARCHITECT | Оборот 1000$ | Линия 3 (3%) |

### Как считается оборот

**Оборот** = сумма всех твоих покупок + сумма покупок твоих рефералов

Пример:
- Ты купил на 100$
- Твои рефералы купили на 200$
- Твой оборот = 300$ → уровень OPERATOR

### 3-уровневая структура

```
ТЫ (партнер)
│
├── Линия 1: Прямые рефералы (10%)
│   ├── Реферал А купил на 100$ → тебе 10$
│   ├── Реферал Б купил на 50$ → тебе 5$
│   └── ...
│
├── Линия 2: Рефералы твоих рефералов (7%)
│   ├── Реферал А привел клиента, тот купил на 100$ → тебе 7$
│   └── ...
│
└── Линия 3: Третий уровень (3%)
    ├── Клиент третьего уровня купил на 100$ → тебе 3$
    └── ...
```

### Пример расчета дохода

**Исходные данные:**
- Ты привел 10 человек (линия 1)
- Они привели 30 человек (линия 2)
- Те привели 50 человек (линия 3)
- Средний чек: 50$

**Расчет:**
```
Линия 1: 10 × 50$ × 10% = 50$
Линия 2: 30 × 50$ × 7% = 105$
Линия 3: 50 × 50$ × 3% = 75$
────────────────────────────
Итого: 230$ в месяц
```

При активном развитии сети доход растет экспоненциально.

### Вывод средств

- Минимальная сумма: 1,000₽
- Способы: карта, криптовалюта
- Срок: 1-3 рабочих дня

### Почему это выгодно

1. **Пассивный доход** — получаешь % даже когда спишь
2. **3 уровня** — зарабатываешь не только с прямых рефералов
3. **Без вложений** — нужна только первая покупка для активации
4. **Накопительный эффект** — чем больше сеть, тем выше доход

### Сравнение с конкурентами

| Параметр | PVNDORA | Типичный конкурент |
|----------|---------|-------------------|
| Уровней | 3 | 1 |
| Комиссия L1 | 10% | 5-10% |
| Комиссия L2 | 7% | — |
| Комиссия L3 | 3% | — |
| Мин. вывод | 1000₽ | 3000-5000₽ |

### Как начать

1. Сделай первую покупку в PVNDORA → уровень PROXY
2. Получи персональную ссылку в профиле
3. Делись ссылкой с друзьями и подписчиками
4. Получай 10% с каждой их покупки
5. Развивай сеть → открывай линии 2 и 3

---

## Сравнительная таблица: Дискаунт vs PVNDORA

| Параметр | Дискаунт | PVNDORA |
|----------|----------|---------|
| Цена | ~10$ | ~60$ |
| Гарантия | Нет (платная страховка) | Включена |
| Замены | Только со страховкой | Бесплатно |
| Поддержка | Минимальная | 24/7 |
| Партнерка L1 | Нет | 10% |
| Партнерка L2 | Нет | 7% (от 250$) |
| Партнерка L3 | Нет | 3% (от 1000$) |
| Баланс/вывод | Нет | Да (от 1000₽) |
| Интерфейс | Кнопки | Mini App + AI |
| Статистика | Базовая | Полная |

*При переходе в PVNDORA статистика из дисконта учитывается

---

## Техническая реализация

### Изменения в БД

```sql
-- 1. Добавить discount_price в products
ALTER TABLE products ADD COLUMN IF NOT EXISTS discount_price NUMERIC(10,2);

-- 2. Добавить source_channel в orders
ALTER TABLE orders ADD COLUMN IF NOT EXISTS source_channel TEXT DEFAULT 'premium';

-- 3. Добавить discount_tier_source в users
ALTER TABLE users ADD COLUMN IF NOT EXISTS discount_tier_source BOOLEAN DEFAULT FALSE;

-- 4. Таблица страховок
CREATE TABLE IF NOT EXISTS insurance_options (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id),
    duration_days INT NOT NULL,
    price_percent NUMERIC(5,2) NOT NULL,
    replacements_count INT DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Связь страховки с заказом
ALTER TABLE order_items ADD COLUMN IF NOT EXISTS insurance_id UUID REFERENCES insurance_options(id);

-- 6. Таблица замен (для отслеживания использованных замен)
CREATE TABLE IF NOT EXISTS insurance_replacements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_item_id UUID REFERENCES order_items(id),
    insurance_id UUID REFERENCES insurance_options(id),
    old_stock_item_id UUID REFERENCES stock_items(id),
    new_stock_item_id UUID REFERENCES stock_items(id),
    reason TEXT,
    -- Модерация (защита от абуза)
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'auto_approved')),
    rejection_reason TEXT,
    processed_by UUID REFERENCES users(id),
    processed_at TIMESTAMPTZ,
    -- Метаданные
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Индексы
CREATE INDEX IF NOT EXISTS idx_orders_source_channel ON orders(source_channel);
CREATE INDEX IF NOT EXISTS idx_users_discount_tier ON users(discount_tier_source);
CREATE INDEX IF NOT EXISTS idx_replacements_order_item ON insurance_replacements(order_item_id);
```

### View для аналитики миграции

```sql
CREATE OR REPLACE VIEW discount_migration_stats AS
SELECT 
    COUNT(DISTINCT CASE WHEN discount_tier_source THEN id END) AS total_discount_users,
    COUNT(DISTINCT CASE 
        WHEN discount_tier_source 
        AND EXISTS (
            SELECT 1 FROM orders o 
            WHERE o.user_id = users.id 
            AND o.source_channel = 'premium'
        ) 
        THEN id 
    END) AS migrated_users,
    ROUND(
        COUNT(DISTINCT CASE 
            WHEN discount_tier_source 
            AND EXISTS (
                SELECT 1 FROM orders o 
                WHERE o.user_id = users.id 
                AND o.source_channel = 'premium'
            ) 
            THEN id 
        END)::numeric / 
        NULLIF(COUNT(DISTINCT CASE WHEN discount_tier_source THEN id END), 0) * 100,
        2
    ) AS migration_rate_percent
FROM users;
```

### Промокоды для миграции

```sql
-- Расширение таблицы промокодов для персонализации
ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS 
    target_user_id UUID REFERENCES users(id);  -- Для кого создан (NULL = публичный)

ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS 
    source_trigger TEXT;  -- Триггер: 'issue_no_insurance', 'loyal_3_purchases', etc.

ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS 
    is_personal BOOLEAN DEFAULT FALSE;

-- Индекс для быстрого поиска персональных промокодов
CREATE INDEX IF NOT EXISTS idx_promo_codes_target_user ON promo_codes(target_user_id) 
WHERE target_user_id IS NOT NULL;
```

**Важно:** Промокоды генерируются персонально при выдаче оффера (см. раздел "Риски").

### Функция подсчета использованных замен

```sql
CREATE OR REPLACE FUNCTION count_replacements(p_order_item_id UUID)
RETURNS INT AS $$
BEGIN
    RETURN (
        SELECT COUNT(*) 
        FROM insurance_replacements 
        WHERE order_item_id = p_order_item_id
    );
END;
$$ LANGUAGE plpgsql;
```

---

## Метрики успеха

### KPI дискаунт-канала
| Метрика | Цель |
|---------|------|
| Заявки/день | 1000+ |
| Конверсия в покупку | 15-20% |
| Средний чек | 1200-1500₽ |
| Продажа страховок | 30-40% |

### KPI перелива
| Метрика | Цель |
|---------|------|
| Миграция в PVNDORA | 20-30% |
| Время до миграции | 7-14 дней |
| LTV мигрированного | x5-10 от дисконта |
| Использование промокодов | 60%+ |

### KPI PVNDORA
| Метрика | Цель |
|---------|------|
| Retention | 60%+ |
| Активация партнерки | 40%+ |
| Средний доход партнера | 5000₽/мес |

---

## Зацикленность экосистемы

### Путь клиента

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  [Поиск "ChatGPT дешево"]                                          │
│           │                                                         │
│           ▼                                                         │
│  ┌─────────────────┐                                               │
│  │  ДИСКАУНТ-БОТ   │ ◄─────────────────────────────────────┐       │
│  │  Покупка 950₽   │                                       │       │
│  └────────┬────────┘                                       │       │
│           │                                                 │       │
│     ┌─────┴─────┐                                          │       │
│     │           │                                          │       │
│     ▼           ▼                                          │       │
│ [Все ок]   [Проблема]                                      │       │
│     │           │                                          │       │
│     │           ▼                                          │       │
│     │    ┌──────────────┐                                  │       │
│     │    │ Есть страховка? │                               │       │
│     │    └──────┬───────┘                                  │       │
│     │      Да   │   Нет                                    │       │
│     │      │    │    │                                     │       │
│     │      ▼    │    ▼                                     │       │
│     │  [Замена] │  [Предложение PVNDORA]                   │       │
│     │      │    │         │                                │       │
│     │      │    │         ▼                                │       │
│     │      │    │    ┌─────────────┐                       │       │
│     │      │    │    │   PVNDORA   │                       │       │
│     │      │    │    │  Покупка    │                       │       │
│     │      │    │    └──────┬──────┘                       │       │
│     │      │    │           │                              │       │
│     │      │    │           ▼                              │       │
│     │      │    │    ┌─────────────┐                       │       │
│     │      │    │    │  ПАРТНЕРКА  │                       │       │
│     │      │    │    │  10%/7%/3%  │                       │       │
│     │      │    │    └──────┬──────┘                       │       │
│     │      │    │           │                              │       │
│     │      │    │           ▼                              │       │
│     │      │    │    [Приводит рефералов]                  │       │
│     │      │    │           │                              │       │
│     │      │    │           │                              │       │
│     ▼      ▼    ▼           ▼                              │       │
│  ┌──────────────────────────────────────┐                  │       │
│  │  Через 7 дней: информация о PVNDORA  │──────────────────┘       │
│  │  Через 3 покупки: персональный оффер │                          │
│  └──────────────────────────────────────┘                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Замкнутый цикл

1. **Захват трафика** → Дискаунт собирает дешевый трафик
2. **Конверсия** → Часть покупает страховку (привыкает к сервису)
3. **Проблемы** → При отлете → предложение PVNDORA
4. **Миграция** → Переход в PVNDORA с промокодом
5. **Партнерка** → Клиент становится партнером
6. **Рефералы** → Партнер приводит новых клиентов
7. **Цикл** → Новые клиенты начинают с дисконта или PVNDORA

### Ключевые точки зацикленности

| Точка | Механика |
|-------|----------|
| Дисконт → PVNDORA | Апселл, проблемы, время |
| PVNDORA → Партнерка | Автоматическая активация |
| Партнерка → Рефералы | Комиссия 10%/7%/3% |
| Рефералы → Дисконт/PVNDORA | Новые клиенты в воронку |

### Защита от утечки

- Клиент покупает на Авито → покупает у нас (мы контролируем Авито)
- Клиент ищет дешевле → находит наш дискаунт
- Клиент хочет гарантии → идет в PVNDORA
- Клиент хочет заработать → партнерка PVNDORA

---

## Риски и узкие места

### 1. Каннибализация трафика

**Проблема:** Если Дискаунт-бот слишком хорош, люди не пойдут в PVNDORA.

**Риск:** Страховка за +50% работает идеально — зачем платить $60?

**Решение: Разница в сервисе + скорости выдачи**

| Параметр | Дискаунт | PVNDORA |
|----------|----------|---------|
| Товар | Тот же | Тот же |
| Скорость выдачи | Очередь 1-4 часа | Мгновенно |
| Гарантия | Нет (платная страховка) | Включена |
| Замены | Ограничены (1-2 по страховке) | Неограничены |
| Поддержка | Нет | 24/7 |
| Партнерка | Нет | 10%/7%/3% |

**Позиционирование:**
- Дискаунт = "склад распродаж" — дешево, но на свой риск, без поддержки
- PVNDORA = "бутик" — премиум сервис, гарантии, возможность заработка

**Ключевые рычаги перелива:**
1. **Боль от отсутствия сервиса** — проблема с аккаунтом → нет замены → оффер PVNDORA
2. **Возможность заработка** — партнерка 10%/7%/3% только в PVNDORA
3. **Скорость** — в дискаунте очередь, в PVNDORA мгновенно

**Искусственная очередь в Дискаунте:**
```
Заказ принят.
Ожидайте выдачу в течение 1-4 часов.

Хочешь мгновенно? В PVNDORA — выдача сразу после оплаты.
[Перейти в PVNDORA]
```

**Реализация очереди:**
```python
async def discount_create_order(user_id, product_id):
    order = await db.create_order(user_id, product_id, source="discount")
    
    # Случайная задержка 1-4 часа
    delay_hours = random.uniform(1, 4)
    delay_seconds = int(delay_hours * 3600)
    
    # Отправляем в QStash с задержкой
    await qstash.publish(
        url=f"{BASE_URL}/api/workers/deliver-goods",
        body={"order_id": str(order.id)},
        delay=delay_seconds
    )
    
    return order, delay_hours
```

---

### 2. Абуз страховки

**Проблема:** Пользователи могут специально "ломать" аккаунты для получения новых и перепродажи.

**Риск:** Потеря маржи, дефицит стока.

**Решение: Модерация + лимиты**

```sql
-- Статус замены для модерации
ALTER TABLE insurance_replacements 
ADD COLUMN status TEXT DEFAULT 'pending' 
CHECK (status IN ('pending', 'approved', 'rejected', 'auto_approved'));

-- Причина отказа
ALTER TABLE insurance_replacements 
ADD COLUMN rejection_reason TEXT;

-- Кто обработал
ALTER TABLE insurance_replacements 
ADD COLUMN processed_by UUID REFERENCES users(id);
ADD COLUMN processed_at TIMESTAMPTZ;
```

**Логика автоматического одобрения:**
```python
async def process_replacement_request(order_item_id, reason):
    user = await get_user_by_order_item(order_item_id)
    
    # Проверка на абуз
    abuse_score = await calculate_abuse_score(user.telegram_id)
    
    if abuse_score < 30:
        # Автоматическое одобрение
        return await auto_approve_replacement(order_item_id)
    elif abuse_score < 70:
        # На модерацию
        return await queue_for_moderation(order_item_id)
    else:
        # Автоматический отказ
        return await auto_reject_replacement(order_item_id, "Подозрительная активность")

async def calculate_abuse_score(telegram_id) -> int:
    """Расчет риска абуза (0-100)"""
    score = 0
    
    # Частота замен за последние 30 дней
    recent_replacements = await count_recent_replacements(telegram_id, days=30)
    if recent_replacements > 3:
        score += 30
    elif recent_replacements > 1:
        score += 15
    
    # Процент замен от покупок
    total_purchases = await count_purchases(telegram_id)
    replacement_rate = recent_replacements / max(total_purchases, 1)
    if replacement_rate > 0.5:
        score += 40
    elif replacement_rate > 0.3:
        score += 20
    
    # Возраст аккаунта
    account_age_days = await get_account_age(telegram_id)
    if account_age_days < 7:
        score += 20
    elif account_age_days < 30:
        score += 10
    
    return min(score, 100)
```

**Лимиты:**
- Максимум 2 замены в месяц на пользователя (независимо от страховки)
- При превышении — только ручная модерация

---

### 3. Утечка промокодов

**Проблема:** Статические промокоды (MIGRATE50) утекут в паблик.

**Риск:** Пользователи PVNDORA, готовые платить $60, будут использовать скидку.

**Решение: Персональные одноразовые промокоды**

```sql
-- Расширение таблицы промокодов
ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS 
    target_user_id UUID REFERENCES users(id);  -- Для кого создан

ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS 
    source_trigger TEXT;  -- Триггер создания: 'issue_no_insurance', 'loyal_3_purchases', etc.

ALTER TABLE promo_codes ADD COLUMN IF NOT EXISTS 
    is_personal BOOLEAN DEFAULT FALSE;
```

**Генерация персонального промокода:**
```python
import secrets

async def generate_personal_promo(
    user_id: str,
    discount_percent: int,
    trigger: str,
    expires_days: int = 7
) -> str:
    """Генерирует персональный промокод"""
    
    # Формат: TRIGGER_USERID_RANDOM
    # Пример: REPLACE_abc123_X7K9
    code = f"{trigger}_{user_id[:6]}_{secrets.token_urlsafe(4).upper()}"
    
    await db.create_promo_code({
        "code": code,
        "discount_percent": discount_percent,
        "usage_limit": 1,  # Одноразовый
        "is_active": True,
        "is_personal": True,
        "target_user_id": user_id,
        "source_trigger": trigger,
        "expires_at": now + timedelta(days=expires_days)
    })
    
    return code

# Использование
promo = await generate_personal_promo(
    user_id=user.id,
    discount_percent=50,
    trigger="REPLACE",
    expires_days=7
)
# Результат: REPLACE_abc123_X7K9
```

**Валидация при использовании:**
```python
async def validate_promo_code(code: str, user_id: str) -> bool:
    promo = await db.get_promo_code(code)
    
    if not promo or not promo.is_active:
        return False
    
    if promo.expires_at and promo.expires_at < now:
        return False
    
    # Проверка персонального промокода
    if promo.is_personal and promo.target_user_id != user_id:
        return False  # Чужой промокод
    
    # Проверка лимита использований
    if promo.usage_limit:
        usage_count = await db.count_promo_usage(code)
        if usage_count >= promo.usage_limit:
            return False
    
    return True
```

---

### 4. Ценообразование страховки

**Проблема:** Страховка не должна быть слишком дешевой.

**Правило:** Страховка ≥ 50% от стоимости аккаунта в дисконте.

**Обновленные варианты:**

| Тип | Срок | Цена | Замены | Мин. цена |
|-----|------|------|--------|-----------|
| Базовая | 7 дней | +50% от цены | 1 | — |
| Расширенная | 14 дней | +80% от цены | 2 | — |

**Пример (ChatGPT Plus = 950₽ в дисконте):**
```
[Купить без страховки] — 950₽

[+] Страховка 7 дней — 475₽ (1 замена)
    Итого: 1,425₽

[+] Страховка 14 дней — 760₽ (2 замены)
    Итого: 1,710₽
```

**Сравнение с PVNDORA:**
```
Дискаунт + страховка 14 дней: 1,710₽ (2 замены, 14 дней)
PVNDORA: ~4,500₽ (неограниченные замены, полный срок, поддержка 24/7)
```

Разница в 2.6x оправдана качеством сервиса.

---

### 5. Техническая сложность двух интерфейсов

**Проблема:** Дискаунт — кнопочный бот, PVNDORA — WebApp.

**Риск:** Две кодовые базы фронтенда на одном бэкенде.

**Решение: Единый API, разные клиенты**

```
┌─────────────────────────────────────────────────────────┐
│                     SUPABASE                            │
│  (products, orders, users, stock_items, referrals)      │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              CORE BACKEND (FastAPI)                     │
│                                                         │
│  services/                                              │
│  ├── catalog.py      # get_products(), get_product()   │
│  ├── orders.py       # create_order(), deliver_order() │
│  ├── insurance.py    # process_replacement()           │
│  └── referrals.py    # get_referral_info()             │
│                                                         │
│  Единая логика для обоих ботов                         │
└───────────────────────┬─────────────────────────────────┘
                        │
          ┌─────────────┴─────────────┐
          │                           │
          ▼                           ▼
┌─────────────────────┐    ┌─────────────────────┐
│   ДИСКАУНТ-БОТ      │    │   PVNDORA           │
│   (aiogram)         │    │   (aiogram + WebApp)│
│                     │    │                     │
│   handlers/         │    │   handlers/         │
│   ├── catalog.py    │    │   ├── catalog.py    │
│   ├── purchase.py   │    │   ├── purchase.py   │
│   └── issues.py     │    │   └── support.py    │
│                     │    │                     │
│   Кнопочный UI      │    │   Mini App UI       │
└─────────────────────┘    └─────────────────────┘
```

**Принцип:** Бизнес-логика в `core/services/`, UI-логика в обработчиках бота.

**Пример единой функции выдачи:**
```python
# core/services/orders.py

async def deliver_order(order_id: str, source: str = "premium") -> DeliveryResult:
    """
    Единая функция выдачи товара.
    Вызывается и из Дискаунта, и из PVNDORA.
    """
    order = await db.get_order(order_id)
    
    # Резервируем товар из стока (один пул для обоих каналов)
    stock_item = await db.reserve_stock_item(product_id=order.product_id)
    
    # Обновляем статус заказа
    await db.update_order(order_id, {
        "status": "delivered",
        "stock_item_id": stock_item.id,
        "delivered_at": now,
        "source_channel": source
    })
    
    return DeliveryResult(
        order_id=order_id,
        credentials=stock_item.credentials,
        warranty_until=calculate_warranty(order, source)
    )
```

**Разница в вызове между каналами:**
```python
# PVNDORA: мгновенная выдача
async def pvndora_purchase(user_id, product_id):
    order = await create_order(user_id, product_id)
    await process_payment(order)
    result = await deliver_order(order.id, source="premium")  # Сразу
    return result

# Дискаунт: выдача через очередь
async def discount_purchase(user_id, product_id):
    order = await create_order(user_id, product_id)
    await process_payment(order)
    
    # Случайная задержка 1-4 часа
    delay_hours = random.uniform(1, 4)
    delay_seconds = int(delay_hours * 3600)
    
    # Отправляем в QStash с задержкой
    await qstash.publish(
        url=f"{BASE_URL}/api/workers/deliver-goods",
        body={"order_id": str(order.id), "source": "discount"},
        delay=delay_seconds
    )
    
    return f"Заказ принят. Выдача через ~{delay_hours:.1f} ч."
```

---

## Следующие шаги

### Фаза 1: Подготовка БД (1-2 недели)
- [ ] Добавить поле `discount_price` в products
- [ ] Создать таблицу `insurance_options` (с ценой ≥50%)
- [ ] Создать таблицу `insurance_replacements` (со статусом модерации)
- [ ] Добавить `source_channel` в orders
- [ ] Добавить `discount_tier_source` в users
- [ ] Расширить `promo_codes` (target_user_id, is_personal, source_trigger)
- [x] Исправить fallback значения комиссий в коде (10/7/3)

### Фаза 2: Дискаунт-бот (2-3 недели)
- [ ] Создать бота @ai_discount_bot
- [ ] Кнопочный интерфейс каталога
- [ ] Механика выбора страховки при покупке (+50%/+80%)
- [ ] Выдача через очередь QStash (задержка 1-4 часа)
- [ ] Кнопка "Проблема с аккаунтом" + обработчик
- [ ] Логика автоматической замены с anti-abuse проверкой

### Фаза 3: Офферы и перелив (1-2 недели)
- [ ] Сообщения после покупки (оффер партнерки)
- [ ] Офферы при проблемах (нет страховки / истекла / лимит)
- [ ] Генерация персональных промокодов (REPLACE_userId_XXX)
- [ ] Cron для отложенных сообщений (7 дней, 3 покупки)
- [ ] Валидация промокодов (проверка target_user_id)

### Фаза 4: Anti-abuse и модерация (1 неделя)
- [ ] Функция calculate_abuse_score()
- [ ] Очередь модерации замен в админке
- [ ] Лимит 2 замены/месяц на пользователя
- [ ] Логирование подозрительной активности

### Фаза 5: Аналитика (1 неделя)
- [ ] View `discount_migration_stats`
- [ ] Dashboard миграции в админке
- [ ] Отслеживание использования промокодов (персональных vs публичных)
- [ ] Метрики abuse_score по пользователям
- [ ] A/B тесты офферов

---

## Приложение A: Исправления в коде

### Проблемные места с неправильными fallback (исправлено ✅)

Все fallback значения обновлены с 20/10/5 на 10/7/3:

1. ✅ `core/services/domains/referral.py:42`
2. ✅ `core/services/database.py:351-353`
3. ✅ `core/routers/admin/referral.py:39-41`
4. ✅ `core/routers/webapp/profile.py:190-192`
5. ✅ `core/models.py:209`
6. ✅ `core/services/models.py:21`

---

## Приложение B: Текущие значения из БД

### referral_settings
```
level1_threshold_usd: 0
level2_threshold_usd: 250
level3_threshold_usd: 1000
level1_commission_percent: 10
level2_commission_percent: 7
level3_commission_percent: 3
```

### Карьерные уровни (career_levels)
```
LOCKED: 0$ — партнерка заблокирована
PROXY: первая покупка — линия 1 (10%)
OPERATOR: 250$ оборота — линия 2 (7%)
ARCHITECT: 1000$ оборота — линия 3 (3%)
```

---

## Приложение C: Шаблоны сообщений

### После успешной покупки
```
Заказ выполнен. Данные выше.

Хочешь зарабатывать на AI-аккаунтах?

В PVNDORA — партнерская программа:
• 10% с каждого приведенного клиента
• 7% с клиентов твоих рефералов  
• 3% с третьей линии

Пример: 10 рефералов купили на 50,000₽ = 5,000₽ тебе

[Подключить партнерку]
```

### При проблеме без страховки
```
В дисконте замены не предусмотрены.

Варианты:
1. Купить новый аккаунт со страховкой
2. Перейти в PVNDORA — гарантия включена

Промокод REPLACE50 — скидка 50%

[Купить в PVNDORA]
[Купить здесь со страховкой]
```

### После 3 покупок
```
3 покупки в дисконте — ты постоянный клиент.

Персональное предложение:
• Скидка 30% на первый заказ в PVNDORA
• Партнерка 10%/7%/3%
• Гарантия на все аккаунты

Промокод LOYAL30

[Активировать]
```

---

## Приложение D: Pre-Deploy Checklist

Финальный чек-лист перед запуском дискаунт-канала.

### 1. Логистика: "Голод" склада (Supply Chain)

**Проблема:** Что если в 3 ночи придет 50 заказов, а аккаунты кончатся?

**Текущее решение в PVNDORA:**
- ✅ Автоматическая конвертация в prepaid при отсутствии стока
- ✅ `refund_to_balance()` если товар недоступен при выдаче
- ✅ Race condition handling (retry с другим stock_item)

```python
# core/services/notifications.py
stock_item = await db.get_available_stock_item(product_id)
if not stock_item:
    await self._refund_to_balance(order, user, language, "Out of stock")
    return False
```

**Дополнительно для дискаунта:**
- [ ] Алерт админу при `stock_count < 5` для популярных товаров
- [ ] Конвертация в prepaid при отсутствии стока (уже работает)
- [ ] Cron-задача проверки стока каждые 30 минут

**Важно:** Не скрываем товары при отсутствии стока — они автоматически становятся предзаказами. Админ получает алерт и должен пополнить сток.

```sql
-- View для мониторинга критического стока (алерт админу)
CREATE OR REPLACE VIEW low_stock_alert AS
SELECT 
    p.id,
    p.name,
    COUNT(si.id) as available_count,
    CASE 
        WHEN COUNT(si.id) = 0 THEN 'prepaid_only'
        WHEN COUNT(si.id) < 3 THEN 'critical'
        WHEN COUNT(si.id) < 5 THEN 'low'
        ELSE 'ok'
    END as stock_status
FROM products p
LEFT JOIN stock_items si ON si.product_id = p.id 
    AND si.status = 'available' 
    AND si.is_sold = FALSE
WHERE p.status = 'active'
GROUP BY p.id, p.name
HAVING COUNT(si.id) < 5;
```

**Логика предзаказа (уже реализовано в PVNDORA):**
```python
# При отсутствии стока заказ становится prepaid
available_stock = await db.get_available_stock_count(product_id)
if available_stock < quantity:
    instant_qty = available_stock
    prepaid_qty = quantity - available_stock
    # Клиент получает сообщение о сроках изготовления
```

---

### 2. Финансы: Платежная система

**Платежный шлюз:** CrystalPay (единственный)

CrystalPay поддерживает:
- Криптовалюты (Bitcoin, USDT, ETH) — не банят
- Фиатные методы (СБП, карты) — через партнеров

**Преимущества:**
- Единая интеграция
- Крипто + фиат в одном месте
- Минимальный риск блокировки

**Действия:**
- [ ] Гайд "Как платить криптой" в FAQ/боте (для пользователей без опыта)
- [ ] Мониторинг статуса CrystalPay (алерт при сбоях)

---

### 3. "Бессмертие" в Telegram (Ban Hammer)

**Риск:** Бан бота = потеря доступа к telegram_id пользователей.

**Решения:**

#### 3.1. Обязательная подписка на канал

- [ ] Middleware проверки подписки на канал перед доступом в бота
- [ ] Канал как backup-канал связи (банят реже ботов)

```python
# core/bot/middlewares.py — новый middleware

class ChannelSubscriptionMiddleware(BaseMiddleware):
    REQUIRED_CHANNEL = "@pvndora_news"  # или дискаунт-канал
    
    async def __call__(self, handler, event, data):
        user = event.from_user
        bot = data.get("bot")
        
        # Проверяем подписку
        try:
            member = await bot.get_chat_member(
                chat_id=self.REQUIRED_CHANNEL, 
                user_id=user.id
            )
            if member.status in ["left", "kicked"]:
                # Не подписан — просим подписаться
                await event.answer(
                    "Для доступа подпишись на канал:\n"
                    f"{self.REQUIRED_CHANNEL}\n\n"
                    "После подписки нажми /start",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text="Подписаться",
                            url=f"https://t.me/{self.REQUIRED_CHANNEL[1:]}"
                        )
                    ]])
                )
                return  # Не пускаем дальше
        except Exception:
            pass  # Если ошибка — пропускаем проверку
        
        return await handler(event, data)
```

#### 3.2. Резервные боты

- [ ] Создать 2-3 резервных бота с готовыми токенами
- [ ] Скрипт быстрой миграции (смена BOT_TOKEN в .env)
- [ ] Пост в канал при смене бота

```bash
# Быстрая миграция на резервный бот
# 1. Обновить TELEGRAM_TOKEN в Vercel
# 2. Перерегистрировать webhook
python scripts/set_webhook.py
# 3. Опубликовать в канале ссылку на нового бота
```

---

### 4. Abuse: Конкуренты и школьники

**Риск:** Покупка со страховкой → меняет пароль сам → "проблема" → получает новый → повторяет 5 раз.

**Решения (уже в документе):**
- ✅ `calculate_abuse_score()` — скоринг риска
- ✅ Модерация замен с полем `status` 
- ✅ Лимит 2 замены/месяц

**Дополнительно:**

#### 4.1. Холдирование для новых пользователей

```python
async def process_replacement_request(order_item_id, reason):
    user = await get_user_by_order_item(order_item_id)
    
    # Первая покупка — всегда на модерацию
    user_orders_count = await count_user_orders(user.telegram_id)
    if user_orders_count <= 1:
        return await queue_for_moderation(
            order_item_id, 
            reason="Первая покупка — ручная проверка"
        )
    
    # Далее стандартная логика abuse_score
    abuse_score = await calculate_abuse_score(user.telegram_id)
    # ...
```

#### 4.2. Blacklist

```sql
-- Таблица блокировок
CREATE TABLE IF NOT EXISTS user_restrictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    restriction_type TEXT NOT NULL CHECK (restriction_type IN (
        'replacement_blocked',  -- Замены заблокированы
        'insurance_blocked',    -- Страховка заблокирована
        'purchase_blocked'      -- Покупки заблокированы
    )),
    reason TEXT,
    expires_at TIMESTAMPTZ,  -- NULL = бессрочно
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Проверка перед выдачей замены
CREATE OR REPLACE FUNCTION can_request_replacement(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN NOT EXISTS (
        SELECT 1 FROM user_restrictions
        WHERE user_id = p_user_id
        AND restriction_type = 'replacement_blocked'
        AND (expires_at IS NULL OR expires_at > NOW())
    );
END;
$$ LANGUAGE plpgsql;
```

---

### 5. Юридическая защита (Disclaimer)

**Текущее решение в PVNDORA:**
- ✅ Страница Terms of Service в WebApp
- ✅ Команда `/terms` в боте
- ✅ Ссылка на ToS при регистрации

**Дополнительно для дискаунта (кнопочный бот):**

#### 5.1. Принятие оферты при /start

```python
@router.message(Command("start"))
async def cmd_start(message: Message, db_user: User):
    # Проверяем, принял ли оферту
    if not db_user.terms_accepted:
        await message.answer(
            "Добро пожаловать в AI Discount!\n\n"
            "Перед началом ознакомься с условиями:\n"
            "• Товары без гарантии\n"
            "• Возврат невозможен\n"
            "• Страховка оплачивается отдельно\n\n"
            "Продолжая, ты принимаешь условия.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="✅ Принимаю условия",
                    callback_data="accept_terms"
                )],
                [InlineKeyboardButton(
                    text="📄 Читать полностью",
                    url="https://pvndora.app/terms"
                )]
            ])
        )
        return
    
    # Обычный /start
    await show_catalog(message, db_user)

@router.callback_query(F.data == "accept_terms")
async def accept_terms_callback(callback: CallbackQuery, db_user: User):
    await db.update_user_terms_accepted(db_user.id, True)
    await callback.answer("Условия приняты!")
    await show_catalog(callback.message, db_user)
```

#### 5.2. Поле в БД

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS 
    terms_accepted BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS 
    terms_accepted_at TIMESTAMPTZ;
```

---

### 6. Локализация (2 языка)

**Текущее решение в PVNDORA:**
- ✅ 9 языков в `locales/*.json`
- ✅ Автоопределение по `language_code` из Telegram
- ✅ `detect_language()` в middleware

**Для дискаунт-бота:**
- [ ] Минимум ru/en (как в PVNDORA)
- [ ] Использовать существующую систему `core/i18n/`

```python
# Использование в обработчиках
from core.i18n import get_text

@router.message(Command("start"))
async def cmd_start(message: Message, db_user: User):
    lang = db_user.language_code  # Автоопределено в middleware
    
    await message.answer(
        get_text("discount.welcome", lang),
        reply_markup=get_catalog_keyboard(lang)
    )
```

---

### Итоговый Pre-Deploy Checklist

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 1 | Алерт при низком стоке | 🔴 HIGH | [ ] |
| 2 | Prepaid при stock=0 | 🔴 HIGH | ✅ (уже работает) |
| 3 | Гайд "Как платить криптой" | 🟡 MED | [ ] |
| 4 | Middleware подписки на канал | 🟡 MED | [ ] |
| 5 | Резервные токены ботов | 🟡 MED | [ ] |
| 6 | Холдирование замен для новичков | 🔴 HIGH | [ ] |
| 7 | Таблица user_restrictions | 🟡 MED | [ ] |
| 8 | Принятие оферты при /start | 🔴 HIGH | [ ] |
| 9 | Поле terms_accepted в users | 🔴 HIGH | [ ] |
| 10 | Локализация ru/en | 🔴 HIGH | ✅ (наследуется) |
