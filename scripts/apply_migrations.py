#!/usr/bin/env python3
"""
Apply pending Supabase migrations.

This script:
1. Lists pending migrations
2. Applies them via Supabase MCP or CLI
3. Verifies they were applied successfully
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

def get_pending_migrations() -> List[Tuple[Path, str]]:
    """Get list of migration files that need to be applied."""
    migrations_dir = Path('supabase/migrations')
    
    if not migrations_dir.exists():
        print("❌ supabase/migrations directory not found")
        return []
    
    migrations = []
    for migration_file in sorted(migrations_dir.glob('*.sql')):
        migrations.append((migration_file, migration_file.stem))
    
    return migrations

def apply_migration_via_cli(migration_file: Path) -> bool:
    """Apply migration via Supabase CLI."""
    try:
        # Check if supabase CLI is available
        result = subprocess.run(
            ['supabase', '--version'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("⚠️  Supabase CLI not found. Skipping CLI method.")
            return False
        
        # Apply migration
        print(f"📦 Applying {migration_file.name} via Supabase CLI...")
        result = subprocess.run(
            ['supabase', 'db', 'push'],
            cwd=Path.cwd(),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Successfully applied {migration_file.name}")
            return True
        else:
            print(f"❌ Failed to apply {migration_file.name}:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("⚠️  Supabase CLI not installed")
        return False
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        return False

def show_migration_sql(migration_file: Path):
    """Show migration SQL content."""
    try:
        content = migration_file.read_text(encoding='utf-8')
        print(f"\n📄 Migration SQL ({migration_file.name}):")
        print("=" * 60)
        print(content[:500] + "..." if len(content) > 500 else content)
        print("=" * 60)
    except Exception as e:
        print(f"❌ Error reading migration file: {e}")

def main():
    """Main function."""
    print("🔄 Checking for pending migrations...\n")
    
    migrations = get_pending_migrations()
    
    if not migrations:
        print("✅ No migrations found")
        return 0
    
    print(f"📋 Found {len(migrations)} migration(s):")
    for migration_file, name in migrations:
        print(f"   - {migration_file.name}")
    
    print("\n💡 To apply migrations:")
    print("   1. Use Supabase Dashboard → SQL Editor")
    print("   2. Copy SQL from migration files")
    print("   3. Or use: supabase db push")
    print("\n   Or use MCP tool: mcp_supabase_apply_migration")
    
    # Show first migration as example
    if migrations:
        show_migration_sql(migrations[0][0])
    
    # Try to apply via CLI if available
    if migrations:
        response = input("\n❓ Apply migrations via Supabase CLI? (y/N): ")
        if response.lower() == 'y':
            for migration_file, name in migrations:
                if not apply_migration_via_cli(migration_file):
                    print(f"⚠️  Skipping {migration_file.name}")
                    break
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

