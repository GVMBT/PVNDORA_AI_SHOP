# Быстрая настройка проекта

## 🚀 Установка зависимостей

### Python (Production)
```bash
pip install -r requirements.txt
```

### Python (Development)
```bash
pip install -r requirements-dev.txt
```

> ⚠️ **Важно:** `requirements.txt` используется Vercel при деплое. Dev-инструменты (black, isort, mypy, pylint, bandit) находятся в `requirements-dev.txt` и **не попадают на production**, чтобы не увеличивать размер бандла (лимит 250 MB).

### Node.js
```bash
npm install
```

## 📝 Проверка качества кода

См. [docs/CODE_QUALITY.md](docs/CODE_QUALITY.md) для подробной информации.

**Быстрый старт:**
```bash
# Python
python scripts/check_code_quality.py --fix

# TypeScript/JavaScript
npm run check:all
```

## 🔧 Автоформатирование в VSCode

Все инструменты настроены для **автоматического форматирования при сохранении** (`Ctrl+S`).

См. `.vscode/settings.json` для настроек.
