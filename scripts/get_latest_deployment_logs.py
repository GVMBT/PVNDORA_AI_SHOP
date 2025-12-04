#!/usr/bin/env python3
"""
Скрипт для получения runtime логов последних деплойментов всех проектов Vercel.
Использует Vercel CLI для получения данных.

Использование:
    python scripts/get_latest_deployment_logs.py
    python scripts/get_latest_deployment_logs.py --follow
    python scripts/get_latest_deployment_logs.py --project pvndora  # только для конкретного проекта
"""

import subprocess
import json
import sys
import argparse
from typing import Optional, List, Dict


def run_command(cmd: List[str]) -> Optional[str]:
    """Выполняет команду и возвращает stdout."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка выполнения команды: {' '.join(cmd)}", file=sys.stderr)
        print(f"   {e.stderr}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("❌ Vercel CLI не найден. Установите: npm i -g vercel", file=sys.stderr)
        return None


def get_projects() -> List[Dict]:
    """Получает список всех проектов."""
    output = run_command(["vercel", "project", "ls", "--json"])
    if not output:
        return []
    
    try:
        projects = json.loads(output)
        return projects if isinstance(projects, list) else []
    except json.JSONDecodeError:
        print("❌ Не удалось распарсить список проектов", file=sys.stderr)
        return []


def get_latest_deployment(project_name: str) -> Optional[Dict]:
    """Получает последний деплоймент проекта."""
    output = run_command(["vercel", "list", project_name, "--json"])
    if not output:
        return None
    
    try:
        deployments = json.loads(output)
        if isinstance(deployments, list) and len(deployments) > 0:
            return deployments[0]
        return None
    except json.JSONDecodeError:
        return None


def get_logs(deployment_id: str, follow: bool = False):
    """Получает логи деплоймента."""
    cmd = ["vercel", "logs", deployment_id]
    if follow:
        cmd.append("--follow")
    
    # Для follow режима не используем capture_output, чтобы видеть логи в реальном времени
    if follow:
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка получения логов: {e}", file=sys.stderr)
        except KeyboardInterrupt:
            print("\n⏹️  Остановлено пользователем")
    else:
        output = run_command(cmd)
        if output:
            print(output)


def main():
    parser = argparse.ArgumentParser(
        description="Получить runtime логи последних деплойментов Vercel"
    )
    parser.add_argument(
        "--follow",
        action="store_true",
        help="Следить за логами в реальном времени (до 5 минут)"
    )
    parser.add_argument(
        "--project",
        type=str,
        help="Получить логи только для конкретного проекта"
    )
    args = parser.parse_args()
    
    print("🔍 Получаю список проектов...")
    projects = get_projects()
    
    if not projects:
        print("❌ Не удалось получить список проектов.", file=sys.stderr)
        print("   Убедитесь, что вы авторизованы: vercel login", file=sys.stderr)
        sys.exit(1)
    
    # Фильтруем по проекту, если указан
    if args.project:
        projects = [p for p in projects if args.project.lower() in p.get("name", "").lower()]
        if not projects:
            print(f"❌ Проект '{args.project}' не найден", file=sys.stderr)
            sys.exit(1)
    
    for project in projects:
        project_id = project.get("id", "")
        project_name = project.get("name", "")
        
        print("")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"📦 Проект: {project_name} ({project_id})")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        latest_deployment = get_latest_deployment(project_name)
        
        if not latest_deployment:
            print(f"⚠️  Нет деплойментов для проекта {project_name}")
            continue
        
        deployment_id = latest_deployment.get("uid", "")
        deployment_url = latest_deployment.get("url", "")
        
        print(f"🚀 Последний деплоймент: {deployment_id}")
        print(f"🌐 URL: {deployment_url}")
        print("")
        print("📋 Runtime логи:")
        print("──────────────────────────────────────────")
        
        get_logs(deployment_id, follow=args.follow)
        
        print("")
    
    print("")
    print("✅ Готово!")


if __name__ == "__main__":
    main()

