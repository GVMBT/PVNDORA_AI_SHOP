# CI/CD Пайплайн и Стратегия Развертывания

## Обзор

Профессиональный CI/CD пайплайн на базе GitHub Actions для автоматизации тестирования, проверки качества кода и развертывания.

## Структура Пайплайна

### Этапы CI/CD

```
┌─────────────┐
│   Trigger   │ (Push to main, PR)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Lint      │ (Code quality checks)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Test      │ (Unit tests, Integration tests)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Build     │ (Build artifacts)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Migrate DB │ (Run Supabase migrations)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Deploy    │ (Deploy to Vercel)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Configure  │ (Setup Telegram bot)
└─────────────┘
```

## GitHub Actions Workflow

### .github/workflows/ci-cd.yml

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.12'
  NODE_VERSION: '18'

jobs:
  lint:
    name: Code Quality Checks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install dependencies
        run: |
          pip install ruff mypy
          npm ci
      
      - name: Lint Python
        run: ruff check .
      
      - name: Type check Python
        run: mypy src/ api/
      
      - name: Lint JavaScript
        run: npm run lint

  test:
    name: Run Tests
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: supabase/postgres:latest
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          npm ci
      
      - name: Run Supabase migrations
        run: |
          supabase db reset --local
        env:
          SUPABASE_DB_URL: postgresql://postgres:postgres@localhost:5432/postgres
      
      - name: Run Python tests
        run: pytest tests/ --cov=src --cov=api
      
      - name: Run JavaScript tests
        run: npm test

  build:
    name: Build Artifacts
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
      
      - name: Build frontend
        run: npm run build
      
      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/

  deploy:
    name: Deploy to Vercel
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Vercel CLI
        run: npm install -g vercel@latest
      
      - name: Deploy to Vercel
        run: vercel --prod --token ${{ secrets.VERCEL_TOKEN }}
        env:
          VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
          VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
      
      - name: Run database migrations
        run: |
          supabase db push --db-url ${{ secrets.SUPABASE_DB_URL }}
        env:
          SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
      
      - name: Configure Telegram bot
        run: |
          python scripts/setup_bot.py
        env:
          TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
          WEBAPP_URL: ${{ secrets.WEBAPP_URL }}
```

## Quality Gates

### Критерии Прохождения

1. **Lint:** Все проверки кода должны пройти без ошибок
2. **Type Check:** Все типы должны быть корректными
3. **Tests:** Покрытие тестами должно быть >= 80%
4. **Build:** Артефакты должны собираться успешно
5. **Migrations:** Миграции БД должны применяться без ошибок

### Автоматический Rollback

При ошибке на любом этапе после деплоя:
- Автоматический откат к предыдущей версии
- Уведомление команды через Telegram/Email

## Управление Секретами

### GitHub Secrets

```yaml
# Vercel
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_PROJECT_ID

# Supabase
SUPABASE_ACCESS_TOKEN
SUPABASE_DB_URL
SUPABASE_SERVICE_ROLE_KEY

# Telegram
TELEGRAM_TOKEN
TELEGRAM_WEBHOOK_URL

# Other
GEMINI_API_KEY
QSTASH_TOKEN
UPSTASH_REDIS_URL
```

### Vercel Environment Variables

Все секреты также должны быть настроены в Vercel Dashboard для runtime.

## Локальная Разработка

### Docker Compose для Полного Стека

```yaml
# docker-compose.yml
version: '3.8'

services:
  supabase:
    image: supabase/postgres:latest
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
    ports:
      - "5432:5432"
    volumes:
      - ./supabase/migrations:/docker-entrypoint-initdb.d
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

### Запуск Локального Окружения

```bash
# Запуск Supabase локально
supabase start

# Применение миграций
supabase db reset

# Запуск приложения
docker-compose up -d
python -m uvicorn api.index:app --reload
```

## Стратегия Развертывания

### Environments

1. **Development:** Автоматический деплой при push в `develop`
2. **Staging:** Автоматический деплой при push в `staging`
3. **Production:** Автоматический деплой при merge в `main`

### Blue-Green Deployment

Для минимизации downtime:
- Деплой новой версии параллельно со старой
- Переключение трафика после успешного health check
- Откат при обнаружении ошибок

## Мониторинг и Алерты

### Health Checks

```python
@app.get("/api/health")
async def health_check():
    """Health check для мониторинга"""
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "qstash": await check_qstash()
    }
    
    if all(checks.values()):
        return {"status": "healthy", "checks": checks}
    else:
        return {"status": "unhealthy", "checks": checks}, 503
```

### Алерты

- Ошибки деплоя → Telegram уведомление
- Health check failures → Email + Telegram
- Высокая нагрузка → Dashboard alert

## Скрипты Конфигурации

### scripts/setup_bot.py

```python
"""Настройка Telegram бота после деплоя"""
import asyncio
from aiogram import Bot
from locales import BOT_CONFIG

async def setup_bot():
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    
    # Настройка для всех языков
    for lang, config in BOT_CONFIG.items():
        await bot.set_my_name(config["name"], language_code=lang)
        await bot.set_my_description(config["description"], language_code=lang)
        await bot.set_my_short_description(config["short_description"], language_code=lang)
    
    # Установка webhook
    webhook_url = f"{os.getenv('WEBAPP_URL')}/api/webhook/telegram"
    await bot.set_webhook(webhook_url)
    
    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(setup_bot())
```

