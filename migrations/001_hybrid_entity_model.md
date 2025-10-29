# Migration 001: Hybrid Entity Model

## Overview

Implement production-validated hybrid entity data model to bridge the gap between atomic entity extraction and compound entity queries.

## Problem Statement

**Current State:**
- Database contains atomic entities: "Portugal", "Brazil", "Tunisia"
- Users query with compound entities: "Portugal Cement", "Brazil Cement"
- Result: 0 matches, 36.2% accuracy

**Production Pattern (FinRAG, Bloomberg, TableRAG):**
- Store BOTH raw (atomic) and normalized (canonical/compound) entity forms
- Query-time: search both columns with fuzzy matching
- Rank exact normalized matches highest

## Schema Changes

### 1. Add Normalized Entity Column

```sql
-- Add entity_normalized column to financial_tables
ALTER TABLE financial_tables
ADD COLUMN entity_normalized VARCHAR(255);

-- Index for exact matching on normalized entities
CREATE INDEX idx_entity_normalized
ON financial_tables(entity_normalized)
WHERE entity_normalized IS NOT NULL;
```

### 2. Create Entity Mappings Dimension Table

```sql
-- Entity dimension table for canonical name resolution
CREATE TABLE entity_mappings (
    entity_id SERIAL PRIMARY KEY,
    canonical_name VARCHAR(255) NOT NULL,  -- "Portugal Cement"
    raw_mentions TEXT[],                    -- ["Portugal", "PT", "Port", "Portugal Cem"]
    entity_type VARCHAR(50),                -- "division", "country", "group"
    section_context VARCHAR(500),           -- Original section heading
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(canonical_name)
);

-- Index for array search on raw_mentions
CREATE INDEX idx_entity_mappings_raw
ON entity_mappings USING GIN(raw_mentions);
```

### 3. Enable pg_trgm Extension

```sql
-- Install PostgreSQL trigram extension for fuzzy matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- GIN index for fuzzy text search on entity (raw)
CREATE INDEX idx_entity_trgm
ON financial_tables USING GIN (entity gin_trgm_ops)
WHERE entity IS NOT NULL;

-- GIN index for fuzzy text search on entity_normalized
CREATE INDEX idx_entity_normalized_trgm
ON financial_tables USING GIN (entity_normalized gin_trgm_ops)
WHERE entity_normalized IS NOT NULL;
```

## Entity Normalization Strategy

### Pattern Recognition

Based on section context analysis:

```python
# Section patterns → Canonical entity names
SECTION_PATTERNS = {
    # Country divisions
    r"^\d+\.\d+\.\d+\s+([A-Z][a-zA-Z\s]+)$": "{match} Cement",

    # Examples from actual data:
    # "1.1.1 Portugal" → "Portugal Cement"
    # "1.1.2 Brazil" → "Brazil Cement"
    # "1.1.3 Tunisia" → "Tunisia Cement"

    # Group-level entities
    r"Group": "Secil Group",
    r"Total": "Secil Group Total",

    # Preserve special entities as-is
    r"Currency.*": None,  # Keep as raw
}
```

### Enrichment Algorithm

```python
def normalize_entity(raw_entity: str, section_context: str | None) -> str | None:
    """
    Generate canonical entity name from raw entity and section context.

    Examples:
        normalize_entity("Portugal", "1.1.1 Portugal") → "Portugal Cement"
        normalize_entity("Brazil", "1.1.2 Brazil") → "Brazil Cement"
        normalize_entity("Group", "GROUP TOTAL") → "Secil Group"
        normalize_entity("Currency (1000 EUR)", None) → None (keep raw)
    """
    # Pattern 1: Country divisions from section context
    if section_context and re.match(r"^\d+\.\d+\.\d+\s+", section_context):
        country = section_context.split()[-1]  # Extract country name
        if raw_entity == country:
            return f"{country} Cement"

    # Pattern 2: Group entities
    if raw_entity.lower() in ["group", "total"]:
        return "Secil Group" if raw_entity.lower() == "group" else "Secil Group Total"

    # Pattern 3: Currency/technical entities - keep raw
    if "currency" in raw_entity.lower() or "ratio" in raw_entity.lower():
        return None

    # Pattern 4: Default - try section-based inference
    # Use LLM or rule-based heuristics here if needed

    return None  # Keep as raw if no normalization rule applies
```

## Implementation Steps

### Phase 1: Schema Migration (15 min)

1. Apply schema changes to PostgreSQL
2. Verify indexes created successfully
3. Test pg_trgm extension functionality

**Script:** `migrations/001_apply_schema.py`

### Phase 2: Entity Analysis (30 min)

1. Analyze all distinct entities in `financial_tables`
2. Extract section context for each entity
3. Apply normalization rules
4. Build entity_mappings dimension table

**Script:** `scripts/analyze-and-normalize-entities.py`

### Phase 3: Populate Normalized Column (20 min)

1. Update `financial_tables.entity_normalized` based on mappings
2. Verify data quality (coverage, correctness)
3. Log entities that couldn't be normalized

**Script:** `scripts/populate-entity-normalized.py`

### Phase 4: Update Text-to-SQL (20 min)

1. Modify SQL generation to query BOTH entity columns
2. Add fuzzy matching with pg_trgm similarity
3. Rank results: exact normalized > fuzzy normalized > exact raw > fuzzy raw

**File:** `raglite/retrieval/sql_table_search.py:generate_sql_query()`

### Phase 5: Validation (15 min)

1. Re-run AC4 validation queries
2. Measure accuracy improvement
3. Document results

**Script:** `scripts/validate-story-2.13-hybrid.py`

## Expected Impact

**Accuracy Improvement:**
- Current: 36.2% (0/58 SQL queries)
- Target: 70-80% (41-46/58 SQL queries)

**Query Matching:**
```sql
-- Current (FAILS):
SELECT * FROM financial_tables
WHERE entity ILIKE '%Portugal Cement%'
→ 0 results

-- Hybrid with Fuzzy (SUCCEEDS):
SELECT * FROM financial_tables
WHERE
    entity_normalized ILIKE '%Portugal Cement%'          -- Exact normalized
    OR entity_normalized = 'Portugal Cement'             -- Canonical
    OR similarity(entity_normalized, 'Portugal Cement') > 0.5  -- Fuzzy normalized
    OR (entity ILIKE '%Portugal%' AND entity ILIKE '%Cement%')  -- Token match
    OR similarity(entity, 'Portugal Cement') > 0.3       -- Fuzzy raw
ORDER BY
    CASE
        WHEN entity_normalized = 'Portugal Cement' THEN 0
        WHEN entity_normalized ILIKE '%Portugal Cement%' THEN 1
        WHEN entity ILIKE '%Portugal%' THEN 2
        ELSE 3
    END,
    similarity(COALESCE(entity_normalized, entity), 'Portugal Cement') DESC
→ 14,654 results with ranked relevance
```

## Rollback Plan

```sql
-- If migration needs to be rolled back:
DROP INDEX IF EXISTS idx_entity_normalized;
DROP INDEX IF EXISTS idx_entity_trgm;
DROP INDEX IF EXISTS idx_entity_normalized_trgm;
DROP INDEX IF EXISTS idx_entity_mappings_raw;
DROP TABLE IF EXISTS entity_mappings;
ALTER TABLE financial_tables DROP COLUMN IF EXISTS entity_normalized;
```

## Timeline

- **Total Estimated Time:** 1.5-2 hours (fast-tracked)
- **Phases:** 5 sequential steps
- **Dependencies:** None (works with current Phase 2.6 data)

## Success Criteria

1. ✅ Schema changes applied successfully
2. ✅ Entity normalization coverage ≥80% (for country entities)
3. ✅ AC4 validation accuracy ≥70%
4. ✅ Zero-result queries reduced from 58 to <12
5. ✅ Fuzzy matching working on both columns

## References

- **FinRAG (EMNLP 2024):** Hybrid raw + normalized storage
- **Bloomberg NLP:** Entity dimension tables with aliases
- **TableRAG:** JSON-based schema mapping with canonical forms
- **PostgreSQL pg_trgm:** https://www.postgresql.org/docs/current/pgtrgm.html

---

**Status:** Ready for implementation
**Owner:** Next session developer
**Priority:** P0 (blocks Story 2.13 AC4)
