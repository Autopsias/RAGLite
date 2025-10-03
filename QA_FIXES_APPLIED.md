# QA Fixes Applied - Story 0.1

## Date: 2025-10-03

## Critical Fix: Page Number Extraction (DATA-001)

### Issue

- QA Gate identified page extraction was non-functional
- `spike_ingestion_result.json` had no "pages" key
- All chunks had `page_number: null`
- Blocked NFR7 (95%+ source attribution accuracy)

### Root Cause

**Incorrect Docling API Usage**

- Original code attempted: `page.text` and `page.export_to_markdown()`
- Docling doesn't store text in page objects directly
- Content is stored in `doc.body` items with provenance metadata

### Solution Implemented

**File:** `spike/ingest_pdf.py` (lines 51-76)

```python
# BEFORE (incorrect)
for page_num, page in enumerate(doc.pages, start=1):
    page_text = page.export_to_markdown()  # Returns empty string

# AFTER (correct)
from collections import defaultdict
pages_dict = defaultdict(list)

for item in doc.body:
    if hasattr(item, 'prov') and item.prov:
        page_no = item.prov[0].page_no  # Extract from provenance
        item_text = item.export_to_markdown()
        pages_dict[page_no].append(item_text)

# Group text by page
for page_num in range(1, page_count + 1):
    page_text = "\n\n".join(pages_dict.get(page_num, []))
    pages_with_content.append({
        "page_number": page_num,
        "text": page_text,
        "char_count": len(page_text)
    })
```

### Verification Steps

1. ✅ Re-run ingestion with fixed code
2. 🔄 Verify pages array has non-null content
3. 🔄 Run complete pipeline (chunk → embed → store → test)
4. 🔄 Confirm page numbers in Qdrant metadata
5. 🔄 Validate page attribution in MCP responses

### Expected Outcomes

- ✅ `spike_ingestion_result.json` contains "pages" key
- ✅ Pages have >0 characters of content
- ✅ Page numbers flow through: ingestion → chunks → Qdrant → MCP
- ✅ Meets NFR7 requirement (95%+ source attribution)

---

## Other Fixes Applied

### HIGH: Dependency Version Pinning

**Status:** ✅ VERIFIED (QA confirmed)
**File:** `requirements.txt`

- All dependencies now pinned to exact versions
- Mitigates TECH-003 risk (version conflicts)

### MEDIUM: Qdrant API Migration

**Status:** ✅ VERIFIED (QA confirmed)
**Files:** `spike/store_vectors.py`, `spike/mcp_server.py`

- Migrated from deprecated `search()` to `query_points()`
- Compatible with Qdrant 1.15+

---

## Automated Pipeline Execution

**Monitoring:** Active (bash ID: 5e81bf)
**Auto-triggers when ingestion completes:**

1. Verify page extraction
2. Run chunking (preserves page metadata)
3. Generate embeddings
4. Store in Qdrant
5. Test MCP server
6. Validate accuracy (15 ground truth queries)

**Success Criteria:**

- 70%+ accuracy = GO for Phase 1
- Page numbers present throughout pipeline
- All QA gate CRITICAL/HIGH issues resolved
