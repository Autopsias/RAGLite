# Implementation Plan: Option C + Phase 2 RAG Enhancements

**Generated:** 2025-10-14
**Author:** Dev Agent (Amelia)
**Status:** COMPREHENSIVE TECHNICAL PLAN
**Context:** Response to root cause analysis of 0% accuracy issue (page numbering bug)

---

## Executive Summary

This document provides a comprehensive implementation plan for:
1. **Option C (Immediate):** Ingest original unsplit 160-page PDF (eliminates page numbering bug)
2. **Phase 2 Enhancements:** Six advanced RAG improvements to achieve >95% accuracy

**Key Finding from Root Cause Analysis:**
- Current issue: Page numbering bug due to split PDFs (pages 41-80 mislabeled as 1-40)
- Original PDF ingestion is **FEASIBLE** (3.63 MB, ~500-800 MB peak memory)
- Semantic search infrastructure is working correctly
- Need enhancements for precision and financial domain understanding

---

## Part 1: Option C - Original Unsplit PDF Ingestion

### 1.1 Technical Feasibility Analysis

**Original PDF Specifications:**
```
Filename: 2025-08 Performance Review CONSO_v2.pdf
Size: 3.63 MB
Pages: 160
Format: PDF 1.7 (standard)
Content: Text + tables + charts (typical financial report)
```

**Memory Footprint Estimation:**

| Component | Memory Usage | Notes |
|-----------|--------------|-------|
| Docling PDF extraction | 200-500 MB | Streams page-by-page, keeps 2-3 pages in memory |
| Chunking buffer | 50-100 MB | Intermediate lists/dicts for chunk assembly |
| Embedding batch (32 chunks) | 100-150 MB | Model weights + 32×1024-dim vectors |
| Qdrant batch insert | 50 MB | Network buffer for vector upload |
| **Total Peak Memory** | **500-800 MB** | Well within Claude Code limits (4-8 GB) |

**Comparison to Split PDFs:**
- Split approach: 4 files × ~1 MB = 4 MB total, **BUT** requires 4 separate ingestion runs + page offset logic
- Unsplit approach: 1 file × 3.63 MB = single ingestion, **NO** page offset complexity

**Conclusion:** ✅ **Original PDF ingestion is FEASIBLE and PREFERRED**

---

### 1.2 Implementation Plan for Option C

#### Story 1.15A: Original PDF Ingestion (Immediate Fix)

**Objective:** Replace split PDF ingestion with original PDF ingestion

**Tasks:**

**Task 1: Update ingestion script (10 minutes)**

```python
# scripts/ingest-pdf.py

async def main():
    """Ingest the ORIGINAL unsplit PDF."""
    pdf_dir = project_root / "docs" / "sample pdf"

    # Use original PDF instead of split files
    original_pdf = pdf_dir / "2025-08 Performance Review CONSO_v2.pdf"

    if not original_pdf.exists():
        print(f"❌ Original PDF not found: {original_pdf}")
        print(f"   Falling back to split PDFs...")
        # Fallback to split PDFs with page offset (Option A)
        await ingest_split_pdfs()
        return

    print("=" * 80)
    print("PDF INGESTION - Story 1.15A (Original Unsplit PDF)")
    print("=" * 80)
    print()
    print(f"📄 Ingesting: {original_pdf.name}")
    print(f"   Size: {original_pdf.stat().st_size / (1024*1024):.2f} MB")
    print(f"   Expected pages: 160")
    print()

    try:
        metadata = await ingest_document(str(original_pdf))
        print(f"   ✓ Ingested {metadata.chunks_count} chunks from {metadata.pages} pages")
        print(f"   ✓ Page range: 1-{metadata.pages}")
        print(f"   ✓ Collection: {settings.qdrant_collection_name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 80)
    print("INGESTION COMPLETE")
    print("=" * 80)
```

**Task 2: Clean Qdrant database (5 minutes)**

```bash
# Remove existing split PDF data
python scripts/inspect-qdrant.py --clean

# Verify collection is empty
python scripts/inspect-qdrant.py
```

**Task 3: Run original PDF ingestion (15-20 minutes estimated)**

```bash
uv run python scripts/ingest-pdf.py
```

**Expected output:**
```
📄 Ingesting: 2025-08 Performance Review CONSO_v2.pdf
   ✓ Ingested ~147 chunks from 160 pages
   ✓ Page range: 1-160
```

**Task 4: Validate page numbers (5 minutes)**

```python
# Verify critical pages exist
python3 -c "
from qdrant_client import QdrantClient
from raglite.shared.config import settings

qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

# Check ground truth pages
critical_pages = [46, 47, 77, 108]

scroll_result = qdrant.scroll(
    collection_name='financial_docs',
    limit=200,
    with_payload=True,
    with_vectors=False
)

for page in critical_pages:
    count = sum(1 for point in scroll_result[0] if point.payload.get('page_number') == page)
    status = '✓' if count > 0 else '✗'
    print(f'{status} Page {page}: {count} chunks')
"
```

**Expected output:**
```
✓ Page 46: 2-3 chunks
✓ Page 47: 2-3 chunks
✓ Page 77: 2-3 chunks
✓ Page 108: 2-3 chunks
```

**Task 5: Run accuracy tests (10 minutes)**

```bash
uv run python scripts/run-accuracy-tests.py
```

**Expected outcome:**
- Retrieval accuracy: **90%+** (45+ / 50 queries)
- Attribution accuracy: **95%+** (48+ / 50 queries)
- NFR6 and NFR7: **PASS** ✅

**Success Criteria:**
- ✅ Original PDF ingested successfully
- ✅ All 160 pages present in Qdrant (pages 1-160)
- ✅ Critical pages (46, 47, 77, 108) have chunks
- ✅ Accuracy tests show ≥90% retrieval, ≥95% attribution
- ✅ Epic 1 validation gate: **PASSED**

**Total Time:** ~45-60 minutes

**Rollback Plan:**
- If original PDF ingestion fails (OOM, timeout, corruption):
  - Implement Option B (auto-detect page offset from filename)
  - Use split PDFs with corrected page numbering

---

## Part 2: Baseline Validation (Story 1.15B)

### 2.0 Baseline Validation - Test Fundamentals First

**Objective:** Validate that basic ingestion and semantic search work correctly with the original PDF BEFORE implementing Phase 2 enhancements.

**Rationale:**
- Establishes performance baseline
- Validates page numbering fix
- Identifies whether Phase 2 enhancements are actually needed
- Prevents over-engineering if baseline already meets NFR6/NFR7

---

#### Story 1.15B: Baseline Validation & Analysis

**Prerequisites:**
- ✅ Story 1.15A complete (original PDF ingested)
- ✅ Qdrant contains 147+ chunks from pages 1-160
- ✅ All critical pages (46, 47, 77, 108) are indexed

**Objectives:**
1. Validate semantic search quality with current E5 embeddings
2. Measure baseline accuracy on ground truth test set
3. Analyze failure patterns to guide Phase 2 priorities
4. Establish performance benchmarks (latency, precision, recall)

---

#### Task 1: Validate Ingestion Quality (15 minutes)

**Subtask 1.1: Inspect Qdrant database**

```bash
python3 -c "
from qdrant_client import QdrantClient
from raglite.shared.config import settings
from collections import Counter

qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

# Get all chunks
scroll_result = qdrant.scroll(
    collection_name='financial_docs',
    limit=200,
    with_payload=True,
    with_vectors=False
)

points = scroll_result[0]

print('=== INGESTION QUALITY REPORT ===')
print()
print(f'Total chunks: {len(points)}')

# Page distribution
pages = [p.payload.get('page_number') for p in points if 'page_number' in p.payload]
print(f'Chunks with page numbers: {len(pages)}')
print(f'Page range: {min(pages)} - {max(pages)}')

# Critical pages for ground truth
critical_pages = [46, 47, 77, 108]
print()
print('Critical pages coverage:')
for page in critical_pages:
    count = sum(1 for p in page if p == page)
    status = '✓' if count > 0 else '✗'
    print(f'  {status} Page {page}: {count} chunks')

# Chunks per page distribution
page_counts = Counter(pages)
avg_chunks = sum(page_counts.values()) / len(page_counts)
print()
print(f'Average chunks per page: {avg_chunks:.1f}')
print(f'Pages with <1 chunk: {sum(1 for c in page_counts.values() if c < 1)}')
print(f'Pages with >5 chunks: {sum(1 for c in page_counts.values() if c > 5)}')

# Source document
sources = set(p.payload.get('source_document') for p in points)
print()
print('Source documents:')
for source in sorted(sources):
    print(f'  - {source}')
"
```

**Expected output:**
```
=== INGESTION QUALITY REPORT ===

Total chunks: 147
Chunks with page numbers: 147
Page range: 1 - 160

Critical pages coverage:
  ✓ Page 46: 2 chunks
  ✓ Page 47: 2 chunks
  ✓ Page 77: 2 chunks
  ✓ Page 108: 2 chunks

Average chunks per page: 0.9
Pages with <1 chunk: 0
Pages with >5 chunks: 0

Source documents:
  - 2025-08 Performance Review CONSO_v2.pdf
```

**Success Criteria:**
- ✅ All 160 pages indexed (147+ chunks expected)
- ✅ Critical pages have chunks
- ✅ No pages with 0 chunks (coverage gaps)

**Subtask 1.2: Sample chunk quality**

```python
# scripts/inspect-chunk-quality.py

"""Inspect sample chunks to validate content quality."""

from qdrant_client import QdrantClient
from raglite.shared.config import settings
import random

qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

# Get chunks from critical pages
scroll_result = qdrant.scroll(
    collection_name='financial_docs',
    limit=200,
    with_payload=True,
    with_vectors=False
)

# Sample 5 chunks from critical pages
critical_pages = [46, 47, 77, 108]
samples = []

for page in critical_pages:
    page_chunks = [
        p for p in scroll_result[0]
        if p.payload.get('page_number') == page
    ]
    if page_chunks:
        samples.append(random.choice(page_chunks))

print('=== CHUNK QUALITY SAMPLES ===')
print()

for i, sample in enumerate(samples, 1):
    print(f'Sample {i}:')
    print(f'  Page: {sample.payload["page_number"]}')
    print(f'  Chunk ID: {sample.id}')
    print(f'  Text length: {len(sample.payload["text"])} chars')
    print(f'  Preview:')
    preview = sample.payload["text"][:300].replace('\n', ' ')
    print(f'    {preview}...')
    print()

    # Check for financial terminology
    financial_terms = ['EUR', 'ton', 'EBITDA', 'margin', 'costs', 'budget', 'YTD', 'YoY']
    found_terms = [term for term in financial_terms if term in sample.payload["text"]]
    if found_terms:
        print(f'  ✓ Financial terms found: {", ".join(found_terms)}')
    else:
        print(f'  ⚠ No financial terms detected')
    print()
```

**Success Criteria:**
- ✅ Chunks contain readable financial content
- ✅ Financial terminology preserved (EUR, EBITDA, etc.)
- ✅ No encoding issues or corruption

---

#### Task 2: Manual Test Queries (30 minutes)

**Objective:** Test semantic search with 10 representative queries before running full test suite.

**Subtask 2.1: Run manual test queries**

```python
# scripts/manual-test-queries.py

"""Manual test queries to validate semantic search."""

import asyncio
from raglite.retrieval.search import search_documents
import sys

# 10 representative queries from ground truth
TEST_QUERIES = [
    # Easy queries (direct keyword match)
    {
        "id": "Q1",
        "query": "What is the variable cost per ton for Portugal Cement?",
        "expected_page": 46,
        "expected_keywords": ["variable costs", "23.2", "EUR/ton"],
    },
    {
        "id": "Q13",
        "query": "What is the EBITDA IFRS margin for Portugal Cement?",
        "expected_page": 46,
        "expected_keywords": ["EBITDA", "IFRS", "margin", "34.8%"],
    },

    # Medium queries (conceptual understanding)
    {
        "id": "Q21",
        "query": "What was the EBITDA for Portugal in August 2025?",
        "expected_page": 77,
        "expected_keywords": ["EBITDA", "Portugal", "77.5"],
    },
    {
        "id": "Q25",
        "query": "How many safety incidents were reported in Portugal Cement?",
        "expected_page": 87,
        "expected_keywords": ["safety", "incidents", "LTI"],
    },

    # Hard queries (multi-hop or complex)
    {
        "id": "Q37",
        "query": "What is the total FTE count for Portugal operations?",
        "expected_page": 108,
        "expected_keywords": ["FTE", "Portugal", "total"],
    },
]


async def main():
    print("=== MANUAL TEST QUERIES ===")
    print()

    passed = 0
    failed = 0

    for test in TEST_QUERIES:
        print(f"{test['id']}: {test['query']}")

        # Search
        results = await search_documents(test['query'], top_k=5)

        # Check if expected page in top 5
        pages_retrieved = [r.page_number for r in results]
        page_match = test['expected_page'] in pages_retrieved

        # Check if keywords found
        all_text = " ".join([r.text for r in results])
        keywords_found = [kw for kw in test['expected_keywords'] if kw.lower() in all_text.lower()]
        keyword_pct = len(keywords_found) / len(test['expected_keywords']) * 100

        # Display results
        print(f"  Expected page: {test['expected_page']}")
        print(f"  Retrieved pages: {pages_retrieved[:5]}")
        print(f"  Page match: {'✓' if page_match else '✗'}")
        print(f"  Keywords found: {len(keywords_found)}/{len(test['expected_keywords'])} ({keyword_pct:.0f}%)")

        if page_match and keyword_pct >= 50:
            print(f"  Status: ✓ PASS")
            passed += 1
        else:
            print(f"  Status: ✗ FAIL")
            failed += 1

            # Debug failing query
            print(f"  Top result:")
            print(f"    Page: {results[0].page_number}, Score: {results[0].similarity_score:.4f}")
            print(f"    Preview: {results[0].text[:200]}...")

        print()

    # Summary
    print("=" * 80)
    print(f"MANUAL TEST SUMMARY: {passed}/10 passed ({passed/10*100:.0f}%)")
    print("=" * 80)

    if passed >= 9:
        print("✓ Baseline semantic search is working well (90%+)")
    elif passed >= 7:
        print("⚠ Baseline semantic search is acceptable (70-90%)")
    else:
        print("✗ Baseline semantic search needs improvement (<70%)")


if __name__ == "__main__":
    asyncio.run(main())
```

**Expected output:**
```
=== MANUAL TEST QUERIES ===

Q1: What is the variable cost per ton for Portugal Cement?
  Expected page: 46
  Retrieved pages: [46, 47, 33, 34, 48]
  Page match: ✓
  Keywords found: 3/3 (100%)
  Status: ✓ PASS

Q13: What is the EBITDA IFRS margin for Portugal Cement?
  Expected page: 46
  Retrieved pages: [46, 77, 45, 48, 47]
  Page match: ✓
  Keywords found: 4/4 (100%)
  Status: ✓ PASS

...

================================================================================
MANUAL TEST SUMMARY: 8/10 passed (80%)
================================================================================
⚠ Baseline semantic search is acceptable (70-90%)
```

**Success Criteria:**
- ✅ ≥7/10 manual tests pass (70%+)
- ✅ Easy queries (Q1, Q13) always pass
- ⚠ Medium/hard queries may fail (expected with baseline)

**Failure Analysis:**
- If <70%: Check embedding quality, chunk boundaries, page extraction
- If 70-89%: Proceed to Phase 2A (hybrid search)
- If ≥90%: Baseline may be sufficient, run full test suite

---

#### Task 3: Full Accuracy Test Suite (15 minutes)

**Subtask 3.1: Run ground truth accuracy tests**

```bash
uv run python scripts/run-accuracy-tests.py 2>&1 | tee baseline-accuracy-report.txt
```

**Subtask 3.2: Analyze results**

```python
# scripts/analyze-baseline-accuracy.py

"""Analyze baseline accuracy test results."""

import json

# Parse accuracy test output
with open('baseline-accuracy-report.txt', 'r') as f:
    output = f.read()

# Extract metrics (assuming JSON output from run-accuracy-tests.py)
# ... parsing logic ...

print("=== BASELINE ACCURACY ANALYSIS ===")
print()

print(f"Retrieval Accuracy: {retrieval_pct:.1f}%")
print(f"  NFR6 Target: ≥90%")
print(f"  Status: {'✓ PASS' if retrieval_pct >= 90 else '✗ FAIL'}")
print()

print(f"Attribution Accuracy: {attribution_pct:.1f}%")
print(f"  NFR7 Target: ≥95%")
print(f"  Status: {'✓ PASS' if attribution_pct >= 95 else '✗ FAIL'}")
print()

# Breakdown by category
print("Accuracy by Category:")
for category in ['cost_analysis', 'margins', 'financial_performance', 'safety', 'workforce', 'operating_expenses']:
    cat_accuracy = calculate_category_accuracy(category)
    print(f"  {category:25s}: {cat_accuracy:.1f}%")
print()

# Breakdown by difficulty
print("Accuracy by Difficulty:")
for difficulty in ['easy', 'medium', 'hard']:
    diff_accuracy = calculate_difficulty_accuracy(difficulty)
    print(f"  {difficulty:10s}: {diff_accuracy:.1f}%")
```

**Expected baseline accuracy (with Option C):**
- **Retrieval accuracy:** 85-92% (page numbering fixed, but no Phase 2 optimizations)
- **Attribution accuracy:** 95-98% (page extraction working correctly)

**Decision Tree:**

```
Baseline Accuracy Results:

├── Retrieval ≥90% AND Attribution ≥95%
│   ✓ EPIC 1 VALIDATED - No Phase 2 needed
│   → Proceed to Epic 2
│
├── Retrieval 85-89% OR Attribution 93-94%
│   ⚠ Close to targets
│   → Implement Phase 2A (Hybrid Search) only
│   → Re-test, likely sufficient
│
└── Retrieval <85% OR Attribution <93%
    ✗ Needs Phase 2 enhancements
    → Analyze failure patterns
    → Prioritize Phase 2A → 2B → 2C in sequence
```

---

#### Task 4: Failure Pattern Analysis (20 minutes)

**Objective:** Understand WHY queries fail to guide Phase 2 priorities.

**Subtask 4.1: Categorize failures**

```python
# scripts/analyze-failure-patterns.py

"""Analyze patterns in failed queries."""

from scripts.run_accuracy_tests import load_ground_truth
from raglite.retrieval.search import search_documents
import asyncio

async def main():
    ground_truth = load_ground_truth()

    failures = {
        'keyword_mismatch': [],    # Keywords present but semantic search missed
        'table_split': [],          # Content in table, possibly split across chunks
        'wrong_page': [],           # Retrieved content from wrong section
        'financial_term': [],       # Financial terminology not understood
        'multi_hop': [],            # Requires combining multiple chunks
    }

    for qa in ground_truth:
        results = await search_documents(qa['query'], top_k=5)

        # Check if failed
        expected_page = qa['expected_page_number']
        pages_retrieved = [r.page_number for r in results]

        if expected_page not in pages_retrieved:
            # Categorize failure
            all_text = " ".join([r.text for r in results])

            # Check if keywords exist somewhere in top 5
            keywords_found = sum(1 for kw in qa['expected_keywords'] if kw.lower() in all_text.lower())

            if keywords_found >= len(qa['expected_keywords']) * 0.5:
                # Keywords found but wrong page = semantic search issue
                failures['keyword_mismatch'].append(qa)
            elif qa['category'] in ['cost_analysis', 'margins', 'financial_performance']:
                # Likely table-related query
                failures['table_split'].append(qa)
            elif any(term in qa['query'].lower() for term in ['ebitda', 'capex', 'opex', 'fte']):
                # Financial terminology
                failures['financial_term'].append(qa)
            else:
                failures['wrong_page'].append(qa)

    # Print analysis
    print("=== FAILURE PATTERN ANALYSIS ===")
    print()

    total_failures = sum(len(v) for v in failures.values())
    print(f"Total failures: {total_failures}/50 ({total_failures/50*100:.0f}%)")
    print()

    for pattern, queries in failures.items():
        if queries:
            print(f"{pattern}: {len(queries)} failures ({len(queries)/total_failures*100:.0f}% of failures)")
            print(f"  Example: {queries[0]['question']}")
            print()

    # Recommendations
    print("=== PHASE 2 PRIORITY RECOMMENDATIONS ===")
    print()

    if failures['keyword_mismatch']:
        print(f"1. HYBRID SEARCH (Phase 2A): {len(failures['keyword_mismatch'])} queries would benefit")

    if failures['table_split']:
        print(f"2. TABLE-AWARE CHUNKING (Phase 2C): {len(failures['table_split'])} queries would benefit")

    if failures['financial_term']:
        print(f"3. FINANCIAL EMBEDDINGS (Phase 2B): {len(failures['financial_term'])} queries would benefit")

    if failures['multi_hop']:
        print(f"4. RE-RANKING (Phase 2D): {len(failures['multi_hop'])} queries would benefit")


if __name__ == "__main__":
    asyncio.run(main())
```

**Expected output:**
```
=== FAILURE PATTERN ANALYSIS ===

Total failures: 6/50 (12%)

keyword_mismatch: 3 failures (50% of failures)
  Example: What is the distribution cost per ton for Portugal Cement?

table_split: 2 failures (33% of failures)
  Example: What are the fixed costs EUR/ton for Portugal Cement?

financial_term: 1 failure (17% of failures)
  Example: What is the EBITDA for Angola operations?

=== PHASE 2 PRIORITY RECOMMENDATIONS ===

1. HYBRID SEARCH (Phase 2A): 3 queries would benefit
2. TABLE-AWARE CHUNKING (Phase 2C): 2 queries would benefit
3. FINANCIAL EMBEDDINGS (Phase 2B): 1 query would benefit
```

**This guides Phase 2 implementation order!**

---

#### Task 5: Performance Benchmarking (10 minutes)

**Subtask 5.1: Measure query latency**

```python
# scripts/benchmark-latency.py

"""Benchmark query latency for baseline."""

import asyncio
import time
from raglite.retrieval.search import search_documents
from scripts.run_accuracy_tests import load_ground_truth

async def main():
    ground_truth = load_ground_truth()

    latencies = []

    print("=== LATENCY BENCHMARK ===")
    print(f"Running {len(ground_truth)} queries...")
    print()

    for qa in ground_truth:
        start = time.time()
        results = await search_documents(qa['query'], top_k=5)
        end = time.time()

        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)

    # Calculate percentiles
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    avg = sum(latencies) / len(latencies)

    print(f"Query Latency (baseline - E5 embeddings + vector search):")
    print(f"  Average: {avg:.1f}ms")
    print(f"  Median (p50): {p50:.1f}ms")
    print(f"  p95: {p95:.1f}ms")
    print(f"  p99: {p99:.1f}ms")
    print()
    print(f"NFR5 Requirement: <10s (10,000ms)")
    print(f"Status: {'✓ PASS' if p95 < 10000 else '✗ FAIL'}")
    print()

    # Latency budget for Phase 2
    budget_remaining = 10000 - p95
    print(f"Latency budget remaining for Phase 2 enhancements: {budget_remaining:.0f}ms")


if __name__ == "__main__":
    asyncio.run(main())
```

**Expected output:**
```
=== LATENCY BENCHMARK ===
Running 50 queries...

Query Latency (baseline - E5 embeddings + vector search):
  Average: 28.5ms
  Median (p50): 25.2ms
  p95: 53.1ms
  p99: 68.4ms

NFR5 Requirement: <10s (10,000ms)
Status: ✓ PASS

Latency budget remaining for Phase 2 enhancements: 9,947ms
```

**Interpretation:**
- Baseline is **FAST** (p95 = 53ms)
- **9,947ms latency budget** available for Phase 2 enhancements
- Can afford expensive enhancements (query expansion +800ms, re-ranking +150ms)

---

#### Story 1.15B: Success Criteria

**COMPLETE when:**
- ✅ Ingestion quality validated (all 160 pages, critical pages have chunks)
- ✅ Manual test queries show ≥70% pass rate
- ✅ Full accuracy test suite executed (baseline metrics recorded)
- ✅ Failure patterns analyzed and Phase 2 priorities identified
- ✅ Performance benchmarked (latency budget calculated)

**Deliverables:**
1. `baseline-accuracy-report.txt` - Full test results
2. `baseline-failure-analysis.md` - Failure patterns and Phase 2 recommendations
3. `baseline-performance-benchmarks.txt` - Latency metrics

**Expected Outcome:**
```
=== BASELINE VALIDATION SUMMARY ===

Retrieval Accuracy: 88.0% (44/50 queries)
Attribution Accuracy: 96.0% (48/50 queries)
Query Latency (p95): 53ms

NFR6 (≥90% retrieval): ✗ CLOSE (88% - need +2%)
NFR7 (≥95% attribution): ✓ PASS (96%)
NFR5 (<10s latency): ✓ PASS (53ms << 10s)

RECOMMENDATION: Implement Phase 2A (Hybrid Search) to reach 90%+ retrieval.
```

**Decision Gate:**
- If retrieval ≥90% → Epic 1 VALIDATED, skip Phase 2
- If retrieval 85-89% → Implement Phase 2A only
- If retrieval <85% → Implement Phase 2A → 2B → 2C sequence

---

## Part 3: Phase 2 RAG Enhancements

### Overview of Enhancements

| Enhancement | Impact | Complexity | Dependencies | Priority |
|-------------|--------|-----------|--------------|----------|
| **2A: Hybrid Search** | +5-10% accuracy | LOW | None (Qdrant SDK) | HIGH |
| **2B: Financial Embeddings** | +10-15% accuracy | MEDIUM | FinBERT or OpenAI | HIGH |
| **2C: Table-Aware Chunking** | +5-8% accuracy | MEDIUM | None (Docling) | MEDIUM |
| **2D: Cross-Encoder Re-ranking** | +3-5% precision | MEDIUM | sentence-transformers ✓ | MEDIUM |
| **2E: Query Expansion** | +2-5% recall | LOW | None (LLM API) | LOW |
| **2F: Multi-Vector Representations** | +5-10% accuracy | HIGH | None (Qdrant) | LOW |

**Recommended Implementation Order:**
1. **Phase 2A** (Hybrid Search) - Quick win, no new dependencies
2. **Phase 2B** (Financial Embeddings) - Highest impact
3. **Phase 2C** (Table-Aware Chunking) - Financial document specific
4. **Phase 2D** (Cross-Encoder Re-ranking) - Precision boost
5. **Phase 2E** (Query Expansion) - If still <95% accuracy
6. **Phase 2F** (Multi-Vector) - Advanced optimization

---

### 2A: Hybrid Search (Semantic + Keyword)

#### Objective
Combine vector similarity search with keyword matching to improve precision for queries with specific data points (numbers, dates, exact phrases).

#### Technical Approach

**Current State:**
```python
# Pure vector similarity search
results = qdrant.query_points(
    collection_name="financial_docs",
    query=query_embedding,
    limit=5,
)
```

**Enhanced Strategy - Post-Search Keyword Re-ranking:**

```python
# Step 1: Vector search with over-retrieval
vector_results = qdrant.query_points(
    collection_name="financial_docs",
    query=query_embedding,
    limit=20,  # Retrieve more candidates
)

# Step 2: Extract keywords from query
query_keywords = extract_keywords(query_text)
# Example: "What is the variable cost per ton?"
# → ["variable cost", "per ton", "EUR/ton"]

# Step 3: Score each result by keyword presence
def score_keyword_match(text: str, keywords: list[str]) -> float:
    """Score document by keyword presence (0.0 - 1.0)."""
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return matches / len(keywords) if keywords else 0.0

keyword_scores = [
    score_keyword_match(result.payload["text"], query_keywords)
    for result in vector_results
]

# Step 4: Combine semantic + keyword scores
SEMANTIC_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3

combined_scores = [
    (SEMANTIC_WEIGHT * result.score) + (KEYWORD_WEIGHT * kw_score)
    for result, kw_score in zip(vector_results, keyword_scores)
]

# Step 5: Re-rank and return top 5
reranked_results = [
    result for _, result in
    sorted(zip(combined_scores, vector_results), reverse=True)
][:5]
```

**Implementation File:** `raglite/retrieval/hybrid.py`

```python
"""Hybrid search combining semantic and keyword matching."""

from raglite.retrieval.search import search_documents
from raglite.shared.models import QueryResult
import re


def extract_keywords(query: str) -> list[str]:
    """Extract important keywords from query.

    Strategy:
        - Remove stop words (the, is, what, etc.)
        - Keep financial terms (EUR, ton, costs, EBITDA)
        - Keep numbers and units
        - Keep multi-word phrases (variable costs, per ton)
    """
    # Financial domain keywords (always include)
    financial_terms = {
        "EUR", "USD", "ton", "costs", "EBITDA", "margin", "revenue",
        "CAPEX", "OPEX", "FTE", "YTD", "YoY", "budget", "actual",
    }

    # Common stop words (exclude)
    stop_words = {
        "the", "is", "are", "what", "how", "where", "when", "who",
        "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    }

    # Extract words
    words = re.findall(r'\b\w+\b', query.lower())

    # Filter keywords
    keywords = []
    for word in words:
        # Include if: financial term OR number OR not stop word
        if (word in financial_terms or
            word.replace('.', '').isdigit() or
            word not in stop_words):
            keywords.append(word)

    # Extract multi-word phrases (bigrams)
    phrases = []
    for i in range(len(words) - 1):
        phrase = f"{words[i]} {words[i+1]}"
        # Include if both words are keywords
        if words[i] not in stop_words and words[i+1] not in stop_words:
            phrases.append(phrase)

    return keywords + phrases


async def hybrid_search(
    query: str,
    top_k: int = 5,
    semantic_weight: float = 0.7,
    keyword_weight: float = 0.3,
    over_retrieve_factor: int = 4,
) -> list[QueryResult]:
    """Hybrid search combining semantic and keyword matching.

    Args:
        query: Natural language query
        top_k: Number of final results to return
        semantic_weight: Weight for semantic similarity (0.0-1.0)
        keyword_weight: Weight for keyword matching (0.0-1.0)
        over_retrieve_factor: Retrieve top_k * factor candidates for re-ranking

    Returns:
        Re-ranked query results combining both signals
    """
    # Step 1: Semantic search with over-retrieval
    candidate_count = top_k * over_retrieve_factor
    vector_results = await search_documents(query, top_k=candidate_count)

    # Step 2: Extract query keywords
    keywords = extract_keywords(query)

    # Step 3: Score keyword matching
    keyword_scores = []
    for result in vector_results:
        text_lower = result.text.lower()
        matches = sum(1 for kw in keywords if kw in text_lower)
        score = matches / len(keywords) if keywords else 0.0
        keyword_scores.append(score)

    # Step 4: Combine scores
    combined_scores = []
    for result, kw_score in zip(vector_results, keyword_scores):
        semantic_score = result.similarity_score
        combined_score = (semantic_weight * semantic_score) + (keyword_weight * kw_score)
        combined_scores.append(combined_score)

    # Step 5: Re-rank and return top_k
    ranked_pairs = sorted(
        zip(combined_scores, vector_results),
        key=lambda x: x[0],
        reverse=True
    )

    # Update similarity scores with combined scores
    reranked_results = []
    for score, result in ranked_pairs[:top_k]:
        result.similarity_score = score  # Update with combined score
        reranked_results.append(result)

    return reranked_results
```

**Integration into MCP Tool:**

```python
# raglite/main.py

from raglite.retrieval.hybrid import hybrid_search

@mcp.tool()
async def query_financial_documents(request: QueryRequest) -> str:
    """Query financial documents using hybrid search."""

    # Use hybrid search instead of pure semantic search
    results = await hybrid_search(
        query=request.query,
        top_k=request.top_k,
        semantic_weight=0.7,  # Configurable
        keyword_weight=0.3,
    )

    # Continue with synthesis...
```

**Testing Strategy:**

```python
# tests/integration/test_hybrid_search.py

async def test_hybrid_search_exact_numbers():
    """Hybrid search should prioritize exact number matches."""
    query = "What is the variable cost per ton? It should be 23.2 EUR/ton."

    results = await hybrid_search(query, top_k=5)

    # Check that results containing "23.2" rank higher
    assert "23.2" in results[0].text
    assert results[0].page_number == 46


async def test_hybrid_search_vs_pure_semantic():
    """Hybrid search should outperform pure semantic on keyword queries."""
    query = "EBITDA IFRS margin for Portugal Cement"

    hybrid_results = await hybrid_search(query)
    semantic_results = await search_documents(query)

    # Hybrid should find more exact matches
    hybrid_keywords = ["EBITDA", "IFRS", "margin"]
    hybrid_matches = sum(1 for r in hybrid_results if any(kw in r.text for kw in hybrid_keywords))
    semantic_matches = sum(1 for r in semantic_results if any(kw in r.text for kw in hybrid_keywords))

    assert hybrid_matches >= semantic_matches
```

**Expected Impact:**
- **Retrieval accuracy:** +5-10% (better for queries with specific numbers/terms)
- **Attribution accuracy:** +3-5% (more precise page matching)
- **Latency:** +5-10ms (keyword scoring overhead)

**Success Criteria:**
- Queries with exact numbers (e.g., "23.2 EUR/ton") retrieve correct chunks in top 3
- Financial terms (EBITDA, CAPEX, YTD) boost relevant documents
- Accuracy tests show ≥92% retrieval accuracy (up from 90%)

---

### 2B: Financial-Specific Embeddings

#### Objective
Replace general-purpose E5-large-v2 embeddings with financial domain-specific embeddings to improve semantic understanding of financial terminology.

#### Technical Analysis

**Current Embedding Model:**
```
Model: intfloat/e5-large-v2
Dimensions: 1024
Training data: General web corpus (Wikipedia, Common Crawl)
Domain: General purpose
Financial terminology: ❌ Not specialized
```

**Candidate Replacement Models:**

| Model | Dims | Domain | Pros | Cons | Cost |
|-------|------|--------|------|------|------|
| **OpenAI text-3-large** | 3072 | General+ | SOTA quality, easy API | API cost, latency | $0.13/1M tokens |
| **FinBERT** | 768 | Finance | Finance-trained | Needs embedding adapter | Free (local) |
| **BGE-large-financial** | 1024 | Finance | Finance corpus | May not exist yet | Free (local) |
| **Fine-tuned E5** | 1024 | Custom | Optimal for our data | Requires training | GPU hours |

#### Option 2B-1: OpenAI Embeddings (Quick Evaluation)

**Implementation:**

```python
# raglite/ingestion/openai_embeddings.py

"""OpenAI embeddings for comparison with E5."""

import asyncio
from openai import AsyncOpenAI
from raglite.shared.config import settings
from raglite.shared.models import Chunk

client = AsyncOpenAI(api_key=settings.openai_api_key)

async def generate_openai_embeddings(
    chunks: list[Chunk],
    model: str = "text-embedding-3-large",
    batch_size: int = 100,
) -> list[Chunk]:
    """Generate OpenAI embeddings for chunks.

    Args:
        chunks: Chunks to embed
        model: OpenAI embedding model (text-embedding-3-large or -small)
        batch_size: API batch size (max 2048 for OpenAI)

    Returns:
        Chunks with populated embedding field
    """
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [chunk.content for chunk in batch]

        # Call OpenAI API
        response = await client.embeddings.create(
            input=texts,
            model=model,
            encoding_format="float"
        )

        # Populate embeddings
        for chunk, embedding_obj in zip(batch, response.data):
            chunk.embedding = embedding_obj.embedding

    return chunks
```

**A/B Test Configuration:**

```python
# scripts/compare-embeddings.py

"""Compare E5 vs OpenAI embeddings on ground truth test set."""

import asyncio
from raglite.ingestion.pipeline import generate_embeddings  # E5
from raglite.ingestion.openai_embeddings import generate_openai_embeddings
from scripts.run_accuracy_tests import run_accuracy_validation

async def main():
    print("=== EMBEDDING MODEL COMPARISON ===")
    print()

    # Test 1: E5-large-v2 (current)
    print("Test 1: E5-large-v2 (baseline)")
    await reingest_with_embeddings("e5-large-v2")
    e5_accuracy = await run_accuracy_validation()
    print(f"  Retrieval: {e5_accuracy.retrieval_pct:.1f}%")
    print(f"  Attribution: {e5_accuracy.attribution_pct:.1f}%")

    # Test 2: OpenAI text-embedding-3-large
    print()
    print("Test 2: OpenAI text-embedding-3-large")
    await reingest_with_embeddings("openai-large")
    openai_accuracy = await run_accuracy_validation()
    print(f"  Retrieval: {openai_accuracy.retrieval_pct:.1f}%")
    print(f"  Attribution: {openai_accuracy.attribution_pct:.1f}%")

    # Comparison
    print()
    print("=== RESULTS ===")
    improvement = openai_accuracy.retrieval_pct - e5_accuracy.retrieval_pct
    print(f"Retrieval improvement: {improvement:+.1f}%")

    if improvement > 5.0:
        print("✓ OpenAI embeddings show significant improvement (>5%)")
        print("  Recommendation: Use OpenAI embeddings")
    elif improvement > 2.0:
        print("⚠ OpenAI embeddings show marginal improvement (2-5%)")
        print("  Recommendation: Evaluate cost vs. benefit")
    else:
        print("✗ OpenAI embeddings do not improve accuracy significantly")
        print("  Recommendation: Stick with E5-large-v2 (free)")

if __name__ == "__main__":
    asyncio.run(main())
```

**Expected Outcome:**
- If OpenAI > +5% accuracy → **Adopt OpenAI embeddings**
- If OpenAI < +2% accuracy → **Keep E5-large-v2** (cost not justified)
- If marginal (+2-5%) → **Evaluate based on budget**

#### Option 2B-2: FinBERT Embeddings (Local Alternative)

**Implementation:**

```python
# raglite/ingestion/finbert_embeddings.py

"""FinBERT embeddings for financial document understanding."""

from transformers import AutoTokenizer, AutoModel
import torch
from raglite.shared.models import Chunk

# Load FinBERT model (singleton)
_tokenizer = None
_model = None

def get_finbert_model():
    """Load FinBERT model (cached)."""
    global _tokenizer, _model
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
        _model = AutoModel.from_pretrained("ProsusAI/finbert")
        _model.eval()  # Inference mode
    return _tokenizer, _model

async def generate_finbert_embeddings(
    chunks: list[Chunk],
    batch_size: int = 32,
) -> list[Chunk]:
    """Generate FinBERT embeddings for chunks.

    Note: FinBERT outputs 768-dimensional vectors (vs 1024 for E5).
    Need to recreate Qdrant collection with vector_size=768.
    """
    tokenizer, model = get_finbert_model()

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [chunk.content for chunk in batch]

        # Tokenize
        encoded = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,  # FinBERT max length
            return_tensors="pt"
        )

        # Generate embeddings (mean pooling of last hidden state)
        with torch.no_grad():
            outputs = model(**encoded)
            embeddings = outputs.last_hidden_state.mean(dim=1)  # Mean pooling

        # Populate embedding field
        for chunk, embedding in zip(batch, embeddings):
            chunk.embedding = embedding.cpu().numpy().tolist()

    return chunks
```

**Challenge:** FinBERT is 768-dim, E5 is 1024-dim
- **Solution:** Recreate Qdrant collection with `vector_size=768`
- **OR:** Pad FinBERT to 1024-dim (add zeros) - less ideal

**Expected Impact:**
- **Financial terminology:** Better understanding of EBITDA, CAPEX, margin, etc.
- **Number context:** May better associate "23.2" with "EUR/ton" as a unit
- **Retrieval accuracy:** +10-15% (hypothesis - needs validation)

---

### 2C: Table-Aware Chunking

#### Objective
Modify chunking strategy to keep financial tables intact, preventing mid-table splits that lose context.

#### Technical Approach

**Current Problem:**

```
Chunk boundary at 500 words

Page 46 content:
Text: "Portugal Cement operational performance shows..."
<CHUNK BOUNDARY - SPLIT HERE>
Table:
| Metric         | Aug-25 YTD | Budget | Aug-24 |
|----------------|-----------|--------|--------|
| Variable costs | 23.2      | 20.3   | 29.4   |  ← Lost in next chunk
| Fixed costs    | 15.8      | 14.2   | 16.1   |
```

**Result:** Query for "variable costs 23.2" might retrieve chunk with text but not table data.

**Enhanced Strategy - Table Detection:**

```python
# raglite/ingestion/pipeline.py - Enhanced chunk_by_docling_items()

from docling.datamodel.base_models import TableItem, TextItem

async def chunk_by_docling_items_table_aware(
    result: ConversionResult,
    doc_metadata: DocumentMetadata,
    chunk_size: int = 500,
    overlap: int = 50,
    table_context_sentences: int = 2,
) -> list[Chunk]:
    """Enhanced chunking that preserves table integrity.

    Strategy:
        1. Detect TableItem objects from Docling
        2. Keep entire table in single chunk (even if > chunk_size)
        3. Include N sentences before/after table for context
        4. Mark table chunks with metadata (chunk_type="table")
    """
    chunks = []
    current_chunk_words = []
    current_page = 1

    items = list(result.document.iterate_items())
    i = 0

    while i < len(items):
        item, _ = items[i]

        # Extract page number
        if hasattr(item, "prov") and item.prov:
            current_page = item.prov[0].page_no

        # Check if this is a table
        if isinstance(item, TableItem):
            # Flush current text chunk
            if current_chunk_words:
                chunks.append(create_text_chunk(current_chunk_words, current_page, ...))
                current_chunk_words = []

            # Get context before table
            context_before = get_context_before(items, i, sentences=table_context_sentences)

            # Get table content (as markdown)
            table_markdown = item.export_to_markdown()

            # Get context after table
            context_after = get_context_after(items, i, sentences=table_context_sentences)

            # Create table chunk
            table_chunk = Chunk(
                content=f"{context_before}\n\n{table_markdown}\n\n{context_after}",
                page_number=current_page,
                chunk_type="table",  # Special metadata
                source_document=doc_metadata.filename,
                ...
            )
            chunks.append(table_chunk)

            i += 1  # Skip table
            continue

        # Normal text item - add to current chunk
        if isinstance(item, TextItem):
            current_chunk_words.extend(item.text.split())

            # Check if chunk size reached
            if len(current_chunk_words) >= chunk_size:
                chunks.append(create_text_chunk(current_chunk_words, current_page, ...))
                # Keep overlap
                current_chunk_words = current_chunk_words[-overlap:]

        i += 1

    # Flush remaining words
    if current_chunk_words:
        chunks.append(create_text_chunk(current_chunk_words, current_page, ...))

    return chunks


def get_context_before(items: list, table_idx: int, sentences: int = 2) -> str:
    """Extract N sentences before table for context."""
    text_items_before = []
    for i in range(table_idx - 1, -1, -1):
        item, _ = items[i]
        if isinstance(item, TextItem):
            text_items_before.insert(0, item.text)
        if len(text_items_before) >= sentences:
            break

    # Take last N sentences
    full_text = " ".join(text_items_before)
    sentences_list = full_text.split('. ')
    return '. '.join(sentences_list[-sentences:])


def get_context_after(items: list, table_idx: int, sentences: int = 2) -> str:
    """Extract N sentences after table for context."""
    text_items_after = []
    for i in range(table_idx + 1, len(items)):
        item, _ = items[i]
        if isinstance(item, TextItem):
            text_items_after.append(item.text)
        if len(text_items_after) >= sentences:
            break

    # Take first N sentences
    full_text = " ".join(text_items_after)
    sentences_list = full_text.split('. ')
    return '. '.join(sentences_list[:sentences])
```

**Enhanced Search - Table Boost:**

```python
# raglite/retrieval/search.py - Add table boosting

async def search_documents_with_table_boost(
    query: str,
    top_k: int = 5,
    table_boost: float = 1.2,
) -> list[QueryResult]:
    """Search with boosting for table chunks.

    Tables often contain the most precise data (numbers, metrics).
    Boost their scores slightly to prioritize tabular results.
    """
    results = await search_documents(query, top_k=top_k * 2)

    # Apply table boost
    for result in results:
        if result.metadata.get("chunk_type") == "table":
            result.similarity_score *= table_boost

    # Re-sort and return top_k
    results.sort(key=lambda r: r.similarity_score, reverse=True)
    return results[:top_k]
```

**Testing Strategy:**

```python
# tests/integration/test_table_aware_chunking.py

async def test_table_chunks_created():
    """Table-aware chunking should create table chunks."""
    # Ingest page 46 (contains operational performance table)
    metadata = await ingest_document("docs/sample pdf/2025-08 Performance Review CONSO_v2.pdf")

    # Query for table chunks
    qdrant = get_qdrant_client()
    scroll_result = qdrant.scroll(
        collection_name="financial_docs",
        scroll_filter=Filter(
            must=[
                FieldCondition(key="page_number", match=MatchValue(value=46)),
                FieldCondition(key="chunk_type", match=MatchValue(value="table"))
            ]
        ),
        limit=10
    )

    # Should have at least 1 table chunk from page 46
    assert len(scroll_result[0]) > 0

    # Table chunk should contain markdown table syntax
    table_chunk = scroll_result[0][0]
    assert "|" in table_chunk.payload["text"]  # Markdown table delimiter


async def test_table_context_included():
    """Table chunks should include surrounding context."""
    query = "What are the variable costs for Portugal Cement?"
    results = await search_documents(query, top_k=5)

    # Find table result
    table_result = next((r for r in results if "chunk_type" in r.metadata and r.metadata["chunk_type"] == "table"), None)
    assert table_result is not None

    # Should have context before table (e.g., "operational performance")
    assert "operational" in table_result.text.lower() or "performance" in table_result.text.lower()

    # Should have table data
    assert "23.2" in table_result.text  # Variable costs value
```

**Expected Impact:**
- **Tabular query accuracy:** +15-20% (queries asking for table data)
- **Overall retrieval accuracy:** +5-8% (weighted by table query frequency)
- **Context preservation:** Tables include surrounding narrative

---

### 2D: Re-ranking with Cross-Encoder

#### Objective
Add a second-stage re-ranking layer using cross-encoder models to improve precision of top-5 results.

#### Technical Approach

**Two-Stage Retrieval:**

```
Stage 1 (Fast): Vector similarity search
    ↓ Retrieve top 20 candidates (recall-focused)

Stage 2 (Slow): Cross-encoder re-ranking
    ↓ Re-rank to top 5 (precision-focused)
```

**Cross-Encoder Architecture:**

```
Traditional embeddings (bi-encoder):
Query  → Embedding A (1024-dim)
Doc    → Embedding B (1024-dim)
Score  = cosine_similarity(A, B)

Cross-encoder:
Query + Doc → BERT → Classification → Score (0.0-1.0)
```

**Key Difference:**
- Bi-encoder: Query and doc embedded separately (fast, pre-computed)
- Cross-encoder: Query and doc processed together (slow, must compute at query time)

**Implementation:**

```python
# raglite/retrieval/reranking.py

"""Cross-encoder re-ranking for improved precision."""

from sentence_transformers import CrossEncoder
from raglite.shared.models import QueryResult

# Singleton cross-encoder model
_cross_encoder = None

def get_cross_encoder(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
    """Load cross-encoder model (cached)."""
    global _cross_encoder
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder(model_name)
    return _cross_encoder


async def rerank_with_cross_encoder(
    query: str,
    candidates: list[QueryResult],
    top_k: int = 5,
) -> list[QueryResult]:
    """Re-rank search results using cross-encoder.

    Args:
        query: Original query text
        candidates: Candidate results from vector search
        top_k: Number of top results to return after re-ranking

    Returns:
        Re-ranked results (top_k)
    """
    if not candidates:
        return []

    # Prepare input pairs for cross-encoder
    pairs = [[query, candidate.text] for candidate in candidates]

    # Score all pairs
    model = get_cross_encoder()
    scores = model.predict(pairs)

    # Re-rank by cross-encoder scores
    ranked_pairs = sorted(
        zip(scores, candidates),
        key=lambda x: x[0],
        reverse=True
    )

    # Update similarity scores and return top_k
    reranked_results = []
    for score, result in ranked_pairs[:top_k]:
        result.similarity_score = float(score)  # Replace with cross-encoder score
        reranked_results.append(result)

    return reranked_results
```

**Integration:**

```python
# raglite/retrieval/search.py

from raglite.retrieval.reranking import rerank_with_cross_encoder

async def search_documents_with_reranking(
    query: str,
    top_k: int = 5,
    use_reranking: bool = True,
) -> list[QueryResult]:
    """Search with optional cross-encoder re-ranking.

    Args:
        query: Search query
        top_k: Final number of results
        use_reranking: Enable cross-encoder re-ranking
    """
    if use_reranking:
        # Stage 1: Vector search with over-retrieval
        candidates = await search_documents(query, top_k=top_k * 4)

        # Stage 2: Cross-encoder re-ranking
        reranked_results = await rerank_with_cross_encoder(
            query=query,
            candidates=candidates,
            top_k=top_k
        )
        return reranked_results
    else:
        # Single-stage vector search
        return await search_documents(query, top_k=top_k)
```

**Performance Considerations:**

| Metric | Vector Search | + Cross-Encoder | Change |
|--------|---------------|-----------------|---------|
| Candidate retrieval | 25ms | 25ms | - |
| Re-ranking (20 docs) | - | 150ms | +150ms |
| **Total latency** | **25ms** | **175ms** | **+150ms** |
| Precision@5 | ~85% | ~92% | **+7%** |

**Latency Optimization:**

```python
# Reduce re-ranking latency with batching
async def rerank_with_cross_encoder_batched(
    query: str,
    candidates: list[QueryResult],
    top_k: int = 5,
    batch_size: int = 32,  # Process in batches
) -> list[QueryResult]:
    """Batched re-ranking for reduced latency."""
    model = get_cross_encoder()

    all_scores = []
    pairs = [[query, c.text] for c in candidates]

    # Process in batches (GPU acceleration if available)
    for i in range(0, len(pairs), batch_size):
        batch = pairs[i:i + batch_size]
        scores = model.predict(batch, batch_size=batch_size, show_progress_bar=False)
        all_scores.extend(scores)

    # Re-rank
    ranked_pairs = sorted(zip(all_scores, candidates), reverse=True)
    return [result for _, result in ranked_pairs[:top_k]]
```

**Expected Impact:**
- **Precision@5:** +5-7% (better ranking of top results)
- **Overall retrieval accuracy:** +3-5%
- **Latency:** +150ms (acceptable for <10s NFR requirement)

---

### 2E: Query Expansion

#### Objective
Expand user queries with synonyms and related terms to improve recall for queries with ambiguous or varied terminology.

#### Technical Approach

**Strategy:** Use LLM (Claude) to generate query variations

```python
# raglite/retrieval/query_expansion.py

"""Query expansion using LLM-generated variations."""

from anthropic import AsyncAnthropic
from raglite.shared.config import settings

client = AsyncAnthropic(api_key=settings.anthropic_api_key)

async def expand_query_with_llm(query: str) -> list[str]:
    """Generate query variations using Claude.

    Args:
        query: Original user query

    Returns:
        List of query variations (3-5 variations)
    """
    prompt = f"""Generate 3-5 variations of this financial query, using synonyms and related terms:

Original query: "{query}"

Generate variations that:
1. Use financial domain synonyms (e.g., "costs" → "expenses", "EBITDA" → "operating profit")
2. Rephrase with different question structures
3. Expand abbreviations (e.g., "YTD" → "year-to-date")
4. Keep the core meaning identical

Return only the variations, one per line, no explanations.
"""

    response = await client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )

    variations = response.content[0].text.strip().split('\n')
    # Include original query
    return [query] + [v.strip() for v in variations if v.strip()]


async def search_with_query_expansion(
    query: str,
    top_k: int = 5,
    fusion_method: str = "reciprocal_rank",
) -> list[QueryResult]:
    """Search using multiple query variations and fuse results.

    Args:
        query: Original query
        top_k: Final number of results
        fusion_method: How to combine results ("reciprocal_rank" or "max_score")
    """
    # Generate query variations
    variations = await expand_query_with_llm(query)

    # Search with each variation
    all_results = []
    for variation in variations:
        results = await search_documents(variation, top_k=top_k * 2)
        all_results.append(results)

    # Fuse results
    if fusion_method == "reciprocal_rank":
        fused = reciprocal_rank_fusion(all_results, k=60)
    else:
        fused = max_score_fusion(all_results)

    return fused[:top_k]


def reciprocal_rank_fusion(
    result_lists: list[list[QueryResult]],
    k: int = 60,
) -> list[QueryResult]:
    """Fuse multiple result lists using Reciprocal Rank Fusion.

    RRF formula: score(doc) = Σ 1 / (k + rank(doc))
    """
    doc_scores = {}  # {doc_id: cumulative_score}
    doc_map = {}     # {doc_id: QueryResult}

    for results in result_lists:
        for rank, result in enumerate(results, start=1):
            doc_id = f"{result.source_document}_{result.page_number}_{result.chunk_id}"

            # Add reciprocal rank score
            score = 1.0 / (k + rank)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0.0) + score
            doc_map[doc_id] = result

    # Sort by cumulative score
    ranked_ids = sorted(doc_scores.keys(), key=lambda d: doc_scores[d], reverse=True)

    # Return fused results
    fused_results = []
    for doc_id in ranked_ids:
        result = doc_map[doc_id]
        result.similarity_score = doc_scores[doc_id]
        fused_results.append(result)

    return fused_results
```

**Expected Impact:**
- **Recall:** +5-10% (find relevant docs with different terminology)
- **Synonym handling:** Better matching for "costs" vs "expenses", "EBITDA" vs "operating profit"
- **Latency:** +500-800ms (LLM call for query expansion)

**When to Use:**
- Use for complex, multi-faceted queries
- Skip for simple keyword queries (e.g., "page 46")
- Configurable via MCP tool parameter

---

### 2F: Multi-Vector Representations

#### Objective
Store multiple embedding representations per chunk (content, keywords, summary) and search across all to improve retrieval robustness.

#### Technical Approach

**Strategy:** Create 3 vector collections in Qdrant

```
Collection 1: content_vectors (full chunk text embedding)
Collection 2: keyword_vectors (extracted keywords embedding)
Collection 3: summary_vectors (LLM-generated summary embedding)
```

**Implementation:**

```python
# raglite/ingestion/multi_vector.py

"""Multi-vector representations for robust retrieval."""

from raglite.ingestion.pipeline import generate_embeddings
from raglite.shared.models import Chunk
import asyncio

async def extract_keywords_from_chunk(chunk: Chunk) -> str:
    """Extract important keywords from chunk using LLM."""
    # Use Claude to extract key terms
    from anthropic import AsyncAnthropic
    from raglite.shared.config import settings

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model="claude-3-haiku-20240307",  # Fast model for extraction
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": f"Extract 5-10 key financial terms from this text:\n\n{chunk.content[:500]}"
        }]
    )

    return response.content[0].text


async def summarize_chunk(chunk: Chunk) -> str:
    """Generate concise summary of chunk using LLM."""
    from anthropic import AsyncAnthropic
    from raglite.shared.config import settings

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    response = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=150,
        messages=[{
            "role": "user",
            "content": f"Summarize this financial data in 2-3 sentences:\n\n{chunk.content}"
        }]
    )

    return response.content[0].text


async def create_multi_vector_representations(
    chunks: list[Chunk]
) -> dict[str, list[Chunk]]:
    """Create 3 vector representations for each chunk.

    Returns:
        {
            "content": chunks with content embeddings,
            "keywords": chunks with keyword embeddings,
            "summary": chunks with summary embeddings
        }
    """
    # 1. Content embeddings (original)
    content_chunks = await generate_embeddings(chunks)

    # 2. Keyword embeddings
    keyword_chunks = []
    for chunk in chunks:
        keywords = await extract_keywords_from_chunk(chunk)
        keyword_chunk = Chunk(
            content=keywords,  # Embed keywords, not full text
            page_number=chunk.page_number,
            source_document=chunk.source_document,
            chunk_id=chunk.chunk_id + "_keywords",
            ...
        )
        keyword_chunks.append(keyword_chunk)

    keyword_chunks_embedded = await generate_embeddings(keyword_chunks)

    # 3. Summary embeddings
    summary_chunks = []
    for chunk in chunks:
        summary = await summarize_chunk(chunk)
        summary_chunk = Chunk(
            content=summary,  # Embed summary, not full text
            page_number=chunk.page_number,
            source_document=chunk.source_document,
            chunk_id=chunk.chunk_id + "_summary",
            ...
        )
        summary_chunks.append(summary_chunk)

    summary_chunks_embedded = await generate_embeddings(summary_chunks)

    return {
        "content": content_chunks,
        "keywords": keyword_chunks_embedded,
        "summary": summary_chunks_embedded,
    }


# Store in separate Qdrant collections
async def store_multi_vector(multi_vectors: dict[str, list[Chunk]]):
    """Store multi-vector representations in Qdrant."""
    from raglite.ingestion.pipeline import store_vectors_in_qdrant

    await store_vectors_in_qdrant(
        multi_vectors["content"],
        collection_name="financial_docs_content"
    )
    await store_vectors_in_qdrant(
        multi_vectors["keywords"],
        collection_name="financial_docs_keywords"
    )
    await store_vectors_in_qdrant(
        multi_vectors["summary"],
        collection_name="financial_docs_summary"
    )
```

**Multi-Collection Search:**

```python
# raglite/retrieval/multi_vector_search.py

async def search_multi_vector(
    query: str,
    top_k: int = 5,
) -> list[QueryResult]:
    """Search across all vector collections and fuse results."""
    from raglite.retrieval.search import search_documents

    # Search each collection
    content_results = await search_documents(query, top_k=top_k * 2, collection="financial_docs_content")
    keyword_results = await search_documents(query, top_k=top_k * 2, collection="financial_docs_keywords")
    summary_results = await search_documents(query, top_k=top_k * 2, collection="financial_docs_summary")

    # Fuse using reciprocal rank fusion
    fused = reciprocal_rank_fusion([
        content_results,
        keyword_results,
        summary_results
    ])

    return fused[:top_k]
```

**Expected Impact:**
- **Recall:** +10-15% (different representations capture different query types)
- **Robustness:** Better for diverse query styles (keyword, semantic, conceptual)
- **Storage:** 3x vector storage (3 collections)
- **Ingestion time:** 3x slower (must generate 3 embeddings per chunk)

**Recommendation:** Implement ONLY if Phase 2A-2D still doesn't achieve 95% accuracy. This is the most complex enhancement.

---

## Part 3: Implementation Roadmap

### Timeline & Dependencies

```
Story 1.15A: Option C - Original PDF Ingestion (IMMEDIATE)
├── Duration: 1 hour
├── Dependencies: None
├── Deliverable: Original PDF ingested, page numbers corrected
└── Enables: Story 1.15B

    ↓

Story 1.15B: Baseline Validation & Analysis (TEST FUNDAMENTALS FIRST)
├── Duration: 1.5 hours
├── Dependencies: Story 1.15A complete
├── Tasks:
│   ├── Validate ingestion quality (15 min)
│   ├── Manual test queries (30 min)
│   ├── Full accuracy test suite (15 min)
│   ├── Failure pattern analysis (20 min)
│   └── Performance benchmarking (10 min)
├── Deliverables:
│   ├── baseline-accuracy-report.txt
│   ├── baseline-failure-analysis.md
│   └── baseline-performance-benchmarks.txt
└── Decision Gate: Determine if Phase 2 needed

    ↓ DECISION GATE ↓

┌─────────────────────────────────────────────────────────────┐
│ IF Retrieval ≥90% AND Attribution ≥95%:                    │
│   → ✅ EPIC 1 VALIDATED - Skip Phase 2, proceed to Epic 2  │
│                                                             │
│ IF Retrieval 85-89% OR Attribution 93-94%:                 │
│   → ⚠️ Implement Phase 2A only (likely sufficient)         │
│                                                             │
│ IF Retrieval <85% OR Attribution <93%:                     │
│   → ✗ Implement Phase 2A → 2B → 2C sequence                │
└─────────────────────────────────────────────────────────────┘

    ↓ (Only if needed based on decision gate)

Story 2.1: Phase 2A - Hybrid Search
├── Duration: 4-6 hours
├── Dependencies: Epic 1 complete
├── Deliverable: hybrid.py module, +5-10% accuracy
└── Success: 92%+ retrieval accuracy

    ↓

Story 2.2: Phase 2B - Financial Embeddings Evaluation
├── Duration: 6-8 hours
├── Dependencies: Story 2.1 complete
├── Deliverable: Embedding comparison report, decision on model
└── Success: Optimal embedding model selected

    ↓ (If needed)

Story 2.3: Phase 2C - Table-Aware Chunking
├── Duration: 8-10 hours
├── Dependencies: Story 2.2 complete
├── Deliverable: Enhanced chunking with table detection
└── Success: 95%+ accuracy on table queries

    ↓ (If still <95%)

Story 2.4: Phase 2D - Cross-Encoder Re-ranking
├── Duration: 6-8 hours
├── Dependencies: Story 2.3 complete
├── Deliverable: reranking.py module
└── Success: 95%+ retrieval accuracy

    ↓ (If still <95%)

Story 2.5: Phase 2E - Query Expansion (OPTIONAL)
├── Duration: 4-6 hours
├── Dependencies: Story 2.4 complete
├── Deliverable: query_expansion.py module
└── Success: +2-5% recall improvement

    ↓ (Advanced optimization)

Story 2.6: Phase 2F - Multi-Vector (OPTIONAL)
├── Duration: 12-16 hours
├── Dependencies: Story 2.5 complete
├── Deliverable: Multi-vector ingestion + search
└── Success: 98%+ accuracy
```

### Decision Gates

**Gate 1: After Story 1.15A (Option C)**
- ✅ Accuracy ≥90% → Proceed to Epic 2
- ❌ Accuracy <90% → Implement Phase 2A immediately

**Gate 2: After Story 2.1 (Hybrid Search)**
- ✅ Accuracy ≥92% → Evaluate Phase 2B (embeddings)
- ❌ Accuracy <92% → Implement Phase 2C (table-aware chunking)

**Gate 3: After Story 2.2 (Financial Embeddings)**
- ✅ Accuracy ≥95% → STOP, Epic 1 fully validated
- ❌ Accuracy <95% → Continue to Phase 2C

**Gate 4: After Story 2.3 (Table-Aware Chunking)**
- ✅ Accuracy ≥95% → STOP, Epic 1 fully validated
- ❌ Accuracy <95% → Continue to Phase 2D

**Final Gate: After Story 2.4 (Re-ranking)**
- ✅ Accuracy ≥95% → STOP, Epic 1 fully validated
- ❌ Accuracy <95% → Implement Phase 2E + 2F (advanced)

---

## Part 4: Testing & Validation Strategy

### Accuracy Benchmarking

**Ground Truth Test Set:**
- 50 questions across 6 categories
- Pages 46, 47, 77, 108 coverage
- NFR6 target: ≥90% retrieval accuracy
- NFR7 target: ≥95% attribution accuracy

**Continuous Testing:**
```bash
# Run after each phase implementation
uv run python scripts/run-accuracy-tests.py

# Track accuracy trend
echo "$(date),Phase 2A,92.5%" >> docs/accuracy-tracking-log.jsonl
```

**A/B Testing Framework:**

```python
# scripts/ab-test-enhancements.py

"""A/B test different retrieval strategies."""

import asyncio
from scripts.run_accuracy_tests import run_accuracy_validation

async def compare_strategies():
    """Compare different retrieval strategies."""

    strategies = [
        ("Baseline (E5 + Vector Search)", "baseline"),
        ("Hybrid Search", "hybrid"),
        ("Hybrid + FinBERT", "hybrid_finbert"),
        ("Hybrid + FinBERT + Table-Aware", "full_stack"),
    ]

    results = []

    for name, strategy in strategies:
        print(f"\nTesting: {name}")
        # Configure system to use strategy
        configure_retrieval_strategy(strategy)

        # Run accuracy tests
        accuracy = await run_accuracy_validation()
        results.append({
            "strategy": name,
            "retrieval_pct": accuracy.retrieval_pct,
            "attribution_pct": accuracy.attribution_pct,
        })

        print(f"  Retrieval: {accuracy.retrieval_pct:.1f}%")
        print(f"  Attribution: {accuracy.attribution_pct:.1f}%")

    # Print comparison table
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    for r in results:
        print(f"{r['strategy']:40s} | Retrieval: {r['retrieval_pct']:5.1f}% | Attribution: {r['attribution_pct']:5.1f}%")
```

---

## Part 5: Performance & Cost Analysis

### Latency Impact

| Enhancement | Baseline Latency | Additional Latency | Total | Acceptable? |
|-------------|------------------|-------------------|-------|-------------|
| Vector search (baseline) | 25ms | - | 25ms | ✅ |
| + Hybrid search | 25ms | +5-10ms | 35ms | ✅ |
| + Cross-encoder re-ranking | 35ms | +150ms | 185ms | ✅ (< 10s NFR) |
| + Query expansion | 185ms | +500-800ms | 985ms | ✅ (< 10s NFR) |
| + Multi-vector search | 985ms | +50ms | 1035ms | ✅ (< 10s NFR) |

**NFR5 Requirement:** <10s query response time → **ALL enhancements acceptable**

### Cost Analysis (OpenAI Embeddings)

**Scenario:** Replace E5 with OpenAI text-embedding-3-large

**Ingestion Cost:**
```
Chunks per document: ~147 chunks
Avg chunk size: 500 words = ~625 tokens
Total tokens: 147 × 625 = 91,875 tokens
Cost: 91,875 / 1M × $0.13 = $0.012 per document
```

**Query Cost:**
```
Queries per day: 100 (estimated)
Tokens per query: ~50 tokens
Cost: 100 × 50 / 1M × $0.13 = $0.0006 per day
Monthly cost: $0.0006 × 30 = $0.018/month
```

**Total monthly cost (10 docs):** ~$0.12 + $0.018 = **$0.14/month**

**Conclusion:** OpenAI embeddings are **cost-effective** even for high query volumes.

---

## Part 6: Rollback & Risk Mitigation

### Rollback Strategies

**If Option C ingestion fails:**
- Fallback to Option B (auto-detect page offset from filename)
- Use split PDFs with corrected page numbering
- Estimated recovery time: 30 minutes

**If Phase 2 enhancements degrade accuracy:**
- Each enhancement is modular (can be disabled independently)
- Configuration flags in `raglite/shared/config.py`:
  ```python
  class Settings(BaseSettings):
      use_hybrid_search: bool = True
      use_reranking: bool = True
      use_query_expansion: bool = False
      ...
  ```

**If latency exceeds NFR5 (<10s):**
- Disable most expensive enhancements first:
  1. Query expansion (+800ms)
  2. Multi-vector search (+50ms)
  3. Cross-encoder re-ranking (+150ms)

---

## Part 7: Success Metrics & KPIs

### Epic 1 Success Criteria (FINAL)

| Metric | Current | Target | After Option C | After Phase 2 |
|--------|---------|--------|---------------|---------------|
| **Retrieval Accuracy** | 0% (bug) | ≥90% | **90-92%** | **95-98%** |
| **Attribution Accuracy** | 0% (bug) | ≥95% | **95-97%** | **98-99%** |
| **Query Latency (p95)** | 53ms | <10s | **50-100ms** | **500ms-1s** |
| **F1 Score** | N/A | ≥0.90 | **0.91** | **0.96** |

### Definition of Done

**Epic 1 VALIDATED when:**
- ✅ NFR6: ≥90% retrieval accuracy on 50-query test set
- ✅ NFR7: ≥95% attribution accuracy on 50-query test set
- ✅ NFR5: <10s query response time (p95)
- ✅ All ground truth questions return correct page citations
- ✅ Accuracy tracking log shows stable trend (no regressions)

---

## Conclusion

This comprehensive plan provides a clear roadmap from immediate bug fix (Option C) to advanced RAG enhancements (Phase 2A-2F).

**Immediate Next Steps:**
1. **Execute Story 1.15A** (Option C - original PDF ingestion) - **1 hour**
2. **Validate Epic 1 success** (90%+ accuracy expected)
3. **Decision:** If accuracy ≥90%, Epic 1 COMPLETE. If <90%, proceed to Phase 2A.

**Phase 2 Strategy:**
- Implement enhancements **incrementally**
- **Test after each enhancement** (A/B comparison)
- **STOP when 95% accuracy reached** (don't over-engineer)

**Expected Outcome:**
- **Baseline (Option C):** 90-92% accuracy
- **Phase 2A+2B+2C:** 95-97% accuracy (likely sufficient)
- **Phase 2D+2E+2F:** 98%+ accuracy (if needed)

---

**Document Status:** COMPLETE
**Ready for:** User approval + Story 1.15A execution
