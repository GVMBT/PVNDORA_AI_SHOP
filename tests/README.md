# Тесты для PVNDORA AI Marketplace

## Установка зависимостей

```bash
pip install -r requirements.txt
```

## Запуск тестов

### Все тесты
```bash
pytest
```

### С покрытием кода
```bash
pytest --cov=src --cov=api --cov-report=html
```

### Конкретный файл
```bash
pytest tests/test_database.py
```

### Конкретный тест
```bash
pytest tests/test_database.py::test_get_user_by_telegram_id
```

### Только быстрые тесты (исключая медленные)
```bash
pytest -m "not slow"
```

## Структура тестов

- `tests/test_database.py` - Тесты для операций с базой данных
- `tests/test_ai_tools.py` - Тесты для AI инструментов (function calling)
- `tests/test_payments.py` - Тесты для обработки платежей (AAIO, Stripe)
- `tests/test_handlers.py` - Тесты для обработчиков бота
- `tests/test_api.py` - Тесты для API endpoints
- `tests/test_validators.py` - Тесты для валидации данных
- `tests/test_notifications.py` - Тесты для сервиса уведомлений
- `tests/test_i18n.py` - Тесты для системы переводов
- `tests/conftest.py` - Фикстуры и конфигурация pytest

## Переменные окружения для тестов

Тесты используют моки и не требуют реальных подключений к базе данных или внешним сервисам. Переменные окружения устанавливаются автоматически в `conftest.py`.

## Покрытие кода

После запуска с `--cov-report=html` отчет будет доступен в `htmlcov/index.html`.

