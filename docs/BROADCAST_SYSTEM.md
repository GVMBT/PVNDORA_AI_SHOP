# PVNDORA — Система рассылок (Broadcast)

## Концепция

Кастомные рассылки с медиа и кнопками для международной аудитории.

---

## Архитектура

### Вариант 1: Шаблоны в БД (Рекомендуемый)

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Admin Panel    │ ──▶  │  Supabase       │ ──▶  │  QStash Worker  │
│  (Create/Edit)  │      │  broadcast_msgs │      │  (Send batch)   │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

**Таблица `broadcast_messages`:**
```sql
CREATE TABLE broadcast_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,           -- 'new_year_2026', 'black_friday'
  
  -- Контент по языкам (JSONB)
  content JSONB NOT NULL,              -- {ru: {...}, en: {...}, ...}
  
  -- Медиа
  media_type TEXT,                     -- 'photo', 'video', 'animation'
  media_file_id TEXT,                  -- Telegram file_id (универсален для всех языков)
  media_url TEXT,                      -- Fallback URL если нет file_id
  
  -- Кнопки (JSONB)
  buttons JSONB,                       -- [{text: {ru: "...", en: "..."}, url: "..."}]
  
  -- Таргетинг
  target_audience TEXT DEFAULT 'all',  -- 'all', 'active', 'inactive', 'vip', 'new'
  target_languages TEXT[],             -- NULL = все, ['ru', 'en'] = только эти
  
  -- Статус
  status TEXT DEFAULT 'draft',         -- 'draft', 'scheduled', 'sending', 'sent'
  scheduled_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  sent_count INT DEFAULT 0,
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  created_by UUID REFERENCES users(id)
);
```

**Пример контента:**
```json
{
  "ru": {
    "text": "🎄 <b>С Новым Годом!</b>\n\nСпецпредложения до 50%",
    "parse_mode": "HTML"
  },
  "en": {
    "text": "🎄 <b>Happy New Year!</b>\n\nSpecial offers up to 50%",
    "parse_mode": "HTML"
  },
  "de": {
    "text": "🎄 <b>Frohes Neues Jahr!</b>\n\nSonderangebote bis zu 50%",
    "parse_mode": "HTML"
  }
}
```

**Пример кнопок:**
```json
[
  {
    "text": {"ru": "🎁 К предложениям", "en": "🎁 View Offers", "de": "🎁 Angebote"},
    "url": "https://t.me/pvndora_ai_bot?start=promo_ny2026"
  },
  {
    "text": {"ru": "🛒 Каталог", "en": "🛒 Catalog", "de": "🛒 Katalog"},
    "web_app": {"url": "https://pvndora.com/catalog"}
  }
]
```

---

### Вариант 2: JSON-файлы в репозитории

```
broadcasts/
├── templates/
│   ├── new_year_2026.json
│   ├── black_friday.json
│   └── product_launch.json
└── media/
    └── new_year_banner.jpg
```

**Плюсы:** Версионирование через Git
**Минусы:** Требует деплой для изменений

---

## API для рассылок

### POST /api/admin/broadcast

**Запуск рассылки:**
```json
{
  "slug": "new_year_2026",
  // или inline контент:
  "content": {
    "ru": {"text": "..."},
    "en": {"text": "..."}
  },
  "media_url": "https://...",
  "buttons": [...],
  "target_audience": "active",
  "target_languages": ["ru", "en"],
  "schedule_at": "2026-01-01T00:00:00Z"  // null = сразу
}
```

### GET /api/admin/broadcast/{id}/status

**Статус рассылки:**
```json
{
  "id": "...",
  "status": "sending",
  "total": 1500,
  "sent": 890,
  "failed": 12,
  "progress": 59.3
}
```

---

## Worker для отправки

```python
@router.post("/send-broadcast")
async def worker_send_broadcast(request: Request):
    """
    QStash Worker: Send broadcast message to batch of users.
    
    Accepts:
    - broadcast_id: ID рассылки
    - user_ids: Batch пользователей (50-100 за раз)
    """
    data = await verify_qstash(request)
    broadcast_id = data.get("broadcast_id")
    user_ids = data.get("user_ids", [])
    
    db = get_database()
    bot = get_bot()
    
    # Получить шаблон
    broadcast = db.client.table("broadcast_messages").select("*").eq("id", broadcast_id).single().execute()
    content = broadcast.data["content"]
    buttons = broadcast.data.get("buttons", [])
    media_file_id = broadcast.data.get("media_file_id")
    media_type = broadcast.data.get("media_type")
    
    sent = 0
    failed = 0
    
    for user_id in user_ids:
        # Получить язык пользователя
        user = db.client.table("users").select("telegram_id, language_code").eq("id", user_id).single().execute()
        lang = user.data.get("language_code", "en")
        
        # Fallback на английский если нет перевода
        msg = content.get(lang) or content.get("en") or list(content.values())[0]
        text = msg["text"]
        parse_mode = msg.get("parse_mode", "HTML")
        
        # Построить клавиатуру
        keyboard = build_keyboard(buttons, lang)
        
        try:
            if media_file_id and media_type == "photo":
                await bot.send_photo(
                    chat_id=user.data["telegram_id"],
                    photo=media_file_id,
                    caption=text,
                    parse_mode=parse_mode,
                    reply_markup=keyboard
                )
            elif media_file_id and media_type == "video":
                await bot.send_video(
                    chat_id=user.data["telegram_id"],
                    video=media_file_id,
                    caption=text,
                    parse_mode=parse_mode,
                    reply_markup=keyboard
                )
            else:
                await bot.send_message(
                    chat_id=user.data["telegram_id"],
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=keyboard
                )
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast to {user_id} failed: {e}")
        
        await asyncio.sleep(0.05)  # Rate limiting
    
    # Обновить статистику
    db.client.table("broadcast_messages").update({
        "sent_count": broadcast.data["sent_count"] + sent
    }).eq("id", broadcast_id).execute()
    
    return {"sent": sent, "failed": failed}
```

---

## Построение клавиатуры

```python
def build_keyboard(buttons: list, lang: str) -> InlineKeyboardMarkup:
    """Build localized keyboard from button config."""
    if not buttons:
        return None
    
    rows = []
    for btn in buttons:
        text = btn["text"].get(lang) or btn["text"].get("en") or list(btn["text"].values())[0]
        
        if "url" in btn:
            rows.append([InlineKeyboardButton(text=text, url=btn["url"])])
        elif "web_app" in btn:
            rows.append([InlineKeyboardButton(text=text, web_app=WebAppInfo(url=btn["web_app"]["url"]))])
        elif "callback_data" in btn:
            rows.append([InlineKeyboardButton(text=text, callback_data=btn["callback_data"])])
    
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

---

## Таргетинг аудитории

| Аудитория | Условие |
|-----------|---------|
| `all` | Все пользователи (is_banned=false, do_not_disturb=false) |
| `active` | last_activity_at > 7 дней назад |
| `inactive` | last_activity_at < 7 дней назад |
| `vip` | is_vip_partner=true |
| `new` | created_at > 30 дней назад |
| `buyers` | Есть хотя бы 1 заказ |
| `non_buyers` | Нет заказов |

---

## Медиа: file_id vs URL

### Рекомендуемый подход: file_id

1. **Первая загрузка:** Отправить медиа себе или в тестовый чат
2. **Сохранить file_id:** Telegram возвращает уникальный file_id
3. **Использовать в рассылках:** file_id работает быстрее и надёжнее

```python
# Получить file_id после первой отправки
message = await bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=open("banner.jpg", "rb"))
file_id = message.photo[-1].file_id
# Сохранить file_id в БД для будущих рассылок
```

### Fallback: URL

Если file_id нет, Telegram скачает файл по URL. Медленнее, но работает.

---

## Пример рассылки: Новый Год

```json
{
  "slug": "new_year_2026",
  "content": {
    "ru": {
      "text": "🎄 <b>С Новым Годом, {name}!</b>\n\n🎁 Дарим <b>-30%</b> на всё до 10 января!\n\nПромокод: <code>NY2026</code>\n\n💎 Успей воспользоваться!",
      "parse_mode": "HTML"
    },
    "en": {
      "text": "🎄 <b>Happy New Year, {name}!</b>\n\n🎁 Get <b>-30%</b> off everything until Jan 10!\n\nPromo code: <code>NY2026</code>\n\n💎 Don't miss out!",
      "parse_mode": "HTML"
    }
  },
  "media_type": "photo",
  "media_file_id": "AgACAgIAAxkBAAI...",
  "buttons": [
    {
      "text": {"ru": "🛒 К покупкам", "en": "🛒 Shop Now"},
      "web_app": {"url": "https://pvndora.com/catalog?promo=NY2026"}
    }
  ],
  "target_audience": "all",
  "target_languages": null
}
```

---

## Admin UI (будущее)

```
┌─────────────────────────────────────────────────────────────────┐
│ 📢 НОВАЯ РАССЫЛКА                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Название: [New Year 2026________________]                       │
│                                                                 │
│ ┌─── Контент ─────────────────────────────────────────────────┐ │
│ │ 🇷🇺 RU │ 🇬🇧 EN │ 🇩🇪 DE │ + Добавить язык                    │ │
│ ├─────────────────────────────────────────────────────────────┤ │
│ │ 🎄 <b>С Новым Годом!</b>                                    │ │
│ │                                                             │ │
│ │ Дарим -30% на всё!                                         │ │
│ │ Промокод: NY2026                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ 📷 Медиа: [banner_ny2026.jpg] [Загрузить]                      │
│                                                                 │
│ 🔘 Кнопки:                                                      │
│ [🛒 К покупкам] → webapp:/catalog?promo=NY2026   [✕]           │
│ [+ Добавить кнопку]                                            │
│                                                                 │
│ 🎯 Аудитория: [Все пользователи ▼]                             │
│ 🌐 Языки: [🇷🇺 RU] [🇬🇧 EN] [🇩🇪 DE]                              │
│                                                                 │
│ ⏰ Отправить: (○) Сейчас  (●) По расписанию: [01.01.2026 00:00]│
│                                                                 │
│ [Предпросмотр]  [Сохранить черновик]  [🚀 Отправить]           │
└─────────────────────────────────────────────────────────────────┘
```

---

## TODO

- [ ] Создать таблицу `broadcast_messages`
- [ ] Создать worker `/api/workers/send-broadcast`
- [ ] Добавить endpoint `/api/admin/broadcast`
- [ ] Реализовать построение локализованной клавиатуры
- [ ] Добавить поддержку персонализации (`{name}`, `{balance}`)
- [ ] Admin UI для создания рассылок
