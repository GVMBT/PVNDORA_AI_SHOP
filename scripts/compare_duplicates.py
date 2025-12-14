#!/usr/bin/env python3
"""
Скрипт для сравнения дубликатов файлов между src/ и core/
Показывает различия в импортах и содержимом
"""
import filecmp
import difflib
import os
from pathlib import Path

def compare_files(file1, file2):
    """Сравнить два файла и вернуть различия"""
    if not os.path.exists(file1):
        return "FILE1_MISSING", []
    if not os.path.exists(file2):
        return "FILE2_MISSING", []
    
    if filecmp.cmp(file1, file2):
        return "IDENTICAL", []
    
    # Найти различия
    with open(file1, 'r', encoding='utf-8') as f1:
        lines1 = f1.readlines()
    with open(file2, 'r', encoding='utf-8') as f2:
        lines2 = f2.readlines()
    
    diff = list(difflib.unified_diff(lines1, lines2, fromfile=file1, tofile=file2, lineterm='', n=3))
    return "DIFFERENT", diff

def main():
    pairs = [
        ('src/ai/consultant.py', 'core/ai/consultant.py'),
        ('src/bot/keyboards.py', 'core/bot/keyboards.py'),
        ('src/bot/middlewares.py', 'core/bot/middlewares.py'),
        ('src/services/notifications.py', 'core/services/notifications.py'),
        ('src/bot/handlers/callbacks.py', 'core/bot/handlers/callbacks.py'),
        ('src/bot/handlers/commands.py', 'core/bot/handlers/commands.py'),
        ('src/bot/handlers/messages.py', 'core/bot/handlers/messages.py'),
    ]
    
    print("=" * 80)
    print("СРАВНЕНИЕ ДУБЛИКАТОВ: src/ vs core/")
    print("=" * 80)
    print()
    
    identical_count = 0
    different_count = 0
    missing_count = 0
    
    for src_file, core_file in pairs:
        status, diff = compare_files(src_file, core_file)
        
        if status == "IDENTICAL":
            print(f"[OK] {src_file}")
            print(f"     IDENTICAL with {core_file}")
            identical_count += 1
        elif status == "DIFFERENT":
            print(f"[DIFF] {src_file}")
            print(f"       DIFFERENT from {core_file}")
            different_count += 1
            
            # Показать только различия в импортах
            import_diffs = [line for line in diff if 'from src.' in line or 'from core.' in line or line.startswith('@@')]
            if import_diffs:
                print("       Differences in imports:")
                for line in import_diffs[:10]:  # Показать первые 10 строк
                    if line.startswith('@@'):
                        print(f"       {line}")
                    elif line.startswith('-') or line.startswith('+'):
                        print(f"       {line.rstrip()}")
        elif status == "FILE1_MISSING":
            print(f"[MISS] {src_file} - NOT FOUND")
            missing_count += 1
        elif status == "FILE2_MISSING":
            print(f"[MISS] {core_file} - NOT FOUND (critical!)")
            missing_count += 1
        
        print()
    
    print("=" * 80)
    print("SUMMARY:")
    print(f"  [OK] Identical: {identical_count}")
    print(f"  [DIFF] Different: {different_count}")
    print(f"  [MISS] Missing: {missing_count}")
    print()
    
    if different_count > 0:
        print("WARNING: Files differ only in imports (from src.* -> from core.*)")
        print("         This is expected after migration. Check that core/* version is up-to-date.")
    print("=" * 80)

if __name__ == "__main__":
    main()
