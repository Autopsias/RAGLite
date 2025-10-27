# Story 2.14: SQL Generation Edge Case Refinement + Backend Integration

**Status:** Draft → IN PROGRESS (Scope Expanded)
**Epic:** Epic 2 - Advanced RAG Architecture Enhancement
**Phase:** Phase 2A-REVISED (SQL Table Search)
**Priority:** 🔴 CRITICAL (Epic 2 completion blocker)
**Effort:** 10 days (2 weeks)
**Depends On:** Story 2.13 (SQL Table Search - AC1-AC3 complete), Story 2.11 (Hybrid Search Scoring - COMPLETE)
**Scope Expansion Date:** 2025-10-27 (per Story 2.11 Senior Developer Review)

## Story

As a **RAG retrieval system**,
I want **SQL backend integration to reliably return results for financial queries AND text-to-SQL generation to handle entity variations, multi-entity queries, calculated metrics, budget periods, currency requests, and value extraction**,
so that **retrieval accuracy improves from 4% baseline to ≥70% target and Epic 2 Phase 2A is complete**.

## Context - SCOPE EXPANDED 2025-10-27

**Story 2.11 Discovery (Senior Developer Review):**
Story 2.11 (Hybrid Search Scoring) successfully fixed the hybrid search scoring bug (AC1-AC3 complete), but **AC4 validation revealed a critical SQL backend issue:**

- ❌ PostgreSQL `financial_tables` returning **0 results for ALL SQL queries**
- ❌ Vector-only search maxes out at 22-28% accuracy (insufficient for 70% target)
- ✅ Story 2.11 correctly fixed hybrid search scoring mechanics
- 🔄 Story 2.14 must now include SQL backend integration + edge case refinement

**Scope Expansion Rationale:**
- Story 2.11 fixed scoring: Hybrid search fusion now works correctly
- Story 2.14 must fix backend: SQL queries now need to actually return data
- Combined: 2.11 (scoring) + 2.14 (SQL backend) → 70%+ accuracy achievable
- Critical path: SQL backend fix is blocking validation of edge case improvements

**Story 2.13 AC4 Validation Context (Original Scope):**
Story 2.13 AC4 validation (2025-10-27) revealed that AC1-AC3 are production-ready:
- ✅ **AC1:** 99.39% table extraction accuracy (Phase 2.7.5 Context-Aware Unit Inference)
- ✅ **AC2:** Valid text-to-SQL query generation (Mistral Small, temperature=0.0)
- ✅ **AC3:** Hybrid search orchestration (SQL + vector search, RRF fusion)

However, **AC4 accuracy validation achieved only 4% (1/25 queries passing)**. Deep analysis identified two issues:
1. **SQL Backend Issue (NEW in Story 2.14 scope):** PostgreSQL returning 0 results for all queries
2. **Edge Case Issues (Original in Story 2.14 scope):** 5 specific SQL generation patterns requiring refinement

**Key Evidence:** Query GT-002 ("What is the variable cost for Portugal Cement in August 2025?") demonstrated end-to-end functionality with valid SQL generation, correct data retrieval, and accurate answer synthesis. The 4% baseline is NOT due to broken implementation, but rather **SQL backend connectivity + edge case patterns** requiring refinement.

**Strategic Rationale:**
- Core retrieval pipeline proven working (Story 2.11 fixed scoring)
- SQL backend needs debugging (new discovery in this story)
- Edge cases are well-defined with clear solutions (original scope)
- Combined approach ensures 70%+ accuracy target
- Iterative testing approach de-risks implementation

## Acceptance Criteria

### AC0: SQL Backend Integration & Debugging (2-3 days) - CRITICAL PRIORITY

**Goal:** Fix PostgreSQL financial_tables to reliably return results for SQL queries

**Problem:** Story 2.11 AC4 validation discovered PostgreSQL returning 0 results for ALL SQL queries, blocking all validation efforts. Root cause: SQL backend connectivity or data consistency issue.

**Investigation Approach:**

```python
# Script: scripts/debug-sql-backend-integration.py

import asyncio
from raglite.retrieval.query_classifier import classify_query
from raglite.retrieval.sql_table_search import execute_sql_search
from raglite.shared.clients import get_db_client

async def debug_sql_backend():
    """Debug SQL backend returning 0 results."""

    test_queries = [
        "What is the variable cost for Portugal Cement in August 2025?",
        "What is the EBITDA for Tunisia in Q3 2025?",
        "How much is the revenue for Brazil?",
    ]

    db_client = get_db_client()

    for query in test_queries:
        print(f"\nTesting: {query}")
        print("="*80)

        # 1. Classify query
        classification = await classify_query(query)
        print(f"Classification: {classification.method}")

        if classification.method == "sql":
            # 2. Get generated SQL
            generated_sql = classification.sql
            print(f"Generated SQL: {generated_sql}")

            # 3. Execute SQL directly on PostgreSQL
            try:
                results = await db_client.execute(generated_sql)
                print(f"SQL Results: {len(results)} rows")
                if results:
                    print(f"Sample row: {results[0]}")
                else:
                    print("⚠️ BUG: No results returned from SQL query!")
            except Exception as e:
                print(f"SQL Error: {e}")

            # 4. Check table schema
            schema_check = await db_client.execute("SELECT * FROM financial_tables LIMIT 1;")
            print(f"Table schema check: {len(schema_check)} rows in financial_tables")

            # 5. Debug: Raw table scan
            raw_check = await db_client.execute(f"SELECT COUNT(*) FROM financial_tables WHERE entity ILIKE '%Portugal%';")
            print(f"Raw table scan (Portugal): {raw_check}")
```

**Implementation Steps:**

1. **Debug SQL Execution:**
   - Run diagnostic script on 3-5 test queries
   - Verify SQL syntax is valid
   - Check PostgreSQL error messages
   - Verify financial_tables schema

2. **Fix SQL Issues:**
   - Fix invalid SQL generation (if applicable)
   - Fix table schema mismatches (if applicable)
   - Fix entity/period column issues (if applicable)
   - Add missing indexes (if applicable)

3. **Validate Data Quality:**
   - Verify data exists in financial_tables (not empty)
   - Run manual SQL queries to ensure connectivity
   - Check column names match schema
   - Verify data types compatible

4. **Re-integrate with Story 2.11 Scoring:**
   - Run hybrid search with SQL results (not vector-only)
   - Verify fusion now receives SQL data
   - Test combined accuracy with both search methods

5. **Validation:**
   - SQL backend returns ≥1 result for test queries (was 0)
   - Hybrid search now includes SQL results in fusion
   - p50 latency <2s (no timeout issues)
   - No PostgreSQL connection errors

**Success Criteria:**
- ✅ PostgreSQL financial_tables returning results (not 0 for all queries)
- ✅ SQL queries execute without timeout or errors
- ✅ Hybrid search receives both SQL + vector results for fusion
- ✅ Data consistency verified (schema, entity names, periods)
- ✅ Diagnostic script completed and results documented

**Files Modified:**
- `raglite/retrieval/sql_table_search.py` (if SQL execution bug found)
- `raglite/retrieval/query_classifier.py` (if SQL generation bug found)
- Database schema migration (if table schema issue found)

**Files Created:**
- `scripts/debug-sql-backend-integration.py` (~100 lines - diagnostic script)

**Expected Impact:**
Once SQL backend returns results, edge case fixes (AC1-AC6) can meaningfully improve accuracy. Without SQL results, all other fixes are irrelevant (vector-only maxes at 22-28%).

---

### AC1: Fuzzy Entity Matching (2 days)

**Goal:** SQL queries use approximate entity matching to find variations/aliases

**Problem:** SQL searches for exact entity name matches, but data uses variations (e.g., "Group" query vs "Currency (1000 EUR)" data)

**Implementation:**
1. Enable PostgreSQL `pg_trgm` extension for trigram similarity
2. Update SQL generation prompt in `raglite/retrieval/query_classifier.py` to use `similarity()` function
3. Search pattern: `WHERE similarity(entity, 'QueryEntity') > 0.3 OR similarity(entity_normalized, 'QueryEntity') > 0.3`
4. Fallback to exact match if similarity yields no results
5. Log matched entities for debugging

**Validation:**
- Query: "Group DSO" → Matches `entity='Currency (1000 EUR)'` via similarity
- Query: "Tunisia sales" → Matches `entity='Tunisia Cement'`
- Query: "Angola EBITDA" → Matches `entity='Secil Angola'`
- Expected: ≥8/10 previously failing entity mismatch queries now pass

**Success Criteria:** ≥8/10 entity mismatch queries pass (80% accuracy on entity queries)

**Impact:** 40% of failures (10/25 queries) should be fixed

---

### AC2: Multi-Entity Comparison Queries (2 days)

**Goal:** SQL queries retrieve multiple entities for comparison

**Problem:** SQL only retrieves one entity when query asks for multiple (e.g., "Compare Portugal and Tunisia" only retrieves Portugal)

**Implementation:**
1. Update SQL generation prompt to detect comparison keywords: "compare", "vs", "versus", "between", "which", "higher", "lower"
2. Extract all entity names from query using regex patterns
3. Generate SQL: `WHERE entity IN ('Entity1', 'Entity2', ...)`
4. Update answer synthesis in `raglite/retrieval/sql_table_search.py` to format comparison results
5. Calculate differences/rankings when applicable

**Validation:**
- Query: "Compare Portugal and Tunisia variable costs" → Retrieves both entities, shows comparison
- Query: "Which Brazil plant has higher EBITDA: Adrianopolis or Pomerode?" → Retrieves both, ranks results
- Expected: ≥4/5 previously failing multi-entity queries now pass

**Success Criteria:** ≥4/5 multi-entity queries pass (80% accuracy on comparison queries)

**Impact:** 20% of failures (5/25 queries) should be fixed

---

### AC3: Calculated Metrics Support (3 days)

**Goal:** SQL queries retrieve component metrics for calculation

**Problem:** SQL cannot retrieve metrics that require calculation (e.g., "EBITDA margin" = EBITDA / Turnover)

**Implementation:**
1. Define calculation patterns in SQL generation:
   - **Margin/Ratio:** `metric1 / metric2 * 100`
   - **Total/Sum:** `SUM(metric1, metric2, ...)`
   - **Growth:** `(value2 - value1) / value1 * 100`
2. Update SQL generation to detect calculation keywords: "margin", "ratio", "total", "sum", "growth", "change", "rate"
3. Identify component metrics (e.g., EBITDA margin requires both EBITDA and Turnover)
4. Generate multi-metric SQL queries
5. Add post-SQL calculation logic in `raglite/retrieval/sql_table_search.py`
6. Format answer with calculation shown: "EBITDA margin = 191.8 / 379.2 = 50.6%"

**Validation:**
- Query: "What is the EBITDA margin for Portugal Cement?" → Retrieves EBITDA=191.8M EUR and Turnover=379.2M EUR, calculates 50.6%
- Query: "What is the total Brazil working capital?" → Retrieves AR + AP + Inventory, calculates sum
- Expected: ≥2/3 previously failing calculated metric queries now pass

**Success Criteria:** ≥2/3 calculated metric queries pass (66% accuracy)

**Impact:** 12% of failures (3/25 queries) should be fixed

---

### AC4: Budget Period Detection (1 day)

**Goal:** SQL queries recognize and label budget vs actual periods

**Problem:** SQL doesn't distinguish "B Aug-25" (Budget) from "Aug-25" (Actual)

**Implementation:**
1. Update SQL generation to detect "budget" keyword in query
2. Map period patterns: "B [Month]-[Year]" = Budget, "[Month]-[Year]" = Actual
3. Generate SQL: `WHERE period IN ('Aug-25', 'B Aug-25')` for budget comparison queries
4. Update answer synthesis to label "Actual" vs "Budget" in results
5. Calculate variance and performance (above/below budget)

**Validation:**
- Query: "How did Portugal's variable costs compare to budget?" → Retrieves both actual and budget, labels correctly, shows variance
- Query: "Is Lebanon Ready-Mix performing above or below budget?" → Compares actual vs budget, states performance
- Expected: 2/2 previously failing budget queries now pass

**Success Criteria:** 2/2 budget queries pass (100% accuracy on budget queries)

**Impact:** 8% of failures (2/25 queries) should be fixed

---

### AC5: Currency Conversion Handling (1 day)

**Goal:** SQL queries detect currency requests and provide explicit messages

**Problem:** Queries ask for specific currency (e.g., AOA, BRL) when data is in EUR

**Implementation:**
1. Add currency code detection to SQL generation (regex for 3-letter currency codes)
2. Check if data exists in requested currency
3. If not available: Return explicit message "Data available in [actual currency] only. Conversion to [requested currency] not supported."
4. Document as future enhancement: FX rate table for automatic conversion (out of scope for Story 2.14)

**Validation:**
- Query: "What is the Angola EBITDA in million AOA?" → Returns "Data available in EUR only. Conversion to AOA not supported."
- Query: "What is the Brazil EBITDA in million BRL?" → Returns "Data available in EUR only. Conversion to BRL not supported."
- Expected: 2/2 queries provide informative messages (may not pass validation but won't fail silently)

**Success Criteria:** 2/2 currency queries provide informative messages about unavailability

**Impact:** 8% of failures (2/25 queries) improve user experience with explicit messaging

---

### AC6: Value Extraction Validation (1 day)

**Goal:** Answer synthesis validates extracted values match query context

**Problem:** Answer synthesis extracts wrong numeric value or hallucinates data

**Implementation:**
1. Add entity/period verification in answer synthesis (`raglite/retrieval/sql_table_search.py`)
2. Compare extracted entity with query entity before finalizing answer
3. Compare extracted period with query period before finalizing answer
4. If mismatch: Request LLM to re-extract or select most relevant value from results
5. Log extraction confidence scores for debugging

**Validation:**
- Query: "Group DSO in August 2025" → Verify entity='Group' (or similar via AC1 fuzzy matching) before extracting DSO value
- Query: "Tunisia sales volume" → Verify entity='Tunisia Cement' before extracting sales volume
- Expected: ≥3/4 previously failing value extraction queries now pass

**Success Criteria:** ≥3/4 value extraction queries pass (75% accuracy)

**Impact:** 16% of failures (4/25 queries) should be fixed

---

### AC8: Full Validation ≥70% Accuracy (1 day) - DECISION GATE (Integrated with Story 2.11)

**Goal:** Comprehensive validation on 25-query ground truth combining Story 2.11 (hybrid search scoring) + Story 2.14 (SQL backend integration + edge cases)

**Context:** This validation integrates the improvements from both stories:
- Story 2.11: Fixed hybrid search score normalization + BM25 tuning
- Story 2.14: Fixed SQL backend + implemented edge case refinements (AC0-AC7)
- Combined result: Hybrid search with working SQL backend + all edge case fixes

**Implementation:**
1. Re-run full validation with ALL fixes applied: `python scripts/validate-story-2.13-v2.py --save`
   - Includes Story 2.11 score normalization + tuning
   - Includes Story 2.14 SQL backend fix + edge case refinements
2. Measure accuracy by edge case category (entity matching, multi-entity, calculated metrics, etc.)
3. Document results in validation report: `docs/validation/story-2.14-validation-results.md`
4. Compare before/after improvements (4% baseline with vector-only → target ≥70% with SQL+vector+fixes)

**Validation Metrics:**

| Category | Baseline | Target | Queries |
|----------|----------|--------|---------|
| **Overall Accuracy** | 4% (1/25) | **≥70% (≥18/25)** | All 25 |
| Entity Matching | 10% (1/10) | ≥80% (≥8/10) | 10 queries |
| Multi-Entity Comparison | 0% (0/5) | ≥80% (≥4/5) | 5 queries |
| Calculated Metrics | 0% (0/3) | ≥66% (≥2/3) | 3 queries |
| Budget Detection | 0% (0/2) | 100% (2/2) | 2 queries |
| Currency Handling | 0% (0/2) | 100% (2/2) | 2 queries |
| Value Extraction | 0% (0/4) | ≥75% (≥3/4) | 4 queries |

**Success Criteria:** Overall accuracy ≥70% (≥18/25 queries passing)

**Decision Gate:**
- **IF ≥70%:** ✅ **Epic 2 Phase 2A COMPLETE** → Proceed to Epic 3 planning
- **IF 60-69%:** ⚠️ Investigate top 3 failures, allocate 1 day for iteration
- **IF <60%:** ❌ Escalate to PM for Phase 2B (cross-encoder re-ranking) evaluation

**Impact:** Validates that all edge case fixes collectively achieve Epic 2 target

---

## Tasks / Subtasks

### Task 1: Setup Iterative Testing Environment (AC: Setup)
**Estimated Effort:** 4 hours (Day 1)

- [ ] **Subtask 1.1:** Extract pages 18-50 from 160-page PDF to create 30-page test excerpt
  - Contains key entities: Portugal, Tunisia, Angola, Brazil, Group
  - Covers most ground truth query data points
  - Output: `docs/sample pdf/test-pages-18-50.pdf`

- [ ] **Subtask 1.2:** Create excerpt validation script
  - Script: `scripts/validate-story-2.14-excerpt.py`
  - Run subset of 15 queries targeting excerpt pages
  - Faster iteration (1-2 min vs 5-6 min for full PDF)

- [ ] **Subtask 1.3:** Re-ingest excerpt into PostgreSQL
  - Verify table extraction quality maintained (≥99% unit accuracy)
  - Validate PostgreSQL schema intact
  - Test query execution on excerpt database

---

### Task 2: Implement Fuzzy Entity Matching (AC1)
**Estimated Effort:** 2 days (Days 2-3)

- [ ] **Subtask 2.1:** Enable PostgreSQL pg_trgm extension
  - Migration: `migrations/enable_pg_trgm.sql`
  - Verify extension loaded: `SELECT * FROM pg_extension WHERE extname='pg_trgm';`

- [ ] **Subtask 2.2:** Update SQL generation prompt in `raglite/retrieval/query_classifier.py`
  - Add similarity() function to WHERE clause template
  - Set similarity threshold = 0.3 (tunable)
  - Search both `entity` and `entity_normalized` columns

- [ ] **Subtask 2.3:** Add entity normalization helper function
  - Normalize entity names: lowercase, remove special chars, trim whitespace
  - Cache normalized entities for performance

- [ ] **Subtask 2.4:** Implement fallback to exact match
  - If similarity search returns 0 results, retry with exact match
  - Log which matching strategy succeeded

- [ ] **Subtask 2.5:** Add GIN indexes for performance
  - Create indexes: `CREATE INDEX idx_entity_trgm ON table USING gin(entity gin_trgm_ops);`
  - Create indexes: `CREATE INDEX idx_entity_normalized_trgm ON table USING gin(entity_normalized gin_trgm_ops);`

- [ ] **Subtask 2.6:** Unit test fuzzy matching
  - Test: "Group" matches "Currency (1000 EUR)" with similarity > 0.3
  - Test: "Tunisia" matches "Tunisia Cement"
  - Test: Exact match fallback when similarity fails

- [ ] **Subtask 2.7:** Run excerpt validation on entity matching queries
  - Target: ≥5/7 entity queries passing on excerpt
  - Debug failures and iterate on similarity threshold if needed

---

### Task 3: Implement Multi-Entity Comparison Queries (AC2)
**Estimated Effort:** 2 days (Days 4-5)

- [ ] **Subtask 3.1:** Add comparison keyword detection to SQL generation prompt
  - Keywords: "compare", "vs", "versus", "between", "which", "higher", "lower"
  - Update prompt in `raglite/retrieval/query_classifier.py:200-451`

- [ ] **Subtask 3.2:** Implement entity extraction from multi-entity queries
  - Regex patterns to extract entity names from comparison queries
  - Handle variations: "Portugal vs Tunisia", "which plant: Adrianopolis or Pomerode"

- [ ] **Subtask 3.3:** Generate SQL with IN clause for multiple entities
  - Template: `WHERE entity IN ('Entity1', 'Entity2', ...)`
  - Combine with fuzzy matching from AC1 if needed

- [ ] **Subtask 3.4:** Update answer synthesis for comparison formatting
  - File: `raglite/retrieval/sql_table_search.py`
  - Format: "Portugal: -23.4 EUR/ton, Tunisia: -18.2 EUR/ton (Portugal is 5.2 higher)"
  - Calculate differences and rankings

- [ ] **Subtask 3.5:** Unit test multi-entity SQL generation
  - Test: "Compare Portugal and Tunisia" generates IN clause with both
  - Test: Answer synthesis formats comparison correctly

- [ ] **Subtask 3.6:** Run excerpt validation on comparison queries
  - Target: ≥4/5 multi-entity queries passing on excerpt

---

### Task 4: Implement Calculated Metrics Support (AC3)
**Estimated Effort:** 3 days (Days 5-7)

- [ ] **Subtask 4.1:** Define calculation pattern library
  - Margin/Ratio: EBITDA margin = EBITDA / Turnover * 100
  - Total/Sum: Working capital = AR + AP + Inventory
  - Growth: Revenue growth = (Q3 - Q2) / Q2 * 100
  - Document patterns in code comments

- [ ] **Subtask 4.2:** Add calculation keyword detection
  - Keywords: "margin", "ratio", "total", "sum", "growth", "change", "rate"
  - Update SQL generation prompt in `query_classifier.py`

- [ ] **Subtask 4.3:** Implement component metric identification
  - For "EBITDA margin", identify components: EBITDA and Turnover
  - For "total working capital", identify: AR, AP, Inventory
  - LLM-based extraction or rule-based mapping

- [ ] **Subtask 4.4:** Generate multi-metric SQL queries
  - Retrieve all component metrics in single query
  - Example: `WHERE metric IN ('EBITDA', 'Turnover') AND entity='Portugal Cement'`

- [ ] **Subtask 4.5:** Add post-SQL calculation logic
  - File: `raglite/retrieval/sql_table_search.py`
  - Perform calculation on retrieved values
  - Handle edge cases: division by zero, missing components

- [ ] **Subtask 4.6:** Format answer with calculation shown
  - Example: "EBITDA margin for Portugal Cement = 191.8 / 379.2 = 50.6%"
  - Show calculation steps for transparency

- [ ] **Subtask 4.7:** Unit test calculated metrics
  - Test: EBITDA margin calculation with mocked data
  - Test: Total sum calculation
  - Test: Error handling for missing components

- [ ] **Subtask 4.8:** Run excerpt validation on calculated metric queries
  - Target: ≥2/3 calculated metric queries passing on excerpt

---

### Task 5: Implement Budget Period Detection (AC4)
**Estimated Effort:** 1 day (Day 6)

- [ ] **Subtask 5.1:** Add budget keyword detection to SQL generation
  - Keyword: "budget" in query text
  - Update prompt in `query_classifier.py`

- [ ] **Subtask 5.2:** Map period patterns
  - Budget pattern: "B [Month]-[Year]" (e.g., "B Aug-25")
  - Actual pattern: "[Month]-[Year]" (e.g., "Aug-25")

- [ ] **Subtask 5.3:** Generate SQL for budget comparison
  - Template: `WHERE period IN ('Aug-25', 'B Aug-25')`
  - Retrieve both actual and budget data

- [ ] **Subtask 5.4:** Update answer synthesis to label periods
  - Label results: "Actual: -23.4 EUR/ton, Budget: -20.0 EUR/ton"
  - Calculate variance: "3.4 EUR/ton above budget (17% variance)"

- [ ] **Subtask 5.5:** Unit test budget period detection
  - Test: SQL generation includes both periods
  - Test: Answer synthesis labels correctly

- [ ] **Subtask 5.6:** Run excerpt validation on budget queries
  - Target: 2/2 budget queries passing on excerpt

---

### Task 6: Implement Currency Conversion Handling (AC5)
**Estimated Effort:** 1 day (Day 7)

- [ ] **Subtask 6.1:** Add currency code detection to SQL generation
  - Regex: `\b[A-Z]{3}\b` to detect 3-letter currency codes (AOA, BRL, USD, TND, EUR)
  - Update prompt in `query_classifier.py`

- [ ] **Subtask 6.2:** Check data availability in requested currency
  - Query database: Does data exist with `unit='M AOA'` or similar?
  - Most data is in EUR, so likely returns false

- [ ] **Subtask 6.3:** Generate explicit unavailability message
  - Message: "Data available in EUR only. Conversion to AOA not supported."
  - Clear, user-friendly response

- [ ] **Subtask 6.4:** Document future enhancement (FX conversion)
  - Add TODO comment: Future story for FX rate table + automatic conversion
  - Out of scope for Story 2.14

- [ ] **Subtask 6.5:** Unit test currency detection
  - Test: "Angola EBITDA in AOA" detects currency request
  - Test: Message format correct

- [ ] **Subtask 6.6:** Run excerpt validation on currency queries
  - Target: 2/2 currency queries provide informative messages

---

### Task 7: Implement Value Extraction Validation (AC6)
**Estimated Effort:** 1 day (Day 8)

- [ ] **Subtask 7.1:** Add entity verification in answer synthesis
  - File: `raglite/retrieval/sql_table_search.py`
  - Before extracting value, verify entity in result matches query entity
  - Use fuzzy matching from AC1 for verification

- [ ] **Subtask 7.2:** Add period verification in answer synthesis
  - Verify period in result matches query period
  - Handle budget period variations from AC4

- [ ] **Subtask 7.3:** Implement LLM re-extraction on mismatch
  - If entity/period mismatch detected, ask LLM to select most relevant value
  - Provide all retrieved rows to LLM for selection

- [ ] **Subtask 7.4:** Add extraction confidence scoring
  - Log confidence based on entity/period match quality
  - High confidence: exact match, Medium: fuzzy match, Low: fallback selection

- [ ] **Subtask 7.5:** Unit test value extraction validation
  - Test: Correct entity → value extracted
  - Test: Wrong entity → re-extraction triggered
  - Test: Confidence scores logged

- [ ] **Subtask 7.6:** Run excerpt validation on value extraction queries
  - Target: ≥3/4 value extraction queries passing on excerpt

---

### Task 8: Code Review and Documentation (AC: All)
**Estimated Effort:** 1 day (Day 9)

- [ ] **Subtask 8.1:** Code review all edge case implementations
  - Review query_classifier.py changes
  - Review sql_table_search.py changes
  - Verify code follows RAGLite coding standards

- [ ] **Subtask 8.2:** Add inline documentation
  - Document fuzzy matching logic
  - Document calculation patterns
  - Add code comments for future maintainers

- [ ] **Subtask 8.3:** Update technical documentation
  - Update `docs/architecture/` with SQL generation enhancements
  - Document edge case patterns in `docs/validation/edge-cases.md`

- [ ] **Subtask 8.4:** Create debugging guide
  - How to debug SQL generation failures
  - How to tune similarity threshold
  - How to add new calculation patterns

---

### Task 9: Full PDF Validation (AC7) - DECISION GATE
**Estimated Effort:** 1 day (Day 10)
**⚠️ IMPORTANT:** This task requires explicit user permission before running. Do NOT proceed with full PDF testing without user approval.

- [ ] **Subtask 9.1:** Re-ingest full 160-page PDF with all fixes (REQUIRES USER PERMISSION)
  - **STOP and request user permission before running full PDF ingestion**
  - Clean PostgreSQL database
  - Re-ingest with all edge case enhancements active
  - Verify data quality

- [ ] **Subtask 9.2:** Run full 25-query validation
  - Script: `python scripts/validate-story-2.13-v2.py --save`
  - Save results: `docs/validation/story-2.14-validation-results.md`

- [ ] **Subtask 9.3:** Measure accuracy by category
  - Overall accuracy: target ≥70% (≥18/25)
  - Entity matching: target ≥80% (≥8/10)
  - Multi-entity: target ≥80% (≥4/5)
  - Calculated metrics: target ≥66% (≥2/3)
  - Budget detection: target 100% (2/2)
  - Currency handling: target 100% (2/2)
  - Value extraction: target ≥75% (≥3/4)

- [ ] **Subtask 9.4:** Compare before/after results
  - Baseline: 4% (1/25)
  - After Story 2.14: target ≥70% (≥18/25)
  - Expected improvement: +66 percentage points

- [ ] **Subtask 9.5:** Document any discrepancies
  - Compare excerpt vs full PDF results
  - Investigate if any new failures emerged
  - Document lessons learned

- [ ] **Subtask 9.6:** Create validation report
  - File: `docs/validation/story-2.14-validation-results.md`
  - Include: accuracy metrics, before/after comparison, failure analysis, next steps

- [ ] **Subtask 9.7:** DECISION GATE - Escalate to PM if needed
  - **IF ≥70%:** Mark Epic 2 Phase 2A COMPLETE, plan Epic 3
  - **IF 60-69%:** Investigate top 3 failures, iterate for 1 day
  - **IF <60%:** Escalate to PM for Phase 2B (cross-encoder) evaluation

---

## Dev Notes

### CRITICAL: Story 2.14 Scope Expansion - SQL Backend Integration

**2025-10-27 Scope Change Rationale:**

Story 2.11 Senior Developer Review revealed that the primary blocker for Epic 2 completion is NOT edge cases, but **SQL backend connectivity**:
- Current State: PostgreSQL returning 0 results for all queries
- Impact: Vector-only search maxes at 22-28% (insufficient)
- Solution: Fix SQL backend first (AC0), then apply edge case refinements (AC1-AC7)

**Implementation Priority:**
1. **AC0 (CRITICAL, Days 1-3):** Debug and fix SQL backend - enables all other work
2. **AC1-AC7 (HIGH, Days 3-9):** Edge case refinements - marginal improvements with working SQL
3. **AC8 (FINAL, Day 10):** Combined validation - validates both fixes together

**Expected Outcome:**
- SQL backend fixed → Hybrid search receives SQL results
- Edge cases fixed → SQL generation handles entity/metric/period variations
- Combined → 70%+ accuracy achievable (was 22% with vector-only)

### Architecture Context

**Files Modified:**
- `raglite/retrieval/sql_table_search.py` (~150 lines modified)
  - **AC0:** SQL backend debugging and integration fix
  - **AC3,AC6:** Answer synthesis improvements for calculated metrics
  - **AC2,AC6:** Comparison formatting for multi-entity queries
  - **AC4:** Budget period labeling
  - **AC5:** Currency message handling
  - **AC6:** Entity/period verification in value extraction

- `raglite/retrieval/query_classifier.py` (~100 lines modified)
  - **AC1:** Fuzzy entity matching with similarity()
  - **AC2:** Multi-entity IN clause generation
  - **AC3:** Calculated metrics component extraction
  - **AC4:** Budget period detection
  - **AC5:** Currency code detection

- `migrations/enable_pg_trgm.sql` (new file, ~10 lines)
  - Enable pg_trgm extension
  - Create GIN indexes on entity and entity_normalized columns

**Database Changes:**
- PostgreSQL extension: `pg_trgm` (trigram similarity)
- Indexes: GIN indexes on `entity` and `entity_normalized` columns for fuzzy matching performance

**No New Dependencies:**
- All functionality uses existing PostgreSQL + Mistral Small + Claude 3.7 Sonnet
- No additional libraries or services required

### Testing Strategy

**Unit Tests:**
- `raglite/tests/unit/test_fuzzy_entity_matching.py` (AC1)
- `raglite/tests/unit/test_multi_entity_queries.py` (AC2)
- `raglite/tests/unit/test_calculated_metrics.py` (AC3)
- `raglite/tests/unit/test_budget_period_detection.py` (AC4)
- `raglite/tests/unit/test_currency_handling.py` (AC5)
- `raglite/tests/unit/test_value_extraction_validation.py` (AC6)

**Integration Tests:**
- `scripts/validate-story-2.14-excerpt.py` - Excerpt validation (15 queries, faster iteration)
- `scripts/validate-story-2.13-v2.py` - Full validation (25 queries, comprehensive)

**Iterative Testing Approach:**
- **PRIMARY:** Use 30-page excerpt (pages 18-50) for rapid iteration (1-2 min per test cycle)
- Validate each AC on excerpt before moving to next (Days 1-9)
- **FINAL ONLY:** Full 160-page PDF validation on Day 10 - **REQUIRES USER PERMISSION BEFORE RUNNING**
- Never run full PDF tests without explicit user approval

### Performance Considerations

**PostgreSQL Fuzzy Matching:**
- GIN indexes required for pg_trgm performance
- Similarity threshold tunable (0.3 is starting point, may need adjustment)
- Query timeout: 5s to prevent slow fuzzy searches

**LLM API Calls:**
- Mistral Small (FREE tier, temperature=0.0) for SQL generation - no cost increase
- Claude 3.7 Sonnet for answer synthesis - existing usage, no significant cost increase
- LLM re-extraction on value mismatch: <5% of queries, minimal cost impact

**Expected Latency:**
- Fuzzy matching overhead: +10-20ms per query
- Calculated metrics overhead: +50-100ms (additional SQL roundtrip + calculation)
- Overall p50 latency: <2s (within NFR13 <15s budget)

### Edge Case Summary

| Edge Case | Failures (Baseline) | Solution | Priority | Effort | Expected Fix |
|-----------|---------------------|----------|----------|--------|--------------|
| Entity Name Mismatches | 10/25 (40%) | PostgreSQL similarity() | HIGH | 2 days | 8-10 queries |
| Multi-Entity Queries | 5/25 (20%) | SQL IN clause + comparison | HIGH | 2 days | 4-5 queries |
| Calculated Metrics | 3/25 (12%) | Multi-metric SQL + post-calc | MEDIUM | 3 days | 2-3 queries |
| Budget Period Detection | 2/25 (8%) | Period pattern mapping | MEDIUM | 1 day | 2 queries |
| Currency Conversion | 2/25 (8%) | Explicit unavailable message | LOW | 1 day | 2 queries |
| Value Extraction | 4/25 (16%) | Entity/period verification | MEDIUM | 1 day | 3-4 queries |
| **TOTAL** | **26/25*** | - | - | **10 days** | **≥18/25 (70%)** |

*Note: Some queries have multiple edge cases, total > 25

### Project Structure Notes

**Alignment with RAGLite Structure:**
- All changes confined to existing `raglite/retrieval/` module
- No new modules or files (except migration script)
- Follows existing patterns in `query_classifier.py` and `sql_table_search.py`

**Database Migration:**
- Migration script: `migrations/enable_pg_trgm.sql`
- Run during Story 2.14 setup (Day 1, Subtask 2.1)
- Idempotent: Can be run multiple times safely

### References

**Source Documents:**
- [Sprint Change Proposal: docs/validation/SPRINT-CHANGE-PROPOSAL-STORY-2.14-SQL-EDGE-CASES.md]
- [Epic 2 PRD: docs/prd/epic-2-advanced-rag-enhancements.md]
- [Story 2.13 (SQL Table Search): docs/stories/2-13-sql-table-search-phase2a-revised.md]
- [Story 2.13 AC4 Validation: docs/validation/story-2.13-ac4-full-validation.json]

**PostgreSQL Documentation:**
- [pg_trgm extension: https://www.postgresql.org/docs/current/pgtrgm.html]
- [GIN indexes: https://www.postgresql.org/docs/current/gin-intro.html]

**Production Evidence:**
- FinRAG (AI competition winner): nDCG@10 0.804 with SQL-based table search
- TableRAG (Huawei Cloud): 75-80% accuracy on table queries via SQL
- Bloomberg: Hybrid SQL+vector at scale (hundreds of thousands of docs daily)

---

## Dev Agent Record

### Context Reference

<!-- Story Context XML will be added by story-context workflow -->

### Agent Model Used

Claude 3.7 Sonnet (claude-sonnet-4-5-20250929)

### Debug Log References

- Setup iteration: `scripts/validate-story-2.14-excerpt.py` output
- Full validation: `scripts/validate-story-2.13-v2.py --save` output
- Validation results: `docs/validation/story-2.14-validation-results.md`

### Completion Notes List

<!-- Will be populated during implementation -->

### File List

**Implementation Files:**
- `raglite/retrieval/query_classifier.py` (modified - SQL generation enhancements)
- `raglite/retrieval/sql_table_search.py` (modified - answer synthesis improvements)
- `migrations/enable_pg_trgm.sql` (new - PostgreSQL extension + indexes)

**Test Files:**
- `raglite/tests/unit/test_fuzzy_entity_matching.py` (new)
- `raglite/tests/unit/test_multi_entity_queries.py` (new)
- `raglite/tests/unit/test_calculated_metrics.py` (new)
- `raglite/tests/unit/test_budget_period_detection.py` (new)
- `raglite/tests/unit/test_currency_handling.py` (new)
- `raglite/tests/unit/test_value_extraction_validation.py` (new)

**Validation Scripts:**
- `scripts/validate-story-2.14-excerpt.py` (new - excerpt validation)
- `docs/sample pdf/test-pages-18-50.pdf` (new - 30-page test excerpt)

**Documentation:**
- `docs/validation/story-2.14-validation-results.md` (new - validation report)
- `docs/validation/edge-cases.md` (new - edge case patterns reference)

---

**Story Created:** 2025-10-27
**Created By:** Bob (Scrum Master)
**Status:** Draft (ready for review and approval)
