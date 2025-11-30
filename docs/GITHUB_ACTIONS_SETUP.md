# Настройка GitHub Actions для автоматического деплоя

## Проблема

Если вы видите ошибку:
```
Error: Input required and not supplied: vercel-token
```

Это означает, что в GitHub Secrets не настроены необходимые токены для деплоя на Vercel.

## Решение

### 1. Получить Vercel токены

1. Перейдите на https://vercel.com/account/tokens
2. Создайте новый токен (Token)
3. Скопируйте токен

### 2. Получить Vercel Project ID и Org ID

**Способ 1: Через Vercel Dashboard**
1. Откройте проект в Vercel
2. Перейдите в Settings → General
3. Найдите:
   - **Project ID** (в разделе "Project ID")
   - **Team ID** или **Org ID** (в разделе "Team")

**Способ 2: Через Vercel CLI**
```bash
vercel link
# Выберите проект, и он покажет Project ID и Org ID
```

### 3. Добавить секреты в GitHub

1. Перейдите в ваш GitHub репозиторий
2. Settings → Secrets and variables → Actions
3. Нажмите "New repository secret"
4. Добавьте следующие секреты:

| Secret Name | Значение | Где взять |
|------------|----------|-----------|
| `VERCEL_TOKEN` | Ваш Vercel токен | https://vercel.com/account/tokens |
| `VERCEL_ORG_ID` | ID вашей организации/команды | Settings → General → Team ID |
| `VERCEL_PROJECT_ID` | ID вашего проекта | Settings → General → Project ID |

### 4. Дополнительные секреты (опционально)

Если используете другие функции CI/CD:

| Secret Name | Описание |
|------------|----------|
| `TELEGRAM_TOKEN` | Токен Telegram бота (для setup-bot job) |
| `TELEGRAM_WEBHOOK_URL` | URL для webhook (для setup-bot job) |
| `SUPABASE_ACCESS_TOKEN` | Supabase access token (для migrations) |
| `SUPABASE_DB_PASSWORD` | Пароль от Supabase DB (для migrations) |
| `SUPABASE_PROJECT_ID` | Supabase project ID (для migrations) |

## Проверка

После добавления секретов:

1. **Сделайте новый commit и push в `main`:**
   ```bash
   git commit --allow-empty -m "test: trigger deployment"
   git push
   ```

2. **Проверьте статус в GitHub Actions:**
   - Перейдите в репозиторий → Actions
   - Должен запуститься workflow "CI/CD Pipeline"
   - Job "Deploy to Vercel" должен пройти успешно

3. **Проверьте деплой в Vercel:**
   - Откройте Vercel Dashboard → Deployments
   - Должен появиться новый deployment с комментарием из commit

## Альтернатива: Отключить автоматический деплой

Если не хотите использовать GitHub Actions для деплоя, можно:

1. Удалить или закомментировать job `deploy` в `.github/workflows/deploy.yml`
2. Использовать только Vercel Git Integration (автоматический деплой при push)

Vercel Git Integration настраивается в:
- Vercel Dashboard → Project Settings → Git
- Подключите GitHub репозиторий
- Vercel будет автоматически деплоить при каждом push

## Troubleshooting

### Ошибка: "vercel-token not found"
- Проверьте, что секрет добавлен в правильный репозиторий
- Убедитесь, что имя секрета точно `VERCEL_TOKEN` (регистр важен)

### Ошибка: "Invalid token"
- Проверьте, что токен не истек
- Создайте новый токен на https://vercel.com/account/tokens

### Ошибка: "Project not found"
- Проверьте `VERCEL_PROJECT_ID` и `VERCEL_ORG_ID`
- Убедитесь, что токен имеет доступ к проекту

### Ошибка: "Workflow не запускается"
- Убедитесь, что вы пушите в ветку `main`
- Проверьте, что workflow файл находится в `.github/workflows/deploy.yml`
- Проверьте, что в Actions включены workflows (Settings → Actions → General → Allow all actions)

## Проверка секретов

Чтобы убедиться, что секреты добавлены:

1. Перейдите в репозиторий → Settings → Secrets and variables → Actions
2. Должны быть видны секреты (значения скрыты):
   - ✅ `VERCEL_TOKEN`
   - ✅ `VERCEL_ORG_ID`
   - ✅ `VERCEL_PROJECT_ID`

Если секретов нет или они не видны, добавьте их заново.
