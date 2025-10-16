# Story 1.14: PDF Ingestion Guide

**Date:** 2025-10-14
**Status:** Ready for Execution

---

## Prerequisites Completed ✅

1. **Qdrant Database Cleaned**
   - Removed 147 test data points from `financial_docs` collection
   - Database is now empty and ready for fresh ingestion
   - Use `python scripts/inspect-qdrant.py` to verify state

2. **PDF Files Split**
   - Original: `docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf` (160 pages)
   - Split into: 4 files in `docs/sample pdf/split/` (40 pages each)
   - Page numbers remain consistent with original PDF

---

## Split PDF Files

| File | Page Range | Size | Path |
|------|------------|------|------|
| Part 1 | Pages 1-40 | 1.4 MB | `2025-08 Performance Review CONSO_v2_part01_pages001-040.pdf` |
| Part 2 | Pages 41-80 | 962 KB | `2025-08 Performance Review CONSO_v2_part02_pages041-080.pdf` |
| Part 3 | Pages 81-120 | 1.1 MB | `2025-08 Performance Review CONSO_v2_part03_pages081-120.pdf` |
| Part 4 | Pages 121-160 | 825 KB | `2025-08 Performance Review CONSO_v2_part04_pages121-160.pdf` |

---

## Ingestion Sequence

**IMPORTANT:** Ingest PDFs sequentially to avoid overloading Claude Code

```bash
# Step 1: Ingest Part 1 (Pages 1-40)
uv run python -m raglite.main ingest "./docs/sample pdf/split/2025-08 Performance Review CONSO_v2_part01_pages001-040.pdf"

# Step 2: Verify ingestion
python scripts/inspect-qdrant.py

# Step 3: Ingest Part 2 (Pages 41-80)
uv run python -m raglite.main ingest "./docs/sample pdf/split/2025-08 Performance Review CONSO_v2_part02_pages041-080.pdf"

# Step 4: Verify ingestion
python scripts/inspect-qdrant.py

# Step 5: Ingest Part 3 (Pages 81-120)
uv run python -m raglite.main ingest "./docs/sample pdf/split/2025-08 Performance Review CONSO_v2_part03_pages081-120.pdf"

# Step 6: Verify ingestion
python scripts/inspect-qdrant.py

# Step 7: Ingest Part 4 (Pages 121-160)
uv run python -m raglite.main ingest "./docs/sample pdf/split/2025-08 Performance Review CONSO_v2_part04_pages121-160.pdf"

# Step 8: Final verification
python scripts/inspect-qdrant.py
```

---

## Validation Process

After all 4 PDFs are ingested:

1. **Manual Validation (Task 1)**
   - Open appropriate split PDF based on page number being validated
   - Pages 1-40: Use `part01` file
   - Pages 41-80: Use `part02` file
   - Pages 81-120: Use `part03` file
   - Pages 121-160: Use `part04` file

2. **Page Number Mapping**
   - Ground truth page numbers are based on the **original 160-page PDF**
   - When validating page 50, use Part 2 (pages 41-80) and navigate to page 50
   - Split PDFs maintain the original page numbering

3. **Testing (Task 3)**
   ```bash
   # Structural validation
   uv run python scripts/validate_ground_truth.py

   # Accuracy tests
   uv run python scripts/run-accuracy-tests.py
   ```

---

## Expected Outcomes

- ✅ All 160 pages ingested successfully
- ✅ Page numbers preserved from original PDF
- ✅ Qdrant contains ~150+ document chunks
- ✅ Ready for ground truth validation

---

## Troubleshooting

**Issue:** Ingestion fails with memory error
**Solution:** Ensure ingesting one file at a time, verify previous ingestion completed

**Issue:** Page numbers don't match
**Solution:** Page numbers in ground truth match original 160-page PDF, not split file page numbers

**Issue:** Database seems empty after ingestion
**Solution:** Run `python scripts/inspect-qdrant.py` to check collection state

---

## Utility Scripts

- **Database inspection:** `python scripts/inspect-qdrant.py`
- **Database cleanup:** `python scripts/inspect-qdrant.py --clean`
- **PDF splitting:** `python scripts/split-pdf.py <input.pdf> --pages-per-file 40`

---

**Next Step:** Begin Story 1.14 Task 1 (Manual Validation) once all PDFs are ingested.
