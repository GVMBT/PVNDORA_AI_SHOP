#!/usr/bin/env python3
"""
Remove already-tracked files that should be ignored.

This script helps clean up files that were accidentally committed
but should be in .gitignore.

Usage:
    python scripts/clean_git_tracked.py
    python scripts/clean_git_tracked.py --dry-run  # Preview only
"""

import subprocess
import sys
import re

# Patterns that should be ignored (from .gitignore)
IGNORE_PATTERNS = [
    r'__pycache__/',
    r'\.pyc$',
    r'\.pyo$',
    r'\.pyd$',
    r'\.coverage$',
    r'\.coverage\..*',
    r'htmlcov/',
    r'\.pytest_cache/',
    r'\.mypy_cache/',
    r'\.ruff_cache/',
    r'\.env\.local$',
    r'\.env\..*\.local$',
    r'\.vercel/',
    r'\.DS_Store$',
    r'Thumbs\.db$',
    r'desktop\.ini$',
    r'\.tmp$',
    r'\.temp$',
    r'\.bak$',
    r'\.orig$',
    r'\.log$',
    r'node_modules/',
    r'dist/',
    r'build/',
    r'\.cache/',
    r'\.parcel-cache/',
    r'\.npm/',
    r'\.eslintcache$',
    r'\.stylelintcache$',
    r'\.tsbuildinfo$',
    r'\.next/',
    r'out/',
    r'\.vscode-test/',
    r'\.history/',
    r'\.cursor/cache/',
    r'\.cursor/logs/',
    r'supabase/\.temp/',
    r'supabase/\.branches/',
]

def get_tracked_files():
    """Get list of all tracked files in git."""
    try:
        result = subprocess.run(
            ['git', 'ls-files'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().split('\n') if result.stdout.strip() else []
    except subprocess.CalledProcessError as e:
        print(f"Error getting tracked files: {e}", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("Git not found. Make sure git is installed.", file=sys.stderr)
        return []

def matches_pattern(filepath, patterns):
    """Check if filepath matches any ignore pattern."""
    for pattern in patterns:
        if re.search(pattern, filepath):
            return True
    return False

def main():
    """Main function."""
    import argparse
    parser = argparse.ArgumentParser(description='Clean tracked files that should be ignored')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without applying')
    args = parser.parse_args()
    
    print("🔍 Checking for tracked files that should be ignored...\n")
    
    tracked_files = get_tracked_files()
    if not tracked_files:
        print("No tracked files found or git error.")
        return 1
    
    files_to_remove = []
    for filepath in tracked_files:
        if matches_pattern(filepath, IGNORE_PATTERNS):
            files_to_remove.append(filepath)
    
    if not files_to_remove:
        print("✅ No files need to be removed. All tracked files are valid.")
        return 0
    
    print(f"📋 Found {len(files_to_remove)} file(s) that should be ignored:\n")
    for filepath in sorted(files_to_remove):
        print(f"  - {filepath}")
    
    if args.dry_run:
        print("\n💡 This is a dry run. Use without --dry-run to remove these files.")
        return 0
    
    print("\n⚠️  This will remove these files from git (but keep them locally).")
    response = input("Continue? (y/N): ")
    
    if response.lower() != 'y':
        print("Cancelled.")
        return 0
    
    print("\n🗑️  Removing files from git index...")
    for filepath in files_to_remove:
        try:
            subprocess.run(
                ['git', 'rm', '--cached', filepath],
                check=True,
                capture_output=True
            )
            print(f"  ✓ Removed: {filepath}")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed to remove {filepath}: {e.stderr.decode()}", file=sys.stderr)
    
    print("\n✅ Done! Files removed from git index.")
    print("💡 Commit these changes to update the repository.")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

