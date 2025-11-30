# Локальная настройка и запуск скриптов

## Проблема: "TELEGRAM_TOKEN not set"

Если при запуске скриптов (`scripts/set_webhook.py`, `scripts/check_webhook.py`, `scripts/setup_bot.py`) вы видите ошибку:
```
❌ Error: TELEGRAM_TOKEN not set
```

Это означает, что скрипт не может найти переменные окружения.

## Решение: Создать .env файл

### 1. Создать .env файл

В корне проекта создайте файл `.env` (на основе `env.example`):

```bash
# Скопируйте пример
cp env.example .env
```

### 2. Заполнить необходимые переменные

Для работы скриптов нужны минимум:

```env
# Telegram Bot
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_WEBHOOK_URL=https://pvndora.app/api/webhook/telegram

# Supabase (опционально, если нужен доступ к БД)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### 3. Установить python-dotenv

Убедитесь, что `python-dotenv` установлен:

```bash
pip install python-dotenv
```

Или установите все зависимости:

```bash
pip install -r requirements.txt
```

### 4. Запустить скрипт

Теперь скрипты автоматически загрузят переменные из `.env`:

```bash
python scripts/set_webhook.py
python scripts/check_webhook.py
python scripts/setup_bot.py
```

## Альтернатива: Установить переменные в системе

### Windows (PowerShell)

```powershell
$env:TELEGRAM_TOKEN="your_token_here"
$env:TELEGRAM_WEBHOOK_URL="https://pvndora.app/api/webhook/telegram"
python scripts/set_webhook.py
```

### Windows (CMD)

```cmd
set TELEGRAM_TOKEN=your_token_here
set TELEGRAM_WEBHOOK_URL=https://pvndora.app/api/webhook/telegram
python scripts/set_webhook.py
```

### Linux/Mac

```bash
export TELEGRAM_TOKEN="your_token_here"
export TELEGRAM_WEBHOOK_URL="https://pvndora.app/api/webhook/telegram"
python scripts/set_webhook.py
```

## Проверка

После создания `.env` файла, скрипт должен вывести:

```
📄 Loaded .env from D:\pvndora\.env
📡 Setting webhook to: https://pvndora.app/api/webhook/telegram
✅ Webhook установлен успешно!
```

## Безопасность

⚠️ **ВАЖНО:** 
- `.env` файл содержит секретные данные
- **НЕ коммитьте** `.env` в Git (он уже в `.gitignore`)
- Используйте `.env` только для локальной разработки
- Для production используйте Vercel Environment Variables

## Troubleshooting

### Ошибка: "ModuleNotFoundError: No module named 'dotenv'"

```bash
pip install python-dotenv
```

### Ошибка: ".env file not found"

Убедитесь, что файл `.env` находится в корне проекта (рядом с `requirements.txt`).

### Ошибка: "Invalid token"

Проверьте, что `TELEGRAM_TOKEN` правильный:
- Получить можно у @BotFather в Telegram
- Формат: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

