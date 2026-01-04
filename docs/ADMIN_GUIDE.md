# Админ-руководство PVNDORA

## 1. Добавление администратора

Чтобы добавить нового администратора в систему, нужно обновить поле `is_admin` в таблице `users`.

### Способ 1: Через Supabase Dashboard (SQL Editor)

1. Откройте Supabase Dashboard → SQL Editor
2. Выполните SQL-запрос (замените `YOUR_TELEGRAM_ID` на реальный Telegram ID пользователя):

```sql
UPDATE users 
SET is_admin = true 
WHERE telegram_id = YOUR_TELEGRAM_ID;
```

**Как узнать Telegram ID:**
- Отправьте `/start` боту `@userinfobot` в Telegram
- Или используйте `@pvndora_ai_bot` - ваш ID будет в логах при первой авторизации

### Способ 2: Через MCP Supabase

```sql
-- Замените YOUR_TELEGRAM_ID на реальный ID
UPDATE users 
SET is_admin = true 
WHERE telegram_id = YOUR_TELEGRAM_ID;
```

### Проверка

После добавления администратора:
1. Выйдите из админ-панели (если были авторизованы)
2. Авторизуйтесь заново через Telegram Login Widget
3. Должен открыться доступ к админ-панели

---

## 2. Отправка сообщений/постов в ботах (Broadcast)

В системе есть API для массовой рассылки сообщений пользователям через оба бота (main и discount).

### API Endpoint

**POST** `/api/admin/broadcast`

### Параметры запроса

```json
{
  "message": "Текст сообщения (HTML поддерживается)",
  "target_bot": "main" | "discount" | "all",
  "filter_language": "ru" | "en" | null,  // опционально
  "filter_has_orders": true | false | null,  // опционально
  "preview_only": false,  // если true - только подсчёт, без отправки
  "parse_mode": "HTML" | "Markdown"
}
```

### Примеры использования

#### Пример 1: Рассылка во все боты (все пользователи)

```bash
curl -X POST https://your-domain.vercel.app/api/admin/broadcast \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "<b>Важное обновление!</b>\n\nМы добавили новые функции...",
    "target_bot": "all",
    "parse_mode": "HTML"
  }'
```

#### Пример 2: Только русскоязычным пользователям в discount-боте

```bash
curl -X POST https://your-domain.vercel.app/api/admin/broadcast \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "<b>Скидка 20%!</b>\n\nТолько сегодня...",
    "target_bot": "discount",
    "filter_language": "ru",
    "parse_mode": "HTML"
  }'
```

#### Пример 3: Только пользователям с покупками (main bot)

```bash
curl -X POST https://your-domain.vercel.app/api/admin/broadcast \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "<b>Спасибо за покупки!</b>\n\nВаш VIP-статус активирован...",
    "target_bot": "main",
    "filter_has_orders": true,
    "parse_mode": "HTML"
  }'
```

#### Пример 4: Предпросмотр (подсчёт пользователей без отправки)

```bash
curl -X POST https://your-domain.vercel.app/api/admin/broadcast \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Тестовое сообщение",
    "target_bot": "all",
    "preview_only": true
  }'
```

**Ответ:**
```json
{
  "target_count": 150,
  "sent_count": 0,
  "failed_count": 0,
  "failed_user_ids": [],
  "preview_only": true
}
```

### Статистика аудитории

**GET** `/api/admin/broadcast/stats`

Получить статистику по аудитории перед рассылкой:

```bash
curl https://your-domain.vercel.app/api/admin/broadcast/stats?target_bot=all \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

**Ответ:**
```json
{
  "total_users": 1000,
  "by_language": {
    "ru": 600,
    "en": 400
  },
  "with_orders": 250,
  "by_bot": {
    "main": 800,
    "discount": 200
  }
}
```

### Поддержка HTML в сообщениях

Telegram поддерживает HTML форматирование:

- `<b>жирный</b>` → **жирный**
- `<i>курсив</i>` → *курсив*
- `<code>код</code>` → `код`
- `<a href="url">ссылка</a>` → [ссылка](url)
- `\n` → перенос строки

### Ограничения

- Максимальная длина сообщения: 4096 символов
- Рассылка выполняется последовательно (не мгновенно для больших аудиторий)
- Telegram API имеет лимит: ~30 сообщений в секунду на бот

---

## 3. Страница Migration в админке

Страница Migration показывает статистику миграции пользователей из discount-бота в основной PVNDORA бот.

### Доступ

Админ-панель → боковое меню → **"Migration"**

### Метрики

- **Discount Users** - общее количество пользователей discount-бота
- **Migrated Users** - пользователи, которые сделали заказы в обоих ботах
- **Migration Rate** - процент миграции
- **Discount Orders** - количество заказов в discount-боте
- **Discount Revenue** - выручка от discount-канала
- **PVNDORA Orders** - заказы в PVNDORA от пользователей discount-бота
- **Promos Generated** - количество сгенерированных промокодов
- **Promo Conversion** - процент использования промокодов

### Графики

- **Migration Trend** - тренд миграции за последние 14 дней (график)
- **Top Migrating Products** - товары, которые чаще всего покупают мигрировавшие пользователи

### Периоды

Переключение между периодами: 7 дней, 30 дней, 90 дней (кнопки в правом верхнем углу)
