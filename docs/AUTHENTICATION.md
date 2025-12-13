# Аутентификация в PVNDORA

## Обзор

PVNDORA поддерживает два режима аутентификации:
1. **Telegram Mini App** - для мобильных и десктопных клиентов Telegram
2. **Web Browser** - для доступа через обычный браузер

## Архитектура

### 1. Telegram Mini App Authentication

**Механизм:** Использует `initData` от Telegram WebApp SDK.

**Поток:**
1. Telegram WebApp предоставляет `initData` через `window.Telegram.WebApp.initData`
2. Frontend отправляет `initData` в заголовке `X-Init-Data` или `Authorization: tma <initData>`
3. Backend валидирует `initData` через Telegram Bot API
4. Если валидно → пользователь аутентифицирован

**Код:**
- Frontend: `src/utils/auth.ts`, `src/hooks/useApi.js`
- Backend: `core/auth/telegram.py::verify_telegram_auth()`

### 2. Web Browser Authentication

**Механизм:** Session tokens (HMAC-SHA256 signed).

**Поток:**
1. Пользователь аутентифицируется через Telegram Login Widget (`/api/webapp/auth/telegram-login`)
2. Backend создаёт session token через `create_web_session()`
3. Token сохраняется в `localStorage` как `pvndora_session`
4. Frontend отправляет token в заголовке `Authorization: Bearer <token>`
5. Backend валидирует token через `verify_web_session_token()`

**Код:**
- Frontend: `src/utils/auth.ts`, `src/components/new/LoginPage.tsx`
- Backend: `core/auth/session.py`, `core/routers/webapp/auth.py`

## Утилиты (Shared Code)

**Файл:** `src/utils/auth.ts`

**Функции:**
- `persistSessionTokenFromQuery()` - извлекает token из URL query и сохраняет в localStorage
- `verifySessionToken(token)` - проверяет token с бэкендом (правильная обработка ошибок)
- `getSessionToken()` - получает token из localStorage
- `saveSessionToken(token)` - сохраняет token в localStorage
- `removeSessionToken()` - удаляет token из localStorage

**Использование:**
```typescript
import { verifySessionToken, saveSessionToken } from '../../utils/auth';

// Проверка сессии
const result = await verifySessionToken(token);
if (result?.valid) {
  // Пользователь аутентифицирован
}

// Сохранение токена
saveSessionToken(data.session_token);
```

## Backend Endpoints

### POST `/api/webapp/auth/telegram-login`

Аутентификация через Telegram Login Widget.

**Request:**
```json
{
  "id": 123456789,
  "first_name": "John",
  "username": "johndoe",
  "auth_date": 1234567890,
  "hash": "..."
}
```

**Response:**
```json
{
  "session_token": "eyJ...",
  "user": {
    "id": 123456789,
    "username": "johndoe",
    "first_name": "John",
    "is_admin": false
  }
}
```

### POST `/api/webapp/auth/verify-session`

Проверка валидности session token.

**Request:**
```json
{
  "session_token": "eyJ..."
}
```

**Response (valid):**
```json
{
  "valid": true,
  "user": {
    "telegram_id": 123456789,
    "username": "johndoe",
    "is_admin": false
  }
}
```

**Response (invalid):**
```json
{
  "detail": "Invalid session or expired"
}
```
Status: 401

## Обработка Ошибок

### Frontend

**Правильная обработка:**
```typescript
// ✅ Правильно - проверяем response.ok перед парсингом JSON
const response = await fetch('/api/webapp/auth/verify-session', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ session_token: token }),
});

if (!response.ok) {
  // Пытаемся получить JSON ошибки
  try {
    const errorData = await response.json();
    console.error('Error:', errorData.detail);
  } catch {
    // Если не JSON, читаем текст
    const text = await response.text();
    console.error('Non-JSON error:', text);
  }
  return null;
}

const data = await response.json();
```

**Неправильно:**
```typescript
// ❌ Неправильно - парсим JSON без проверки response.ok
const response = await fetch(...);
const data = await response.json(); // Ошибка если сервер вернул HTML/текст!
```

### Backend

Все endpoints возвращают JSON ошибки через `HTTPException`:
```python
raise HTTPException(status_code=401, detail="Invalid session or expired")
```

FastAPI автоматически оборачивает это в JSON:
```json
{"detail": "Invalid session or expired"}
```

## Session Token Format

**Структура:** `{payload}.{signature}`

**Payload (Base64URL):**
```json
{
  "user_id": "uuid",
  "telegram_id": 123456789,
  "username": "johndoe",
  "is_admin": false,
  "exp": 1234567890  // Unix timestamp
}
```

**Signature:** HMAC-SHA256(payload, secret)

**TTL:** 30 дней (настраивается в `core/auth/session.py`)

## Security

1. **HMAC Verification:** Все токены подписываются HMAC-SHA256
2. **Expiration Check:** Проверка времени истечения на каждый запрос
3. **Secret Key:** Хранится в `SESSION_SECRET` env variable
4. **Token Storage:** localStorage (клиентская сторона)
5. **HTTPS Only:** В production все запросы должны быть через HTTPS

## Troubleshooting

### Ошибка: "Unexpected token 'A', ... is not valid JSON"

**Причина:** Сервер вернул не-JSON ответ (HTML страницу ошибки), но код пытается парсить как JSON.

**Решение:** Использовать `verifySessionToken()` из `src/utils/auth.ts`, который правильно обрабатывает ошибки.

### Ошибка: "Invalid session token"

**Причины:**
1. Token истёк (TTL 30 дней)
2. Неверная подпись
3. Token повреждён

**Решение:** Повторная аутентификация через Telegram Login Widget.

### Дублирование кода

Все функции аутентификации должны использовать утилиты из `src/utils/auth.ts`:
- ✅ `verifySessionToken()` - вместо прямого fetch
- ✅ `getSessionToken()` - вместо `localStorage.getItem()`
- ✅ `saveSessionToken()` - вместо `localStorage.setItem()`
- ✅ `removeSessionToken()` - вместо `localStorage.removeItem()`

## Миграция со старого кода

**Было (дублирование):**
```typescript
// В LoginPage.tsx
fetch('/api/webapp/auth/verify-session', ...)
  .then(r => r.json())  // ❌ Ошибка если не JSON

// В NewApp.tsx  
fetch('/api/webapp/auth/verify-session', ...)
  .then(r => r.json())  // ❌ Дублирование
```

**Стало (общий код):**
```typescript
// Используем общую утилиту везде
import { verifySessionToken } from '../../utils/auth';

const result = await verifySessionToken(token);
if (result?.valid) {
  // Успех
}
```
