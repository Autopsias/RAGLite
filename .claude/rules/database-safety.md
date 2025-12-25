# Database Operation Safety

**CRITICAL:** All database operations must follow the three-mode system.

---

## Three-Mode System

| Mode | Use Case | Ports | Can Delete? |
|------|----------|-------|-------------|
| **TEST** | pytest, CI | 6335/5433 | Yes (test data only) |
| **PRODUCTION READ/WRITE** | MCP, queries | 6333/5432 | **NO** |
| **PRODUCTION DEPLOY** | Schema updates | 6333/5432 | Only with `--force-data-loss` |

See `docs/architecture/database-operation-modes.md` for full documentation.

---

## Key Safety Rules

1. Tests MUST use `APP_ENV=test` and will **FAIL** if they detect production ports
2. Use `scripts/deploy-to-production.py` for schema updates to production
3. NEVER call `delete_collection()` directly on production - use SafetyGuard
4. All database operations must use `SafetyGuard` class from `raglite/shared/safety.py`

---

## Required Pattern

```python
from raglite.shared.safety import SafetyGuard, ProductionProtectionError

guard = SafetyGuard()
guard.validate_test_environment("my_fixture")  # Raises if on production ports!
```

---

## Database Discovery

### Production Data Locations

| Database | Port | Container | Collection/Table | Row Count |
|----------|------|-----------|------------------|-----------|
| **Qdrant** | 6333 | raglite-qdrant | `financial_docs` | 6,625 vectors (33 PDFs) |
| **PostgreSQL** | 5432 | raglite-postgresql | `financial_tables` | 78,759 rows |
| **PostgreSQL** | 5432 | raglite-postgresql | `financial_chunks` | 14 rows |

### Test Database Ports (safe for modifications)
- Qdrant test: `localhost:6335`
- PostgreSQL test: `localhost:5433`

---

## Quick Access Commands

```bash
# Count Qdrant vectors
python3 -c "from qdrant_client import QdrantClient; c=QdrantClient('localhost',6333); print(c.get_collection('financial_docs').points_count)"

# List unique documents in Qdrant
python3 -c "
from qdrant_client import QdrantClient
from collections import Counter
c=QdrantClient('localhost',6333)
docs=Counter()
for p in c.scroll('financial_docs',limit=10000,with_payload=['source_document'])[0]:
    docs[p.payload.get('source_document','unknown')]+=1
print(f'{len(docs)} documents'); [print(f'  {d}: {n} chunks') for d,n in docs.most_common(5)]
"

# Count PostgreSQL rows
docker exec raglite-postgresql psql -U raglite -d raglite -c "SELECT COUNT(*) FROM financial_tables"

# List PostgreSQL tables
docker exec raglite-postgresql psql -U raglite -d raglite -c "\dt"
```

---

## Qdrant Payload Fields

- `source_document` - Original PDF filename
- `text` - Chunk content
- `page_number` - Source page
- `chunk_index` - Position in document
- `section_type` - "Table", "Text", etc.
- `document_type` - "Income Statement", "Cash Flow Statement", etc.
- `reporting_period` - "May-24", "Oct-25", etc.

---

## Python Access Patterns

```python
# Qdrant (vector search)
from qdrant_client import QdrantClient
qdrant = QdrantClient(host='localhost', port=6333)
results = qdrant.search(collection_name='financial_docs', query_vector=embedding, limit=10)

# PostgreSQL (structured queries) - via Docker
# docker exec raglite-postgresql psql -U raglite -d raglite -c "SELECT * FROM financial_tables LIMIT 5"
```

---

## Container Volume Mount Issues

### Problem: "Databases Empty" Despite Data on Disk

If Qdrant/PostgreSQL report empty databases but `qdrant_storage/` or `postgresql_data/` contain data:

**Root cause:** Docker containers have stale volume mounts pointing to wrong paths (often from CI runs).

### Diagnosis

```bash
# Check current mount paths
docker inspect raglite-qdrant --format='{{range .Mounts}}{{.Source}}{{end}}'
docker inspect raglite-postgresql --format='{{range .Mounts}}{{.Source}}{{end}}'

# Run verification script
./scripts/verify-containers.sh
```

### Fix

```bash
# Recreate containers with correct mounts
docker stop raglite-qdrant raglite-postgresql
docker rm raglite-qdrant raglite-postgresql
docker-compose up -d qdrant postgresql
```

### Prevention

**Development Startup (recommended):**
```bash
# Run this when starting a new dev session
./scripts/start-dev.sh
```

This script:
1. Verifies container volume mounts are correct
2. Recreates containers if mounts are wrong
3. Waits for services to be ready
4. Confirms data is accessible

**CI Isolation (automatic):**
- CI jobs use unique container names: `-test`, `-agentic`, `-discovery`, `-burnin`
- CI containers use ephemeral storage (tmpfs), NOT production volumes
- CI cleanup removes all CI containers after each job
- Production containers (`raglite-qdrant`, `raglite-postgresql`) are NEVER touched by CI

**Container Naming Convention:**
| Context | Qdrant Container | PostgreSQL Container |
|---------|------------------|----------------------|
| **Production** | `raglite-qdrant` | `raglite-postgresql` |
| **Unit Tests** | `raglite-qdrant-test` | `raglite-postgresql-test` |
| **CI Agentic** | `raglite-qdrant-agentic` | `raglite-postgresql-agentic` |
| **CI Discovery** | `raglite-qdrant-discovery` | `raglite-postgresql-discovery` |
| **CI Burn-in** | `raglite-qdrant-burnin` | `raglite-postgresql-burnin` |
