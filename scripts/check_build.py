#!/usr/bin/env python3
"""
Скрипт для проверки билда проекта.
Проверяет импорты основных модулей и структуру проекта.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_imports():
    """Проверка импортов основных модулей."""
    errors = []

    print("=" * 60)
    print("Проверка импортов основных модулей")
    print("=" * 60)

    # Проверка FastAPI app
    try:
        from api.index import app

        print("[OK] FastAPI app (api/index.py)")
    except Exception as e:
        errors.append(f"FastAPI app: {e}")
        print(f"[ERROR] FastAPI app: {e}")

    # Проверка database
    try:
        from core.services.database import get_database

        print("[OK] Database service (core/services/database.py)")
    except Exception as e:
        errors.append(f"Database service: {e}")
        print(f"[ERROR] Database service: {e}")

    # Проверка bot handlers
    try:
        from core.bot.handlers import router

        print("[OK] Bot handlers (core/bot/handlers)")
    except Exception as e:
        errors.append(f"Bot handlers: {e}")
        print(f"[ERROR] Bot handlers: {e}")

    # Проверка routers
    try:
        from core.routers.admin import router as admin_router
        from core.routers.user import router as user_router
        from core.routers.webapp import router as webapp_router
        from core.routers.webhooks import router as webhooks_router
        from core.routers.workers import router as workers_router

        print("[OK] All routers imported")
    except Exception as e:
        errors.append(f"Routers: {e}")
        print(f"[ERROR] Routers: {e}")

    # Проверка agent
    try:
        from core.agent import get_shop_agent

        print("[OK] AI Agent (core/agent)")
    except Exception as e:
        errors.append(f"AI Agent: {e}")
        print(f"[ERROR] AI Agent: {e}")

    return errors


def check_pyproject():
    """Проверка pyproject.toml."""
    print("\n" + "=" * 60)
    print("Проверка pyproject.toml")
    print("=" * 60)

    try:
        import tomllib

        with open(PROJECT_ROOT / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)

        project = data.get("project", {})
        if not project:
            print("[ERROR] [project] table not found")
            return False

        print(f"[OK] Project name: {project.get('name')}")
        print(f"[OK] Version: {project.get('version')}")
        print(f"[OK] Python: {project.get('requires-python')}")

        deps = project.get("dependencies", [])
        print(f"[OK] Dependencies: {len(deps)} packages")

        # Проверка критичных зависимостей
        dep_names = [dep.split(">=")[0].split("==")[0] for dep in deps]
        critical = ["fastapi", "pydantic", "aiogram", "supabase"]
        missing = [d for d in critical if d not in dep_names]

        if missing:
            print(f"[ERROR] Missing critical dependencies: {missing}")
            return False
        else:
            print("[OK] All critical dependencies present")

        return True
    except Exception as e:
        print(f"[ERROR] Error reading pyproject.toml: {e}")
        return False


def main():
    """Главная функция."""
    print("\n[BUILD CHECK] Проверка билда проекта PVNDORA\n")

    # Проверка pyproject.toml
    pyproject_ok = check_pyproject()

    # Проверка импортов
    import_errors = check_imports()

    # Итоги
    print("\n" + "=" * 60)
    print("ИТОГИ")
    print("=" * 60)

    if pyproject_ok and not import_errors:
        print("[SUCCESS] Все проверки пройдены успешно!")
        print("         Проект готов к деплою на Vercel.")
        return 0
    else:
        if not pyproject_ok:
            print("[ERROR] Ошибки в pyproject.toml")
        if import_errors:
            print(f"[ERROR] Ошибки импорта: {len(import_errors)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
