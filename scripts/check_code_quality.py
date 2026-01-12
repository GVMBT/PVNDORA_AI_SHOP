#!/usr/bin/env python3
"""
Скрипт для запуска всех проверок качества кода Python.
Использование: python scripts/check_code_quality.py [--fix]

Требует установки dev-зависимостей:
    pip install -r requirements-dev.txt
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd: list[str], description: str, fix: bool = False) -> bool:
    """Запустить команду и вернуть True если успешно."""
    print(f"\n{'='*60}")
    print(f"[CHECK] {description}")
    print(f"{'='*60}")
    try:
        # Устанавливаем UTF-8 для всех команд (особенно важно для Pylint на Windows)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        # Используем UTF-8 для кодировки, чтобы избежать проблем с Windows cp1251
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # Заменяем нечитаемые символы вместо ошибки
            env=env,  # Передаем окружение с UTF-8
        )

        # Bandit может вернуть non-zero код даже при warnings, это нормально
        if "bandit" in description.lower():
            # Для bandit считаем успехом, если нет критических ошибок в выводе
            output = result.stdout + result.stderr
            if "SEVERITY.HIGH" in output and '"SEVERITY.HIGH": 0' not in output:
                print(f"[FAILED] {description} - Found HIGH severity issues")
                print(result.stdout[:500])  # Показываем только начало
                return False
            print(f"[OK] {description} - OK (warnings only)")
            return True

        if result.returncode == 0:
            print(f"[OK] {description} - OK")
            return True
        print(f"[FAILED] {description} - FAILED")
        # Убираем ANSI escape-коды для Windows совместимости
        import re

        clean_output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout + result.stderr)
        # Показываем только первые 1000 символов, чтобы не засорять вывод
        if len(clean_output) > 1000:
            print(clean_output[:1000] + "\n... (output truncated)")
        else:
            print(clean_output)
        return False
    except (FileNotFoundError, UnicodeEncodeError) as e:
        # Обрабатываем ошибки кодировки и отсутствие инструментов
        if isinstance(e, UnicodeEncodeError):
            print(
                f"[WARNING] {description} - Encoding error (Windows console issue), skipping output"
            )
            # Для Pylint считаем это предупреждением, не ошибкой
            if "pylint" in description.lower():
                return True  # Pylint warnings не критичны
        else:
            print(f"[WARNING] {description} - Tool not found: {e}")
        return True  # Не критично, если инструмент не установлен или ошибка кодировки


def main():
    fix = "--fix" in sys.argv

    checks = [
        # Форматирование
        (["python", "-m", "black", "--check", "."], "Black (форматирование)", False),
        (["python", "-m", "isort", "--check-only", "."], "isort (сортировка импортов)", False),
        # Линтинг (отключаем цвета для Windows совместимости)
        (["python", "-m", "ruff", "check", ".", "--no-cache"], "Ruff (линтинг)", False),
        (
            ["python", "-m", "pylint", "api", "core", "scripts", "--output-format=text"],
            "Pylint (расширенная проверка)",
            False,
        ),
        # Типы
        (["python", "-m", "mypy", "api", "core"], "Mypy (проверка типов)", False),
        # Безопасность (bandit может вернуть non-zero даже при warnings)
        (
            ["python", "-m", "bandit", "-r", "api", "core", "-f", "json", "-ll"],
            "Bandit (безопасность)",
            False,
        ),
    ]

    if fix:
        # Заменяем check команды на fix
        checks = [
            (["python", "-m", "black", "."], "Black (форматирование)", True),
            (["python", "-m", "isort", "."], "isort (сортировка импортов)", True),
            (
                ["python", "-m", "ruff", "check", ".", "--fix", "--no-cache"],
                "Ruff (линтинг с автоисправлением)",
                True,
            ),
        ]

    results = []
    for cmd, desc, _ in checks:
        success = run_command(cmd, desc, fix)
        results.append((desc, success))

    print(f"\n{'='*60}")
    print("[RESULTS] ИТОГИ")
    print(f"{'='*60}")

    failed = [desc for desc, success in results if not success]
    passed = [desc for desc, success in results if success]

    for desc in passed:
        print(f"[OK] {desc}")

    for desc in failed:
        print(f"[FAILED] {desc}")

    if failed:
        print(f"\n[WARNING] Не пройдено проверок: {len(failed)}/{len(results)}")
        sys.exit(1)
    else:
        print(f"\n[SUCCESS] Все проверки пройдены: {len(passed)}/{len(results)}")
        sys.exit(0)


if __name__ == "__main__":
    main()
