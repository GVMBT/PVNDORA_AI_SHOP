# Database Migration & Validation Scripts

## Overview

These scripts help ensure database migrations are applied correctly and match API expectations.

## Scripts

### 0. `clean_git_tracked.py`

**Purpose:** Remove already-tracked files that should be ignored.

**Usage:**
```bash
# Preview what will be removed
python scripts/clean_git_tracked.py --dry-run

# Actually remove from git index
python scripts/clean_git_tracked.py
```

**What it does:**
- Finds files tracked in git that match .gitignore patterns
- Removes them from git index (keeps files locally)
- Helps clean up accidentally committed files

### 1. `check_db_api_mismatch.py`

**Purpose:** Check for mismatches between database views and API expectations.

**Usage:**
```bash
python scripts/check_db_api_mismatch.py
```

**What it does:**
- Scans migration files for view definitions
- Scans API code for view usage
- Compares field names
- Reports mismatches

**Example output:**
```
🔍 Checking for database view and API mismatches...

📊 Scanning migration files...
   Found 4 views in migrations

🔌 Scanning API code...
   Found 2 views used in API

⚠️  Checking for mismatches...

❌ View 'partner_analytics' missing fields: total_referrals, paying_referrals
```

### 2. `validate_migration.py`

**Purpose:** Validate a specific migration file before applying it.

**Usage:**
```bash
python scripts/validate_migration.py supabase/migrations/009_fix_partner_analytics_view.sql
```

**What it does:**
- Extracts view definitions from migration file
- Checks what fields API expects
- Reports missing or extra fields

### 3. `apply_migrations.py`

**Purpose:** List and apply pending migrations.

**Usage:**
```bash
python scripts/apply_migrations.py
```

**What it does:**
- Lists all migration files
- Shows migration SQL
- Optionally applies via Supabase CLI

## Workflow

### When Creating a Migration

1. **Create migration file:**
   ```bash
   # Create: supabase/migrations/009_descriptive_name.sql
   ```

2. **Validate migration:**
   ```bash
   python scripts/validate_migration.py supabase/migrations/009_descriptive_name.sql
   ```

3. **Apply migration:**
   - Via Supabase Dashboard SQL Editor (recommended)
   - Via Supabase CLI: `supabase db push`
   - Via MCP tool: `mcp_supabase_apply_migration`

4. **Verify:**
   ```bash
   python scripts/check_db_api_mismatch.py
   ```

### Before Committing

The pre-commit hook automatically runs `check_db_api_mismatch.py` when:
- Migration files are modified
- API files are modified

**To bypass (not recommended):**
```bash
git commit --no-verify
```

## IDE Integration (Cursor)

The IDE will automatically:

1. **Detect migration files** - When you create/modify SQL files
2. **Check for mismatches** - Run validation automatically
3. **Suggest applying migrations** - Prompt to apply via MCP tools
4. **Verify field names** - Check API code for expected fields

**Rules file:** `.cursor/rules/database-migrations.mdc`

## Common Issues

### Issue: View missing fields

**Symptom:**
```
❌ View 'partner_analytics' missing fields: total_referrals
```

**Fix:**
1. Check API code to see what fields are expected
2. Update view to include missing fields
3. Re-run validation

### Issue: Field name mismatch

**Symptom:**
```
View returns: users_attracted
API expects: total_referrals
```

**Fix:**
1. Update view to use alias: `COUNT(...) AS total_referrals`
2. Or update API to use correct field name

### Issue: Migration not applied

**Symptom:**
- View doesn't exist in database
- API returns errors

**Fix:**
1. Apply migration via Supabase Dashboard
2. Or use: `supabase db push`
3. Verify with: `mcp_supabase_list_tables`

## Best Practices

1. **Always validate before applying** - Run `validate_migration.py`
2. **Apply immediately** - Don't leave migrations unapplied
3. **Test API endpoint** - After applying, test the endpoint
4. **Check logs** - Verify no errors in runtime logs
5. **Document changes** - Add comments in migration file

## Troubleshooting

### Script not found

```bash
# Make sure you're in project root
cd /path/to/pvndora

# Check Python is available
python --version
```

### Permission denied (Linux/Mac)

```bash
chmod +x scripts/*.py
```

### Windows PowerShell

Scripts work without chmod. Just run:
```powershell
python scripts/check_db_api_mismatch.py
```

