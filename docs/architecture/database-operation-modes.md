# Database Operation Modes

> **Story 4.0.7**: Three-Mode Database Operation System
> **Created**: 2025-11-27 (after production data loss incident)
> **Status**: ACTIVE - All agents and developers MUST follow these rules

## Overview

RAGLite uses a **three-mode database operation system** to prevent accidental data loss
while enabling safe development and deployment workflows. This system was implemented
after a critical incident on 2025-11-27 where the VS Code test runner deleted production data.

## The Three Modes

### Mode 1: TEST (pytest, CI)

**Purpose**: Full control for testing - can create, delete, and clear data freely.

| Aspect | Value |
|--------|-------|
| **Qdrant Port** | 6335 |
| **PostgreSQL Port** | 5433 |
| **Collection Names** | `financial_docs_test`, `financial_docs_ci` |
| **Allowed Operations** | CREATE, DELETE, CLEAR, DROP (full control) |
| **Blocked Operations** | Cannot access production ports 6333/5432 |
| **Trigger** | `APP_ENV=test` environment variable |

**Key Protection**: `SafetyGuard.validate_test_environment()` HARD BLOCKS any test
attempting to run on production infrastructure.

```python
# Tests MUST run with APP_ENV=test
# SafetyGuard.validate_test_environment() will BLOCK if on production ports
os.environ["APP_ENV"] = "test"
```

### Mode 2: PRODUCTION READ/WRITE (MCP, normal operations)

**Purpose**: Normal application operations - read and write, but never delete.

| Aspect | Value |
|--------|-------|
| **Qdrant Port** | 6333 |
| **PostgreSQL Port** | 5432 |
| **Collection Names** | `financial_docs` |
| **Allowed Operations** | READ, INSERT, UPDATE vectors and metadata |
| **Blocked Operations** | DELETE collection, CLEAR tables, DROP |
| **Trigger** | Default when `APP_ENV=production` or unset |

**Key Protection**: `SafetyGuard.block_destructive_on_production()` prevents any
destructive operations during normal use.

```python
# Normal operations use production ports but cannot delete
# SafetyGuard blocks: delete_collection(), TRUNCATE, DROP
guard = SafetyGuard()
guard.block_destructive_on_production("delete_collection")  # Raises!
```

### Mode 3: PRODUCTION DEPLOY (explicit schema updates)

**Purpose**: Intentional production changes with explicit confirmation.

| Aspect | Value |
|--------|-------|
| **Qdrant Port** | 6333 |
| **PostgreSQL Port** | 5432 |
| **Requires** | `--deploy-production` flag + typed confirmation |
| **Allowed Operations** | Run migrations, add indexes, CREATE IF NOT EXISTS |
| **Blocked Operations** | Data deletion without `--force-data-loss` flag |
| **Trigger** | `scripts/deploy-to-production.py` script |

**Key Protection**: User must type `DEPLOY TO PRODUCTION` to confirm.

```bash
# Schema updates require explicit script
python scripts/deploy-to-production.py --deploy-production

# Data-loss operations require additional flag
python scripts/deploy-to-production.py --deploy-production --force-data-loss
```

## Safety Rules (MUST Follow)

### Rule 1: Tests NEVER Touch Production

Tests are HARD BLOCKED from accessing production ports:

- Qdrant port 6333 → BLOCKED in test mode
- PostgreSQL port 5432 → BLOCKED in test mode
- Collection without `_test` or `_ci` suffix → BLOCKED

**Enforced by**: `SafetyGuard.validate_test_environment()`

### Rule 2: Production Deletion Requires Explicit Consent

Any operation that could delete production data requires:

1. Using `scripts/deploy-to-production.py`
2. Passing `--deploy-production` flag
3. Typing `DEPLOY TO PRODUCTION` exactly
4. For data-loss operations: additional `--force-data-loss` flag

**Enforced by**: `SafetyGuard.check_operation()` with `OperationType.DESTRUCTIVE`

### Rule 3: All Operations Are Logged

Every database operation is logged with environment context:

```python
guard.log_operation("delete_collection")
# Logs: environment=PRODUCTION/TEST, ports, collection name
```

### Rule 4: Collection Names Must Have Test Suffix

Test collections MUST end with `_test` or `_ci`:

- ✅ `financial_docs_test`
- ✅ `financial_docs_ci`
- ❌ `financial_docs` (blocked in test mode)

## Usage Guidelines

### For BMAD Agents (Dev, Architect, etc.)

When implementing features that involve database operations:

1. **Always use SafetyGuard** before destructive operations
2. **Never bypass** the three-mode system
3. **Document** which mode the code operates in
4. **Test** on test infrastructure (port 6335/5433)

### For Tests

```python
# At the start of any test fixture that does database operations:
from raglite.shared.safety import SafetyGuard, ProductionProtectionError

guard = SafetyGuard()
guard.validate_test_environment("my_fixture_name")
# Raises ProductionProtectionError if on production ports
```

### For MCP/Normal Operations

```python
# Normal operations use production ports but cannot delete
# This is automatic - no special code needed
# SafetyGuard is integrated into ingest_pdf() and storage operations
```

### For Deployments

```bash
# 1. See what would change (dry-run)
python scripts/deploy-to-production.py --dry-run

# 2. Deploy schema updates (safe - no data loss)
python scripts/deploy-to-production.py --deploy-production

# 3. Re-initialize collection (DELETES existing data - use with caution!)
python scripts/deploy-to-production.py --deploy-production --force-data-loss
```

## Code Patterns

### Required Pattern: SafetyGuard for Destructive Operations

```python
from raglite.shared.safety import SafetyGuard, ProductionProtectionError, OperationType

guard = SafetyGuard()

# For test fixtures - validate test environment first
guard.validate_test_environment("fixture_name")

# For production operations - use operation classification
guard.check_operation("delete_old_vectors", OperationType.DESTRUCTIVE, force_data_loss=False)
```

### Forbidden Pattern: Direct Deletion Without SafetyGuard

```python
# ❌ WRONG - Direct deletion without SafetyGuard
qdrant.delete_collection("financial_docs")

# ❌ WRONG - Assuming environment without validation
if os.getenv("APP_ENV") == "test":
    qdrant.delete_collection(...)  # Still dangerous if port is 6333!

# ✅ CORRECT - Use SafetyGuard which checks BOTH env AND ports
guard = SafetyGuard()
guard.validate_test_environment("my_operation")
qdrant.delete_collection(...)
```

## Port Reference

| Environment | Qdrant | PostgreSQL | Collection |
|-------------|--------|------------|------------|
| Production | 6333 | 5432 | `financial_docs` |
| Local Test | 6335 | 5433 | `financial_docs_test` |
| CI Test | 6335 | 5433 | `financial_docs_ci` |

## Related Files

- **SafetyGuard implementation**: `raglite/shared/safety.py`
- **Test fixture with validation**: `tests/integration/conftest.py`
- **Deployment script**: `scripts/deploy-to-production.py`
- **Production init script**: `scripts/init-production.py`

## History

| Date | Event |
|------|-------|
| 2025-11-25 | First production data loss incident (Story 4.0.6 created) |
| 2025-11-27 | Second incident - VS Code test runner deleted production data |
| 2025-11-27 | Story 4.0.7 implemented: Three-mode system with hard port validation |
