# Архитектурные паттерны и guidelines

**Дата создания:** 2025-12-15  
**Цель:** Документировать принятые архитектурные решения и guidelines для разработки

---

## 📋 СОДЕРЖАНИЕ

1. [Lazy Imports Pattern](#lazy-imports-pattern)
2. [Dependency Injection](#dependency-injection)
3. [Singleton Pattern](#singleton-pattern)
4. [Barrel Exports](#barrel-exports)
5. [Guidelines по добавлению новых модулей](#guidelines-по-добавлению-новых-модулей)

---

## 🔄 LAZY IMPORTS PATTERN

### Когда использовать Lazy Imports?

**Используйте lazy imports когда:**
- ✅ Модуль тяжелый (AI, большие библиотеки)
- ✅ Модуль используется не всегда (условная загрузка)
- ✅ Модуль может вызвать циклические зависимости
- ✅ Оптимизация cold start для Vercel serverless

**НЕ используйте lazy imports когда:**
- ❌ Модуль легкий и используется часто
- ❌ Нужна проверка импорта на этапе загрузки
- ❌ Модуль критичен для инициализации приложения

### Примеры реализации

#### 1. Lazy в `core/__init__.py` (через `__getattr__`)

**Использование:** Для основных инфраструктурных компонентов

```python
# core/__init__.py
def __getattr__(name):
    if name == "get_supabase":
        from core.db import get_supabase
        return get_supabase
    # ...
```

**Когда использовать:**
- Критичные инфраструктурные компоненты (DB, Redis, QStash)
- Используются везде, но не должны загружаться при импорте модуля

#### 2. Lazy в функциях (router deps)

**Использование:** Для сервисов с зависимостями

```python
# core/routers/deps.py
def get_notification_service():
    global _notification_service
    if _notification_service is None:
        from core.services.notifications import NotificationService
        _notification_service = NotificationService()
    return _notification_service
```

**Когда использовать:**
- Сервисы с тяжелой инициализацией
- Singleton сервисы для DI
- Избегание циклических зависимостей

#### 3. Lazy в cron jobs (внутри функций)

**Использование:** Для простых cron jobs

```python
# api/cron/auto_alloc.py
@app.get("/api/cron/auto_alloc")
async def auto_alloc_entrypoint(request: Request):
    from core.services.database import get_database
    db = get_database()
    # ...
```

**Когда использовать:**
- Простые cron jobs без сложных зависимостей
- Когда DI через Depends не нужен
- Для оптимизации cold start

---

## 💉 DEPENDENCY INJECTION

### Паттерны DI в проекте

#### 1. FastAPI Depends (основной)

**Использование:** Для роутеров и endpoints

```python
from fastapi import Depends
from core.auth import verify_telegram_auth

@app.get("/api/webapp/profile")
async def get_profile(
    user: TelegramUser = Depends(verify_telegram_auth)
):
    # user injected via DI
    pass
```

**Когда использовать:**
- API endpoints в роутерах
- Нужна валидация/авторизация
- Переиспользование зависимостей

#### 2. Фабрики в deps.py

**Использование:** Для сервисов

```python
# core/routers/deps.py
def get_notification_service():
    # lazy singleton
    ...

# Использование
from core.routers.deps import get_notification_service

@app.post("/endpoint")
async def handler():
    notification_service = get_notification_service()
    # ...
```

**Когда использовать:**
- Сервисы, которые нужны не всегда
- Singleton сервисы
- Когда Depends не подходит (cron, workers)

#### 3. Прямые импорты (когда уместно)

**Использование:** Для легких утилит

```python
from core.services.money import to_decimal
from core.utils.validators import validate_telegram_init_data
```

**Когда использовать:**
- Легкие pure функции
- Нет побочных эффектов при импорте
- Используются часто и везде

---

## 🎯 SINGLETON PATTERN

### Текущие реализации

#### 1. Singleton в модуле (`core/cart/service.py`)

```python
# core/cart/service.py
_cart_manager: Optional[CartManager] = None

def get_cart_manager() -> CartManager:
    global _cart_manager
    if _cart_manager is None:
        _cart_manager = CartManager()
    return _cart_manager
```

**Использование:** Для доменных сервисов

#### 2. Singleton в deps.py (`core/routers/deps.py`)

```python
# core/routers/deps.py
_notification_service: Optional["NotificationService"] = None

def get_notification_service():
    global _notification_service
    if _notification_service is None:
        from core.services.notifications import NotificationService
        _notification_service = NotificationService()
    return _notification_service
```

**Использование:** Для DI в роутерах

### Guidelines

- ✅ Используйте singleton для сервисов с состоянием (HTTP clients, DB connections)
- ✅ Ленивая инициализация для оптимизации cold start
- ✅ В роутерах используйте `deps.py` для консистентности
- ❌ НЕ используйте singleton для pure функций
- ❌ НЕ используйте singleton для тестируемости (предпочитайте DI)

---

## 📦 BARREL EXPORTS

### Frontend (TypeScript)

**Цель:** Улучшить tree-shaking и консистентность импортов

#### Структура

```
src/
├── utils/
│   ├── index.ts        # ✅ Barrel export всех утилит
│   ├── auth.ts
│   ├── logger.ts
│   └── ...
├── hooks/
│   ├── api/
│   │   ├── index.ts    # ✅ Barrel export всех API hooks
│   │   └── ...
│   └── ...
└── components/
    └── new/
        ├── index.ts    # ✅ Barrel export компонентов
        └── ...
```

#### Использование

```typescript
// ✅ Хорошо - через barrel export
import { logger, formatDate, getApiHeaders } from '../utils';
import { useProductsTyped, useOrdersTyped } from '../hooks/api';

// ⚠️ Приемлемо - прямой импорт (если нужен только один)
import { logger } from '../utils/logger';
```

**Правила:**
- Используйте barrel exports для 2+ импортов из одной директории
- Используйте прямые импорты для одиночных импортов (лучший tree-shaking)
- Всегда экспортируйте типы через barrel exports

---

## 📝 GUIDELINES ПО ДОБАВЛЕНИЮ НОВЫХ МОДУЛЕЙ

### Backend (Python)

#### 1. Добавление нового роутера

```
core/routers/
└── new_domain/
    ├── __init__.py          # Export router
    ├── endpoints.py         # Route handlers
    └── models.py            # Pydantic models (опционально)
```

**Шаги:**
1. Создать директорию `core/routers/new_domain/`
2. Создать `__init__.py` с экспортом router:
   ```python
   from fastapi import APIRouter
   from .endpoints import router
   __all__ = ["router"]
   ```
3. В `api/index.py` добавить:
   ```python
   from core.routers.new_domain import router as new_domain_router
   app.include_router(new_domain_router, prefix="/api/new-domain")
   ```

#### 2. Добавление нового сервиса

```
core/services/
└── new_service.py
```

**Шаги:**
1. Создать файл `core/services/new_service.py`
2. Если нужен singleton - добавить в `core/routers/deps.py`:
   ```python
   def get_new_service():
       global _new_service
       if _new_service is None:
           from core.services.new_service import NewService
           _new_service = NewService()
       return _new_service
   ```

#### 3. Добавление нового repository

```
core/services/repositories/
└── new_repo.py
```

**Шаги:**
1. Наследоваться от `BaseRepository`
2. Реализовать методы доступа к данным
3. Использовать в `database.py` через delegation

#### 4. Добавление нового domain service

```
core/services/domains/
└── new_domain.py
```

**Шаги:**
1. Создать файл с бизнес-логикой
2. Использовать repositories для доступа к данным
3. Экспортировать через `core/services/domains/__init__.py`

---

### Frontend (TypeScript)

#### 1. Добавление новой утилиты

```
src/utils/
└── newUtil.ts
```

**Шаги:**
1. Создать файл `src/utils/newUtil.ts`
2. Экспортировать функции/типы
3. Добавить экспорт в `src/utils/index.ts`:
   ```typescript
   export { function1, function2, type Type1 } from './newUtil';
   ```

#### 2. Добавление нового API hook

```
src/hooks/api/
└── useNewApi.ts
```

**Шаги:**
1. Создать файл `src/hooks/api/useNewApi.ts`
2. Использовать `useApiTyped` или `useApi` как базовый хук
3. Добавить экспорт в `src/hooks/api/index.ts`

#### 3. Добавление нового компонента

```
src/components/new/
└── NewComponent.tsx
```

**Шаги:**
1. Создать компонент
2. Если нужен API - создать `NewComponentConnected.tsx`
3. Добавить экспорт в `src/components/new/index.ts` (если публичный)

---

## 🔍 ПРОВЕРКА ПЕРЕД COMMIT

### Python (Backend)

- [ ] Все импорты используют правильный паттерн (lazy vs прямой)
- [ ] Нет циклических зависимостей
- [ ] Новые сервисы добавлены в `deps.py` если нужны
- [ ] `pyflakes` проходит без ошибок
- [ ] Нет неиспользуемых импортов

### TypeScript (Frontend)

- [ ] Все экспорты добавлены в barrel exports
- [ ] Импорты используют barrel exports для 2+ элементов
- [ ] TypeScript компиляция проходит (`npm run build`)
- [ ] Линтер проходит (`npm run lint`)
- [ ] Нет неиспользуемых импортов

---

## 📚 ПРИМЕРЫ

### Пример: Добавление нового платежного метода

#### Backend

1. **Service:**
   ```python
   # core/services/payments.py
   class PaymentService:
       async def create_new_payment_method(self, ...):
           # ...
   ```

2. **Router:**
   ```python
   # core/routers/webapp/payments.py (новый файл)
   from fastapi import APIRouter, Depends
   from core.routers.deps import get_payment_service
   
   router = APIRouter()
   
   @router.post("/payments/new-method")
   async def create_payment(
       payment_service = Depends(get_payment_service)
   ):
       # ...
   ```

3. **Подключение:**
   ```python
   # core/routers/webapp/__init__.py
   from .payments import router as payments_router
   router.include_router(payments_router)
   ```

#### Frontend

1. **Hook:**
   ```typescript
   // src/hooks/api/usePaymentsApi.ts
   export function usePaymentsTyped() {
     return useApiTyped<PaymentResponse>('/api/webapp/payments');
   }
   ```

2. **Barrel export:**
   ```typescript
   // src/hooks/api/index.ts
   export { usePaymentsTyped } from './usePaymentsApi';
   ```

3. **Использование:**
   ```typescript
   // src/components/new/PaymentMethod.tsx
   import { usePaymentsTyped } from '../../hooks/api';
   ```

---

## ⚠️ ЧАСТЫЕ ОШИБКИ

### 1. Циклические зависимости

**Проблема:**
```python
# core/services/a.py
from core.services.b import func_b

# core/services/b.py
from core.services.a import func_a  # ❌ Цикл!
```

**Решение:**
- Использовать lazy imports
- Переместить общую логику в отдельный модуль
- Использовать TYPE_CHECKING для типов

### 2. Импорт тяжелых модулей на верхнем уровне

**Проблема:**
```python
# core/routers/webapp/profile.py
from core.ai.consultant import AIConsultant  # ❌ Тяжелый импорт

# Лучше:
def handler():
    from core.ai.consultant import AIConsultant  # ✅ Lazy
```

### 3. Забыли добавить в barrel export

**Проблема:**
```typescript
// Создали src/utils/newUtil.ts
export function newFunction() { ... }

// Забыли добавить в src/utils/index.ts ❌
```

**Решение:**
- Всегда добавлять новые экспорты в barrel exports
- Проверять перед commit

---

## 📖 ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ

- `docs/ARCHITECTURE.md` - Общая архитектура проекта
- `docs/FRONTEND_ARCHITECTURE.md` - Frontend архитектура
- `ARCHITECTURE_ANALYSIS.md` - Детальный анализ архитектуры
- `.cursor/rules/architecture.mdc` - Правила архитектуры

---

## ✅ ЧЕКЛИСТ ПРИ РАБОТЕ С МОДУЛЯМИ

**Перед добавлением модуля:**
- [ ] Определить слой (Entry/Router/Service/Domain/Infrastructure)
- [ ] Выбрать правильный паттерн (lazy import, DI, singleton)
- [ ] Проверить на циклические зависимости
- [ ] Добавить в соответствующие barrel exports (frontend)
- [ ] Обновить `__init__.py` если нужно (backend)

**После добавления:**
- [ ] Проверить импорты (pyflakes / TypeScript)
- [ ] Убедиться, что нет неиспользуемых импортов
- [ ] Проверить, что все экспорты доступны через barrel exports
- [ ] Обновить документацию если нужно





