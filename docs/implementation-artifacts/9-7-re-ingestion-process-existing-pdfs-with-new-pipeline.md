# Story 9.7: Re-ingestion - Process Existing PDFs with New Pipeline

**Epic:** [Epic 9 - Data Quality at Ingestion](../epics/epic-9-tracking.md)

Status: done

## Story

As a data engineer,
I want to re-ingest all existing production PDFs (33 documents) using the classification-enabled pipeline,
so that all financial data has period_type, value_type, and entity_level fields populated, enabling simplified forecasting queries and validating the Epic 9 classification accuracy targets.

## Background

**Current Production Data:**
- Qdrant: 6,625 vectors across 33 PDFs
- PostgreSQL: 78,759 rows in `financial_tables` (all classification columns currently NULL)
- PostgreSQL: 14 rows in `financial_chunks`

**Completed Prerequisites:**
- Story 9.1: Schema migration added period_type, value_type, entity_level columns
- Story 9.2-9.4: Classification modules implemented (period, value type, entity level)
- Story 9.5: Classification integrated into extraction pipeline (`classify_rows_batch`)
- Story 9.6: Storage layer now persists classification fields to PostgreSQL

**Purpose:**
Re-process all existing documents so that:
1. All 78,759+ table rows have classification fields populated (no NULLs)
2. Classification coverage report generated for quality verification
3. Accuracy validated against ground truth expectations (95%+ period_type)

## Acceptance Criteria (BDD Format)

### AC1: Re-ingestion Script Updates

```gherkin
Given the existing scripts/reingest-all-documents.py script
And the classification-enabled ingestion pipeline from Stories 9.5 and 9.6
When the re-ingestion script is executed
Then it uses the updated ingest_document() which includes classification
And classification fields are automatically populated via the Story 9.5 integration
And the script supports all 33 production PDFs (not just the original 10)
And execution can be parallelized with --parallel N flag for faster processing
And progress is reported with classification summary per document
```

### AC2: Production Data Cleanup

```gherkin
Given the production databases contain existing data:
  - Qdrant: 6,625 vectors in financial_docs collection
  - PostgreSQL: 78,759 rows in financial_tables
When preparing for re-ingestion
Then a full backup is created using scripts/backup-all.sh
And backup files are verified before proceeding
And old data is cleared ONLY after backup verification
And Qdrant collection is recreated (delete + create with same schema)
And PostgreSQL financial_tables data is truncated (schema preserved)
And financial_chunks table is truncated
And SafetyGuard patterns from .claude/rules/database-safety.md are followed
And --dry-run flag is supported to preview actions without executing
```

### AC3: Classification Coverage Validation

```gherkin
Given re-ingestion is complete for all 33 documents
When validating classification coverage
Then 100% of rows have period_type populated (no NULLs)
And 100% of rows have value_type populated (no NULLs)
And 100% of rows have entity_level populated (no NULLs)
And validation query confirms: SELECT COUNT(*) FROM financial_tables WHERE period_type IS NULL = 0
And classification breakdown is generated:
  | Classification | Count | Percentage |
  |----------------|-------|------------|
  | monthly_actual | X     | Y%         |
  | ytd_actual     | X     | Y%         |
  | budget         | X     | Y%         |
  | unknown        | X     | Y%         |
And coverage report is saved to docs/sprint-artifacts/classification-coverage-report.md
```

### AC4: Classification Accuracy Validation

```gherkin
Given a ground truth dataset exists with expected classifications:
  - tests/fixtures/classification_ground_truth.json (50+ manually verified rows)
When comparing re-ingested data against ground truth
Then period_type accuracy is >= 95% (per Epic 9 AC1)
And value_type accuracy is >= 90%
And entity_level accuracy is >= 90%
And misclassifications are logged for review
And accuracy report is generated with:
  | Metric       | Expected | Actual | Status |
  |--------------|----------|--------|--------|
  | period_type  | >= 95%   | X%     | PASS/FAIL |
  | value_type   | >= 90%   | X%     | PASS/FAIL |
  | entity_level | >= 90%   | X%     | PASS/FAIL |
```

### AC5: Re-ingestion Performance Metrics

```gherkin
Given re-ingestion processes 33 PDFs with 78,759+ table rows
When tracking performance
Then total re-ingestion time is recorded
And per-document timing is logged:
  | Document | Pages | Tables | Rows | Duration | Rows/sec |
  |----------|-------|--------|------|----------|----------|
Then average classification overhead is calculated (extraction time with vs without classification)
And overhead confirms <20% increase per Epic 9 AC4
And throughput metrics are saved to docs/sprint-artifacts/re-ingestion-metrics.md
```

### AC6: Error Handling and Recovery

```gherkin
Given re-ingestion may encounter failures on individual documents
When a document fails to ingest
Then the error is logged with full context (document name, page, error message)
And processing continues with remaining documents (fail-forward)
And failed documents are tracked in a failures list
And at completion, a retry mechanism can re-process only failed documents
And partial success is acceptable (report which succeeded/failed)
And rollback to backup is documented if critical failure occurs
```

## Tasks / Subtasks

- [ ] Task 1: Update re-ingestion script for all 33 documents (AC: #1)
  - [ ] 1.1: Discover all 33 PDFs in production (query Qdrant for unique source_document values)
  - [ ] 1.2: Update DOCUMENTS list to include all 33 PDFs with correct paths
  - [ ] 1.3: Add --parallel N flag for concurrent ingestion (default: sequential)
  - [ ] 1.4: Add classification summary output per document
  - [ ] 1.5: Update estimated time based on parallel option

- [ ] Task 2: Create production data cleanup script (AC: #2)
  - [ ] 2.1: Create scripts/prepare-reingestion.py with backup verification
  - [ ] 2.2: Implement SafetyGuard checks before any destructive operations
  - [ ] 2.3: Add --dry-run mode to preview actions
  - [ ] 2.4: Implement Qdrant collection recreation (delete_collection + create_collection)
  - [ ] 2.5: Implement PostgreSQL TRUNCATE for financial_tables and financial_chunks
  - [ ] 2.6: Add explicit user confirmation prompt before cleanup

- [ ] Task 3: Create classification coverage validation script (AC: #3)
  - [ ] 3.1: Create scripts/validate-classification-coverage.py
  - [ ] 3.2: Query PostgreSQL for NULL counts in classification columns
  - [ ] 3.3: Generate classification breakdown by type
  - [ ] 3.4: Output coverage report in markdown format
  - [ ] 3.5: Return exit code 0 if 100% coverage, 1 otherwise

- [ ] Task 4: Create classification accuracy validation (AC: #4)
  - [ ] 4.1: Create tests/fixtures/classification_ground_truth.json with 50+ verified examples
  - [ ] 4.2: Create scripts/validate-classification-accuracy.py
  - [ ] 4.3: Compare database rows against ground truth by document/page/row identifiers
  - [ ] 4.4: Calculate accuracy percentages for each classification type
  - [ ] 4.5: Log misclassifications for manual review
  - [ ] 4.6: Generate accuracy report in markdown format

- [ ] Task 5: Add performance tracking (AC: #5)
  - [ ] 5.1: Add timing instrumentation to re-ingestion script
  - [ ] 5.2: Calculate and log per-document metrics (pages, tables, rows, duration, rows/sec)
  - [ ] 5.3: Calculate total re-ingestion duration
  - [ ] 5.4: Compare against baseline (pre-classification) ingestion time if available
  - [ ] 5.5: Generate performance report in markdown format

- [ ] Task 6: Implement error handling and recovery (AC: #6)
  - [ ] 6.1: Add try/except per document with error logging
  - [ ] 6.2: Track failed documents in separate list
  - [ ] 6.3: Add --retry-failed mode to re-process only failures
  - [ ] 6.4: Generate summary report with success/failure counts
  - [ ] 6.5: Document rollback procedure in script docstring

- [ ] Task 7: Unit tests for new scripts (AC: #1-6)
  - [ ] 7.1: Test backup verification logic
  - [ ] 7.2: Test dry-run mode prevents destructive operations
  - [ ] 7.3: Test coverage calculation logic
  - [ ] 7.4: Test accuracy calculation against mock ground truth
  - [ ] 7.5: Test error handling continues processing after failures

- [ ] Task 8: Integration tests (AC: #1-6)
  - [ ] 8.1: Create tests/integration/test_reingestion_pipeline.py
  - [ ] 8.2: Test full pipeline: backup -> cleanup -> reingest -> validate on test database
  - [ ] 8.3: Verify classification fields populated after re-ingestion
  - [ ] 8.4: Test with sample PDF subset (2-3 documents)

- [ ] Task 9: Execute production re-ingestion (AC: #1-6)
  - [ ] 9.1: Run prepare-reingestion.py --dry-run to preview
  - [ ] 9.2: Execute backup using scripts/backup-all.sh
  - [ ] 9.3: Run prepare-reingestion.py to clear production data
  - [ ] 9.4: Execute reingest-all-documents.py (with parallel if desired)
  - [ ] 9.5: Run validate-classification-coverage.py
  - [ ] 9.6: Run validate-classification-accuracy.py
  - [ ] 9.7: Archive reports to docs/sprint-artifacts/

## Dev Notes

### Production Database Access

Per `.claude/rules/database-safety.md`:

```python
# REQUIRED: SafetyGuard pattern for production operations
from raglite.shared.safety import SafetyGuard, ProductionProtectionError

guard = SafetyGuard()

# This script intentionally operates on production
# Use explicit flag to bypass protection
if not args.force_production:
    raise ProductionProtectionError("Use --force-production flag for production operations")
```

### Document Discovery (All 33 PDFs)

```python
# Query Qdrant for unique source documents
from qdrant_client import QdrantClient
from collections import Counter

client = QdrantClient(host='localhost', port=6333)
docs = Counter()
points, _ = client.scroll('financial_docs', limit=10000, with_payload=['source_document'])
for point in points:
    doc = point.payload.get('source_document', 'unknown')
    docs[doc] += 1

print(f"Found {len(docs)} unique documents")
for doc, count in docs.most_common():
    print(f"  {doc}: {count} chunks")
```

### PDF Locations

Based on existing script and production data:
- Primary: `/Users/ricardocarvalho/Downloads/OneDrive_1_11-25-2025 2/`
- Additional PDFs may be in subdirectories or alternate locations
- Discovery script should search recursively if needed

### Backup Before Re-ingestion

```bash
# REQUIRED before any production data modification
./scripts/backup-all.sh

# Verify backup files exist
ls -la backups/postgresql_backup_*.sql
ls -la backups/qdrant_snapshot_*/
```

### Cleanup Script Pattern

```python
# scripts/prepare-reingestion.py

import argparse
from qdrant_client import QdrantClient
import psycopg2

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Preview without executing')
    parser.add_argument('--force-production', action='store_true', help='Required for production')
    args = parser.parse_args()

    if args.dry_run:
        print("[DRY RUN] Would perform the following actions:")
        print("  1. Delete Qdrant collection 'financial_docs'")
        print("  2. Recreate Qdrant collection with same schema")
        print("  3. TRUNCATE financial_tables")
        print("  4. TRUNCATE financial_chunks")
        return 0

    if not args.force_production:
        print("ERROR: Use --force-production flag for production operations")
        return 1

    # Verify backup exists
    if not verify_backup_exists():
        print("ERROR: No recent backup found. Run scripts/backup-all.sh first")
        return 1

    # Prompt for confirmation
    response = input("This will DELETE all production data. Type 'DELETE' to confirm: ")
    if response != 'DELETE':
        print("Aborted")
        return 1

    # Execute cleanup...
```

### Parallel Ingestion Option

```python
import asyncio
from concurrent.futures import ProcessPoolExecutor

async def ingest_parallel(documents: list[str], max_workers: int = 4):
    """Ingest documents in parallel using process pool."""
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        tasks = [
            loop.run_in_executor(executor, ingest_document_sync, doc)
            for doc in documents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Classification Ground Truth Format

```json
// tests/fixtures/classification_ground_truth.json
{
  "version": "1.0",
  "created": "2026-02-01",
  "entries": [
    {
      "document": "2024-12 Performance Review CONSO_v1.pdf",
      "page": 12,
      "table_index": 0,
      "row_index": 5,
      "period": "Dec-24",
      "entity": "Portugal Cement",
      "expected_period_type": "monthly_actual",
      "expected_value_type": "actual",
      "expected_entity_level": "company_only"
    }
    // ... 50+ entries covering edge cases
  ]
}
```

### Validation Queries

```sql
-- Coverage validation (AC3)
SELECT
  COUNT(*) as total_rows,
  COUNT(period_type) as with_period_type,
  COUNT(value_type) as with_value_type,
  COUNT(entity_level) as with_entity_level,
  SUM(CASE WHEN period_type IS NULL THEN 1 ELSE 0 END) as null_period_type,
  SUM(CASE WHEN value_type IS NULL THEN 1 ELSE 0 END) as null_value_type,
  SUM(CASE WHEN entity_level IS NULL THEN 1 ELSE 0 END) as null_entity_level
FROM financial_tables;

-- Classification breakdown (AC3)
SELECT period_type, COUNT(*) as count,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as percentage
FROM financial_tables
GROUP BY period_type
ORDER BY count DESC;

-- Sample verification (AC4)
SELECT document_id, page_number, table_index, row_index,
       entity, metric, period,
       period_type, value_type, entity_level
FROM financial_tables
WHERE document_id LIKE '%2024-12%'
LIMIT 20;
```

### Report Output Location

All reports saved to `docs/sprint-artifacts/`:
- `classification-coverage-report.md` - AC3 coverage validation
- `classification-accuracy-report.md` - AC4 ground truth comparison
- `re-ingestion-metrics.md` - AC5 performance data
- `re-ingestion-summary.md` - Overall success/failure summary

### Performance Baseline

From Story 9.5 Dev Notes:
- Classification overhead: ~10ms per 100 rows (~4% of extraction time)
- Expected total overhead: <20% (Epic 9 AC4)

For 78,759 rows:
- Estimated classification time: ~8 seconds
- Original ingestion time (33 PDFs): ~3-4 hours
- Expected re-ingestion time: ~3.5-4.5 hours (sequential)
- With --parallel 4: ~1-1.5 hours

### Error Recovery Procedure

If re-ingestion fails mid-process:

1. Check error logs for failed documents
2. Run `--retry-failed` to re-process only failures
3. If critical failure, restore from backup:
   ```bash
   # Restore PostgreSQL
   docker exec -i raglite-postgresql psql -U raglite -d raglite < backups/postgresql_backup_YYYYMMDD_HHMMSS.sql

   # Restore Qdrant (see backups/README.md for snapshot recovery)
   ```

### Dependencies

- **Requires:** Story 9.1 (schema), 9.2-9.4 (classifiers), 9.5 (integration), 9.6 (storage)
- **Enables:** Story 9.8 (forecasting query simplification)
- **Enables:** Story 9.9 (validation - verify data quality improvement)

### File Size Constraints

Per `.claude/rules/file-size-limits.md`:
- Each script should be <300 LOC (well within limit)
- Shared utilities can be extracted if needed

### Test Organization

- Unit tests: `tests/unit/scripts/test_reingestion.py`
- Integration tests: `tests/integration/test_reingestion_pipeline.py`
- Acceptance tests: `tests/acceptance/story_9_7/` (if ATDD approach used)

### References

- [Source: scripts/reingest-all-documents.py] - Existing sequential re-ingestion script
- [Source: scripts/backup-all.sh] - Database backup script
- [Source: .claude/rules/database-safety.md] - SafetyGuard patterns
- [Source: raglite/ingestion/document_ingestion.py] - Main ingestion entry point
- [Source: raglite/ingestion/classification/integration.py] - Story 9.5 classification integration
- [Source: raglite/ingestion/storage/table_store.py] - Story 9.6 storage with classification
- [Source: docs/epics/epic-9-tracking.md] - Epic requirements (95% period_type accuracy)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
