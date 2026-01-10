# Техническая Документация PVNDORA

## Обзор

Эта папка содержит детальную техническую документацию для реализации проекта PVNDORA AI Marketplace.

## Структура Документации

### 1. [Спецификация API](./api-specification.md)
Контракт взаимодействия:
- Эндпоинты для Mini App (webapp)
- Эндпоинты для QStash Workers
- Вебхуки (Telegram, CrystalPay)
- Аутентификация и авторизация

### 2. [Валюты и Локализация](./CURRENCY_LOCALIZATION.md)
Архитектура валютной системы:
- Multi-Currency Anchor Architecture
- Anchor Prices для товаров
- Transaction Snapshots для точности
- Balance Currency и конвертация

### 3. [Асинхронная Архитектура](./QSTASH_EXPLAINED.md)
Описание гибридной асинхронной архитектуры:
- Best-Effort обработка (BackgroundTasks)
- Guaranteed Delivery (QStash)
- Конфигурация и примеры использования

### 4. [CI/CD Пайплайн](./cicd-pipeline.md)
Автоматизация разработки:
- GitHub Actions workflow
- Quality Gates
- Управление секретами
- Стратегия развертывания

### 5. [Аутентификация](./AUTHENTICATION.md)
Описание системы аутентификации:
- Telegram Mini App authentication (initData)
- Web Browser authentication (session tokens)
- Общие утилиты и обработка ошибок
- Troubleshooting
- [Roadmap](./AUTHENTICATION_ROADMAP.md): Email/Password, Guest Mode, Magic Links

### 6. [FAQ по Безопасности](./SECURITY_FAQ.md)
Ответы на частые вопросы о безопасности:
- Безопасность Telegram-авторизации
- Что мы получаем и не получаем от Telegram
- Планы по альтернативным методам авторизации
- Рекомендации для пользователей

### 7. [Модель "Под Заказ"](./ON_DEMAND_ORDERS.md)
Бизнес-модель работы с товаром "скоропортом":
- Instant Fulfillment (товар в наличии)
- Prepaid Orders (товар под заказ)
- Автоматическое разделение на instant + prepaid при недостаточном наличии
- Управление корзиной через Redis (до оплаты)
- Редактирование корзины (изменение количества, удаление товаров)
- Система возвратов
- Таймауты и автоматические возвраты

### 8. [UX, Deep Linking и Локализация](./ux-deep-linking.md)
Спецификация пользовательского опыта:
- Разделение ответственности: Чат vs Mini App
- Бесшовный Deep Linking (Base64url)
- RTL поддержка
- Культурная адаптация
- Виральность через switchInlineQuery
- Human Handoff процесс

## Удаленные Функции

Следующие функции были исключены из MVP:
- **Визуальный поиск** - сложность пайплайна (скачивание файла с Telegram, загрузка в Google)
- **Обработка голосовых сообщений** - аналогичная сложность пайплайна

## Связанные Документы

- [PROJECT_MAP.md](../PROJECT_MAP.md) - Карта проекта и структура
- [REFACTORING_PLAN.md](../REFACTORING_PLAN.md) - План рефакторинга
- [REFACTORING_STATUS.md](../REFACTORING_STATUS.md) - Статус рефакторинга
- [.cursor/rules/](../.cursor/rules/) - Правила архитектуры и разработки

## Быстрый Старт

1. Изучите [PROJECT_MAP.md](../PROJECT_MAP.md) для понимания структуры проекта
2. Ознакомьтесь с [.cursor/rules/architecture.mdc](../.cursor/rules/architecture.mdc) для архитектурных правил
3. Изучите техническую документацию в этой папке для деталей реализации

## Порядок Реализации

1. **Настройка инфраструктуры:**
   - Supabase (БД + миграции)
   - Upstash (QStash + Redis)
   - Vercel (деплой)

2. **База данных:**
   - Применение миграций (`supabase/migrations/`)
   - Создание SQL View
   - Настройка хранимых процедур (RPC)

3. **Backend:**
   - FastAPI приложение (`api/index.py`)
   - Интеграция с QStash (см. [QSTASH_EXPLAINED.md](./QSTASH_EXPLAINED.md))
   - AI-консультант с LangGraph (OpenRouter + Gemini)

4. **Frontend:**
   - Mini App (React + TypeScript)
   - Интеграция с Telegram WebApp API
   - Локализация (i18n)

5. **CI/CD:**
   - Настройка GitHub Actions
   - Автоматизация деплоя (см. [cicd-pipeline.md](./cicd-pipeline.md))

---

## Технологический Стек

- **Runtime:** Python 3.12 (Vercel Serverless)
- **Framework:** FastAPI 0.115+ (single Serverless Function entry point)
- **AI Core:** OpenRouter API + LangGraph (Model: google/gemini-3-flash-preview)
- **Database:** Supabase (PostgreSQL) via supabase-py (NO ORM)
- **Async Messaging:** Upstash QStash (guaranteed delivery)
- **State/Cache:** Upstash Redis (HTTP REST API)
- **Frontend:** React 19 + TypeScript + Vite
- **Deployment:** Vercel (Pro plan required for commercial use)

