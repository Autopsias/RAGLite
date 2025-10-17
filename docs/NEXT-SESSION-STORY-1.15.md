# Next Session: Story 1.15 - Quick Start Guide

**Date:** 2025-10-14
**Session Type:** Story 1.15 Implementation (Table Extraction Fix)
**Prerequisite:** Story 1.15A COMPLETE ✅

---

## 🎯 Quick Context (60 seconds)

**What Story 1.15A Accomplished:**
- ✅ Ingested full PDF (147 chunks, pages 1-160)
- ✅ Identified root cause of 0% accuracy
- ✅ Validated retrieval system is working correctly

**The Problem:**
Docling extracts table **headers and footnotes** as text, but **NOT table cell data** (numerical values). Financial metrics like costs (23.2 EUR/ton), margins (50.6%), and EBITDA values are stored in table cells and are **completely missing** from indexed chunks.

**The Evidence:**
- Search for "23.2" returns ZERO chunks (data not extracted)
- Page 46 exists but contains only headers/footnotes
- Retrieval system working (0.83-0.87 similarity scores)
- Ground truth validated against PDF (data IS in PDF, NOT in chunks)

---

## 🚀 What to Do First

### Step 1: Load Story 1.15
```bash
# Read the story file
cat docs/stories/story-1.15-accuracy-test-validation.md

# Check current Qdrant state
python scripts/inspect-qdrant.py
# Expected: 147 points, pages 1-160
```

### Step 2: Research Docling Table Extraction
**Goal:** Find out if Docling supports table-to-text conversion

**Check these resources:**
1. Docling documentation: https://github.com/DS4SD/docling
2. Look for `TableFormer`, `table_settings`, or table extraction in docs
3. Check our current usage in `raglite/ingestion/pipeline.py:441`

**Current code:**
```python
converter = DocumentConverter()  # Line 441 in pipeline.py
```

**Questions to answer:**
- Does Docling have table extraction built-in?
- What parameters exist for `DocumentConverter()`?
- Can we enable table parsing with a config option?

### Step 3: Choose Implementation Path

**Path A: Docling Native (PREFERRED if available)**
```python
# If Docling supports tables natively
converter = DocumentConverter(
    table_extraction=True,  # Check actual parameter name
    table_format="text"     # Convert tables to searchable text
)
```

**Path B: Alternative Library (if Docling doesn't support)**
```python
# Option 1: pdfplumber (good for tables)
import pdfplumber
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        # Convert tables to text and merge with Docling chunks

# Option 2: camelot-py (specialized for tables)
import camelot
tables = camelot.read_pdf(pdf_path, pages='all')
# Convert to text and merge

# Option 3: tabula-py (Java-based, very robust)
import tabula
tables = tabula.read_pdf(pdf_path, pages='all')
# Convert to text and merge
```

---

## 📋 Implementation Checklist

### Task 1: Fix Table Extraction (1-1.5 hours)
- [ ] Research Docling table extraction capabilities
- [ ] Test table extraction on page 46 (verify "23.2" is extracted)
- [ ] Implement chosen solution (Docling config OR alternative library)
- [ ] Update `raglite/ingestion/pipeline.py` with table extraction code

### Task 2: Update Pipeline (30-45 min)
- [ ] Modify `ingest_pdf()` function to extract tables
- [ ] Ensure table data converted to searchable text format
- [ ] Preserve page attribution for table cells
- [ ] Update chunking logic to include table rows/cells

### Task 3: Re-Ingest PDF (15-20 min)
- [ ] Clear Qdrant: `python -c "from raglite.shared.clients import get_qdrant_client; get_qdrant_client().delete_collection('financial_docs')"`
- [ ] Re-ingest: `uv run python scripts/ingest-pdf.py` (or whole PDF script)
- [ ] Verify: `python scripts/inspect-qdrant.py` shows 300+ chunks
- [ ] Test: Search for "23.2" returns chunks from page 46

### Task 4: Quick Validation (30 min)
- [ ] Re-run 3 diagnostic queries from Story 1.15A
- [ ] Verify page 46 and 77 in top 5 results
- [ ] Verify specific keywords found ("23.2", "50.6%", "104,647")
- [ ] Quick accuracy check: 50-70% on sample queries

### Task 5: Full Ground Truth Validation (1-1.5 hours)
- [ ] Run: `python scripts/run-accuracy-tests.py`
- [ ] Measure retrieval accuracy (target: ≥90%)
- [ ] Measure attribution accuracy (target: ≥95%)
- [ ] Generate validation report

### Task 6: Epic 1 Sign-Off (if passing)
- [ ] Document final metrics in Story 1.15
- [ ] Update Epic 1 status to COMPLETE
- [ ] Prepare for Phase 3

---

## 🔧 Key Files to Modify

1. **`raglite/ingestion/pipeline.py`** (PRIMARY)
   - Function: `ingest_pdf()` around line 437
   - Add: Table extraction logic
   - Ensure: Page numbers preserved for table cells

2. **`scripts/ingest-pdf.py`** (MAYBE)
   - May need update if pipeline signature changes
   - Currently just calls `ingest_document()`

3. **`docs/stories/story-1.15-accuracy-test-validation.md`**
   - Update with validation results
   - Document table extraction implementation

4. **`docs/qa/epic-1-final-validation-report.md`** (CREATE)
   - Final validation metrics
   - GO/NO-GO decision for Phase 3

---

## 📊 Expected Results

**Before Fix (Story 1.15A - Current State):**
- 147 chunks indexed
- 0% accuracy (table data missing)
- Search for "23.2": 0 results

**After Fix (Story 1.15 - Target):**
- 300+ chunks indexed (147 text + ~150-200 table cells)
- 90%+ retrieval accuracy
- 95%+ attribution accuracy
- Search for "23.2": Returns page 46 chunks

---

## 🚨 Common Issues & Solutions

**Issue 1: Docling doesn't support table extraction**
- **Solution:** Use pdfplumber or camelot-py
- **Effort:** +30 minutes for library integration

**Issue 2: Table extraction takes too long**
- **Solution:** Process tables in parallel or cache results
- **Effort:** +15 minutes for optimization

**Issue 3: Table data not searchable**
- **Solution:** Convert table rows to sentences (e.g., "Variable costs: 23.2 EUR/ton")
- **Effort:** +20 minutes for formatting logic

**Issue 4: Accuracy still <90% after fix**
- **Solution:** Adjust chunking strategy or embedding approach
- **Escalation:** May need Story 1.15B or Phase 2 (GraphRAG)

---

## 📚 Reference Documents

- **Story 1.15A:** `docs/stories/story-1.15A.md` (THIS STORY - contains diagnostic results)
- **Story 1.15:** `docs/stories/story-1.15-accuracy-test-validation.md` (NEXT STORY)
- **Ground Truth:** `tests/fixtures/ground_truth.py` (50 validated queries)
- **Pipeline Code:** `raglite/ingestion/pipeline.py` (table extraction goes here)
- **Epic 1 PRD:** `docs/prd/epic-1-foundation-accurate-retrieval.md` (NFR targets)

---

## ⏱️ Time Estimate

**Total: 3.5-4.5 hours**
- Research & implementation: 1.5-2 hours
- Re-ingestion: 15-20 minutes
- Validation: 1.5-2 hours

**Quick Win Path (if Docling supports tables):**
- Config change: 15 minutes
- Re-ingest: 15 minutes
- Validation: 1.5 hours
- **Total: ~2 hours**

---

## 🎯 Success Criteria

Story 1.15 is COMPLETE when:
1. ✅ Table data extracted and searchable
2. ✅ 300+ chunks indexed
3. ✅ Retrieval accuracy ≥90% (45/50 queries)
4. ✅ Attribution accuracy ≥95% (48/50 queries)
5. ✅ All ground truth queries validated
6. ✅ Epic 1 validation report created

---

## 💡 Quick Commands

```bash
# Start Story 1.15
bmad dev dev-story
# Select: Story 1.15

# Check current state
python scripts/inspect-qdrant.py

# Test table extraction (after implementation)
uv run python -c "
from raglite.ingestion.pipeline import ingest_document
import asyncio
asyncio.run(ingest_document('docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf'))
"

# Verify fix
uv run python -c "
from raglite.shared.clients import get_qdrant_client
client = get_qdrant_client()
results = client.scroll(collection_name='financial_docs', limit=200, with_payload=True)[0]
matches = [r for r in results if '23.2' in r.payload.get('text', '')]
print(f'Chunks with \"23.2\": {len(matches)}')
for m in matches[:3]:
    print(f'Page {m.payload.get(\"page_number\")}: {m.payload.get(\"text\")[:200]}...')
"

# Run full validation
python scripts/run-accuracy-tests.py
```

---

**Good luck! The hard part (diagnosis) is done. Now we just need to implement the fix!** 🚀
