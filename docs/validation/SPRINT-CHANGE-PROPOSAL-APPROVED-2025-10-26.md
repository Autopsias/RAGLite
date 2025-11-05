# Sprint Change Proposal: Story 2.13 JSON/DataFrame Investigation

**Date:** 2025-10-26
**Session:** Dev Session (Post-AC4 Validation Failure)
**Status:** INVESTIGATION COMPLETE - AWAITING EMPIRICAL TEST RESULTS

---

## Executive Summary

**Story 2.13 AC4 validation FAILED at 25.8%** (target: ≥70%).

**Root Cause Identified:** Multi-header table structure in financial PDFs cannot be parsed from Markdown export.

**Solution Investigated:** JSON export per architect session, BUT `export_to_dict()` method **does NOT exist** in Docling API.

**Alternative Discovered:** `export_to_dataframe()` method IS available.

**Next Steps:** Empirically test DataFrame export to determine if it preserves multi-header structure, then research best approach.

---

## Session Progress

### ✅ Completed

1. **Validation Failure Analyzed** - 25.8% vs 70% target
2. **Root Cause Documented** - Multi-header tables, corrupted database (36,967 rows)
3. **Architect Session Solution Reviewed** - JSON export approach documented
4. **JSON Validation Script Created** - `scripts/validate-json-table-export.py`
5. **JSON Validation Run** - FAILED: `export_to_dict()` does NOT exist
6. **Docling API Methods Discovered** - Found `export_to_dataframe()` available
7. **DataFrame Test Script Created** - `scripts/test-dataframe-export.py`
8. **DataFrame Test Running** - Testing on small PDF (currently processing)

### ⏳ In Progress

- **DataFrame Export Test** - Testing if MultiIndex preserves multi-headers
- **Empirical Validation** - Seeing actual data structure from Docling

### 📋 Pending

- Complete DataFrame test analysis
- Research DataFrame vs other export methods (MCP deep research)
- Implement chosen approach
- Re-ingest with corrected extraction
- Re-run AC4 validation

---

## Key Findings

### 1. JSON Export Does NOT Work

**Problem:**
```python
table_data = item.export_to_dict()  # AttributeError!
```

**Docling API Methods Actually Available:**
- ✅ `export_to_dataframe()` - Returns pandas DataFrame
- ✅ `export_to_html()` - HTML with structure
- ✅ `model_dump_json()` - Pydantic serialization
- ✅ `dict()` - Pydantic dict method
- ❌ `export_to_dict()` - **DOES NOT EXIST**

### 2. Multi-Header Table Structure Confirmed

**Markdown Debug Output Showed:**
```
| '' | Frequency Ratio (1) | Frequency Ratio (1) | ... |  ← HEADER ROW 1
| '' | Portugal | Angola | Tunisia | ... |                ← HEADER ROW 2!
| Jan-25 | 7.45 | - | - | ... |                          ← DATA ROW
```

**This is common in European financial reporting (IFRS, local GAAP).**

### 3. Database Corruption Confirmed

**PostgreSQL Inspection:**
- 36,967 rows ingested
- Entities: "-", "0", "Jan-25" (should be "Portugal Cement")
- Metrics: "Group", "3,68" (should be "Variable Costs")
- **Conclusion:** AC1 (Table Extraction) never worked correctly

---

## Available Export Methods Analysis

**From Docling API Discovery:**

| Method | Returns | Use Case | Multi-Header Support? |
|--------|---------|----------|----------------------|
| `export_to_markdown()` | str | Text display | ❌ Flattens headers |
| `export_to_html()` | str | Web display | ⚠️ Preserves structure (needs parsing) |
| `export_to_dataframe()` | pandas.DataFrame | Data analysis | ✅ MultiIndex columns? (TESTING) |
| `model_dump_json()` | str (JSON) | Pydantic serialization | ⚠️ Generic, may not preserve table structure |
| `dict()` | dict | Python object | ⚠️ Generic Pydantic dict |

**Key Question:** Does `export_to_dataframe()` create MultiIndex columns for multi-header tables?

**Current Status:** Testing script running to find out!

---

## Next Session Plan

### Priority 1: Complete DataFrame Test (ETA: 2 minutes)

Check output of `scripts/test-dataframe-export.py`:
- Does DataFrame have MultiIndex columns?
- Can we access hierarchical headers?
- Is data structure preserved?

### Priority 2: Research Best Approach (30 min - MCP Required)

**DO NOT assume DataFrame is best** - need research validation:

```python
# Use MCP deep research
from mcp import deep_researcher

question = """
For financial PDF table extraction with multi-header tables, compare:
1. pandas DataFrame export (MultiIndex columns)
2. HTML parsing (BeautifulSoup/lxml)
3. Pydantic JSON serialization

Which approach is most reliable for preserving hierarchical table structure?
Industry best practices for financial data extraction?
Production use cases?
"""

results = await deep_researcher.research(question)
```

### Priority 3: Implement Chosen Approach (2-4 hours)

Based on test results + research:
- Implement table extractor using validated method
- Create unit tests
- Validate on sample tables

### Priority 4: Re-ingest & Validate (1 hour)

- Re-ingest with corrected extraction
- Run AC4 validation
- Target: ≥70% accuracy

---

## Files Created This Session

1. **`docs/validation/CRITICAL-ROOT-CAUSE-FOUND.md`**
   - Root cause analysis
   - Database corruption evidence

2. **`docs/validation/EXECUTIVE-SUMMARY-PM-PRESENTATION.md`**
   - Business-focused summary
   - For PM presentation

3. **`docs/validation/SOLUTION-PRODUCTION-PROVEN-APPROACH.md`**
   - DataFrame solution (DRAFT - needs validation)

4. **`scripts/validate-json-table-export.py`**
   - JSON validation script (revealed API mismatch)

5. **`scripts/test-dataframe-export.py`**
   - DataFrame test script (currently running)

6. **`scripts/debug-docling-markdown.py`**
   - Completed - showed multi-header structure

---

## Decision Points

### Decision 1: After DataFrame Test (TODAY)

**IF** DataFrame has MultiIndex → Research DataFrame vs alternatives
**IF** DataFrame is flat → Research HTML or Pydantic approaches

### Decision 2: After Research (TODAY/TOMORROW)

**IF** research validates approach → Implement
**IF** research shows better alternative → Pivot to that approach

### Decision 3: After Implementation (TOMORROW)

**IF** ≥70% accuracy → Story 2.13 COMPLETE ✅
**IF** <70% accuracy → Phase 2B (Structured Multi-Index)

---

## References

- **Architect Session:** `docs/sessions/2025-10-26-architect-session-docling-research-json-solution.md`
- **ADR-004:** `docs/architecture/decisions/ADR-004-json-export-multi-header-tables.md` (NEEDS UPDATE - JSON doesn't exist!)
- **Story 2.13:** `docs/stories/story-2.13-sql-table-search-phase2a-revised.md`

---

**NEXT SESSION COMMAND:**
```bash
# 1. Check DataFrame test results
python scripts/test-dataframe-export.py

# 2. Research best approach (MCP deep research required)
# 3. Implement validated solution
# 4. Re-ingest and validate
```

---

**STATUS:** Ready for next session - empirical test running, research needed before proceeding.
