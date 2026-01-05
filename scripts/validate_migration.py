#!/usr/bin/env python3
"""
Validate that a migration file matches API expectations.

Usage:
    python scripts/validate_migration.py supabase/migrations/009_fix_partner_analytics_view.sql
"""

import sys
import re
from pathlib import Path
from typing import Set

def extract_view_fields(sql_content: str, view_name: str) -> Set[str]:
    """Extract field names from a CREATE VIEW statement."""
    fields = set()
    
    # Find the view definition
    view_pattern = rf'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+{view_name}\s+AS'
    match = re.search(view_pattern, sql_content, re.IGNORECASE)
    
    if not match:
        return fields
    
    # Find SELECT clause
    select_start = sql_content.find('SELECT', match.end())
    if select_start == -1:
        return fields
    
    # Find FROM clause to limit scope
    from_pos = sql_content.find('FROM', select_start)
    if from_pos == -1:
        return fields
    
    select_clause = sql_content[select_start:from_pos]
    
    # Extract field aliases (AS keyword)
    alias_pattern = r'\s+AS\s+(\w+)'
    for alias_match in re.finditer(alias_pattern, select_clause, re.IGNORECASE):
        fields.add(alias_match.group(1))
    
    # Extract direct column selections
    # Pattern: column_name, or column_name AS alias
    column_pattern = r'(\w+)(?:\s+AS\s+\w+)?(?:\s*,|\s+FROM)'
    for col_match in re.finditer(column_pattern, select_clause):
        field = col_match.group(1).strip()
        if field.upper() not in ['SELECT', 'DISTINCT', 'COUNT', 'SUM', 'COALESCE', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END']:
            fields.add(field)
    
    return fields

def find_api_expectations(view_name: str) -> Set[str]:
    """Find what fields API expects from a view."""
    expected_fields = set()
    api_dir = Path('core/routers')
    
    if not api_dir.exists():
        return expected_fields
    
    for py_file in api_dir.rglob('*.py'):
        try:
            content = py_file.read_text(encoding='utf-8')
            
            # Check if this file uses the view
            if view_name not in content:
                continue
            
            # Find .get() calls that reference fields
            # Pattern: p.get("field_name") or p.get('field_name')
            get_pattern = r'\.get\(["\']([^"\']+)["\']\)'
            for match in re.finditer(get_pattern, content):
                field = match.group(1)
                # Check if it's in context of this view
                context_start = max(0, match.start() - 200)
                context = content[context_start:match.end()]
                if view_name in context or 'partner' in context.lower():
                    expected_fields.add(field)
            
        except Exception as e:
            print(f"Error reading {py_file}: {e}", file=sys.stderr)
    
    return expected_fields

def validate_migration(migration_file: Path):
    """Validate a migration file."""
    print(f"🔍 Validating {migration_file.name}...\n")
    
    if not migration_file.exists():
        print(f"❌ File not found: {migration_file}")
        return 1
    
    try:
        sql_content = migration_file.read_text(encoding='utf-8')
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return 1
    
    # Find all views in migration
    view_pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)\s+AS'
    views = re.findall(view_pattern, sql_content, re.IGNORECASE)
    
    if not views:
        print("ℹ️  No views found in migration file")
        return 0
    
    issues = []
    
    for view_name in views:
        print(f"📊 Checking view: {view_name}")
        
        # Extract fields from view
        view_fields = extract_view_fields(sql_content, view_name)
        print(f"   View returns: {len(view_fields)} fields")
        
        # Find API expectations
        api_fields = find_api_expectations(view_name)
        print(f"   API expects: {len(api_fields)} fields")
        
        # Check for mismatches
        missing = api_fields - view_fields
        extra = view_fields - api_fields
        
        if missing:
            issues.append(f"❌ View '{view_name}' missing fields: {', '.join(sorted(missing))}")
        
        if extra:
            print(f"   ℹ️  Extra fields (OK): {', '.join(sorted(extra))}")
    
    if issues:
        print("\n⚠️  Issues found:\n")
        for issue in issues:
            print(f"  {issue}")
        print("\n💡 Fix: Update view to include missing fields")
        return 1
    else:
        print("\n✅ Migration looks good!")
        return 0

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_migration.py <migration_file.sql>")
        sys.exit(1)
    
    migration_file = Path(sys.argv[1])
    sys.exit(validate_migration(migration_file))

