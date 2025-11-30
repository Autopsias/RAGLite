# Next Session: Story 1.15C - Complete Table Cell Data Extraction

**Date Created:** 2025-10-16
**Priority:** CRITICAL - Blocks Story 1.15B baseline validation
**Estimated Effort:** 2-3 hours
**Prerequisite:** Story 1.15 (BLOCKED - partial completion)

---

## Quick Summary

Story 1.15 attempted to fix table extraction but discovered that **table cell data is not being extracted** despite Docling being configured correctly. The blocker is in how we process Docling items - we only handle `.text` attributes, but table data uses different attributes.

---

## What Was Completed (Story 1.15)

✅ **Docling configured for table extraction:**
- `PdfPipelineOptions(do_table_structure=True)`
- `TableFormerMode.ACCURATE`
- Configuration confirmed in logs

✅ **PDF re-ingested:**
- 336 chunks (target: 300+)
- All 160 pages processed
- Duration: 12.5 minutes
- No errors

✅ **Tests passing:**
- 41/41 unit tests
- 11/13 integration tests

❌ **Table cell data NOT extracted:**
- Search for "23.2": 0 results
- Search for "50.6%": 0 results
- Search for "104,647": 0 results
- Only table headers found, not cell values

---

## Root Cause

**File:** `raglite/ingestion/pipeline.py`
**Function:** `chunk_by_docling_items()` (line 978)
**Issue:**

```python
if hasattr(item, "text") and item.text.strip():
    page_items[page_no].append(item.text)
```

This only processes items with `.text` attribute. Table items likely use:
- `.data` attribute for cell data
- `.grid` attribute for structure
- `.export_to_markdown()` method
- Or require special type checking (`isinstance(item, TableItem)`)

---

## What Needs to Be Done (Story 1.15C)

### 1. Debug Docling Table Items (30-45 min)

**Goal:** Understand how Docling represents table data

**Approach:**
```python
from docling.document_converter import DocumentConverter

# Iterate items and inspect table types
for item, level in result.document.iterate_items():
    item_type = type(item).__name__
    if "Table" in item_type:
        print(f"Table item attributes: {dir(item)}")
        # Check: .text, .data, .grid, .export_to_markdown()
```

**Questions to answer:**
- What type are table items? (`TableItem`, `TableCell`, etc.)
- Do they have `.text` attribute with cell data?
- Do they have `.data` or `.grid` with structured data?
- Can we use `.export_to_markdown()` per-item?

**Alternative approach:**
- Check if `result.document.export_to_markdown()` includes table data
- If yes, use that instead of `iterate_items()`

### 2. Update `chunk_by_docling_items()` (45-60 min)

**Option A: Handle table items separately**
```python
for item, _ in result.document.iterate_items():
    if isinstance(item, TableItem):  # or check type name
        # Extract table data via .data, .grid, or .export_to_markdown()
        table_text = extract_table_text(item)
        page_items[page_no].append(table_text)
    elif hasattr(item, "text") and item.text.strip():
        page_items[page_no].append(item.text)
```

**Option B: Use markdown export**
```python
# Replace iterate_items() with export_to_markdown()
markdown_text = result.document.export_to_markdown()
# Then chunk the markdown (may include tables already)
```

**Option C: Process tables as separate chunks**
```python
# Keep current text processing
# Add separate loop for table items
# Create dedicated table chunks with page attribution
```

**Choose based on:**
- What works (debug findings from step 1)
- KISS principle (simplest that works)
- Page attribution preservation

### 3. Re-Ingest PDF (15-20 min)

```bash
# Clear Qdrant
python scripts/inspect-qdrant.py  # Verify current: 336 points

# Re-ingest with table fix
uv run python scripts/ingest-pdf.py "docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"

# Verify results
python scripts/verify-table-data.py
# Expected: "23.2", "50.6%", "104,647" all found
```

**Expected outcome:**
- 400-500 chunks (text + table cells)
- Table cell values searchable
- Page attribution preserved

### 4. Run Diagnostic Validation (30 min)

**Test queries** (from `tests/fixtures/ground_truth.py`):

1. **Query 1 (Cost Analysis):**
   - Question: "What is the variable cost per ton for Portugal Cement?"
   - Expected page: 46
   - Expected keywords: "23.2", "EUR/ton", "variable costs"

2. **Query 13 (Margins):**
   - Question: "What is the EBITDA IFRS margin for Portugal Cement?"
   - Expected page: 46
   - Expected keywords: "50.6%", "EBITDA", "margin"

3. **Query 21 (Financial):**
   - Question: "What was the EBITDA for Portugal in August 2025?"
   - Expected page: 77
   - Expected keywords: "104,647", "EBITDA", "portugal"

**Success criteria:**
- All 3 queries return results
- Pages 46, 77 in top-5 results
- Numeric keywords found in chunks
- Baseline accuracy: 50-70% (acceptable for Story 1.15B to proceed)

---

## Files to Focus On

**Primary:**
- `raglite/ingestion/pipeline.py` - `chunk_by_docling_items()` function (lines 931-1061)

**Testing:**
- `scripts/verify-table-data.py` - Verify table values extracted
- `scripts/inspect-page-46.py` - Inspect page 46 chunks
- `scripts/debug-docling-tables.py` - Debug Docling item structure

**Reference:**
- `tests/fixtures/ground_truth.py` - Test queries Q1, Q13, Q21
- `docs/stories/story-1.15-table-extraction-fix.md` - Current status + blocker details

---

## Key Constraints

🚨 **CRITICAL:**
- Use Docling official SDK patterns ONLY (no custom wrappers)
- Preserve page attribution for all chunks (including tables)
- Follow KISS principle (simplest approach that works)
- NO new dependencies without approval

**Tech stack:**
- Docling 2.55.1 (LOCKED - already installed)
- NO pdfplumber/camelot unless Docling fundamentally cannot handle tables

---

## Success Criteria (Story 1.15C Complete)

- [x] Table cell data extracted and searchable
- [x] Search for "23.2" returns chunks from page 46
- [x] Search for "50.6%" returns chunks from page 46
- [x] Search for "104,647" returns chunks from page 77
- [x] 3/3 diagnostic queries return relevant pages
- [x] Page attribution preserved for table chunks
- [x] All existing tests still pass (no regressions)
- [x] Ingestion creates 400-500 chunks (up from 336)

**Quality gate:** Cannot proceed to Story 1.15B without confirmed table data extraction.

---

## Debugging Commands

```bash
# Verify current Qdrant state
python scripts/inspect-qdrant.py

# Test table extraction manually
python scripts/debug-docling-tables.py

# Check specific page chunks
python scripts/inspect-page-46.py

# Verify table data after fix
python scripts/verify-table-data.py

# Re-ingest PDF
uv run python scripts/ingest-pdf.py "docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf"

# Run unit tests
uv run pytest tests/unit/test_ingestion.py -v

# Run integration tests
uv run pytest tests/integration/test_ingestion_integration.py -v
```

---

## Rollback Plan

**If Docling cannot extract table cells:**
1. Escalate to architecture review
2. Consider alternative: Use pdfplumber for tables, Docling for text
3. Fallback: Manual table annotation (not scalable)

**If fix takes >3 hours:**
1. Document progress in Story 1.15C
2. Create Story 1.15D for remaining work
3. Update Epic 1 timeline

---

## References

**Docling Documentation:**
- Table extraction: https://github.com/docling-project/docling/blob/main/docs/usage/advanced_options.md
- Item structure: Check Docling source code for `TableItem`, `TableCell` types

**Story Files:**
- Story 1.15: `docs/stories/story-1.15-table-extraction-fix.md` (BLOCKED)
- Story 1.15A: `docs/stories/story-1.15A.md` (root cause analysis)
- Story Context: `docs/stories/story-context-1.1.15.xml`

**Code Files:**
- Current implementation: `raglite/ingestion/pipeline.py:931-1061`
- Docling import: `raglite/ingestion/pipeline.py:13-16`

---

## Estimated Timeline

| Task | Duration | Total |
|------|----------|-------|
| Debug Docling table items | 30-45 min | 0:45 |
| Update chunk_by_docling_items() | 45-60 min | 1:45 |
| Re-ingest PDF | 15-20 min | 2:05 |
| Run diagnostic validation | 30 min | 2:35 |
| Document & update story | 15 min | **2:50** |

**Buffer:** 10 min
**Total:** **3 hours**

---

## Next Steps (Immediate)

1. **Start:** Load DEV agent for Story 1.15C
2. **First action:** Debug Docling table item structure (30-45 min)
3. **Decision point:** Choose Option A, B, or C based on findings
4. **Implementation:** Update `chunk_by_docling_items()` with table handling
5. **Validation:** Re-ingest + verify table data extraction
6. **Complete:** Mark Story 1.15C done, unblock Story 1.15B

---

**Status:** READY TO START
**Blocker Identified:** Yes - clear root cause documented
**Path Forward:** Clear - 3 implementation options defined
**Risk Level:** MEDIUM - Docling item structure unknown, may need alternative approach
