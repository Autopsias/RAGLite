# Database Migrations

**Story 4.0.7**: Three-Mode Database Operation System

This directory contains PostgreSQL schema migrations for RAGLite.

## Naming Convention

Migrations are numbered sequentially:
- `000_schema_versions.sql` - Schema version tracking (bootstrap)
- `001_feature_name.sql` - First feature migration
- `002_another_feature.sql` - Second feature migration

## Migration Rules

1. **Idempotent**: Each migration must be safe to run multiple times
2. **Forward-only**: No rollback migrations (keep it simple for MVP)
3. **Non-destructive by default**: Never delete data without explicit consent
4. **Version tracking**: Each migration inserts itself into `schema_versions`

## Template

```sql
-- Migration: NNN_feature_name
-- Story: X.Y - Story Name
-- Purpose: Brief description
-- Created: YYYY-MM-DD

-- Your schema changes here
-- Use CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS, etc.

-- Track this migration
INSERT INTO schema_versions (version, name, applied_by)
VALUES (NNN, 'NNN_feature_name', 'deploy-to-production.py')
ON CONFLICT (version) DO NOTHING;
```

## Running Migrations

**Never run migrations directly on production!**

Use the deployment script:

```bash
# Dry-run (see what would change)
python scripts/deploy-to-production.py --dry-run

# Apply migrations
python scripts/deploy-to-production.py --deploy-production
```

## See Also

- `docs/architecture/database-operation-modes.md` - Full documentation
- `scripts/deploy-to-production.py` - Safe deployment script
- `raglite/shared/safety.py` - SafetyGuard implementation
