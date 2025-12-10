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
