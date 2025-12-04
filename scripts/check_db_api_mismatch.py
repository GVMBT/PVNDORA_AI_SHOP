#!/usr/bin/env python3
"""
Check for mismatches between database views and API expectations.

This script:
1. Scans API endpoints for database view usage
2. Checks if views return expected fields
3. Reports any mismatches
"""

import re
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Patterns to find view usage in API code
VIEW_PATTERN = r'\.table\(["\']([^"\']+)["\']\)'
SELECT_PATTERN = r'\.select\(["\']([^"\']+)["\']\)'
FIELD_PATTERN = r'\.get\(["\']([^"\']+)["\']\)'

def find_view_usage_in_file(file_path: Path) -> List[Tuple[str, Set[str]]]:
    """Find database view usage and expected fields in a Python file."""
    views_and_fields = []
    
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Find table/view usage
        for match in re.finditer(VIEW_PATTERN, content):
            view_name = match.group(1)
            
            # Find fields accessed after this view
            fields = set()
            
            # Look for .get() calls after this view reference
            view_context = content[match.end():match.end()+500]  # Next 500 chars
            for field_match in re.finditer(FIELD_PATTERN, view_context):
                fields.add(field_match.group(1))
            
            # Also check for field names in comments or docstrings
            if view_name.endswith('_analytics') or 'view' in view_name.lower():
                # Look for field names in comments
                comment_pattern = r'#.*?(\w+_referrals|\w+_revenue|\w+_earned|\w+_balance)'
                for comment_match in re.finditer(comment_pattern, content):
                    fields.add(comment_match.group(1))
            
            if fields:
                views_and_fields.append((view_name, fields))
    
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return views_and_fields

def find_views_in_migrations() -> Dict[str, Set[str]]:
    """Find all views and their fields in migration files."""
    views = {}
    migrations_dir = Path('supabase/migrations')
    
    if not migrations_dir.exists():
        return views
    
    for migration_file in sorted(migrations_dir.glob('*.sql')):
        try:
            content = migration_file.read_text(encoding='utf-8')
            
            # Find CREATE VIEW statements
            view_pattern = r'CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)\s+AS'
            for match in re.finditer(view_pattern, content, re.IGNORECASE):
                view_name = match.group(1)
                
                # Extract SELECT fields
                select_start = content.find('SELECT', match.end())
                if select_start == -1:
                    continue
                
                # Find fields in SELECT (simplified - just column names)
                field_pattern = r'\s+(\w+)\s+AS\s+(\w+)'
                fields = set()
                
                # Get SELECT clause (up to FROM)
                from_pos = content.find('FROM', select_start)
                if from_pos == -1:
                    continue
                
                select_clause = content[select_start:from_pos]
                for field_match in re.finditer(field_pattern, select_clause, re.IGNORECASE):
                    alias = field_match.group(2)
                    fields.add(alias)
                
                # Also get direct column names without AS
                direct_pattern = r'\s+(\w+)(?:,|\s+FROM)'
                for direct_match in re.finditer(direct_pattern, select_clause):
                    field = direct_match.group(1).strip()
                    if field.upper() not in ['SELECT', 'DISTINCT', 'COUNT', 'SUM', 'COALESCE']:
                        fields.add(field)
                
                views[view_name] = fields
                
        except Exception as e:
            print(f"Error reading migration {migration_file}: {e}")
    
    return views

def check_mismatches():
    """Check for mismatches between views and API expectations."""
    print("🔍 Checking for database view and API mismatches...\n")
    
    # Find views in migrations
    print("📊 Scanning migration files...")
    views_in_db = find_views_in_migrations()
    print(f"   Found {len(views_in_db)} views in migrations")
    
    # Find API usage
    print("\n🔌 Scanning API code...")
    api_dir = Path('core/routers')
    api_views = {}
    
    if api_dir.exists():
        for py_file in api_dir.rglob('*.py'):
            views_and_fields = find_view_usage_in_file(py_file)
            for view_name, fields in views_and_fields:
                if view_name not in api_views:
                    api_views[view_name] = set()
                api_views[view_name].update(fields)
    
    print(f"   Found {len(api_views)} views used in API")
    
    # Check for mismatches
    print("\n⚠️  Checking for mismatches...\n")
    issues = []
    
    for view_name, api_fields in api_views.items():
        if view_name not in views_in_db:
            issues.append(f"❌ View '{view_name}' used in API but not found in migrations")
            continue
        
        db_fields = views_in_db[view_name]
        missing_fields = api_fields - db_fields
        
        if missing_fields:
            issues.append(
                f"❌ View '{view_name}' missing fields: {', '.join(sorted(missing_fields))}"
            )
    
    # Check for views in DB but not used
    for view_name in views_in_db:
        if view_name not in api_views:
            print(f"ℹ️  View '{view_name}' exists in DB but not used in API (might be OK)")
    
    if issues:
        print("Found issues:\n")
        for issue in issues:
            print(f"  {issue}")
        print("\n💡 Fix: Update view in migration file to include missing fields")
        return 1
    else:
        print("✅ No mismatches found!")
        return 0

if __name__ == '__main__':
    exit(check_mismatches())

