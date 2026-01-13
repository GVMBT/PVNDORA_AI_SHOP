#!/usr/bin/env python3
"""
Скрипт для запуска анализа SonarQube/SonarCloud во всем проекте.

Использование:
    python scripts/run_sonarqube.py

Требования:
    - Установлен Node.js
    - Установлен sonarqube-scanner: npm install -g sonarqube-scanner
    - Токен SonarCloud (переменная окружения SONAR_TOKEN или .env)
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def check_sonar_scanner() -> bool:
    """Проверить, установлен ли sonar-scanner."""
    import shutil
    
    # Проверяем через which/where
    scanner_path = shutil.which("sonar-scanner")
    if scanner_path:
        return True
    
    # Проверяем через npm
    try:
        result = subprocess.run(
            ["npm", "list", "-g", "sonarqube-scanner"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "sonarqube-scanner" in result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_sonar_token() -> str | None:
    """Получить токен SonarCloud из переменных окружения или .env."""
    # Проверяем переменную окружения
    token = os.environ.get("SONAR_TOKEN")
    if token:
        return token

    # Проверяем .env файл
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("SONAR_TOKEN="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass

    return None


def main():
    """Запустить анализ SonarQube."""
    print("=" * 60)
    print("SonarQube/SonarCloud Analysis")
    print("=" * 60)

    # Проверяем наличие sonar-scanner
    if not check_sonar_scanner():
        print("\n[ERROR] sonar-scanner не установлен")
        print("\nУстановите sonar-scanner:")
        print("  npm install -g sonarqube-scanner")
        print("\nИли используйте Docker:")
        print("  docker run --rm -v $(pwd):/usr/src sonarsource/sonar-scanner-cli")
        sys.exit(1)

    # Получаем токен
    token = get_sonar_token()
    if not token:
        print("\n[ERROR] SONAR_TOKEN не найден")
        print("\nУстановите токен одним из способов:")
        print("  1. Переменная окружения: set SONAR_TOKEN=your_token")
        print("  2. В файле .env: SONAR_TOKEN=your_token")
        print("\nПолучить токен: SonarCloud -> My Account -> Security")
        sys.exit(1)

    print("\n[OK] sonar-scanner найден")
    print("[OK] SONAR_TOKEN найден")
    print("\n[RUN] Запуск анализа...")
    print("=" * 60)

    # Запускаем sonar-scanner
    try:
        result = subprocess.run(
            ["sonar-scanner"],
            cwd=PROJECT_ROOT,
            env={**os.environ, "SONAR_TOKEN": token},
            check=False,
        )

        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("[SUCCESS] Анализ завершен успешно!")
            print("=" * 60)
            print("\nРезультаты доступны в SonarCloud:")
            print("  https://sonarcloud.io/project/overview?id=GVMBT_PVNDORA_AI_SHOP")
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("[ERROR] Анализ завершился с ошибками")
            print("=" * 60)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n[WARNING] Анализ прерван пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Ошибка при запуске анализа: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
