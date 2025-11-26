#!/usr/bin/env python3
"""
Static validation script for tests
Checks imports and basic syntax without running tests
"""
import ast
import sys
from pathlib import Path

def check_file(filepath):
    """Check if Python file has valid syntax"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error reading file: {e}"

def main():
    """Validate all test files"""
    test_dir = Path("tests")
    if not test_dir.exists():
        print("❌ tests/ directory not found")
        return 1
    
    test_files = list(test_dir.glob("test_*.py"))
    if not test_files:
        print("❌ No test files found")
        return 1
    
    print(f"Validating {len(test_files)} test files...\n")
    
    all_valid = True
    for test_file in sorted(test_files):
        is_valid, error = check_file(test_file)
        if is_valid:
            print(f"✅ {test_file.name}")
        else:
            print(f"❌ {test_file.name}: {error}")
            all_valid = False
    
    print()
    if all_valid:
        print("✅ All test files have valid syntax!")
        return 0
    else:
        print("❌ Some test files have syntax errors")
        return 1

if __name__ == "__main__":
    sys.exit(main())

