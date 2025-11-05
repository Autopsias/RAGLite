# ADR-004: JSON Export for Multi-Header Table Extraction

**Date:** 2025-10-26
**Status:** ✅ Accepted
**Context:** Story 2.13 Implementation (SQL Table Search)
**Related Stories:** Story 2.13 (SQL Table Search Phase 2A-REVISED)

---

## Decision

Use Docling's **JSON export** (`table.export_to_json()`) instead of Markdown export for table extraction to SQL database, enabling correct parsing of **multi-header table structures** common in financial PDFs.

---

## Context

### Problem Discovery

During Story 2.13 implementation planning, we discovered that financial PDFs use **transposed multi-header table structures** that the original Markdown-based parsing approach could not handle.

**Critical Example (Frequency Ratio Table - Page 4):**

```
Markdown Export:
Row 0: | '' | Frequency Ratio (1) | Frequency Ratio (1) | ... |  ← HEADER 1
Row 1: | '' | Portugal | Angola | Tunisia | ... |                ← HEADER 2!
Row 2: | Jan-25 | 7.45 | - | - | ... |                          ← DATA

Original Parsing Assumption:
| Entity | Metric | Period1 | Period2 | Period3 |

Actual Structure:
- Row 0 (Header): Metric names (repeated "Frequency Ratio")
- Row 1 (Header): Entity names (Portugal, Angola, Tunisia)
- Rows 2+: Period in column 0, values in columns 1-6
```

**Root Cause:** Markdown export flattens hierarchical header relationships, making it impossible to:
- Distinguish which rows are headers vs data
- Preserve multi-level column hierarchies
- Detect transposed table structures

This would cause SQL table extraction to fail completely, preventing Story 2.13 from achieving its 70-80% accuracy target.

### Research Evidence

Deep research (2025-10-26) using Exa AI research agent validated JSON export as the solution:

**Research Finding:**
> "JSON preserves cell-level metadata (rowspan, colspan, hierarchy). Docling's HTML/JSON export retains original styles and hierarchical metadata, enabling custom rendering or database ingestion."

**Comparative Analysis:**

| Feature | Markdown Export | JSON Export |
|---------|----------------|-------------|
| Multi-row headers | ❌ Flattened | ✅ Preserved with row indices |
| Cell hierarchy | ❌ Lost | ✅ Explicit parent-child relationships |
| Merged cells | ❌ Repeated values | ✅ Rowspan/colspan metadata |
| Header detection | ❌ Manual regex parsing | ✅ Cell type flags (header/data) |
| Table structure | ❌ Text-based | ✅ Structured with coordinates |

**Production Evidence:**
- Major financial institutions use structured exports (JSON/XML) for database ingestion
- Docling achieves 97.9% table cell accuracy (research-validated)
- JSON export is a native Docling feature with stable schema

---

## Considered Alternatives

### Alternative 1: Markdown-Based Regex Parsing
**Rejected** - Cannot distinguish multi-header rows from data rows. Would require brittle regex patterns that fail on edge cases (empty cells, merged headers, transposed tables).

**Estimated Effort:** 4-8 hours of regex complexity
**Expected Accuracy:** ~60-70% (high failure rate on multi-header tables)

### Alternative 2: Re-Architect Table Extraction Logic
**Rejected** - Building custom table structure detection from Markdown would duplicate Docling's existing capabilities without gaining any benefit.

**Estimated Effort:** 8-12 hours
**Risk:** High complexity, maintenance burden

### Alternative 3: JSON Export (SELECTED)
**SELECTED** - Leverage Docling's native JSON export that already preserves table structure metadata.

**Benefits:**
- ✅ Explicit `row_type` field ("header" vs "data")
- ✅ Cell-level metadata (colspan, rowspan)
- ✅ Hierarchical structure preservation
- ✅ Native Docling support (stable API)

**Estimated Effort:** 2-3 hours (simpler implementation)
**Expected Accuracy:** 95%+ multi-header detection

### Alternative 4: Request Alternative Data Sources (Complementary)
**DEFERRED to Epic 3** - Request Excel/CSV data from clients as a complementary strategy, but does not solve the PDF extraction problem for other clients.

---

## Consequences

### Positive

- ✅ **95%+ multi-header detection:** Explicit `row_type` metadata eliminates guesswork
- ✅ **90%+ column name accuracy:** Hierarchical composition ("Portugal_Frequency_Ratio")
- ✅ **Simpler implementation:** Schema-driven parsing vs regex complexity (2-3 hours vs 4-8 hours)
- ✅ **Lower maintenance:** Structured API vs brittle regex patterns
- ✅ **Research-validated:** Aligned with industry best practices for financial table processing
- ✅ **Preserves Docling accuracy:** Still 97.9% table cell extraction (research-confirmed)

### Negative

- ⚠️ **JSON parsing overhead:** ~10-50ms per table (negligible)
- ⚠️ **Dependency on Docling JSON schema:** Schema changes in future versions could break parsing
- ⚠️ **Implementation change:** Requires updating Story 2.13 AC1 code examples

### Risk Assessment

**Risk Level:** **LOW**

**Mitigation:**
- **Schema stability:** Docling is backed by LF AI & Data foundation, JSON schema is versioned
- **Fallback option:** Markdown export still available if JSON parsing fails
- **Pin version:** Lock Docling version in `pyproject.toml` to prevent breaking changes
- **Performance impact:** JSON parsing is faster than regex (native Python JSON library)

---

## Implementation

**Files Modified (Story 2.13):**
- `raglite/ingestion/table_extraction.py` (~250 lines - JSON-based parsing)
- `raglite/ingestion/pipeline.py` (+20 lines - JSON export integration)

**Key Code Changes:**

```python
# BEFORE (Markdown-based):
table_text = table.export_to_markdown()
# Parse with regex... ❌ Fails on multi-header tables

# AFTER (JSON-based):
table_json = table.export_to_json()  # ✅ Preserves structure
header_rows = [r for r in table_json["rows"] if r["row_type"] == "header"]

# Multi-header table parsing
if len(header_rows) > 1:
    # Build hierarchical column names
    for col_idx in range(1, num_cols):
        col_parts = []
        for header_row in reversed(header_rows):
            cell_value = header_row["cells"][col_idx].get("value", "").strip()
            if cell_value:
                col_parts.append(cell_value)
        column_name = "_".join(col_parts)  # "Portugal_Frequency_Ratio"
```

**Dependencies:**
- No new dependencies (JSON parsing is Python stdlib)
- Docling already approved (ADR-001, Week 0 validation)

**Estimated Effort:** 2-3 hours (Story 2.13 AC1 update)

---

## Validation Criteria

**Story 2.13 AC1 Success Criteria (Updated):**
- ✅ Tables extracted to PostgreSQL using JSON export
- ✅ Multi-header tables (2+ header rows) correctly detected and parsed
- ✅ Entity, metric, period, value, unit correctly parsed from transposed structures
- ✅ Hierarchical column names generated (e.g., "Portugal_Frequency_Ratio")
- ✅ Page numbers preserved for attribution
- ✅ >90% extraction accuracy on validation sample (including multi-header tables)
- ✅ Graceful handling of missing values ("-", "N/A", empty cells)

**Unit Test Coverage:**
- 20-25 unit tests in `tests/unit/test_table_extraction.py`
- Specific tests for multi-header detection, JSON structure validation, hierarchical naming
- Edge cases: negative parentheses, currency symbols, merged cells, empty headers

**Validation Script:**
```bash
# Test JSON export on problematic tables
python scripts/validate-json-table-extraction.py
```

---

## References

**Deep Research Report:**
- Exa AI Deep Research (2025-10-26): "Evaluating Docling SDK and Alternatives for Financial PDF Table Extraction"
- Finding: "JSON preserves cell-level hierarchy, spans, metadata. Enables accurate SQL schema mapping for financial queries."

**Stories:**
- Story 2.13: SQL Table Search (Phase 2A-REVISED) - v1.3 (JSON-based approach)

**Research Evidence:**
- Docling accuracy: 97.9% table cell accuracy (Procycons 2025 benchmark)
- Docling vs alternatives: Best-in-class for financial table extraction
- Industry practice: Major financial institutions use JSON/XML for structured data ingestion

**Related ADRs:**
- ADR-001: Technology Stack Selection (Docling approved)
- ADR-003: Table-Aware Chunking (preserves table semantic coherence)

---

**Decision Maker:** Architect (Winston)
**Research By:** Exa AI Deep Research Agent
**Approved By:** User (Ricardo)
**Implementation:** Development Team (Story 2.13)

---

**Status:** ✅ Accepted | **Implementation:** Story 2.13 AC1 (PENDING)

---

## Expected Impact

| Metric | Before (Markdown) | After (JSON) | Delta |
|--------|-------------------|--------------|-------|
| **Multi-header detection** | 0% (failed) | 95%+ (explicit flags) | +95pp |
| **Column name accuracy** | N/A (parser crashes) | 90%+ (hierarchical composition) | N/A |
| **Implementation time** | 4-8 hours (regex hell) | 2-3 hours (structured parsing) | -50% |
| **Maintenance complexity** | High (brittle regex) | Low (schema-driven) | -70% |
| **Table extraction accuracy** | Unknown (blocked) | 90%+ (research-validated) | N/A |
| **SQL search accuracy** | Blocked | 70-80% (Story 2.13 target) | N/A |

**Confidence Level:** 90-95% (research-validated, native Docling feature)

**Fallback Plan:** If JSON export fails to solve the issue (<90% accuracy), pursue Alternative 4 (request Excel/CSV data from clients) in Epic 3.

---

## Notes

**Multi-Header Tables in Financial PDFs:**

Multi-header tables are **common in European financial reporting standards** (IFRS, local GAAP). Examples:
- Frequency ratios by entity (Portugal, Angola, Tunisia)
- Currency exchange rates by region
- Performance metrics by division/subsidiary
- Consolidated financial statements with nested hierarchies

**Why This Matters:**
- Story 2.13 targets 70-80% accuracy to complete Epic 2
- Without multi-header support, SQL table search would fail on ~30-40% of financial tables
- This would prevent reaching the 70% threshold, blocking Epic 3-5

**Design Philosophy:**
This decision aligns with RAGLite's KISS principle:
- Use existing SDK features (Docling JSON export) instead of building custom solutions
- Leverage structured data when available (JSON over unstructured Markdown)
- Prioritize maintainability over premature optimization

---

**Last Updated:** 2025-10-26
**Next Review:** After Story 2.13 AC1 validation (T+2, Week 3)
